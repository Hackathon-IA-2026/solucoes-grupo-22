# FINDINGS — Base de Pesquisa para Inteligência Comparativa da Transição Energética

**Projeto:** CoppeZIP (Equipe ZIP)
**Branch:** `claude-sonnet-5`
**Modelo:** Claude Sonnet 5 (orquestrador) + 5 subagentes paralelos
**Data:** 13 de setembro de 2026
**Pergunta-guia:** *Como transformar os relatórios financeiros e socioambientais que as empresas do setor elétrico são obrigadas a divulgar em inteligência comparativa, capaz de revelar, de forma rápida e rastreável, como cada companhia investe, se posiciona e avança na transição energética?*

> **Diferencial metodológico desta pesquisa:** todos os 5 subagentes foram instruídos a **baixar e inspecionar dados reais** (não apenas verificar que uma URL responde 200) — CSVs foram abertos e suas colunas reais conferidas, PDFs foram lidos com `pdftotext` e números reais extraídos com página de origem, a API não-documentada da B3 foi descoberta por engenharia reversa, e falhas reais (404, 403/WAF, links mortos, nomenclatura enganosa) foram documentadas como achados, não escondidas. Isso torna este documento auditável célula por célula.

---

## SUMÁRIO EXECUTIVO

O ecossistema de dados do setor elétrico brasileiro tem uma característica rara: a camada **física/regulatória (ANEEL/ONS/EPE/BNDES)** é excelente, estruturada e com CNPJ como chave de junção; a camada **financeira (CVM)** é estruturada mas o conteúdo ESG textual (FRE 2.7/4.1) não vem tabulado — exige extração de PDF/HTML; e a camada **ESG corporativa (relatórios de sustentabilidade)** está em PDFs nativos de boa qualidade, com índices remissivos GRI/SASB que facilitam a extração por IA.

**Cinco achados que mudam a estratégia do produto:**

1. **O relatório de sustentabilidade IFRS S1/S2 no Brasil é VOLUNTÁRIO desde maio/2026** (Resolução CVM 244, que revogou a obrigatoriedade que entraria em vigor em 2026 prevista pela Resolução CVM 193/2023). A partir de 01/01/2027 vale o regime **"pratique ou explique"**. Isso significa que o universo de empresas com relato climático estruturado **não é exaustivo por lei** — quem não divulga também é um sinal competitivo (e o produto deve capturar as duas coisas).
2. **A CVM não usa XBRL nos dados abertos.** DFP/ITR/FRE são ZIPs de CSV com plano de contas fixo/variável — já estruturado, sem necessidade de parser XBRL (Arelle é irrelevante aqui). O conteúdo ESG textual do FRE (itens 1.8/2.7 governança sustentável e 4.1 risco climático) **não está em nenhum CSV** — só existe dentro do documento completo (PDF/HTML) linkado pelo índice.
3. **BNDES "operações de financiamento não automáticas" tem CNPJ por contrato individual** — é o melhor proxy de investimento em transição energética financiado por banco público que existe em dados abertos, com 5.587 registros específicos do subsetor "Energia Elétrica".
4. **A B3 tem uma API JSON não-documentada** (`GetPortfolioDay`) que devolve a composição diária dos índices IEE (código real: `IEEX`), ISE B3 (código real: `ISEE`) e ICO2 (`ICO2`) — muito mais barato que fazer scraping do site (que é um SPA em JS).
5. **CCEE bloqueia scraping via WAF (Akamai)** — `curl`/`requests` simples recebem 403; é preciso `WebFetch`/browser headless para essa fonte específica.

Abaixo, o detalhamento por área, com tabelas de fontes, formato, processabilidade e as citações/páginas reais extraídas de relatórios ESG de 10 empresas.

---

## 1. DADOS FINANCEIROS ESTRUTURADOS — CVM, B3, ANBIMA

*(pesquisado e baixado por subagente dedicado — 8 arquivos CVM baixados e inspecionados linha a linha, API da B3 descoberta e testada, planilha ANBIMA de 1.925+1.282+845 linhas aberta com openpyxl)*

### 1.1 Tabela-síntese

