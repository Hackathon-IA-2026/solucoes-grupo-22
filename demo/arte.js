// Gera a arte da demo (cartelas e selos) em PNG, renderizando HTML/CSS no Chromium.
//
// Por que assim e não com drawtext do ffmpeg: aqui dá para usar a tipografia do próprio produto
// (Inter, embutida em base64), gradientes, cantos arredondados, sombras e espaçamento de letras —
// o que faz a arte parecer parte do EnergyNexus e não uma legenda colada por cima.
//
// Cartelas: 3840x2160 (2x) para o ffmpeg poder dar um leve zoom sem perder nitidez.
// Selos: fundo transparente (omitBackground), sobrepostos no vídeo com overlay.
//
// Rodar: node arte.js

const { chromium } = require('/impa/home/a/al.richard.viana/projects/clean-hack/coppezip/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const CHROME = '/local/al.richard.viana/playwright/chromium-1194/chrome-linux/chrome';
const REPO = '/impa/home/a/al.richard.viana/projects/clean-hack/coppezip';
const T = process.env.DEMO_DIR || __dirname;
const OUT = path.join(T, 'arte');

const b64 = (p) => fs.readFileSync(p).toString('base64');
const FONTE = {
  regular: b64(`${REPO}/client/public/fonts/Inter-Regular.woff2`),
  semi: b64(`${REPO}/client/public/fonts/Inter-SemiBold.woff2`),
  bold: b64(`${REPO}/client/public/fonts/Inter-Bold.woff2`),
};
const LOGO = b64(`${REPO}/client/public/assets/energynexus.png`);

// ---------------------------------------------------------------- estilo comum
const BASE_CSS = `
@font-face{font-family:Inter;font-weight:400;src:url(data:font/woff2;base64,${FONTE.regular}) format('woff2')}
@font-face{font-family:Inter;font-weight:600;src:url(data:font/woff2;base64,${FONTE.semi}) format('woff2')}
@font-face{font-family:Inter;font-weight:700;src:url(data:font/woff2;base64,${FONTE.bold}) format('woff2')}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;font-family:Inter,sans-serif;-webkit-font-smoothing:antialiased}
body{background:transparent;overflow:hidden}

/* fundo das cartelas: roxo do produto, escuro, com brilho difuso e uma malha discreta */
.cartela{
  position:relative;width:1920px;height:1080px;
  background:
    radial-gradient(1200px 760px at 82% 8%, rgba(139,92,246,.24), transparent 62%),
    radial-gradient(900px 620px at 8% 96%, rgba(109,40,217,.20), transparent 60%),
    linear-gradient(145deg,#0a0713 0%,#120d22 46%,#1a0f33 100%);
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  overflow:hidden;
}
.cartela::after{ /* linhas finas na diagonal, quase invisíveis: dão textura sem sujar */
  content:'';position:absolute;inset:0;opacity:.055;
  background:repeating-linear-gradient(115deg,#fff 0 1px,transparent 1px 84px);
}
.vinheta{position:absolute;inset:0;box-shadow:inset 0 0 300px 90px rgba(0,0,0,.55)}

.barra{width:74px;height:5px;border-radius:3px;background:linear-gradient(90deg,#a78bfa,#6d28d9)}
.rotulo{
  font-weight:600;font-size:23px;letter-spacing:.30em;text-transform:uppercase;
  color:#c4b5fd;
}
.titulo{
  font-weight:700;font-size:76px;line-height:1.14;letter-spacing:-.022em;color:#fff;
  max-width:1420px;text-align:center;text-wrap:balance;
}
.sub{
  font-weight:400;font-size:33px;line-height:1.45;color:#a6a0c4;
  max-width:1180px;text-align:center;
}
.z{position:relative;z-index:2;display:flex;flex-direction:column;align-items:center}

/* selo: placa translúcida com barra de destaque, para apontar um número na tela */
.selo{
  display:inline-flex;align-items:stretch;border-radius:16px;overflow:hidden;
  background:rgba(12,9,20,.90);
  box-shadow:0 26px 60px rgba(0,0,0,.62),0 0 0 1px rgba(167,139,250,.28) inset;
  backdrop-filter:blur(8px);
}
.selo .fio{width:6px;background:linear-gradient(180deg,#a78bfa,#6d28d9)}
.selo .corpo{padding:20px 30px 22px}
.selo .topo{font-weight:600;font-size:19px;letter-spacing:.18em;text-transform:uppercase;color:#c4b5fd;margin-bottom:8px}
.selo .linha{font-weight:600;font-size:34px;color:#fff;letter-spacing:-.01em;white-space:nowrap}
.selo .pe{font-weight:400;font-size:22px;color:#9b95bb;margin-top:7px;white-space:nowrap}
`;

// --------------------------------------------------------------- as cartelas
const ICONE = `<div style="width:150px;height:150px;border-radius:34px;background:#fff;
  box-shadow:0 30px 70px rgba(0,0,0,.55),0 0 0 1px rgba(255,255,255,.10);
  display:flex;align-items:center;justify-content:center;overflow:hidden">
  <img src="data:image/png;base64,${LOGO}" style="width:150px;height:150px;object-fit:cover"></div>`;

function cartelaAbertura() {
  return `<div class="cartela"><div class="vinheta"></div><div class="z">
    ${ICONE}
    <div style="height:46px"></div>
    <div style="font-weight:700;font-size:104px;letter-spacing:-.03em;color:#fff">EnergyNexus</div>
    <div style="height:18px"></div>
    <div class="sub" style="font-size:36px;color:#b9b2da">Inteligência sobre o setor elétrico brasileiro</div>
    <div style="height:54px"></div>
    <div style="width:520px;height:1px;background:linear-gradient(90deg,transparent,rgba(167,139,250,.55),transparent)"></div>
    <div style="height:34px"></div>
    <div style="display:flex;gap:56px;align-items:baseline">
      ${[['13', 'bases oficiais'], ['2.497', 'documentos'], ['79.247', 'páginas indexadas'], ['19', 'ferramentas de IA']]
        .map(([n, r]) => `<div style="text-align:center">
            <div style="font-weight:700;font-size:46px;color:#ddd6fe;letter-spacing:-.02em">${n}</div>
            <div style="font-weight:400;font-size:21px;color:#8d87ab;margin-top:6px">${r}</div>
          </div>`).join('')}
    </div>
  </div>
  <div style="position:absolute;bottom:52px;left:0;right:0;text-align:center;z-index:2;
    font-weight:400;font-size:21px;letter-spacing:.06em;color:#6e6790">
    Hackathon IA 2026 · Grupo 22</div>
  </div>`;
}

function cartelaTexto({ rotulo, titulo, sub }) {
  return `<div class="cartela"><div class="vinheta"></div><div class="z">
    <div class="barra"></div>
    <div style="height:26px"></div>
    <div class="rotulo">${rotulo}</div>
    <div style="height:30px"></div>
    <div class="titulo">${titulo}</div>
    ${sub ? `<div style="height:30px"></div><div class="sub">${sub}</div>` : ''}
  </div></div>`;
}

function cartelaFinal({ stats }) {
  return `<div class="cartela"><div class="vinheta"></div><div class="z">
    <div class="titulo" style="font-size:82px;max-width:1500px">Uma pergunta.<br>Um relatório pronto para o comitê.</div>
    <div style="height:34px"></div>
    <div class="sub" style="font-size:31px">Sem planilha, sem retrabalho — com a fonte de cada número.</div>
    <div style="height:64px"></div>
    <div style="display:flex;gap:18px">
      ${stats.map((s) => `<div style="padding:15px 27px;border-radius:999px;background:rgba(167,139,250,.11);
        box-shadow:0 0 0 1px rgba(167,139,250,.26) inset;font-weight:600;font-size:23px;color:#ddd6fe">${s}</div>`).join('')}
    </div>
    <div style="height:70px"></div>
    <div style="display:flex;align-items:center;gap:20px">
      <div style="width:56px;height:56px;border-radius:14px;background:#fff;overflow:hidden;display:flex">
        <img src="data:image/png;base64,${LOGO}" style="width:56px;height:56px;object-fit:cover"></div>
      <div style="font-weight:700;font-size:38px;color:#fff;letter-spacing:-.02em">EnergyNexus</div>
    </div>
    <div style="height:26px"></div>
    <div style="font-weight:400;font-size:24px;color:#8d87ab;letter-spacing:.02em">
      github.com/Hackathon-IA-2026/solucoes-grupo-22</div>
  </div></div>`;
}

function selo({ topo, linha, pe }) {
  return `<div style="padding:60px;display:inline-block">
    <div class="selo"><div class="fio"></div><div class="corpo">
      <div class="topo">${topo}</div>
      <div class="linha">${linha}</div>
      ${pe ? `<div class="pe">${pe}</div>` : ''}
    </div></div></div>`;
}

// ------------------------------------------------------------------- execução
(async () => {
  const copia = JSON.parse(fs.readFileSync(path.join(T, 'copia.json'), 'utf8'));

  const pecas = [];
  pecas.push({ nome: 'c00_abertura', tipo: 'cartela', html: cartelaAbertura() });
  for (const c of copia.cartelas) {
    pecas.push({ nome: c.nome, tipo: 'cartela', html: cartelaTexto(c) });
  }
  pecas.push({ nome: 'c99_final', tipo: 'cartela', html: cartelaFinal({ stats: copia.stats_finais }) });
  for (const s of copia.selos) {
    pecas.push({ nome: s.nome, tipo: 'selo', html: selo(s) });
  }

  fs.rmSync(OUT, { recursive: true, force: true });
  fs.mkdirSync(OUT, { recursive: true });

  const nav = await chromium.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--force-color-profile=srgb', '--font-render-hinting=none'],
  });

  const manifesto = [];
  for (const p of pecas) {
    const ctx = await nav.newContext({
      viewport: { width: 1920, height: 1080 },
      deviceScaleFactor: 2, // 3840x2160: dá folga para zoom suave no ffmpeg
      colorScheme: 'dark',
    });
    const pag = await ctx.newPage();
    await pag.setContent(`<!doctype html><meta charset="utf-8"><style>${BASE_CSS}</style>${p.html}`,
      { waitUntil: 'load' });
    await pag.evaluate(() => document.fonts.ready);
    await pag.waitForTimeout(250);
    const arq = path.join(OUT, `${p.nome}.png`);
    if (p.tipo === 'selo') {
      const alvo = pag.locator('.selo');
      const caixa = await alvo.boundingBox();
      // recorta com folga para a sombra não ser cortada
      await pag.screenshot({
        path: arq,
        omitBackground: true,
        clip: { x: caixa.x - 40, y: caixa.y - 40, width: caixa.width + 80, height: caixa.height + 80 },
      });
    } else {
      await pag.screenshot({ path: arq });
    }
    const dim = await pag.evaluate(() => [document.body.scrollWidth, document.body.scrollHeight]);
    manifesto.push({ nome: p.nome, tipo: p.tipo, arquivo: arq });
    console.log(`${p.nome} -> ${arq} (css ${dim.join('x')})`);
    await ctx.close();
  }

  await nav.close();
  fs.writeFileSync(path.join(OUT, 'manifesto.json'), JSON.stringify(manifesto, null, 1));
  console.log(`\n${manifesto.length} peças em ${OUT}`);
})().catch((e) => { console.error('ERRO:', e.stack); process.exit(1); });
