const express = require('express');
const { Readable } = require('stream');
const { logger } = require('@librechat/data-schemas');
const requireJwtAuth = require('~/server/middleware/requireJwtAuth');

const router = express.Router();
router.use(requireJwtAuth);

// Proxy para proper_mcps/docs/busca.py, que o iniciar.sh sobe em 127.0.0.1:BUSCA_PORTA (.env).
const ROTAS = new Set(['resumo', 'buscar', 'pagina', 'imagem', 'pdf', 'timeline', 'timeline_empresas']);

router.get('/:rota', async (req, res) => {
  const base = `http://127.0.0.1:${process.env.BUSCA_PORTA}`;
  if (!ROTAS.has(req.params.rota)) {
    return res.status(404).json({ message: 'rota inexistente' });
  }
  // empresa/ano podem repetir (busca.py le com parse_qs); URLSearchParams(objeto) so aceita um valor por chave
  const params = new URLSearchParams();
  for (const [chave, valor] of Object.entries(req.query)) {
    for (const v of Array.isArray(valor) ? valor : [valor]) {
      params.append(chave, String(v));
    }
  }
  const query = params.toString();
  const url = `${base}/${req.params.rota}${query ? `?${query}` : ''}`;
  try {
    const resposta = await fetch(url);
    res.status(resposta.status);
    res.set('Content-Type', resposta.headers.get('content-type') || 'application/octet-stream');
    if (!resposta.body) {
      return res.end();
    }
    Readable.fromWeb(resposta.body).pipe(res);
  } catch (error) {
    logger.error('[busca] Erro chamando o servico de busca', error);
    res.status(502).json({ message: `servico de busca indisponivel (${base}): ${error.message}` });
  }
});

module.exports = router;