| Fonte | URL direta | Formato | Frequência | Granularidade | Proc. (1-5) | Relevância |
|---|---|---|---|---|---|---|
| CVM DFP (anual) | `dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_AAAA.zip` | ZIP → 19 CSVs `;`, ISO-8859-1 | Anual (2010–2026) | Linha de conta contábil por empresa/ano/consolidado ou individual | 5 | Receita, CAPEX, dívida, provisões ambientais |
| CVM ITR (trimestral) | `.../ITR/DADOS/itr_cia_aberta_AAAA.zip` | Idêntico ao DFP | Trimestral | Idêntica | 5 | Séries intra-ano |
| CVM FRE (estruturado) | `.../FRE/DADOS/fre_cia_aberta_AAAA.zip` | ZIP → 36 CSVs | Anual/eventual | Governança, capital, remuneração, diversidade | 4 | Contexto de governança — **não traz ESG/clima estruturado** |
| CVM FRE — itens 1.8/2.7 (ESG) e 4.1 (risco climático) | via `LINK_DOC` do CSV-índice → `rad.cvm.gov.br/ENETCONSULTA` | HTML/PDF do formulário completo | Anual/eventual | Texto livre por item | 2 | Altíssima em conteúdo, exige parsing/LLM |
| CVM FCA (cadastral) | `.../FCA/DADOS/fca_cia_aberta_AAAA.zip` | ZIP → 10 CSVs | Anual/eventual | Cadastro, auditor, DRI | 4 | Join de metadados |
| CVM CAD (cadastro mestre) | `dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv` | CSV único | Contínua | 1 linha/companhia | 5 | `SETOR_ATIV="Energia Elétrica"` → **90 companhias ativas** confirmadas |
| CVM IPE (documentos eventuais) | `.../IPE/DADOS/ipe_cia_aberta_AAAA.zip` | ZIP → CSV índice; `Link_Download` → PDF real | Contínua | 1 linha/documento | 3 (índice) / 1 (PDF) | Categorias **"Relatório de Sustentabilidade"/"Relato Integrado"** apontam direto pro PDF ESG |
| B3 API índices (não-documentada) | `sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/{base64}` | JSON | Diário | Ticker/peso por índice | 5 | `IEEX` (12 ativos), `UTIL` (16), `ICO2` (61), `ISEE` (68) — **testados e retornando dados reais** |
| ANBIMA — debêntures incentivadas (Lei 12.431) | `anbima.com.br/data/files/.../Tabela_12_431.xlsx` | XLSX, 3 abas | Periódica | Emissão individual: emissor, valor, spread, **setor** | 4 | Fonte primária de dívida "verde"/infraestrutura |

### 1.2 CD_CONTA confirmados (verificado cruzando CEMIG 002453 × CPFL 018660)

Os códigos de nível superior (`ST_CONTA_FIXA='S'`) são fixos e idênticos entre companhias:

- **DRE:** `3.01` Receita Líquida · `3.05` ≈EBIT · `3.11` Lucro Líquido (não existe conta nativa de EBITDA — somar D&A do DFC)
- **DFC-MI:** `6.01.01.02` Depreciação/Amortização (+ `3.05` = EBITDA aprox.) · `6.02.02` CAPEX imobilizado · `6.02.03` CAPEX intangível · `6.02.04` **CAPEX regulatório/ativo de contrato de concessão (IFRIC 12)** — típico de distribuidoras/transmissoras, rótulo varia por empresa
- **BPP:** `2.01.04`+`2.02.01` = Dívida bruta (subconta `.02` = debêntures) · `2.01.06.02.03`/`2.02.04.02.03` = **Provisões para Passivos Ambientais e Desativação**

### 1.3 Gotchas confirmados na prática

1. Encoding **ISO-8859-1**, separador `;`, decimal `.`
2. Sempre pegar a **maior `VERSAO`** por `CNPJ_CIA`+`DT_REFER` (retificações)
3. `ORDEM_EXERC` = `"ÚLTIMO"`/`"PENÚLTIMO"` — cuidado com encoding na comparação de string
4. `ESCALA_MOEDA` (`MIL`/`UNIDADE`) varia **dentro do mesmo arquivo**, entre empresas — normalizar sempre
5. Usar `_con_` (consolidado) para holdings; `_ind_` para subsidiárias sem consolidado
6. **FRE não tem atalho estruturado para ESG/risco climático** — é preciso baixar o documento completo via `LINK_DOC` e extrair texto
7. IPE `Link_Download` exige header `User-Agent` de navegador, senão falha silenciosamente
8. B3: código público ≠ código da API interna (`IEE`→`IEEX`, `ISE`→`ISEE`) — descoberto por tentativa/erro
9. `dados.gov.br` para debêntures incentivadas retornou **401** nesta sessão — usar o XLSX direto da ANBIMA
10. Bibliotecas Python reais confirmadas via GitHub API: `eudesrodrigo/brFinance`, `eduresser/cvm-sqlite`, `glourencoffee/pycvm`, `gustavomoers/BrazilianMarketDataCollector`. **`jordanestralioto/Global-Data-Finance`** (citado pela branch big-pickle) **existe** (GitHub API HTTP 200, conferido em 23/09/2026) — a versão original deste documento dizia que não existia porque o subagente só testou o nome genérico, sem o dono do repositório; corrigido nesta cópia.

---

## 2. DADOS REGULATÓRIOS E OPERACIONAIS — ANEEL, ONS, EPE, CCEE, BNDES

