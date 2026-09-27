// Terceiro passe de pickup, sem chamar o modelo:
//   01_abertura -> regrava a tela inicial SEM o ponto do ponteiro falso parado no vazio
//   07b_pdf     -> regrava o clímax com o visualizador em "página inteira" (#view=Fit): a 100% o
//                  texto do relatório saía cortado na direita, o que parecia defeito em projeção
//
// Rodar: node pickup3.js

const { chromium } = require('/impa/home/a/al.richard.viana/projects/clean-hack/coppezip/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const C = require('./comum');

const ROTULO = 'EnergyNexus Analista (Claude)';
const relato = { fps: C.FPS, cenas: [], textos: {} };
const G = C.criarGravador(relato);

(async () => {
  const { nav, ctx } = await C.abrirNavegador(chromium);
  const pag = await ctx.newPage();
  await C.entrar(pag);

  // =========================================================================
  // CENA 01 — a tela inicial com o perfil do Claude já escolhido (escolha fora de cena)
  // =========================================================================
  await pag.evaluate(() => {
    for (const k of Object.keys(localStorage)) {
      if (/^lastConversationSetup|^lastSelectedSpec|^lastModel/.test(k)) localStorage.removeItem(k);
    }
  });
  await pag.goto(`${C.BASE}/c/new`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await pag.waitForSelector('#prompt-textarea', { timeout: 60000 });
  await pag.waitForTimeout(2500);
  await pag.click('[data-testid="model-selector-button"]');
  await pag.waitForTimeout(1000);
  await pag.getByText(ROTULO, { exact: true }).last().click({ timeout: 15000 });
  await pag.waitForTimeout(2500);
  const perfil = await pag.evaluate(() => JSON.parse(localStorage.getItem('lastConversationSetup_0') || '{}'));
  console.log(`perfil: endpoint=${perfil.endpoint} model=${perfil.model}`);
  if (perfil.endpoint !== 'bedrock' || !/claude/i.test(perfil.model || '')) {
    console.error('ABORTA: a conversa não ficou no Claude.');
    process.exit(3);
  }
  relato.textos.modelo = perfil.model;
  // volta para uma conversa nova, já com o perfil aplicado, e deixa o ponteiro fora da tela
  await pag.goto(`${C.BASE}/c/new`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await pag.waitForSelector('#prompt-textarea', { timeout: 60000 });
  await pag.waitForTimeout(3000);
  await pag.mouse.move(-50, -50);
  await G.cursor(pag, false);

  G.abrirCena('01_abertura');
  await G.gravarQuadros(pag, 40); // 1,6s na tela inicial
  G.fecharCena();

  // =========================================================================
  // CENA 07b — O CLÍMAX: o relatório em PDF, página inteira, passando as folhas
  // =========================================================================
  const item = pag.locator('a,[data-testid^="convo-item"]').filter({ hasText: /Cemig, Copel/i }).first();
  if (!(await item.count())) {
    console.error('ABORTA: a conversa da comparação não está na barra lateral.');
    process.exit(3);
  }
  await item.click();
  await pag.waitForSelector('.agent-turn', { timeout: 60000 });
  await pag.waitForTimeout(3500);
  await pag.evaluate(C.MARCAR_ROLAGEM);
  await pag.evaluate(() => {
    const el = document.querySelector('[data-demo-rolagem]');
    if (el) el.scrollTop = el.scrollHeight;
  });
  await pag.waitForTimeout(1800);

  G.abrirCena('07b_pdf');
  let cartao = pag.locator('button').filter({ hasText: /\.pdf/i }).first();
  if (!(await cartao.count())) cartao = pag.locator('button').filter({ hasText: /Clique para abrir/i }).first();
  let pdfOk = false;
  if (await cartao.count()) {
    await cartao.scrollIntoViewIfNeeded();
    await pag.waitForTimeout(700);
    await G.gravarQuadros(pag, 20);
    G.marcar('cartao_na_tela');
    await G.clicarEm(pag, cartao);
    await G.gravar(pag, 2200); // o painel entra deslizando
    // o visualizador do Chromium abre em 100% e corta a página na direita; #view=Fit mostra a
    // folha inteira, que é o que interessa aqui (é um documento pronto, não um trecho de texto)
    const ajustou = await pag.evaluate(() => {
      const q = document.querySelector('iframe[title]');
      if (!q) return false;
      const base = q.src.split('#')[0];
      q.src = `${base}#view=Fit&toolbar=1`;
      return true;
    });
    console.log('ajuste de zoom do visualizador:', ajustou);
    await pag.waitForTimeout(3200); // recarrega e renderiza a capa
    pdfOk = (await pag.locator('iframe[title]').count()) > 0;
    await G.cursor(pag, false);
    G.marcar('capa');
    await G.gravarQuadros(pag, 55); // 2,2s na capa do relatório
    // passa as folhas: com a página inteira na tela, cada rolagem entrega uma folha completa
    await pag.mouse.move(C.CSS.width / 2, C.CSS.height / 2);
    for (let i = 0; i < 130; i++) {
      await pag.mouse.wheel(0, 22);
      await G.quadro(pag);
    }
    G.marcar('folheado');
    await G.gravarQuadros(pag, 30);
  } else {
    console.log('não achei o cartão do artefato');
    await pag.screenshot({ path: path.join(C.T, 'falha_artefato3.png') });
  }
  relato.textos.pdf_ok = pdfOk;
  G.fecharCena();

  fs.writeFileSync(path.join(C.T, 'relato_pickup3.json'), JSON.stringify(relato, null, 1));
  console.log(`\nrelato em ${path.join(C.T, 'relato_pickup3.json')}`);
  await ctx.close();
  await nav.close();
})().catch((e) => { console.error('ERRO:', e.stack); process.exit(1); });
