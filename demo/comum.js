// Helpers compartilhados pelos passes de gravação (gravar3.js tem a própria cópia, histórica).
const fs = require('fs');
const path = require('path');

const T = process.env.DEMO_DIR || __dirname;
const FRAMES = path.join(T, 'frames');
const BASE = 'http://127.0.0.1:3090';
const CHROME = '/local/al.richard.viana/playwright/chromium-1194/chrome-linux/chrome';
const CSS = { width: 1440, height: 810 };
const DSF = 4 / 3; // 1440x810 * 4/3 = 1920x1080
const FPS = 25;
const FRAME_MS = Math.round(1000 / FPS);

// roxo da marca (violet-400/500): o azul #8ab4f8 da primeira gravação briga com a identidade
const REALCE_BORDA = '#a78bfa';
const REALCE_FUNDO = 'rgba(139,92,246,.20)';

const CURSOR_JS = `
(() => {
  if (document.getElementById('__cur')) return;
  const c = document.createElement('div');
  c.id = '__cur';
  c.style.cssText = [
    'position:fixed','left:-60px','top:-60px','width:22px','height:22px',
    'border-radius:50%','background:rgba(255,255,255,.92)',
    'box-shadow:0 0 0 3px rgba(0,0,0,.45),0 4px 18px rgba(0,0,0,.55)',
    'pointer-events:none','z-index:2147483647','transition:transform .1s ease,opacity .15s ease',
    'opacity:0','will-change:left,top'
  ].join(';');
  const põe = () => document.body && document.body.appendChild(c);
  if (document.body) põe(); else document.addEventListener('DOMContentLoaded', põe);
  document.addEventListener('mousemove', (e) => {
    c.style.left = (e.clientX - 11) + 'px'; c.style.top = (e.clientY - 11) + 'px';
  }, true);
  document.addEventListener('mousedown', () => {
    c.style.transform = 'scale(.62)'; c.style.background = '${REALCE_BORDA}';
  }, true);
  document.addEventListener('mouseup', () => {
    c.style.transform = 'scale(1)'; c.style.background = 'rgba(255,255,255,.92)';
  }, true);
})();`;

// marca o container rolável da conversa (o mais interno que realmente rola)
const MARCAR_ROLAGEM = `(() => {
  const alvo = document.querySelector('.agent-turn') || document.querySelector('[data-testid^="convo-"]');
  let el = alvo;
  while (el && el !== document.body) {
    const s = getComputedStyle(el);
    if ((s.overflowY === 'auto' || s.overflowY === 'scroll') && el.scrollHeight > el.clientHeight + 40) {
      el.setAttribute('data-demo-rolagem', '1');
      return { ok: true, altura: el.scrollHeight, visivel: el.clientHeight, topo: el.scrollTop };
    }
    el = el.parentElement;
  }
  return { ok: false };
})()`;

