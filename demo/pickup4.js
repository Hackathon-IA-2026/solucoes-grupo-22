// Quarto passe de pickup, sem chamar o modelo. Corrige o único defeito grave que restava:
// o relatório em PDF aparecia CORTADO na direita. A causa não era o zoom: era a régua de
// miniaturas do visualizador, que come ~430 px CSS. Com ela recolhida (clique no hambúrguer,
// CSS 42,88), a folha de 1104 px cabe inteira nos 1440 px da tela, em 100% de zoom — nítida.
//
// Duas cenas, para que o recolhimento aconteça FORA de cena (no corte entre elas):
//   07b_pdf    -> o cartão do entregável, o clique, e o painel entrando
//   07c_folhas -> a capa inteira e as folhas passando
//
// Rodar: node pickup4.js

const { chromium } = require('/impa/home/a/al.richard.viana/projects/clean-hack/coppezip/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const C = require('./comum');

const HAMBURGUER = { x: 42, y: 88 };  // recolhe a régua de miniaturas
const MENOS = { x: 815, y: 88 };      // o primeiro clique só dá foco ao visualizador
const relato = { fps: C.FPS, cenas: [], textos: {} };
const G = C.criarGravador(relato);

(async () => {
  const { nav, ctx } = await C.abrirNavegador(chromium);
  const pag = await ctx.newPage();
  await C.entrar(pag);

  const item = pag.locator('a,[data-testid^="convo-item"]').filter({ hasText: /Cemig, Copel/i }).first();
  if (!(await item.count())) {
    console.error('ABORTA: a conversa da comparação não está na barra lateral.');
    process.exit(3);
  }
  await item.click();
  await pag.waitForSelector('.agent-turn', { timeout: 60000 });
  await pag.waitForTimeout(2500);
  const parar = pag.locator('[data-testid="stop-button"]').first();
  if (await parar.count()) {
    console.log('havia geração em curso: parando');
    await parar.click().catch(() => {});
    await pag.waitForTimeout(1500);
  }
  await pag.goto(pag.url(), { waitUntil: 'domcontentloaded', timeout: 60000 }); // tela parada
  await pag.waitForSelector('.agent-turn', { timeout: 60000 });
  await pag.waitForTimeout(4000);
  await pag.evaluate(C.MARCAR_ROLAGEM);
  await pag.evaluate(() => {
    const el = document.querySelector('[data-demo-rolagem]');
    if (el) el.scrollTop = el.scrollHeight;
  });
  await pag.waitForTimeout(2000);
  await G.cursor(pag, false);

  // =========================================================================
  // CENA 07b — o cartão do entregável e o painel do artefato entrando
  // =========================================================================
  let cartao = pag.locator('button').filter({ hasText: /\.pdf/i }).first();
  if (!(await cartao.count())) cartao = pag.locator('button').filter({ hasText: /Clique para abrir/i }).first();
  if (!(await cartao.count())) {
    console.error('ABORTA: não achei o cartão do artefato.');
    await pag.screenshot({ path: path.join(C.T, 'falha_artefato4.png') });
    process.exit(3);
  }
  await cartao.scrollIntoViewIfNeeded();
  await pag.waitForTimeout(700);

  G.abrirCena('07b_pdf');
  await G.gravarQuadros(pag, 22);
  G.marcar('cartao_na_tela');
  await G.clicarEm(pag, cartao);
  await G.gravar(pag, 2400); // o painel desliza e o visualizador carrega
  await G.cursor(pag, false);
  await G.gravarQuadros(pag, 10);
  G.fecharCena();

  const temIframe = (await pag.locator('iframe[title]').count()) > 0;
  console.log('iframe do PDF:', temIframe);
  if (!temIframe) { console.error('ABORTA: o visualizador não abriu.'); process.exit(3); }

  // ---- fora de cena: recolhe as miniaturas para a folha caber inteira
  await pag.waitForTimeout(1200);
  await pag.mouse.click(HAMBURGUER.x, HAMBURGUER.y);
  await pag.waitForTimeout(1600);
  await pag.mouse.click(MENOS.x, MENOS.y); // apenas dá foco ao visualizador (mantém 100%)
  await pag.waitForTimeout(1600);
  await pag.mouse.move(-60, -60);
  await pag.waitForTimeout(600);
  await pag.screenshot({ path: path.join(C.T, 'conf_07c.png') }); // para conferência visual

  // =========================================================================
  // CENA 07c — a folha inteira e as páginas passando
  // =========================================================================
  G.abrirCena('07c_folhas');
  await G.gravarQuadros(pag, 50); // 2s na capa inteira
  G.marcar('capa');
  await pag.mouse.move(C.CSS.width / 2, C.CSS.height / 2);
  for (let i = 0; i < 132; i++) {
    await pag.mouse.wheel(0, 34);
    await G.quadro(pag);
  }
  G.marcar('folheado');
  await pag.mouse.move(-60, -60);
  await G.gravarQuadros(pag, 34);
  G.fecharCena();
  await pag.screenshot({ path: path.join(C.T, 'conf_07c_fim.png') });

  fs.writeFileSync(path.join(C.T, 'relato_pickup4.json'), JSON.stringify(relato, null, 1));
  console.log(`\nrelato em ${path.join(C.T, 'relato_pickup4.json')}`);
  await ctx.close();
  await nav.close();
})().catch((e) => { console.error('ERRO:', e.stack); process.exit(1); });
