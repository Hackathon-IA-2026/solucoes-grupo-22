// Grava o material bruto da demo executiva do EnergyNexus.
//
// Diferenças em relação ao gravar2.js:
//   - viewport 1440x810 com deviceScaleFactor 4/3 => screenshot 1920x1080 com a interface 33% maior (legível em vídeo)
//   - perfil fixado pela URL (?spec=energynexus-analista-claude): não depende do modelo padrão (o vLLM está fora)
//   - LaTeXParsing desligado no localStorage: "R$ 39,82 bi" deixa de virar fórmula matemática
//   - pergunta comparativa (resposta com conclusão, tabela de 8 indicadores, fontes e ressalvas)
//   - rolagem suave quadro a quadro pela resposta (scrollTop += passo por frame), não "behavior:smooth" em time-lapse
//   - cena do relatório em PDF: o painel abre sozinho e a gente amplia para a tela toda
//   - cada cena grava em frames/<NN_nome>/ com numeração própria, para a edição cortar cena por cena
//
// Rodar: node gravar3.js   (o Playwright vem do node_modules do repositório)

const { chromium } = require('/impa/home/a/al.richard.viana/projects/clean-hack/coppezip/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const CHROME = '/local/al.richard.viana/playwright/chromium-1194/chrome-linux/chrome';
const T = process.env.DEMO_DIR || __dirname;
const FRAMES = path.join(T, 'frames');
const BASE = 'http://127.0.0.1:3090';
const SPEC = 'energynexus-analista-claude';
const ROTULO = 'EnergyNexus Analista (Claude)'; // como o perfil aparece no seletor de modelo
const CNPJ = '17155730000164'; // Cemig holding

const PERGUNTA =
  'Compare Cemig, Copel e Energisa em 2024: receita líquida, EBITDA, margem EBITDA, ' +
  'dívida líquida/EBITDA e investimento total. Monte a tabela e diga qual está em melhor situação financeira.';
const PEDIDO_PDF = 'Gere o relatório em PDF dessa comparação para o comitê de investimentos.';
const BUSCA = 'meta de redução de emissões da Cemig';

const CSS = { width: 1440, height: 810 };
const DSF = 4 / 3; // 1440x810 * 4/3 = 1920x1080
const FPS = 25;
const FRAME_MS = Math.round(1000 / FPS);

// cursor visível (o Chrome não grava o ponteiro do sistema)
const CURSOR_JS = `
(() => {
  if (document.getElementById('__cur')) return;
  const c = document.createElement('div');
  c.id = '__cur';
  c.style.cssText = [
    'position:fixed','left:-60px','top:-60px','width:22px','height:22px',
    'border-radius:50%','background:rgba(255,255,255,.92)',
    'box-shadow:0 0 0 3px rgba(0,0,0,.45),0 4px 18px rgba(0,0,0,.55)',
    'pointer-events:none','z-index:2147483647','transition:transform .1s ease',
    'will-change:left,top'
  ].join(';');
  const põe = () => document.body && document.body.appendChild(c);
  if (document.body) põe(); else document.addEventListener('DOMContentLoaded', põe);
  document.addEventListener('mousemove', (e) => {
    c.style.left = (e.clientX - 11) + 'px'; c.style.top = (e.clientY - 11) + 'px';
  }, true);
  document.addEventListener('mousedown', () => {
    c.style.transform = 'scale(.62)'; c.style.background = '#8ab4f8';
  }, true);
  document.addEventListener('mouseup', () => {
    c.style.transform = 'scale(1)'; c.style.background = 'rgba(255,255,255,.92)';
  }, true);
})();`;

const relato = { fps: FPS, largura: 1920, altura: 1080, cenas: [], textos: {} };
let cenaAtual = null;

function abrirCena(nome) {
  const dir = path.join(FRAMES, nome);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  cenaAtual = { nome, dir, n: 0, marcas: {} };
  console.log(`\n=== cena ${nome} ===`);
  return cenaAtual;
}

function fecharCena() {
  if (!cenaAtual) return;
  const { nome, n, marcas } = cenaAtual;
  relato.cenas.push({ nome, frames: n, segundos: +(n / FPS).toFixed(2), marcas });
  console.log(`--- ${nome}: ${n} frames (${(n / FPS).toFixed(1)}s)`);
  cenaAtual = null;
}

// grava um quadro na cena aberta
async function quadro(pag) {
  cenaAtual.n += 1;
  await pag.screenshot({ path: path.join(cenaAtual.dir, `${String(cenaAtual.n).padStart(6, '0')}.png`) });
}

// marca em que quadro da cena algo aconteceu (a edição usa isso para sincronizar legendas)
function marcar(nome) {
  if (cenaAtual) cenaAtual.marcas[nome] = cenaAtual.n;
}

// grava por `ms` de tempo real, um quadro a cada FRAME_MS
async function gravar(pag, ms) {
  const fim = Date.now() + ms;
  while (Date.now() < fim) {
    const t0 = Date.now();
    await quadro(pag);
    const resta = FRAME_MS - (Date.now() - t0);
    if (resta > 0) await pag.waitForTimeout(resta);
  }
}

// grava `n` quadros seguidos (sem esperar tempo real: usado quando a tela está parada)
async function gravarQuadros(pag, n) {
  for (let i = 0; i < n; i++) await quadro(pag);
}

async function moverMouse(pag, alvo, passos = 16) {
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
}

async function clicarEm(pag, alvo) {
  await moverMouse(pag, alvo);
  await quadro(pag);
  await pag.mouse.down();
  await quadro(pag);
  await pag.mouse.up();
  await quadro(pag);
}

// digita o texto em pedaços, gravando um quadro por pedaço (digitação rápida e fluida no vídeo)
async function digitar(pag, seletor, texto, pedaco = 4) {
  await pag.click(seletor);
  for (let i = 0; i < texto.length; i += pedaco) {
    await pag.keyboard.insertText(texto.slice(i, i + pedaco));
    await quadro(pag);
  }
}

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

// rola `passo` px por quadro, gravando cada quadro (rolagem suave de verdade)
async function rolarGravando(pag, passo, quadros) {
  for (let i = 0; i < quadros; i++) {
    const fim = await pag.evaluate((p) => {
      const el = document.querySelector('[data-demo-rolagem]') || document.scrollingElement;
      const antes = el.scrollTop;
      el.scrollTop = antes + p;
      return el.scrollTop <= antes + 0.5; // chegou no fim
    }, passo);
    await quadro(pag);
    if (fim) break;
  }
}

async function rolarJanela(pag, passo, quadros) {
  for (let i = 0; i < quadros; i++) {
    const fim = await pag.evaluate((p) => {
      const el = document.scrollingElement;
      const antes = el.scrollTop;
      el.scrollTop = antes + p;
      return el.scrollTop <= antes + 0.5;
    }, passo);
    await quadro(pag);
    if (fim) break;
  }
}

(async () => {
  fs.mkdirSync(FRAMES, { recursive: true });

  const nav = await chromium.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--hide-scrollbars',
           '--force-color-profile=srgb', '--disable-gpu-vsync', '--font-render-hinting=none'],
  });
  const ctx = await nav.newContext({
    viewport: CSS,
    deviceScaleFactor: DSF,
    colorScheme: 'dark',
    locale: 'pt-BR',
    timezoneId: 'America/Sao_Paulo',
  });
  await ctx.addInitScript(CURSOR_JS);
  await ctx.addInitScript(() => {
    try {
      localStorage.setItem('theme', 'dark');
      // "R$ 39,82 bi" dentro da tabela virava fórmula LaTeX (o $ abre modo matemático)
      localStorage.setItem('LaTeXParsing', 'false');
      // resíduo de conversa manda o pedido para o endpoint anterior: começa do zero e escolhe o perfil pelo menu
      for (const k of Object.keys(localStorage)) {
        if (/^lastConversationSetup|^lastSelectedSpec|^lastModel/.test(k)) localStorage.removeItem(k);
      }
    } catch (e) {}
  });

  // ---------- login ----------
  {
    const p = await ctx.newPage();
    await p.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    // usuário da gravação pelo ambiente: senha não entra no repositório
    if (!process.env.DEMO_EMAIL || !process.env.DEMO_SENHA) {
      console.error('defina DEMO_EMAIL e DEMO_SENHA com o usuário do LibreChat usado na gravação');
      process.exit(2);
    }
    await p.fill('#email', process.env.DEMO_EMAIL);
    await p.fill('#password', process.env.DEMO_SENHA);
    await p.click('[data-testid="login-button"]');
    await p.waitForURL('**/c/**', { timeout: 60000 });
    await p.waitForTimeout(1500);
    await p.close();
    console.log('login ok');
  }

  const pag = await ctx.newPage();
  pag.setDefaultTimeout(90000);

  // -------------------------------------------------------------------------
  // fora de cena: põe a conversa no Claude (Bedrock).
  // O ?spec= da URL NÃO serve: ele grava só o nome do perfil e deixa endpoint/modelo do padrão
  // (EnergyNexus/qwen3.8-27b, vLLM fora do ar) — o pedido fica pendurado para sempre.
  // Escolher pelo menu aplica o preset inteiro (endpoint bedrock, modelo, maxOutputTokens 32000).
  // -------------------------------------------------------------------------
  await pag.goto(`${BASE}/c/new`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await pag.waitForSelector('#prompt-textarea', { timeout: 60000 });
  await pag.waitForTimeout(2500);
  await pag.click('[data-testid="model-selector-button"]');
  await pag.waitForTimeout(1000);
  await pag.getByText(ROTULO, { exact: true }).last().click({ timeout: 15000 });
  await pag.waitForTimeout(2500);
  const perfil = await pag.evaluate(() => JSON.parse(localStorage.getItem('lastConversationSetup_0') || '{}'));
  console.log(`perfil: endpoint=${perfil.endpoint} model=${perfil.model} maxOut=${perfil.maxOutputTokens}`);
  if (perfil.endpoint !== 'bedrock' || !/claude/i.test(perfil.model || '')) {
    console.error('ABORTA: a conversa não ficou no Claude — o pedido iria para o vLLM que está fora do ar.');
    await pag.screenshot({ path: path.join(T, 'falha_perfil.png') });
    process.exit(3);
  }
  relato.textos.modelo = perfil.model;
  // o cursor falso segue o ponteiro; volta para o meio antes de gravar
  await pag.mouse.move(CSS.width / 2, CSS.height - 60);
  pag.__m = { x: CSS.width / 2, y: CSS.height - 60 };
  await pag.waitForTimeout(600);

  // =========================================================================
  // CENA 01 — abertura: a tela inicial do chat, com as perguntas sugeridas
  // =========================================================================
  abrirCena('01_abertura');
  await gravar(pag, 2000);
  fecharCena();

  // =========================================================================
  // CENA 02 — a pergunta sendo digitada
  // =========================================================================
  abrirCena('02_pergunta');
  await digitar(pag, '#prompt-textarea', PERGUNTA, 4);
  await gravarQuadros(pag, 18); // 0,7s com a pergunta inteira na tela
  marcar('pergunta_completa');
  const btnEnviar = pag.locator('[data-testid="send-button"]');
  await clicarEm(pag, btnEnviar);
  marcar('enviado');
  fecharCena();

  // =========================================================================
  // CENA 03 — o agente trabalhando: as chamadas de ferramenta aparecendo
  // =========================================================================
  abrirCena('03_ferramentas');
  // os primeiros segundos em tempo real (é quando as ferramentas aparecem uma a uma)
  await gravar(pag, 9000);
  marcar('ferramentas_na_tela');
  // o resto da geração em time-lapse: 1 quadro a cada 1,2s
  let texto = '';
  let estavel = 0;
  const limite = Date.now() + 180000;
  while (Date.now() < limite) {
    await pag.waitForTimeout(1200);
    await quadro(pag);
    const resp = pag.locator('.agent-turn .message-content').last();
    if (await resp.count()) {
      const novo = await resp.innerText().catch(() => '');
      if (novo.length > 300) {
        if (novo === texto) { estavel += 1; if (estavel >= 3) break; } else estavel = 0;
        texto = novo;
      } else {
        texto = novo;
      }
    }
  }
  marcar('resposta_pronta');
  relato.textos.resposta = texto;
  console.log(`resposta com ${texto.length} caracteres`);
  if (texto.length < 800) {
    console.error('ABORTA: a resposta não chegou (o endpoint do perfil pode estar fora do ar).');
    console.error('trecho:', JSON.stringify(texto.slice(0, 300)));
    await pag.screenshot({ path: path.join(T, 'falha_resposta.png') });
    process.exit(2);
  }
  // conta as ferramentas que a interface declara ("7 ferramentas usadas")
  relato.textos.ferramentas = await pag
    .locator('.agent-turn')
    .last()
    .innerText()
    .then((t) => (t.match(/(\d+)\s+ferramentas?\s+usadas?/i) || [])[0] || '')
    .catch(() => '');
  await gravarQuadros(pag, 12);
  fecharCena();

  // =========================================================================
  // CENA 04 — a conclusão: o veredito no alto da resposta
  // =========================================================================
  abrirCena('04_conclusao');
  const rolagem = await pag.evaluate(MARCAR_ROLAGEM);
  console.log('container de rolagem:', JSON.stringify(rolagem));
  // põe o título "Conclusão" no alto da área visível
  await pag.evaluate(() => {
    const h = [...document.querySelectorAll('.agent-turn h1,.agent-turn h2,.agent-turn h3,.agent-turn strong')]
      .find((e) => /Conclus/i.test(e.textContent || ''));
    if (h) h.scrollIntoView({ block: 'start' });
    const el = document.querySelector('[data-demo-rolagem]');
    if (el) el.scrollTop = Math.max(0, el.scrollTop - 90);
  });
  await pag.waitForTimeout(600);
  await gravarQuadros(pag, 62); // 2,5s de leitura
  fecharCena();

  // =========================================================================
  // CENA 05 — a tabela: rolagem suave e realce da linha da alavancagem
  // =========================================================================
  abrirCena('05_tabela');
  await rolarGravando(pag, 7, 120); // ~5s de rolagem contínua (175 px/s)
  marcar('tabela_na_tela');
  // centraliza a tabela e realça a linha de dívida líquida/EBITDA
  const realce = await pag.evaluate(() => {
    const tab = document.querySelector('.agent-turn table');
    if (!tab) return { ok: false };
    tab.scrollIntoView({ block: 'center' });
    const linha = [...tab.querySelectorAll('tr')].find((r) => /Dívida líquida\s*\/\s*EBITDA/i.test(r.innerText || ''));
    if (linha) {
      linha.style.cssText =
        'outline:2px solid #8ab4f8;outline-offset:-2px;background:rgba(138,180,248,.16);' +
        'border-radius:6px;transition:background .4s ease';
    }
    return { ok: true, realcou: !!linha, linha: linha ? linha.innerText.replace(/\s+/g, ' ') : '' };
  });
  console.log('realce da tabela:', JSON.stringify(realce));
  relato.textos.linha_alavancagem = realce.linha || '';
  await pag.waitForTimeout(400);
  await gravarQuadros(pag, 70); // 2,8s com a linha realçada
  fecharCena();

  // =========================================================================
  // CENA 06 — a fonte: a linha que diz de onde veio cada número
  // =========================================================================
  abrirCena('06_fonte');
  const fonte = await pag.evaluate(() => {
    const p = [...document.querySelectorAll('.agent-turn p,.agent-turn li')]
      .find((e) => /^Fonte:/i.test((e.textContent || '').trim()));
    if (!p) return { ok: false };
    p.scrollIntoView({ block: 'center' });
    p.style.cssText = 'background:rgba(138,180,248,.10);border-left:3px solid #8ab4f8;padding-left:12px;border-radius:4px';
    return { ok: true, texto: (p.textContent || '').slice(0, 300) };
  });
  console.log('fonte:', JSON.stringify(fonte).slice(0, 220));
  relato.textos.fonte = fonte.texto || '';
  await pag.waitForTimeout(400);
  await gravarQuadros(pag, 62);
  fecharCena();

  // =========================================================================
  // CENA 07 — o entregável: o relatório em PDF para o comitê
  // =========================================================================
  abrirCena('07_relatorio');
  await pag.evaluate(() => {
    const el = document.querySelector('[data-demo-rolagem]');
    if (el) el.scrollTop = el.scrollHeight;
  });
  // o produto tem botão próprio para isso — clicar nele mostra o recurso melhor do que digitar o pedido
  const btnPdf = pag.getByRole('button', { name: 'Gerar relatório em PDF' }).first();
  if (await btnPdf.count()) {
    await gravarQuadros(pag, 20); // meio segundo com o botão na tela antes do clique
    await clicarEm(pag, btnPdf);
    relato.textos.pdf_por_botao = true;
  } else {
    await digitar(pag, '#prompt-textarea', PEDIDO_PDF, 4);
    await gravarQuadros(pag, 12);
    await clicarEm(pag, pag.locator('[data-testid="send-button"]'));
    relato.textos.pdf_por_botao = false;
  }
  marcar('pedido_enviado');
  await gravar(pag, 5000); // tempo real no começo (o roteiro do relatório sendo carregado)
  // espera o painel do PDF abrir (ele abre sozinho quando o relatório sai), em time-lapse
  const limitePdf = Date.now() + 300000;
  let pdfAberto = false;
  while (Date.now() < limitePdf) {
    await pag.waitForTimeout(1500);
    await quadro(pag);
    pdfAberto = (await pag.locator('iframe[title], embed[type="application/pdf"], object[type="application/pdf"]').count()) > 0
      || (await pag.locator('[aria-label="Ampliar para a tela toda"]').count()) > 0;
    if (pdfAberto) break;
  }
  console.log(`painel do PDF aberto: ${pdfAberto}`);
  relato.textos.pdf_abriu = pdfAberto;
  if (pdfAberto) {
    await pag.waitForTimeout(2500); // o PDF renderiza a primeira página
    await gravarQuadros(pag, 50); // 2s com o PDF ao lado do chat
    marcar('pdf_ao_lado');
    const ampliar = pag.locator('[aria-label="Ampliar para a tela toda"]').first();
    if (await ampliar.count()) {
      await clicarEm(pag, ampliar);
      await pag.waitForTimeout(1800);
      marcar('pdf_ampliado');
      await gravarQuadros(pag, 55); // 2,2s com o PDF em tela cheia
      // rola uma página do relatório
      await pag.evaluate(() => {
        const q = document.querySelector('iframe');
        if (q) q.scrollIntoView({ block: 'center' });
      });
      await gravarQuadros(pag, 25);
    }
  } else {
    await gravarQuadros(pag, 30);
  }
  fecharCena();

  // =========================================================================
  // CENA 08 — grafo de conhecimento: o mesmo indicador com a fonte declarada
  // =========================================================================
  abrirCena('08_grafo');
  try {
    await pag.goto(`${BASE}/grafo?empresa=${CNPJ}`, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await pag.waitForSelector('.kg-exp-grade .kg-exp-card, .kg-node--empresa, .kg-node', { timeout: 90000 });
    await pag.waitForTimeout(2600);
    await gravar(pag, 1400);
    marcar('grafo_montado');
    const cat = pag.locator('.kg-node').filter({ hasText: 'Indicadores financeiros anuais' }).first();
    if (await cat.count()) {
      await clicarEm(pag, cat);
      await pag.waitForTimeout(1600);
      await gravarQuadros(pag, 18);
    }
    let alvo = pag.locator('.kg-node').filter({ hasText: 'Dívida líquida / EBITDA' }).first();
    if (!(await alvo.count())) alvo = pag.locator('.kg-node').filter({ hasText: 'Receita líquida' }).first();
    if (await alvo.count()) {
      await clicarEm(pag, alvo);
      await pag.waitForSelector('aside.kg-panel', { timeout: 20000 }).catch(() => {});
      await pag.waitForTimeout(1400);
      marcar('painel_do_no');
      await gravarQuadros(pag, 30);
      // realça a linha de 2024 e a linha da FONTE no painel lateral
      const p = await pag.evaluate(() => {
        const lado = document.querySelector('aside.kg-panel');
        if (!lado) return { ok: false };
        const tr = [...lado.querySelectorAll('tr')].find((r) => /\b2024\b/.test(r.innerText || ''));
        if (tr) {
          tr.scrollIntoView({ block: 'center' });
          tr.style.cssText = 'outline:2px solid #8ab4f8;outline-offset:-2px;background:rgba(138,180,248,.18)';
        }
        const fonte = [...lado.querySelectorAll('*')].find((e) =>
          /CVM DFP/i.test(e.textContent || '') && e.children.length === 0);
        return { ok: true, ano: tr ? tr.innerText.replace(/\s+/g, ' ') : '', fonte: fonte ? fonte.textContent.slice(0, 200) : '' };
      });
      relato.textos.grafo = p;
      console.log('painel do nó:', JSON.stringify(p).slice(0, 240));
      await pag.waitForTimeout(400);
      await gravarQuadros(pag, 50);
    }
  } catch (e) {
    console.log('erro na cena do grafo:', e.message);
  }
  fecharCena();

  // =========================================================================
  // CENA 09 — painel de dados: as 13 bases prontas para consultar
  // =========================================================================
  abrirCena('09_painel');
  try {
    await pag.goto(`${BASE}/painel`, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await pag.waitForSelector('section[aria-label="Indicadores"] button', { timeout: 90000 });
    await pag.waitForTimeout(2400);
    await gravarQuadros(pag, 42);
    marcar('painel_visao');
    await rolarJanela(pag, 9, 70); // desce até os gráficos
    await gravarQuadros(pag, 40);
  } catch (e) {
    console.log('erro na cena do painel:', e.message);
  }
  fecharCena();

  // =========================================================================
  // CENA 10 — linha do tempo: os eventos de sustentabilidade da Cemig
  // =========================================================================
  abrirCena('10_timeline');
  try {
    await pag.goto(`${BASE}/timeline/${CNPJ}?de=2023&ate=2025`, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await pag.waitForSelector('section[aria-labelledby="linha-do-tempo"]', { timeout: 120000 }).catch(() => {});
    await pag.waitForTimeout(3000);
    await gravarQuadros(pag, 40);
    marcar('timeline_visao');
    await rolarJanela(pag, 8, 70);
    await gravarQuadros(pag, 40);
  } catch (e) {
    console.log('erro na cena da timeline:', e.message);
  }
  fecharCena();

  // =========================================================================
  // CENA 11 — busca semântica: o trecho com documento, página e similaridade
  // =========================================================================
  abrirCena('11_busca');
  try {
    await pag.goto(`${BASE}/busca`, { waitUntil: 'domcontentloaded', timeout: 90000 });
    const campo = pag.locator('input[placeholder^="Em que página está isso?"]');
    await campo.waitFor({ timeout: 60000 });
    await pag.waitForFunction(() => /documentos indexados/.test(document.body.innerText), null, { timeout: 60000 })
      .catch(() => {});
    await pag.waitForTimeout(1200);
    await gravarQuadros(pag, 25);
    await digitar(pag, 'input[placeholder^="Em que página está isso?"]', BUSCA, 3);
    await gravarQuadros(pag, 10);
    await clicarEm(pag, pag.getByRole('button', { name: 'Buscar' }));
    marcar('buscou');
    await pag.waitForSelector('.rounded-lg.border.border-border-medium.p-4', { timeout: 60000 });
    await pag.waitForTimeout(1200);
    marcar('resultados');
    await gravarQuadros(pag, 45);
    // realça o primeiro resultado (documento, página e similaridade)
    const primeiro = await pag.evaluate(() => {
      const c = document.querySelector('.rounded-lg.border.border-border-medium.p-4');
      if (!c) return '';
      c.style.cssText += ';outline:2px solid #8ab4f8;outline-offset:2px;border-radius:10px';
      c.scrollIntoView({ block: 'center' });
      return c.innerText.replace(/\s+/g, ' ').slice(0, 240);
    });
    relato.textos.busca_primeiro = primeiro;
    console.log('1º resultado:', primeiro.slice(0, 160));
    await pag.waitForTimeout(400);
    await gravarQuadros(pag, 45);
  } catch (e) {
    console.log('erro na cena da busca:', e.message);
  }
  fecharCena();

  await ctx.close();
  await nav.close();
  fs.writeFileSync(path.join(T, 'relato.json'), JSON.stringify(relato, null, 1));
  console.log('\nrelato em', path.join(T, 'relato.json'));
})().catch((e) => { console.error('ERRO:', e.stack); process.exit(1); });