*(22 fontes testadas com curl nesta sessão, incluindo 1 teste negativo real de 404 e 1 bloqueio real de WAF documentados como achado)*

### 2.1 Tabela-síntese

| Fonte | URL (exemplo real testado) | Formato | Frequência | Granularidade | Chave de junção | Proc. | Relevância |
|---|---|---|---|---|---|---|---|
| ANEEL SIGA (capacidade instalada) | `.../download/siga-empreendimentos-geracao.csv` | CSV/XML/Parquet | Diária | Por usina | `CodCEG` + CNPJ embutido em texto | 4 | Parque gerador por empresa/fonte |
| ANEEL MMGD (geração distribuída) | `.../empreendimento-geracao-distribuida.parquet` | Parquet/CSV/ZIP | Mensal | Por empreendimento/UC | Distribuidora + código | 5 | Proxy investimento em GD |
| ANEEL DEC/FEC | `.../indicadores-continuidade-...-2020-2029.csv` | CSV/Parquet | Mensal | Por conjunto de UCs | `NumCNPJ` direto | 4 | Qualidade/investimento em O&M |
| ANEEL Tarifas homologadas | `.../tarifas-homologadas-distribuidoras-energia-eletrica.csv` | CSV/XML | Por reajuste | Por distribuidora | `NumCNPJDistribuidora` direto | 4 | Componentes tarifárias |
| ANEEL P&D (Lei 9.991) | `.../proj-ped-energia-eletrica.csv` | CSV | Contínua | Por projeto/empresa | `NumCPFCNPJ` direto | 5 | Investimento em inovação/transição |
| ANEEL PEE (eficiência energética) | `.../projetos-eficiencia-energetica-empresa.csv` | CSV | Contínua | Por projeto/empresa | Nome do agente (precisa reconciliar) | 3 | Investimento social/eficiência |
| ANEEL Resultado de Leilões | `.../resultado-leiloes-geracao.csv` | CSV | Por leilão | Por empreendimento | `CodCEG` + nome vencedor | 4 | Expansão contratada e preço |
| ANEEL PDD (Plano Desenv. Distribuição) | `.../pdd-distribuicao-aneel.csv` | CSV | Anual | Por distribuidora/UF | `NumCPFCNPJ` direto | 5 | **CAPEX planejado vs. realizado por empresa** |
| ANEEL SIGET (transmissão/RAP) | `siget-contrato-agente.csv` ⋈ `siget-contrato-empreendimento-obra-modulo.csv` | CSV | Diária | Por contrato/módulo | `NumCNPJ` + join por `IdeCcd` → `VlrHisRct` (RAP) | 3 (exige join) | **RAP = receita regulada real da transmissora** |
| ONS Geração por usina | `GERACAO_USINA-2_AAAA.csv` (S3) | CSV/Parquet | Horária | Por usina/hora | `ceg` (cruza c/ SIGA) | 5 | Operação real vs. outorgada |
| ONS Curtailment eólico/solar | `RESTRICAO_COFF_EOLICA_AAAA_MM.csv` | CSV/XLSX | Mensal/semi-horária | Por usina | `ceg` | 4 | Ineficiência de rede que penaliza renováveis |
| ONS ENA/EAR, CMO | `ENA_DIARIO_SUBSISTEMA_AAAA.csv`, `CMO_SEMIHORARIO_AAAA.csv` | CSV/XLSX/Parquet | Diária/semi-horária | Subsistema | Sem CNPJ (contexto) | 5 | Risco hidrológico, preço spot |
| EPE Anuário (Dados Brutos) | `epe.gov.br/.../Dados%20brutos.xlsx` | XLSX | Anual | Consumo por UF/setor | Sem CNPJ | 3 | Contexto de mercado |
| EPE PDE 2035 (dados completos + transmissão) | `.../PDE 2035_Dados_Relatório Final.zip` + `Empreendimentos_Transmissão.xlsx` | ZIP/XLSX | Quinquenal | Nacional + por obra futura | `SIGET.codDMSE` | 3-4 | Pipeline oficial de expansão (R$3,5 tri) |
| CCEE PLD, ACL/ACR, Geração UHE/MRE | `dadosabertos.ccee.org.br` (⚠️ WAF bloqueia curl — usar WebFetch) | CSV | Mensal/horário | Submercado/usina | Parcial (nome, sem CNPJ) | 2 (acesso) | Sinal de preço + migração ao mercado livre |
| **BNDES Operações não automáticas** | `.../operacoes-financiamento-operacoes-nao-automaticas.csv` | CSV | Por contrato, desde 2002 | **Por operação/cliente** | **`cnpj` direto + `cliente`** | 5 | **Melhor proxy de investimento financiado por banco público** — 5.587 registros "Energia Elétrica" |
| BNDES Desembolsos por setor CNAE (agregado) | `.../desembolsos-por-setor-cnae-desembolsos.csv` | CSV | Mensal desde 1995 | 4 macro-setores | Nenhuma | 4 | Baixa granularidade — usar como contexto, não fonte primária |