function criarGravador(relato) {
  let cena = null;

  const abrirCena = (nome) => {
    const dir = path.join(FRAMES, nome);
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(dir, { recursive: true });
    cena = { nome, dir, n: 0, marcas: {} };
    console.log(`\n=== cena ${nome} ===`);
  };

  const fecharCena = () => {
    if (!cena) return;
    relato.cenas.push({ nome: cena.nome, frames: cena.n, segundos: +(cena.n / FPS).toFixed(2), marcas: cena.marcas });
    console.log(`--- ${cena.nome}: ${cena.n} frames (${(cena.n / FPS).toFixed(1)}s)`);
    cena = null;
  };

  const quadro = async (pag) => {
    cena.n += 1;
    await pag.screenshot({ path: path.join(cena.dir, `${String(cena.n).padStart(6, '0')}.png`) });
  };

  const marcar = (nome) => { if (cena) cena.marcas[nome] = cena.n; };

  // grava por `ms` de tempo real (para animações da interface)
  const gravar = async (pag, ms) => {
    const fim = Date.now() + ms;
    while (Date.now() < fim) {
      const t0 = Date.now();
      await quadro(pag);
      const resta = FRAME_MS - (Date.now() - t0);
      if (resta > 0) await pag.waitForTimeout(resta);
    }
  };

  // grava `n` quadros seguidos (tela parada: só estica o tempo na edição)
  const gravarQuadros = async (pag, n) => { for (let i = 0; i < n; i++) await quadro(pag); };

  // o ponteiro falso só aparece quando a cena é sobre clicar em algo
  const cursor = (pag, on) =>
    pag.evaluate((v) => {
      const c = document.getElementById('__cur');
      if (c) c.style.opacity = v ? '1' : '0';
    }, on).catch(() => {});

  const moverMouse = async (pag, alvo, passos = 16) => {
    const box = await alvo.boundingBox();
    if (!box) return;
    const tx = box.x + box.width / 2;
    const ty = box.y + box.height / 2;
    const de = pag.__m || { x: CSS.width / 2, y: CSS.height - 60 };
    for (let i = 1; i <= passos; i++) {
      const t = i / passos;
      const s = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; // easeInOutQuad
      await pag.mouse.move(de.x + (tx - de.x) * s, de.y + (ty - de.y) * s);
      if (i % 2 === 0) await quadro(pag);
    }
    pag.__m = { x: tx, y: ty };
  };

  const clicarEm = async (pag, alvo) => {
    await cursor(pag, true);
    await moverMouse(pag, alvo);
    await quadro(pag);
    await pag.mouse.down();
    await quadro(pag);
    await pag.mouse.up();
    await quadro(pag);
  };

  // rola `passo` px por quadro no container marcado (rolagem suave de verdade)
  const rolarGravando = async (pag, passo, quadros, seletor = '[data-demo-rolagem]') => {
    for (let i = 0; i < quadros; i++) {
      const fim = await pag.evaluate(([s, p]) => {
        const el = document.querySelector(s) || document.scrollingElement;
        const antes = el.scrollTop;
        el.scrollTop = antes + p;
        return el.scrollTop <= antes + 0.5;
      }, [seletor, passo]);
      await quadro(pag);
      if (fim) break;
    }
  };

  return { abrirCena, fecharCena, quadro, marcar, gravar, gravarQuadros, cursor, moverMouse, clicarEm, rolarGravando };
}

async function abrirNavegador(chromium) {
  const nav = await chromium.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--hide-scrollbars',
           '--force-color-profile=srgb', '--disable-gpu-vsync', '--font-render-hinting=none'],
  });
  const ctx = await nav.newContext({
    viewport: CSS, deviceScaleFactor: DSF, colorScheme: 'dark',
    locale: 'pt-BR', timezoneId: 'America/Sao_Paulo',
  });
  await ctx.addInitScript(CURSOR_JS);
  await ctx.addInitScript(() => {
    try {
      localStorage.setItem('theme', 'dark');
      localStorage.setItem('LaTeXParsing', 'false');
    } catch (e) {}
  });
  return { nav, ctx };
}

async function entrar(pag) {
  // o usuário da gravação vem do ambiente: senha não entra no repositório
  const email = process.env.DEMO_EMAIL;
  const senha = process.env.DEMO_SENHA;
  if (!email || !senha) {
    console.error('defina DEMO_EMAIL e DEMO_SENHA com o usuário do LibreChat usado na gravação');
    process.exit(2);
  }
  await pag.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await pag.fill('#email', email);
  await pag.fill('#password', senha);
  await pag.click('[data-testid="login-button"]');
  await pag.waitForURL('**/c/**', { timeout: 60000 });
  await pag.waitForTimeout(2500);
  console.log('login ok');
}

module.exports = {
  T, FRAMES, BASE, CHROME, CSS, DSF, FPS, FRAME_MS,
  REALCE_BORDA, REALCE_FUNDO, CURSOR_JS, MARCAR_ROLAGEM,
  criarGravador, abrirNavegador, entrar,
};
