// Quinto passe de pickup, sem chamar o modelo. Duas correções nas telas do produto:
//   09_painel -> a nota metodológica (parágrafo denso) ficava em cima dos cartões e a rolagem não
//                acontecia (o gravador antigo rolava a JANELA, mas quem rola é um contêiner interno).
//                Aqui a nota é recolhida e a rolagem usa o contêiner certo.
//   11_busca  -> o realce do primeiro resultado ainda era o azul antigo (#8ab4f8), que briga com o
//                roxo da marca; passa a usar o mesmo realce das outras cenas.
//
// Rodar: node pickup5.js

const { chromium } = require('/impa/home/a/al.richard.viana/projects/clean-hack/coppezip/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const C = require('./comum');

const BUSCA = 'meta de redução de emissões da Cemig';
const relato = { fps: C.FPS, cenas: [], textos: {} };
const G = C.criarGravador(relato);

// acha o maior contêiner rolável da página e marca para o gravador
const MARCAR_MAIOR_ROLAGEM = `(() => {
  let melhor = null;
  for (const el of document.querySelectorAll('div,main,section')) {
    const s = getComputedStyle(el);
    if (s.overflowY !== 'auto' && s.overflowY !== 'scroll') continue;
    if (el.scrollHeight <= el.clientHeight + 40) continue;
    if (!melhor || el.clientHeight > melhor.clientHeight) melhor = el;
  }
  if (!melhor) return { ok: false };
  melhor.setAttribute('data-demo-rolagem', '1');
  return { ok: true, altura: melhor.scrollHeight, visivel: melhor.clientHeight };
})()`;

const digitar = async (pag, seletor, texto, porQuadro) => {
  await pag.click(seletor);
  for (let i = 0; i < texto.length; i += porQuadro) {
    await pag.type(seletor, texto.slice(i, i + porQuadro), { delay: 0 });
    await G.quadro(pag);
  }
};

(async () => {
  const { nav, ctx } = await C.abrirNavegador(chromium);
  const pag = await ctx.newPage();
  await C.entrar(pag);

  // =========================================================================
  // CENA 09 — painel de dados: os indicadores do ano, em cartões
  // =========================================================================
  G.abrirCena('09_painel');
  try {
    await pag.goto(`${C.BASE}/painel`, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await pag.waitForSelector('section[aria-label="Indicadores"] button', { timeout: 90000 });
    await pag.waitForTimeout(2600);
    // recolhe a nota metodológica: é ela que empurra os cartões para baixo
    const recolheu = await pag.evaluate(() => {
      const alvos = [...document.querySelectorAll('button,summary,[role="button"]')];
      const b = alvos.find((e) => /Indicadores financeiros anuais/i.test(e.textContent || ''));
      if (!b) return { ok: false, amostra: alvos.slice(0, 6).map((e) => (e.textContent || '').slice(0, 40)) };
      const aberto = b.getAttribute('aria-expanded');
      b.click();
      return { ok: true, aberto, tag: b.tagName };
    });
    console.log('nota metodológica:', JSON.stringify(recolheu).slice(0, 200));
    await pag.waitForTimeout(1400);
    await G.cursor(pag, false);
    await G.gravarQuadros(pag, 46); // 1,8s nos cartões do ano
    G.marcar('painel_visao');
    const rol = await pag.evaluate(MARCAR_MAIOR_ROLAGEM);
    console.log('contêiner de rolagem do painel:', JSON.stringify(rol));
    if (rol.ok) await G.rolarGravando(pag, 10, 66); // desce até os gráficos
    await G.gravarQuadros(pag, 34);
  } catch (e) {
    console.log('erro na cena do painel:', e.message);
  }
  G.fecharCena();

  // =========================================================================
  // CENA 11 — busca semântica: documento, página e similaridade
  // =========================================================================
  G.abrirCena('11_busca');
  try {
    await pag.goto(`${C.BASE}/busca`, { waitUntil: 'domcontentloaded', timeout: 90000 });
    const sel = 'input[placeholder^="Em que página está isso?"]';
    await pag.waitForSelector(sel, { timeout: 60000 });
    await pag.waitForFunction(() => /documentos indexados/.test(document.body.innerText), null, { timeout: 60000 })
      .catch(() => {});
    await pag.waitForTimeout(1200);
    await G.cursor(pag, false);
    await G.gravarQuadros(pag, 22);
    await digitar(pag, sel, BUSCA, 3);
    await G.gravarQuadros(pag, 10);
    await G.clicarEm(pag, pag.getByRole('button', { name: 'Buscar' }));
    G.marcar('buscou');
    await pag.waitForSelector('.rounded-lg.border.border-border-medium.p-4', { timeout: 60000 });
    await pag.waitForTimeout(1200);
    await G.cursor(pag, false);
    G.marcar('resultados');
    await G.gravarQuadros(pag, 40);
    const primeiro = await pag.evaluate(([borda, fundo]) => {
      const c = document.querySelector('.rounded-lg.border.border-border-medium.p-4');
      if (!c) return '';
      c.style.cssText += `;outline:2px solid ${borda};outline-offset:2px;border-radius:10px;background:${fundo}`;
      c.scrollIntoView({ block: 'center' });
      return c.innerText.replace(/\s+/g, ' ').slice(0, 240);
    }, [C.REALCE_BORDA, C.REALCE_FUNDO]);
    relato.textos.busca_primeiro = primeiro;
    console.log('1º resultado:', primeiro.slice(0, 160));
    await pag.waitForTimeout(400);
    await G.gravarQuadros(pag, 48);
  } catch (e) {
    console.log('erro na cena da busca:', e.message);
  }
  G.fecharCena();

  fs.writeFileSync(path.join(C.T, 'relato_pickup5.json'), JSON.stringify(relato, null, 1));
  console.log(`\nrelato em ${path.join(C.T, 'relato_pickup5.json')}`);
  await ctx.close();
  await nav.close();
})().catch((e) => { console.error('ERRO:', e.stack); process.exit(1); });