### 2.2 Achados-chave

- **CNPJ é a chave universal** do lado financeiro/regulatório (ANEEL tarifas/P&D/PDD/DEC-FEC/SIGET-Agente, BNDES); **CodCEG** é a chave universal do lado físico (SIGA, ONS, leilões) — o pipeline precisa das duas tabelas de-para.
- **SIGET exige join de 2 arquivos** (`Contrato Agente` ⋈ `Contrato Empreendimento Obra Módulo` via `IdeCcd`) para chegar na RAP por empresa — não é óbvio, vale documentar no código.
- **BNDES "operações não automáticas"** é o achado mais valioso desta área: contrato individual, CNPJ, nome do cliente, produto (ex.: Eletropaulo recebeu R$277mi+R$795mi+R$182mi em "Distribuição de Energia Elétrica").
- **CCEE tem WAF ativo (Akamai)** — todo teste com `curl` retornou 403 "Acesso bloqueado", inclusive no subdomínio de download dedicado (`pda-download.ccee.org.br`). `WebFetch` (fingerprint de navegador) conseguiu acessar o mesmo conteúdo. **Implicação de arquitetura:** a coleta CCEE não pode ser `curl`/`requests` simples — precisa de headers realistas ou Playwright/Selenium.
- **ONS confirma nomenclatura previsível por ano** — teste de `GERACAO_USINA-2_2026.csv` deu 404 real (arquivo do ano corrente ainda não publicado); o pipeline deve tratar isso como caso normal.
- Datasets **sem chave de empresa** (ENA/EAR, CMO, PLD, Anuário EPE) servem só como contexto de mercado/hidrológico, não para comparação direta entre companhias.

---

## 3. RELATÓRIOS DE SUSTENTABILIDADE / ESG DAS EMPRESAS

*(10 PDFs de 10 empresas diferentes efetivamente baixados e lidos com `pdftotext`, >1.400 páginas — números abaixo têm página de origem citada)*

### 3.1 Tabela por empresa

| Empresa | Relatório | URL direta (testada) | Frameworks | Processabilidade | Destaques |
|---|---|---|---|---|---|
| **Engie Brasil** | RS 2024 (152p) | engie.com.br/wp-content/uploads/2025/04/Engie_RS2024_PT.pdf (exige header Referer) | GRI, SASB IF-EU, TCFD/TNFD, CDP | Nativo, sumário GRI/SASB p.118 | 100% renovável; CAPEX recorde R$9,7 bi |
| **CPFL Energia** | RA24 resumido (15p) | grupocpfl.com.br/.../CPFL_RA24_Versão Resumida.pdf | GRI/Pacto Global citados, sem tabela GEE | Raso (é versão de marketing) | Meta carbono neutro desde 2025; 96% renovável |
| **Cemig** | RAS 2024 (161p) | novoportal.cemig.com.br/.../Relatorio-Anual-de-Sustentabilidade-2024.pdf | GRI+Suplemento Setorial Elétrico, SASB, TCFD, CDP, Relato Integrado | Excelente — índice GRI p.144, SASB p.156 | Net Zero 2040; asseguração Bureau Veritas (ISAE 3000) |
| **Auren Energia** | RA 2024 (126p) | aurenenergia.com.br/.../AUREN_relan24.pdf | GRI, SASB, TCFD, **ISSB/IFRS S1-S2** anunciado p/ 2026 | Boa — tabelas GRI p.88-89 | 100% renovável; asseguração Bureau Veritas |
| **ISA Energia Brasil (ex-CTEEP)** | RAS 2024 (185p) | ri.isaenergiabrasil.com.br/.../relatorio-anual-isacteep-2024.pdf | GRI (coluna "asseguração" por indicador), TCFD/IFRS S2, CDP nota B | Excelente | 100% do Escopo 1+2 **já neutralizado** (créditos Verra + I-RECs); CAPEX recorde R$3,6bi; ESG PwC / DFs Deloitte |
| **Eneva** | Relato Integrado 2025 (170p) | fd-siteeneva.../RI_Eneva2025_PT.pdf | GRI, SASB, TCFD, **ISSB/ESRS/IFRS S1-S2 com Readiness Assessment KPMG** | Nativo; **tem Databook ESG em XLSX separado** | Escopo 1: 5,8Mt (+20% YoY, mais térmica gás/carvão) |
| **Axia Energia (ex-Eletrobras)** | RAS 2025 (168p) | axia.com.br/documents/.../relatorio-anual-sustentabilidade-2025 | GRI, SASB, TCFD, TNFD, CDP A List, IFRS S2 | Excelente, séries históricas limpas | Net Zero **2030** (mais agressivo do setor); Escopo 1 caiu -96% em 2 anos (3,99Mt→92,9kt) |
| **Neoenergia** | RAS 2024 (339p) | neoenergia.com/documents/.../relatorio_neoenergia_aneel_2024 | GRI, SASB, TCFD (nota: absorvida pelo IFRS S2), ISSB/IFRS S1-S2, CDP score A | Boa | ~90% renovável; meta 20 gCO2e/kWh 2030; CAPEX R$9,8bi; asseguração Deloitte |
| **EDP Brasil** | RAS 2024 (136p) | edp.com/.../Relatorio Anual de Sustentabilidade 2024.pdf | GRI, SASB, TCFD — **sem menção a ISSB/IFRS S1-S2** | Boa | 100% renovável desde 2024 (venda usina a carvão Pecém); Net Zero 2040 |
| **Taesa** | RS 2024 (206p) | ri.taesa.com.br/.../TAESA-Relatorio-de-Sustentabilidade-2024.pdf | GRI, SASB, IFRS S1/S2 citados de leve — **sem CDP nem asseguração externa mencionada** | Boa, tabela GEE clara p.170-171 | Intensidade piorou 0,0385→0,0545 tCO2/MWh (reflexo da matriz nacional) |

