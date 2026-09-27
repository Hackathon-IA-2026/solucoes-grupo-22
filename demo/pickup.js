// Passe de pickup: regrava as cenas que saíram fracas na gravação principal, SEM chamar o modelo.
// Reabre a conversa já gravada (a resposta e o relatório estão no histórico) e:
//   06_fonte   -> realça o parágrafo que declara as contas da CVM (o casamento por /^Fonte:/ falhou)
//   05_tabela  -> mesma rolagem, mas com o realce no roxo da marca em vez do azul
//   07b_pdf    -> O CLÍMAX QUE FALTOU: abre o artefato do relatório, amplia e passa as páginas
//                 (na gravação principal o relatório ainda estava sendo escrito quando a cena acabou)
//   08_grafo   -> clica no chip "Dívida líquida / EBITDA" dentro do painel da categoria (não é um nó)
//
// Rodar: node pickup.js

const { chromium } = require('/impa/home/a/al.richard.viana/projects/clean-hack/coppezip/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const CHROME = '/local/al.richard.viana/playwright/chromium-1194/chrome-linux/chrome';
const T = process.env.DEMO_DIR || __dirname;
const FRAMES = path.join(T, 'frames');
const BASE = 'http://127.0.0.1:3090';
const CNPJ = '17155730000164';
const CSS = { width: 1440, height: 810 };
const DSF = 4 / 3;
const FPS = 25;
const FRAME_MS = Math.round(1000 / FPS);

// roxo da marca (violet-400/500) — o azul #8ab4f8 da primeira gravação briga com a identidade
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

const relato = { fps: FPS, cenas: [], textos: {} };
let cenaAtual = null;

function abrirCena(nome) {
  const dir = path.join(FRAMES, nome);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  cenaAtual = { nome, dir, n: 0, marcas: {} };
  console.log(`\n=== cena ${nome} ===`);
}

function fecharCena() {
  if (!cenaAtual) return;
  const { nome, n, marcas } = cenaAtual;
  relato.cenas.push({ nome, frames: n, segundos: +(n / FPS).toFixed(2), marcas });
  console.log(`--- ${nome}: ${n} frames (${(n / FPS).toFixed(1)}s)`);
  cenaAtual = null;
}

async function quadro(pag) {
  cenaAtual.n += 1;
  await pag.screenshot({ path: path.join(cenaAtual.dir, `${String(cenaAtual.n).padStart(6, '0')}.png`) });
}

function marcar(nome) {
  if (cenaAtual) cenaAtual.marcas[nome] = cenaAtual.n;
}

async function gravar(pag, ms) {
  const fim = Date.now() + ms;
  while (Date.now() < fim) {
    const t0 = Date.now();
    await quadro(pag);
    const resta = FRAME_MS - (Date.now() - t0);
    if (resta > 0) await pag.waitForTimeout(resta);
  }
}

async function gravarQuadros(pag, n) {
  for (let i = 0; i < n; i++) await quadro(pag);
}

// o ponteiro falso só aparece quando a cena é sobre clicar em algo
const cursor = (pag, on) =>
  pag.evaluate((v) => {
    const c = document.getElementById('__cur');
    if (c) c.style.opacity = v ? '1' : '0';
  }, on).catch(() => {});

async function moverMouse(pag, alvo, passos = 16) {
  const box = await alvo.boundingBox();
  if (!box) return;
  const tx = box.x + box.width / 2;
  const ty = box.y + box.height / 2;
  const de = pag.__m || { x: CSS.width / 2, y: CSS.height - 60 };
  for (let i = 1; i <= passos; i++) {
    const t = i / passos;
    const s = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    await pag.mouse.move(de.x + (tx - de.x) * s, de.y + (ty - de.y) * s);
    if (i % 2 === 0) await quadro(pag);
  }
  pag.__m = { x: tx, y: ty };
}

async function clicarEm(pag, alvo) {
  await cursor(pag, true);
  await moverMouse(pag, alvo);
  await quadro(pag);
  await pag.mouse.down();
  await quadro(pag);
  await pag.mouse.up();
  await quadro(pag);
}

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

async function rolarGravando(pag, passo, quadros) {
  for (let i = 0; i < quadros; i++) {
    const fim = await pag.evaluate((p) => {
      const el = document.querySelector('[data-demo-rolagem]') || document.scrollingElement;
      const antes = el.scrollTop;
      el.scrollTop = antes + p;
      return el.scrollTop <= antes + 0.5;
    }, passo);
    await quadro(pag);
    if (fim) break;
  }
}

(async () => {
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

  const pag = await ctx.newPage();
  await pag.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  // usuário da gravação pelo ambiente: senha não entra no repositório
  if (!process.env.DEMO_EMAIL || !process.env.DEMO_SENHA) {
    console.error('defina DEMO_EMAIL e DEMO_SENHA com o usuário do LibreChat usado na gravação');
    process.exit(2);
  }
  await pag.fill('#email', process.env.DEMO_EMAIL);
  await pag.fill('#password', process.env.DEMO_SENHA);
  await pag.click('[data-testid="login-button"]');
  await pag.waitForURL('**/c/**', { timeout: 60000 });
  await pag.waitForTimeout(2500);
  console.log('login ok');

  // ---- abre a conversa da comparação (já está no histórico, não gasta chamada ao modelo)
  const item = pag.locator('a,[data-testid^="convo-item"]').filter({ hasText: /Cemig, Copel/i }).first();
  if (!(await item.count())) {
    console.error('ABORTA: a conversa da comparação não está na barra lateral.');
    await pag.screenshot({ path: path.join(T, 'falha_pickup.png') });
    process.exit(3);
  }
  await item.click();
  await pag.waitForSelector('.agent-turn', { timeout: 60000 });
  await pag.waitForTimeout(3500);
  relato.textos.url = pag.url();
  console.log('conversa:', pag.url());

  // a resposta da comparação é o PRIMEIRO turno do agente (o segundo é o relatório)
  await pag.evaluate(() => {
    const t = document.querySelectorAll('.agent-turn')[0];
    if (t) t.setAttribute('data-demo-resposta', '1');
  });
  const rolagem = await pag.evaluate(MARCAR_ROLAGEM);
  console.log('container de rolagem:', JSON.stringify(rolagem));

  // =========================================================================
  // CENA 05 — a tabela, com o realce no roxo da marca
  // =========================================================================
  abrirCena('05_tabela');
  await cursor(pag, false);
  await pag.evaluate(() => {
    const h = [...document.querySelectorAll('[data-demo-resposta] h1,[data-demo-resposta] h2,[data-demo-resposta] h3')]
      .find((e) => /Conclus/i.test(e.textContent || ''));
    if (h) h.scrollIntoView({ block: 'start' });
    const el = document.querySelector('[data-demo-rolagem]');
    if (el) el.scrollTop = Math.max(0, el.scrollTop - 90);
  });
  await pag.waitForTimeout(700);
  await gravarQuadros(pag, 20);
  await rolarGravando(pag, 7, 120);
  marcar('tabela_na_tela');
  const realce = await pag.evaluate(([borda, fundo]) => {
    const tab = document.querySelector('[data-demo-resposta] table');
    if (!tab) return { ok: false };
    tab.scrollIntoView({ block: 'center' });
    const linha = [...tab.querySelectorAll('tr')].find((r) => /Dívida líquida\s*\/\s*EBITDA/i.test(r.innerText || ''));
    if (linha) {
      linha.style.cssText =
        `outline:2px solid ${borda};outline-offset:-2px;background:${fundo};border-radius:6px`;
    }
    return { ok: true, realcou: !!linha, linha: linha ? linha.innerText.replace(/\s+/g, ' ') : '' };
  }, [REALCE_BORDA, REALCE_FUNDO]);
  console.log('realce da tabela:', JSON.stringify(realce));
  relato.textos.linha_alavancagem = realce.linha || '';
  await pag.waitForTimeout(400);
  await gravarQuadros(pag, 80);
  fecharCena();

  // =========================================================================
  // CENA 06 — a fonte: o parágrafo que diz conta por conta de onde vem o número
  // =========================================================================
  abrirCena('06_fonte');
  const fonte = await pag.evaluate(([borda, fundo]) => {
    const alvos = [...document.querySelectorAll('[data-demo-resposta] p,[data-demo-resposta] li')];
    const p = alvos.find((e) => /CVM\s+DFP/i.test(e.textContent || ''))
           || alvos.find((e) => /^Fonte:/i.test((e.textContent || '').trim()));
    if (!p) return { ok: false, amostra: alvos.slice(0, 4).map((e) => (e.textContent || '').slice(0, 60)) };
    p.scrollIntoView({ block: 'center' });
    p.style.cssText = `background:${fundo};border-left:3px solid ${borda};padding:10px 14px;border-radius:6px`;
    return { ok: true, texto: (p.textContent || '').slice(0, 300) };
  }, [REALCE_BORDA, REALCE_FUNDO]);
  console.log('fonte:', JSON.stringify(fonte).slice(0, 300));
  relato.textos.fonte = fonte.texto || '';
  await pag.waitForTimeout(400);
  await gravarQuadros(pag, 80);
  fecharCena();

  // =========================================================================
  // CENA 07b — O CLÍMAX: o relatório em PDF. O cartão do artefato está na resposta;
  // clicar nele abre o painel (o auto-abrir só vale enquanto a resposta está sendo escrita).
  // =========================================================================
  abrirCena('07b_pdf');
  await pag.evaluate(() => {
    const el = document.querySelector('[data-demo-rolagem]');
    if (el) el.scrollTop = el.scrollHeight;
  });
  await pag.waitForTimeout(1500);
  const cartoes = await pag.evaluate(() =>
    [...document.querySelectorAll('button')]
      .map((b) => (b.innerText || '').replace(/\s+/g, ' ').trim())
      .filter((t) => /relat|pdf|clique|artefato/i.test(t) && t.length < 90));
  console.log('cartões candidatos:', JSON.stringify(cartoes));
  let cartao = pag.locator('button').filter({ hasText: /Clique para (abrir|ver)|relat.rio/i }).last();
  if (!(await cartao.count())) cartao = pag.locator('button').filter({ hasText: /\.pdf/i }).last();
  let pdfOk = false;
  if (await cartao.count()) {
    await gravarQuadros(pag, 18);
    await clicarEm(pag, cartao);
    // o painel entra deslizando: vale gravar em tempo real
    await gravar(pag, 2200);
    const iframe = pag.locator('iframe[title]').first();
    pdfOk = (await iframe.count()) > 0;
    console.log('painel com iframe do PDF:', pdfOk);
    if (pdfOk) {
      await pag.waitForTimeout(2500); // primeira página renderiza
      marcar('pdf_ao_lado');
      await gravarQuadros(pag, 40);
      const ampliar = pag.locator('[aria-label="Ampliar para a tela toda"]').first();
      if (await ampliar.count()) {
        await clicarEm(pag, ampliar);
        await gravar(pag, 1600);
        marcar('pdf_ampliado');
        await cursor(pag, false);
        await gravarQuadros(pag, 45);
        // passa as páginas do relatório com a roda do mouse sobre o visualizador
        const cx = CSS.width / 2;
        const cy = CSS.height / 2;
        await pag.mouse.move(cx, cy);
        for (let i = 0; i < 90; i++) {
          await pag.mouse.wheel(0, 26);
          await quadro(pag);
        }
        marcar('pdf_rolado');
        await gravarQuadros(pag, 30);
      } else {
        console.log('sem botão de ampliar; fica no painel lateral');
        await gravarQuadros(pag, 60);
      }
    } else {
      await gravarQuadros(pag, 40);
    }
  } else {
    console.log('ABORTA a cena: não achei o cartão do artefato');
    await pag.screenshot({ path: path.join(T, 'falha_artefato.png') });
  }
  relato.textos.pdf_ok = pdfOk;
  fecharCena();

  // =========================================================================
  // CENA 08 — grafo: abre a categoria e clica no indicador dentro do painel
  // =========================================================================
  abrirCena('08_grafo');
  try {
    await pag.goto(`${BASE}/grafo?empresa=${CNPJ}`, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await pag.waitForSelector('.kg-exp-grade .kg-exp-card, .kg-node--empresa, .kg-node', { timeout: 90000 });
    await pag.waitForTimeout(2600);
    await cursor(pag, false);
    await gravarQuadros(pag, 30); // 1,2s com o grafo montado
    marcar('grafo_montado');

    const cat = pag.locator('.kg-node').filter({ hasText: 'Indicadores financeiros anuais' }).first();
    if (await cat.count()) {
      await clicarEm(pag, cat);
      await gravar(pag, 1200);
      await gravarQuadros(pag, 22); // o painel com os 24 indicadores
      marcar('categoria_aberta');
    }

    // o indicador é um CHIP do painel ("Contém (24)"), não um nó do grafo — foi o que faltou na 1ª gravação.
    // clicar nele revela o nó, seleciona e leva a câmera até ele.
    let chip = pag.locator('button.kg-link-chip').filter({ hasText: /Dívida líquida\s*\/\s*EBITDA/i }).first();
    if (!(await chip.count())) {
      chip = pag.locator('button.kg-link-chip').filter({ hasText: /EBITDA/i }).first();
    }
    if (await chip.count()) {
      await clicarEm(pag, chip);
      await gravar(pag, 2000); // a câmera anda até o nó
      marcar('indicador_revelado');
      await cursor(pag, false);
      await gravarQuadros(pag, 20);
      const p = await pag.evaluate(([borda, fundo]) => {
        const lado = document.querySelector('aside.kg-panel') || document.querySelector('.kg-panel');
        if (!lado) return { ok: false };
        const tr = [...lado.querySelectorAll('tr')].find((r) => /\b2024\b/.test(r.innerText || ''));
        if (tr) {
          tr.scrollIntoView({ block: 'center' });
          tr.style.cssText = `outline:2px solid ${borda};outline-offset:-2px;background:${fundo}`;
        }
        const fonte = [...lado.querySelectorAll('.kg-chip,.kg-sub,span,div')]
          .find((e) => /CVM|DFP/i.test(e.textContent || '') && e.children.length === 0);
        if (fonte) {
          fonte.style.cssText += `;outline:1px solid ${borda};background:${fundo};border-radius:5px;padding:2px 6px`;
        }
        return {
          ok: true,
          titulo: (lado.querySelector('.kg-title') || {}).textContent || '',
          ano: tr ? tr.innerText.replace(/\s+/g, ' ') : '',
          fonte: fonte ? fonte.textContent.slice(0, 120) : '',
        };
      }, [REALCE_BORDA, REALCE_FUNDO]);
      relato.textos.grafo = p;
      console.log('painel do indicador:', JSON.stringify(p).slice(0, 260));
      await pag.waitForTimeout(400);
      await gravarQuadros(pag, 62); // 2,5s de leitura do valor com a fonte declarada
    } else {
      console.log('não achei o chip do indicador no painel');
      await gravarQuadros(pag, 40);
    }
  } catch (e) {
    console.log('erro na cena do grafo:', e.message);
  }
  fecharCena();

  fs.writeFileSync(path.join(T, 'relato_pickup.json'), JSON.stringify(relato, null, 1));
  console.log(`\nrelato em ${path.join(T, 'relato_pickup.json')}`);
  await ctx.close();
  await nav.close();
})().catch((e) => { console.error('ERRO:', e.stack); process.exit(1); });
