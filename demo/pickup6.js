// Sexto passe de pickup, sem chamar o modelo. A cartela promete "sete consultas às bases", mas a
// cena mostrava só duas linhas recolhidas ("4 ferramentas usadas" / "3 ferramentas usadas") numa
// tela quase vazia. Aqui as duas linhas são ABERTAS, para a plateia ver as consultas nomeadas.
//
// Rodar: node pickup6.js

const { chromium } = require('/impa/home/a/al.richard.viana/projects/clean-hack/coppezip/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const C = require('./comum');

const relato = { fps: C.FPS, cenas: [], textos: {} };
const G = C.criarGravador(relato);

(async () => {
  const { nav, ctx } = await C.abrirNavegador(chromium);
  const pag = await ctx.newPage();
  await C.entrar(pag);

  const item = pag.locator('a,[data-testid^="convo-item"]').filter({ hasText: /Cemig, Copel/i }).first();
  await item.click();
  await pag.waitForSelector('.agent-turn', { timeout: 60000 });
  await pag.waitForTimeout(2500);
  const parar = pag.locator('[data-testid="stop-button"]').first();
  if (await parar.count()) { await parar.click().catch(() => {}); await pag.waitForTimeout(1500); }
  await pag.goto(pag.url(), { waitUntil: 'domcontentloaded', timeout: 60000 });
  await pag.waitForSelector('.agent-turn', { timeout: 60000 });
  await pag.waitForTimeout(4000);
  await pag.evaluate(C.MARCAR_ROLAGEM);
  await pag.evaluate(() => {
    const t = document.querySelectorAll('.agent-turn')[0];
    if (t) t.setAttribute('data-demo-resposta', '1');
    const el = document.querySelector('[data-demo-rolagem]');
    if (el) el.scrollTop = 0;
  });
  await pag.waitForTimeout(1200);
  await G.cursor(pag, false);

  // abre as duas linhas de ferramentas do primeiro turno
  const abriu = await pag.evaluate(() => {
    const botoes = [...document.querySelectorAll('[data-demo-resposta] button')]
      .filter((b) => /ferramentas? usadas?/i.test(b.textContent || ''));
    botoes.forEach((b) => b.click());
    return botoes.map((b) => (b.textContent || '').replace(/\s+/g, ' ').trim());
  });
  console.log('linhas abertas:', JSON.stringify(abriu));
  await pag.waitForTimeout(1600);
  const nomes = await pag.evaluate(() => {
    const t = document.querySelector('[data-demo-resposta]');
    return (t ? t.innerText : '').replace(/\s+/g, ' ').slice(0, 900);
  });
  relato.textos.ferramentas = nomes;
  console.log('texto do turno:', nomes.slice(0, 600));
  await pag.screenshot({ path: path.join(C.T, 'conf_03b.png') });

  G.abrirCena('03b_ferramentas');
  await G.gravarQuadros(pag, 60);
  G.marcar('lista_aberta');
  await G.rolarGravando(pag, 6, 40);
  await G.gravarQuadros(pag, 40);
  G.fecharCena();

  fs.writeFileSync(path.join(C.T, 'relato_pickup6.json'), JSON.stringify(relato, null, 1));
  console.log(`\nrelato em ${path.join(C.T, 'relato_pickup6.json')}`);
  await ctx.close();
  await nav.close();
})().catch((e) => { console.error('ERRO:', e.stack); process.exit(1); });