**Casos com link testado mas conteúdo problemático (documentado para não repetir o erro):** Equatorial (o PDF encontrado é da subsidiária de seguros, não do grupo elétrico — holding usa portal JS sem link direto), Alupar ("2024" no nome do arquivo = conteúdo real de 2023), Copel (portal dinâmico, só documentos de apoio têm URL estável), Light (nenhum relatório pós-2021 — sinal de baixa maturidade ESG associável à recuperação judicial), Energisa (versão em inglês achada, português bloqueado por sessão).

### 3.2 Números reais extraídos (com página)

| Empresa | Escopo 1 (tCO2e) | Escopo 2 (tCO2e) | Escopo 3 (tCO2e) | Pág. |
|---|---:|---:|---:|---|
| Engie Brasil (2024) | 17.361,38 | n/d | 242.514,38 | p.73 |
| Cemig (2024) | 42.860,81 | 376.174,25 | 5.911.209,35 | p.139-140 |
| Auren (2024) | 12.597,6 | 1.561,2 | 1.607,1 | p.88-89 |
| ISA Energia Brasil (2024) | 14.455 | — | 2.774 | p.82 |
| Axia/Eletrobras (2024→2025) | 2.332.558 → 92.957 | 460.723 → 410.857 | 1.918.957 → 558.794 | p.93 |
| Neoenergia (2024) | 108.284 | 415.898 | 2.023.488 | p.37 |
| Taesa (2024) | 9.367,51 | 77.270,32 | — | p.170 |
| Eneva (2025) | 5.800.000 | ver databook | ver databook | p.70 |

**Metas Net Zero:** Axia/Eletrobras 2030 · Cemig 2040 · Neoenergia <2040 · EDP Brasil 2040 · CPFL "desde 2025" · ISA Energia Brasil já neutralizado.

**CAPEX 2024 (mais recente):** Engie R$9,7bi · Neoenergia R$9,8bi · Axia R$9,6bi · ISA Energia Brasil R$3,6bi · Cemig R$5,7bi · EDP Brasil R$1,5bi (regional) + plano R$10bi até 2030.

### 3.3 Achados de processabilidade

1. **Todos os 10 PDFs são nativos/pesquisáveis** — nenhum é scan de imagem.
2. **Índices remissivos GRI/SASB (Disclosure→Página)** são o padrão entre os líderes (Cemig, Axia, ISA Energia Brasil, Neoenergia, Auren) — mapeáveis por regex/tabela sem LLM pesado.
3. **Eneva é o único achado com Databook ESG em Excel separado** (7,7MB) — melhor caso de processabilidade encontrado.
4. Cartas de asseguração às vezes são **imagem embutida** dentro de PDF nativo (Eneva p.167-168 ficou vazia na extração de texto) — atenção ao desenhar o pipeline.
5. **ISSB/IFRS S1-S2 já citado** por Auren, Neoenergia, Eneva, ISA Energia Brasil, Axia — ausente em EDP Brasil e Taesa: é um eixo de comparação direto sobre maturidade regulatória.
6. **Nomenclatura de arquivo/link é enganosa** em pelo menos 2 casos confirmados — o pipeline deve validar ano/empresa no conteúdo real da capa, não confiar no nome do arquivo.
7. Portais JS-only (mziq, mídia dinâmica) em Copel/Light/parte de Neoenergia-Alupar não expõem link direto estável — vão precisar de browser headless.

---

## 4. FRAMEWORKS REGULATÓRIOS E BENCHMARKS ESG

*(pesquisa focada no status regulatório atual — set/2026 — com fontes primárias CVM/IFRS/B3/TPI)*

