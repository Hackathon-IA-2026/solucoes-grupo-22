const fs = require('fs');
const path = require('path');
const express = require('express');
const { logger } = require('@librechat/data-schemas');
const requireJwtAuth = require('~/server/middleware/requireJwtAuth');

const router = express.Router();
router.use(requireJwtAuth);

// data/painel.json, gerado por data/exportar_painel.py e relido a cada acesso (não precisa reiniciar).
const PAINEL = path.resolve(__dirname, '../../../data/painel.json');

router.get('/dados', async (req, res) => {
  try {
    const conteudo = await fs.promises.readFile(PAINEL, 'utf8');
    res.status(200).type('application/json').send(conteudo);
  } catch (error) {
    logger.error('[painel] Erro lendo painel.json', error);
    const status = error.code === 'ENOENT' ? 404 : 500;
    const dica = error.code === 'ENOENT' ? '; rode data/exportar_painel.py' : '';
    res.status(status).json({ message: `não consegui ler data/painel.json${dica}` });
  }
});

module.exports = router;
