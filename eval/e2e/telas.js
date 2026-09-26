// E2E das telas do Placar: gera os três artefatos com o servidor coppezip-placar e abre cada um no navegador para
// conferir que renderizam, que TODO número mostrado traz fonte e que o preço de carbono recalcula na hora.
// Usa o Playwright que já vem com o LibreChat e o Chromium do sistema (não baixa navegador).
//
// Rodar: node eval/e2e/telas.js
const { execFileSync } = require('child_process');
const path = require('path');
const { chromium } = require('playwright');

const RAIZ = path.resolve(__dirname, '..', '..');
const NAVEGADOR = '/usr/bin/chromium-browser';
const PASTA = path.join(RAIZ, '.runtime', 'relatorios');

const GERAR = `
import importlib.util, json, os
spec = importlib.util.spec_from_file_location("placar_server", os.path.join(${JSON.stringify(RAIZ)}, "proper_mcps", "placar", "server.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(json.dumps({"ranking": m.tela_ranking("escopo1_2")["tela"], "radar": m.tela_radar()["tela"],
                  "carbono": m.tela_carbono(150.0)["tela"]}))
`;

const falhas = [];
const conferir = (ok, oque) => { console.log(`${ok ? '  ok  ' : '  FALHOU '} ${oque}`); if (!ok) falhas.push(oque); };

(async () => {
  const telas = JSON.parse(execFileSync(path.join(RAIZ, '.runtime', 'venv', 'bin', 'python'), ['-c', GERAR],
    { encoding: 'utf8' }).trim().split('\n').pop());
  const navegador = await chromium.launch({ executablePath: NAVEGADOR });
  const pagina = await navegador.newPage({ viewport: { width: 1000, height: 900 } });
  const abrir = (t) => pagina.goto('file://' + path.join(PASTA, path.basename(telas[t])));

  // ---- ranking: uma barra por empresa, valor visível e fonte em cada linha da tabela
  await abrir('ranking');
  const barras = await pagina.locator('.barra').count();
  conferir(barras > 0, `ranking: ${barras} barras desenhadas`);
  conferir(await pagina.locator('.val').count() === barras, 'ranking: valor escrito em cada barra');
  const fontes = await pagina.locator('tbody tr td.f').allTextContents();
  conferir(fontes.length === barras && fontes.every(f => /\.pdf p\.\d/.test(f)),
    'ranking: toda linha da tabela cita documento e página');
  conferir(await pagina.evaluate(() => document.body.scrollWidth <= window.innerWidth),
    'ranking: sem rolagem horizontal');

  // ---- radar: cada alerta com severidade escrita e as duas evidências
  await abrir('radar');
  const alertas = await pagina.locator('.alerta').count();
  conferir(alertas > 0, `radar: ${alertas} alertas`);
  conferir(await pagina.locator('.sev').count() === alertas, 'radar: severidade escrita em todo alerta');
  const evidencias = await pagina.locator('.alerta .ev').allTextContents();
  conferir(evidencias.every(e => e.includes('Evidência no relatório') && e.includes('Evidência na base')),
    'radar: as duas evidências em todo alerta');

  // ---- carbono: a barra de preço recalcula a exposição (dobrar o preço dobra o R$ da fórmula)
  await abrir('carbono');
  const primeiraExposicao = async () => parseFloat(
    (await pagina.locator('tbody#linhas tr td.n').nth(1).textContent()).replace(/\./g, '').replace(',', '.'));
  await pagina.locator('#preco').fill('100');
  const a100 = await primeiraExposicao();
  await pagina.locator('#preco').fill('200');
  const a200 = await primeiraExposicao();
  conferir(Math.abs(a200 - 2 * a100) < 0.2, `carbono: R$ 100/t -> ${a100} mi, R$ 200/t -> ${a200} mi`);
  conferir((await pagina.locator('#vp').textContent()).includes('200'), 'carbono: o preço escolhido aparece na tela');
  const contas = await pagina.locator('tbody#linhas tr td.f').allTextContents();
  conferir(contas.length > 0 && contas.every(c => /tCO2e × R\$/.test(c) && /\.pdf p\.\d/.test(c)),
    'carbono: fórmula e fonte em toda linha');

  await navegador.close();
  console.log(falhas.length ? `\n${falhas.length} falha(s)` : '\ntudo certo');
  process.exit(falhas.length ? 1 : 0);
})();