| Framework/Benchmark | Autoridade | Status atual (set/2026) | Formato | Automatização |
|---|---|---|---|---|
| **IFRS S1/S2 via Resolução CVM 193→244** | CVM + CBPS | **VOLUNTÁRIO desde 29/mai/2026** (Res. 244 revogou a obrigatoriedade prevista p/ 2026). "Pratique ou explique" a partir de 01/01/2027 (justificativa via comunicado ao mercado se não divulgar; quem divulga mantém por ≥3 exercícios) | PDF/relatório narrativo (XBRL ainda não obrigatório no Brasil para esse relatório) | Média |
| **ISSB IFRS S1/S2** | IFRS Foundation | Vigente globalmente como baseline; no Brasil é a base técnica do reporte voluntário | Estruturado por tópico, mas divulgado em PDF | Média-Alta |
| **GRI** | GRI/GSSB | **Não existe Sector Standard GRI dedicado a "Electric Utilities"** hoje (pipeline setorial cobre Oil&Gas/Coal/Agricultura/Mineração; Utilities não confirmado). Legado usado: **G4 Electric Utilities (EU1-EU30)**, 2013 | Índice de conteúdo em tabela | Baixa-Média |
| **SASB Electric Utilities & Power Generators (IF-EU)** | Sob ISSB desde ago/2022 | **Em revisão ativa**: consulta pública ISSB 26/mar–24/jul/2026 propõe nova métrica **IF-EU-110a.7** ("como riscos de transição climática influenciam o CAPEX") — ainda não ratificada em set/2026 | Códigos fixos, tabela padronizada | **Alta** — o mais tabulável dos frameworks |
| **CSRD/ESRS (UE)** | EC/EFRAG | **"Omnibus" aprovado pelo Conselho em 24/fev/2026** — limiares sobem para >1.000 funcionários e >€450mi faturamento; empresas "onda 1" fora do novo escopo ficam isentas 2025/26; ESRS simplificados previstos meados 2026 | **XBRL/ESEF obrigatório** onde aplicável | Alta (onde aplicável) — afeta indiretamente subsidiárias BR de grupos europeus (Engie, EDP, Neoenergia/Iberdrola) |
| **Taxonomia Sustentável Brasileira (TSB)** | Min. Fazenda/CITSB | Instituída (Decreto 12.705/2025), regimento CITSB aprovado abr/2026 — **ainda não é exigência de disclosure**, reguladores setoriais têm até 2027 para decidir integração | Sem padrão de reporte definido ainda | Baixa (prematuro) |
| **TCFD** | Extinto out/2023 | Absorvido integralmente pelo IFRS S2 — "TCFD" hoje é sinônimo histórico | — | — |
| **SBTi** | Independente | Neoenergia (net-zero 2039, validada) e Engie Brasil (meta ≤43MtCO2e certificada) confirmadas; CPFL/Eletrobras não confirmadas nesta pesquisa | Dashboard público consultável | Alta |
| **CDP (Climate/Water)** | Independente | Ciclo 2026 aberto; scores públicos A-D- por empresa/setor | Questionário estruturado, respostas parciais públicas | Média-Alta |
| **TPI (Transition Pathway Initiative)** | Ligado à LSE | Cobertura confirmada: Eletrobras/Axia, Cemig, Equatorial (páginas dedicadas) | **Dataset aberto e estruturado (CSV/planilha)** | **Alta** — um dos poucos benchmarks abertos e comparáveis |
| **B3 ISE** | B3 | 21ª carteira (04/mai/2026): 69 empresas/38 setores. Elétricas: Axia, Cemig, Copel, Eneva, Engie, Equatorial, ISA Energia, Vibra, CPFL | Lista simples (via API `ISEE` descoberta) | Média |
| **B3 ICO2** | B3+GVces | 65 empresas 2026; 14 cumprem as 10 práticas integralmente; ISA Energia Brasil no índice pelo 4º ano | Lista + metodologia PDF | Média-Alta |

**Mudanças críticas 2025-2026 que corrigem premissas antigas:** obrigatoriedade do IFRS S1/S2 **revogada** (não confundir com "obrigatório 2026"); TCFD **não existe mais como entidade**; CSRD **enxugada pelo Omnibus** (menos empresas brasileiras afetadas indiretamente); SASB Electric Utilities **em revisão** com métrica nova de CAPEX de transição (IF-EU-110a.7) ainda não ratificada; TSB **existe mas não é obrigatória ainda**.

---

## 5. FERRAMENTAS E PIPELINE TÉCNICO

*(verificação de existência/atividade real via GitHub API e benchmarks públicos)*

