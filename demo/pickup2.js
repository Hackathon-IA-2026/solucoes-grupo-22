// Segundo passe de pickup, sem chamar o modelo. Corrige o que o primeiro deixou pela metade:
//   - para qualquer geração pendente e RECARREGA a conversa, para gravar numa tela parada
//     (no passe anterior o chat ainda estava escrevendo e o texto cru ':::artifact{...' aparecia)
//   04_conclusao -> o veredito realçado, com as duas linhas de "ferramentas usadas" visíveis
//   06_fonte     -> o parágrafo que declara conta por conta (CVM DFP 2024, conta 3.01, 3.05, 6.02)
//   07b_pdf      -> O CLÍMAX: o artefato do relatório abre em TELA CHEIA (o painel já nasce ampliado
//                   quando o artefato é PDF) e as páginas passam com a roda do mouse
//   08_grafo     -> o mesmo do passe 1, mais a rolagem do painel até a seção FONTE
//
// Rodar: node pickup2.js

const { chromium } = require('/impa/home/a/al.richard.viana/projects/clean-hack/coppezip/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const C = require('./comum');

const CNPJ = '17155730000164'; // Cemig holding
const relato = { fps: C.FPS, cenas: [], textos: {} };
const G = C.criarGravador(relato);

(async () => {
  const { nav, ctx } = await C.abrirNavegador(chromium);
  const pag = await ctx.newPage();
  await C.entrar(pag);

  // ---- abre a conversa da comparação e garante que nada está sendo gerado
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
  const url = pag.url();
  await pag.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 }); // recarrega: tela parada
  await pag.waitForSelector('.agent-turn', { timeout: 60000 });
  await pag.waitForTimeout(4000);
  relato.textos.url = url;
  console.log('conversa:', url);

  // a resposta da comparação é o PRIMEIRO turno do agente
  await pag.evaluate(() => {
    const t = document.querySelectorAll('.agent-turn')[0];
    if (t) t.setAttribute('data-demo-resposta', '1');
  });
  const rolagem = await pag.evaluate(C.MARCAR_ROLAGEM);
  console.log('container de rolagem:', JSON.stringify(rolagem));
  await G.cursor(pag, false);

  // =========================================================================
  // CENA 04 — o veredito: a conclusão realçada, logo abaixo das ferramentas usadas
  // =========================================================================
  G.abrirCena('04_conclusao');
  const veredito = await pag.evaluate(([borda, fundo]) => {
    const alvos = [...document.querySelectorAll('[data-demo-resposta] p,[data-demo-resposta] li')];
    const p = alvos.find((e) => /Conclus.o \(modo conclusivo\)/i.test(e.textContent || ''))
           || alvos.find((e) => /Conclus/i.test(e.textContent || ''));
    if (!p) return { ok: false };
    p.style.cssText = `background:${fundo};border-left:3px solid ${borda};padding:12px 16px;border-radius:8px`;
    // enquadra a pergunta + as ferramentas + o veredito
    const topo = document.querySelector('[data-demo-resposta]');
    if (topo) topo.scrollIntoView({ block: 'start' });
    const el = document.querySelector('[data-demo-rolagem]');
    if (el) el.scrollTop = Math.max(0, el.scrollTop - 150);
    return { ok: true, texto: (p.textContent || '').slice(0, 200) };
  }, [C.REALCE_BORDA, C.REALCE_FUNDO]);
  console.log('veredito:', JSON.stringify(veredito).slice(0, 220));
  relato.textos.veredito = veredito.texto || '';
  await pag.waitForTimeout(600);
  await G.gravarQuadros(pag, 90); // 3,6s de leitura
  G.fecharCena();

  // =========================================================================
  // CENA 05 — a tabela: rolagem suave até a tabela, com a linha da alavancagem realçada
  // =========================================================================
  G.abrirCena('05_tabela');
  await G.rolarGravando(pag, 7, 130);
  G.marcar('tabela_na_tela');
  const realce = await pag.evaluate(([borda, fundo]) => {
    const tab = document.querySelector('[data-demo-resposta] table');
    if (!tab) return { ok: false };
    tab.scrollIntoView({ block: 'center' });
    const linha = [...tab.querySelectorAll('tr')].find((r) => /Dívida líquida\s*\/\s*EBITDA/i.test(r.innerText || ''));
    if (linha) linha.style.cssText = `outline:2px solid ${borda};outline-offset:-2px;background:${fundo};border-radius:6px`;
    return { ok: true, realcou: !!linha, linha: linha ? linha.innerText.replace(/\s+/g, ' ') : '' };
  }, [C.REALCE_BORDA, C.REALCE_FUNDO]);
  console.log('realce da tabela:', JSON.stringify(realce));
  relato.textos.linha_alavancagem = realce.linha || '';
  await pag.waitForTimeout(400);
  await G.gravarQuadros(pag, 85);
  G.fecharCena();

  // =========================================================================
  // CENA 06 — a prova: o parágrafo que diz de que conta da CVM saiu cada número
  // =========================================================================
  G.abrirCena('06_fonte');
  const fonte = await pag.evaluate(([borda, fundo]) => {
    const alvos = [...document.querySelectorAll('[data-demo-resposta] p,[data-demo-resposta] li')];
    const p = alvos.find((e) => /conta 3\.01|conta 6\.02/i.test(e.textContent || ''))
           || alvos.find((e) => /CVM DFP 2024/i.test(e.textContent || ''));
    if (!p) return { ok: false, amostra: alvos.slice(0, 5).map((e) => (e.textContent || '').slice(0, 70)) };
    p.style.cssText = `background:${fundo};border-left:3px solid ${borda};padding:12px 16px;border-radius:8px`;
    p.scrollIntoView({ block: 'center' });
    const el = document.querySelector('[data-demo-rolagem]');
    if (el) el.scrollTop = Math.max(0, el.scrollTop - 60); // deixa a tabela aparecer embaixo
    return { ok: true, texto: (p.textContent || '').slice(0, 300) };
  }, [C.REALCE_BORDA, C.REALCE_FUNDO]);
  console.log('fonte:', JSON.stringify(fonte).slice(0, 320));
  relato.textos.fonte = fonte.texto || '';
  await pag.waitForTimeout(400);
  await G.gravarQuadros(pag, 90);
  G.fecharCena();

  // =========================================================================
  // CENA 07b — O CLÍMAX: o relatório em PDF, em tela cheia
  // =========================================================================
  G.abrirCena('07b_pdf');
  await pag.evaluate(() => {
    const el = document.querySelector('[data-demo-rolagem]');
    if (el) el.scrollTop = el.scrollHeight;
  });
  await pag.waitForTimeout(2000);
  let cartao = pag.locator('button').filter({ hasText: /\.pdf/i }).first();
  if (!(await cartao.count())) cartao = pag.locator('button').filter({ hasText: /Clique para abrir/i }).first();
  let pdfOk = false;
  if (await cartao.count()) {
    await cartao.scrollIntoViewIfNeeded();
    await pag.waitForTimeout(700);
    await G.gravarQuadros(pag, 20); // o cartão do entregável na tela
    G.marcar('cartao_na_tela');
    await G.clicarEm(pag, cartao);
    await G.gravar(pag, 2600); // o painel entra deslizando e o PDF renderiza
    pdfOk = (await pag.locator('iframe[title]').count()) > 0;
    console.log('iframe do PDF:', pdfOk);
    if (pdfOk) {
      await pag.waitForTimeout(2600);
      await G.cursor(pag, false);
      G.marcar('pdf_na_tela');
      await G.gravarQuadros(pag, 55); // 2,2s parado na capa
      // passa as páginas com a roda do mouse sobre o visualizador
      await pag.mouse.move(C.CSS.width / 2, C.CSS.height / 2);
      for (let i = 0; i < 110; i++) {
        await pag.mouse.wheel(0, 24);
        await G.quadro(pag);
      }
      G.marcar('pdf_rolado');
      await G.gravarQuadros(pag, 35);
    } else {
      await G.gravarQuadros(pag, 40);
    }
  } else {
    console.log('não achei o cartão do artefato');
    await pag.screenshot({ path: path.join(C.T, 'falha_artefato.png') });
  }
  relato.textos.pdf_ok = pdfOk;
  G.fecharCena();

  // =========================================================================
  // CENA 08 — grafo: o mesmo indicador da tabela, com a série anual e a fonte declarada
  // =========================================================================
  G.abrirCena('08_grafo');
  try {
    await pag.goto(`${C.BASE}/grafo?empresa=${CNPJ}`, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await pag.waitForSelector('.kg-exp-grade .kg-exp-card, .kg-node--empresa, .kg-node', { timeout: 90000 });
    await pag.waitForTimeout(2600);
    await G.cursor(pag, false);
    await G.gravarQuadros(pag, 30);
    G.marcar('grafo_montado');

    const cat = pag.locator('.kg-node').filter({ hasText: 'Indicadores financeiros anuais' }).first();
    if (await cat.count()) {
      await G.clicarEm(pag, cat);
      await G.gravar(pag, 1200);
      await G.gravarQuadros(pag, 20);
      G.marcar('categoria_aberta');
    }

    // o indicador é um CHIP do painel ("Contém (24)"), não um nó: clicar revela, seleciona e leva a câmera
    let chip = pag.locator('button.kg-link-chip').filter({ hasText: /Dívida líquida\s*\/\s*EBITDA/i }).first();
    if (!(await chip.count())) chip = pag.locator('button.kg-link-chip').filter({ hasText: /EBITDA/i }).first();
    if (await chip.count()) {
      await G.clicarEm(pag, chip);
      await G.gravar(pag, 2000);
      G.marcar('indicador_revelado');
      await G.cursor(pag, false);
      const p = await pag.evaluate(([borda, fundo]) => {
        const lado = document.querySelector('aside.kg-panel') || document.querySelector('.kg-panel');
        if (!lado) return { ok: false };
        const tr = [...lado.querySelectorAll('tr')].find((r) => /\b2024\b/.test(r.innerText || ''));
        if (tr) tr.style.cssText = `outline:2px solid ${borda};outline-offset:-2px;background:${fundo}`;
        lado.setAttribute('data-demo-painel', '1');
        return { ok: true, ano: tr ? tr.innerText.replace(/\s+/g, ' ') : '' };
      }, [C.REALCE_BORDA, C.REALCE_FUNDO]);
      relato.textos.grafo = p;
      console.log('painel do indicador:', JSON.stringify(p).slice(0, 200));
      await G.gravarQuadros(pag, 55); // 2,2s no valor de 2024
      // desce o painel até a seção FONTE: é o fecho do argumento de rastreabilidade
      await G.rolarGravando(pag, 9, 60, '[data-demo-painel]');
      const f = await pag.evaluate(([borda, fundo]) => {
        const lado = document.querySelector('[data-demo-painel]');
        if (!lado) return { ok: false };
        const alvo = [...lado.querySelectorAll('div,span,a,td')]
          .find((e) => /CVM|DFP/i.test(e.textContent || '') && e.children.length === 0);
        if (alvo) {
          alvo.scrollIntoView({ block: 'center' });
          const caixa = alvo.closest('.kg-card,.kg-ref,li,div') || alvo;
          caixa.style.cssText += `;outline:2px solid ${borda};background:${fundo};border-radius:8px`;
        }
        return { ok: true, fonte: alvo ? alvo.textContent.replace(/\s+/g, ' ').slice(0, 160) : '' };
      }, [C.REALCE_BORDA, C.REALCE_FUNDO]);
      console.log('fonte no grafo:', JSON.stringify(f).slice(0, 220));
      relato.textos.grafo_fonte = f.fonte || '';
      await pag.waitForTimeout(400);
      await G.gravarQuadros(pag, 62);
    } else {
      console.log('não achei o chip do indicador');
      await G.gravarQuadros(pag, 40);
    }
  } catch (e) {
    console.log('erro na cena do grafo:', e.message);
  }
  G.fecharCena();

  fs.writeFileSync(path.join(C.T, 'relato_pickup2.json'), JSON.stringify(relato, null, 1));
  console.log(`\nrelato em ${path.join(C.T, 'relato_pickup2.json')}`);
  await ctx.close();
  await nav.close();
})().catch((e) => { console.error('ERRO:', e.stack); process.exit(1); });