| Ferramenta | Função | Licença | Evidência de atividade | Recomendação |
|---|---|---|---|---|
| **Docling** (IBM) | Parser universal (PDF/DOCX/XLSX/HTML/**XBRL**), modelo TableFormer | MIT | 66,3k stars | **Extrator principal** — 97,9% acurácia em tabelas de sustentabilidade (benchmark Procycons 2025), roda em CPU |
| **MinerU** | Parser complexo (fórmulas, OCR, layout difícil) | Apache 2.0 + termos | 57,2k stars | Bom mas lento (0,54 pág/s) — não prioritário para hackathon |
| **Marker** | PDF→Markdown, melhor score olmOCR-bench (76%) | Apache 2.0 (código) | Ativo, "Marker 2" 2026 | Boa 2ª opção, precisa GPU pra performance completa |
| **MarkItDown** (Microsoft) | Conversor genérico → Markdown | MIT | Viral, 25k+ stars/2 semanas | Utilitário para Excel/CSV auxiliares, não para tabela financeira complexa |
| **pdfplumber / Camelot** | Extração de tabela sem ML | MIT | Ativas (⚠️ fork `pypdf_table_extraction` do Camelot foi arquivado abr/2025) | Fallback pontual para tabelas problemáticas |
| **Instructor** (Pydantic) | Força LLM a devolver JSON validado, com retry automático | MIT | 11k stars, 3M+ downloads/mês | **Peça central da extração numérica confiável** — schema com campo obrigatório de página/documento fonte reduz alucinação |
| **Arelle** | Validador XBRL | Apache 2.0 | Ativo | **Irrelevante aqui** — CVM não publica XBRL instance documents |
| **RAGFlow** | RAG com citação nativa | Apache 2.0 | 73,2k stars | Melhor citação pronta, mas exige Docker + 16GB RAM — pesado para 24-48h |
| **LlamaIndex** | RAG com `source_nodes` | MIT | Muito ativa | Melhor equilíbrio esforço/citação para hackathon |
| **DuckDB** | OLAP embutido + extensão VSS (vetores) | MIT | Muito ativa | **Recomendado como único banco** — zero servidor |
| **cvm-sqlite / pycvm** | Parsers prontos para CVM | MIT | Existem (poucas stars, checar antes de depender) | Testar rapidamente antes de escrever parser do zero |
| **Dados-Abertos-Setor-Eletrico-Brasileiro** | Wrapper ANEEL/ONS/CCEE | MIT | 65 stars, CI ativo | Vale testar para complementar dados operacionais |

**Recomendação de stack mínimo (24-48h):** Docling (extração) + Instructor/Pydantic (schema numérico com campo de página obrigatório) + DuckDB único (dados tabulares CVM/ANEEL + fatos extraídos + embeddings via VSS) + LlamaIndex leve para RAG com citação. Evitar Postgres/RAGFlow/Docker — infraestrutura desnecessária para o prazo.

```python
# Esqueleto mínimo do fluxo fim-a-fim
converter = DocumentConverter()  # Docling
chunks = converter.convert("relatorio_esg.pdf").document.export_to_markdown_chunks(with_page_numbers=True)

class EmissaoGEE(BaseModel):
    empresa: str; ano: int; escopo: int = Field(ge=1, le=3)
    valor_tco2e: float = Field(gt=0); documento_fonte: str; pagina_fonte: int

client = instructor.from_anthropic(Anthropic())
fato = client.chat.completions.create(model="claude-sonnet-5", response_model=EmissaoGEE,
       max_retries=2, messages=[...])  # Instructor rejeita e re-tenta se schema falhar

# Resposta ao usuário: SEMPRE citar [documento, página] do source_node recuperado no DuckDB/VSS
```

---

## 6. MAPEAMENTO DE EMPRESAS (consolidado desta pesquisa)

| Empresa | Tickers | CNPJ (confirmado em DFP real) | Situação de nome | Net Zero | Maturidade ESG observada |
|---|---|---|---|---|---|
| Axia Energia (ex-Eletrobras) | ELET3/6 → AXIA3 | 00.001.180/0001-26 | Renomeada, confirmada no DFP 2024 | 2030 | Alta (CDP A List, GRI+SASB+TCFD+TNFD) |
| Engie Brasil | EGIE3 | 02.474.103/0001-19 | — | — (100% renovável) | Alta |
| Cemig | CMIG4 | 17.155.730/0001-64 | — | 2040 | Alta (asseguração ISAE 3000) |
| Neoenergia | NEOE3 | 01.083.200/0001-18 | — | <2040 | Alta |
| Taesa | TAEE11 | 07.859.971/0001-30 | — | não confirmado | Média (sem CDP/asseguração externa citada) |
| Auren Energia | AURE3 | 39.646.410/0001-41 | — | — | Alta |
| ISA Energia Brasil (ex-CTEEP) | TRPL4/ISAE4 | 02.998.611/0001-04 | Renomeada | já neutralizado | Alta (ESG PwC, DFs Deloitte) |
| Equatorial Energia | EQTL3 | 03.220.438/0001-73 | Holding sem relatório ESG com URL estável localizado | — | Baixa processabilidade (portal JS) |
| Copel | CPLE6 | 76.483.817/0001-20 | Portal dinâmico | — | Baixa processabilidade |
| Light | LIGT3 | — | **Sem relatório pós-2021** | — | Baixa (recuperação judicial) |
| Energisa | — | 00.864.214/0001-06 | Versão PT bloqueada por sessão | — | Não confirmada |
| EDP Brasil | ENBR3 | 03.983.431/0001-03 | — | 2040 | Boa, mas sem ISSB/IFRS S1-S2 ainda |
| Eneva | ENEV3 | 04.423.567/0001-21 | — | não é foco (térmica) | Boa (Databook Excel) |
| Alupar | ALUP11 | 08.364.948/0001-38 | ⚠️ Link "2024" = conteúdo real 2023 | — | Não confirmada |
| CPFL Energia | CPFE3 | 02.429.144/0001-93 | Relatório completo não localizado (só resumo raso) | desde 2025 | Baixa processabilidade do resumo público |

---

## 7. IMPLICAÇÕES PARA O PRODUTO COPPEZIP

1. **A regra de inclusão de empresas deve ser dupla**: (a) empresas que divulgam relatório ISSB voluntariamente — capturar frameworks/asseguração/maturidade; (b) empresas que não divulgam ou divulgam de forma rasa (CPFL resumida, Taesa sem asseguração, Light sem relatório desde 2021) — isso também é sinal competitivo e deve aparecer no comparativo, não ser tratado como dado faltante.
2. **Duas chaves de junção, não uma**: CNPJ (financeiro/regulatório) e CodCEG (físico/geração) — construir a tabela de-para logo no início do pipeline.
3. **BNDES por contrato + CVM DFP + ANEEL PDD/SIGET** juntos dão uma visão de **investimento real** (quem recebeu financiamento público, quanto declarou de CAPEX contábil, quanto a ANEEL projeta para a rede) — cruzamento ainda não visto em nenhuma branch anterior do projeto.
4. **CCEE precisa de coletor especial** (WebFetch/browser) — não incluir no primeiro sprint de scraping automatizado por `requests`/`curl`.
5. **Eneva** é o único caso com Databook Excel — ótimo para prova de conceito de extração 100% estruturada (sem LLM) antes de atacar os PDFs mais difíceis.
6. **Nunca confiar no nome do arquivo/link** para ano ou empresa — validar sempre pelo conteúdo da capa (2 casos reais de erro encontrados: Alupar e Equatorial).

---

## ANEXO — Todos os links verificados nesta pesquisa (por categoria)

**CVM:** dados.cvm.gov.br (DFP/ITR/FRE/FCA/CAD/IPE — todos baixados) · rad.cvm.gov.br/ENETCONSULTA (FRE completo)
**B3:** sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay (IEEX/UTIL/ICO2/ISEE — testados) · b3.com.br (Diretrizes ISE 2025)
**ANBIMA:** anbima.com.br/data/files/.../Tabela_12_431_042024.xlsx
**ANEEL:** dadosabertos.aneel.gov.br (SIGA, MMGD, DEC/FEC, tarifas, P&D, PEE, leilões, PDD, SIGET — todos baixados)
**ONS:** dados.ons.org.br + ons-aws-prod-opendata.s3.amazonaws.com (geração, curtailment, ENA, CMO, capacidade — todos baixados)
**EPE:** epe.gov.br (Anuário Dados Brutos, PDE 2035 completo + transmissão — todos baixados)
**CCEE:** dadosabertos.ccee.org.br + pda-download.ccee.org.br (via WebFetch — curl bloqueado por WAF)
**BNDES:** dadosabertos.bndes.gov.br (operações não automáticas, desembolsos por setor — baixados)
**Relatórios ESG (PDFs reais baixados e lidos):** Engie, CPFL, Cemig, Auren, ISA Energia Brasil, Eneva (+Databook XLSX), Axia/Eletrobras, Neoenergia, EDP Brasil, Taesa
**Frameworks:** conteudo.cvm.gov.br (Res. 193/244) · ifrs.org (S1/S2, revisão SASB 2026) · globalreporting.org (Sector Program) · sasb.ifrs.org · efrag.org (Omnibus, ESRS) · transitionpathwayinitiative.org · cdp.net · sciencebasedtargets.org
**Ferramentas:** github.com/docling-project/docling · github.com/opendatalab/MinerU · github.com/datalab-to/marker · github.com/567-labs/instructor · github.com/infiniflow/ragflow · github.com/eduresser/cvm-sqlite · github.com/glourencoffee/pycvm · github.com/diegonerii/Dados-Abertos-Setor-Eletrico-Brasileiro
