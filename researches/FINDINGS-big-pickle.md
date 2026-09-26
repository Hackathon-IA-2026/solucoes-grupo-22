# FINDINGS — Base de Pesquisa para Inteligência Comparativa da Transição Energética no Setor Elétrico

**Projeto:** CoppeZIP (Equipe ZIP)
**Branch:** `big-pickle`
**Data da pesquisa:** 13/09/2026
**Pergunta-guia:** *Como transformar os relatórios financeiros e socioambientais que as empresas do setor elétrico são obrigadas a divulgar em inteligência comparativa, capaz de revelar, de forma rápida e rastreável, como cada companhia investe, se posiciona e avança na transição energética?*

> **Método:** pesquisa web com 5 subagentes paralelos (dados financeiros CVM/B3; dados regulatórios ANEEL/EPE/ONS; relatórios ESG das empresas; frameworks regulatórios; ferramentas de extração/tooling). URLs verificadas via webfetch/websearch em set/2026. Frameworks regulatórios detalhados em `FRAMEWORKS.md` (arquivo irmão).

---

## 1. RESUMO EXECUTIVO — O QUE FOI ENCONTRADO

O ecossistema brasileiro de dados do setor elétrico é **fragmentado porém altamente acessível por download direto ou API CKAN** (sem chave). Não há XBRL nas demonstrações financeiras (a CVM usa CSV/XML proprietário via Empresas.NET) e o relatório ISS de sustentabilidade **deixou de ser obrigatório** (CVM 244/2026). A base física de verdade (MW por fonte, DEC/FEC, geração horária, tarifas) está aberta em ANEEL/ONS/EPE e é o ponto de ancoragem para comparabilidade que não depende do regime de disclosure. As empresas do setor já publicam relatórios de sustentabilidade FY2025 (2026) com GRI + SASB, e várias com alinhamento ISSB/TCFD e metas SBTi validadas.

**Achados críticos que corrigem premissas anteriores:**
1. **Resolução CVM 244/2026** revogou a obrigatoriedade da Resolução CVM 193 (ISSB). O reporte de sustentabilidade virou voluntário + regime "pratique ou explique" a partir de 01/01/2027.
2. **GRI 11 é do setor de Óleo & Gás**, não de elétricas. O setor elétrico usa o legado **GRI G4 Electric Utilities (EU1–EU14)**; o padrão setorial "Power production and energy utilities" está priorizado na GRI mas ainda não foi desenvolvido.
3. **DFP/ITR da CVM NÃO são XBRL** — são XML proprietário (Empresas.NET) publicados como CSV no portal de dados abertos. Não existe "BPE" para companhias.
4. **Eletrobras não aparece na base DFP/ITR 2024 verificada** (pós-reorganização pós-privatização; ex-ativos sob outros nomes como AXIA ENERGIA). Necessário confirmar caso a caso.
5. CSVs da CVM (e BNDES) são **encoding Latin-1/Windows-1252**, separador `;` → é o ponto nº1 de "code smell" para ingestão.

---

## 2. FONTES — DADOS FINANCEIROS ESTRUTURADOS

### 2.1 CVM Dados Abertos (fonte primária de demonstrações financeiras)
- **Portal:** https://dados.cvm.gov.br — plataforma CKAN, licença ODbL, **sem autenticação**. API CKAN: `https://dados.cvm.gov.br/api/3/action/package_search`.
- **DFP (anual):** https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp
  - Download: `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ANO}.zip` (2010–2026, ~13 MB/ano). ZIP = **19 CSVs** (BPA, BPP, DRE, DRA, DFC-MD, DFC-MI, DMPL, DVA — consolidado e individual —, composicao_capital, parecer e índice geral com `LINK_DOC` para o formulário).
  - Encoding **Latin-1/ISO-8859-1**; separador `;`.
  - Campos-chave: `CNPJ_CIA; DT_REFER; VERSAO; DENOM_CIA; CD_CVM; GRUPO_DFP; MOEDA; ESCALA_MOEDA; ORDEM_EXERC; DT_INI_EXERC; DT_FIM_EXERC; CD_CONTA; DS_CONTA; VL_CONTA; ST_CONTA_FIXA`.
  - Dicionário/META: `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/META/meta_dfp_cia_aberta_txt.zip`.
- **ITR (trimestral):** https://dados.cvm.gov.br/dataset/cia_aberta-doc-itr
  - Download: `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_{ANO}.zip` (2011–2026, ~31 MB/ano). Atualização semanal.
- **FCA (Formulário Cadastral):** `.../DOC/FCA/DADOS/fca_cia_aberta_{ANO}.zip` (9 CSVs).
- **FRE (Formulário de Referência):** `.../DOC/FRE/DADOS/fre_cia_aberta_{ANO}.zip` — **inclui item de ESG (2.7)**; baseline estruturado de governança ESG.
- **CAD (Cadastro de companhias) — base mestra:** `https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv` (CSV diário; contém **SETOR="Energia Elétrica"**, CNPJ, CD_CVM, situação, DRI, auditor).
- Catálogo completo: `https://dados.cvm.gov.br/misc/InventarioBasesCVM.pdf`.

### 2.2 Indicador de CAPEX (proxy de investimento)
- **Fonte primária:** arquivo `DFC_MI` (demonstração de fluxo de caixa, método indireto, consolidado), contas:
  - `6.02.01` — Aquisição de imobilizado (**proxy de CAPEX**)
  - `6.02.02` — Alienação de imobilizado
  - `6.02.03` — Intangível
  - SQL: `SELECT VL_CONTA FROM dfp_cia_aberta_DFC_MI WHERE CD_CONTA='6.02.01' AND ORDEM_EXERC='ÚLTIMO'`.
- **Atenção:** valores em `ESCALA_MOEDA` (MIL/UNIDADE); multiplicar adequadamente. Nome do arquivo = ano-base (DT_REFER), não ano de entrega. `dfp_cia_aberta_2025.zip` aparecia no catálogo mas 404 no filesystem (set/2026); `2026` quase vazio (empresas com exercício não-calendário).

### 2.3 Download Múltiplo / texto livre das notas
- `https://seguro.bmfbovespa.com.br/rad/download/SolicitaDownload.asp` (POST) — **requer login Empresas.NET**; XML com anexos e notas explicativas (texto livre com detalhes de CAPEX por segmento, MW adicionados, metas de descarbonização). Especificações: `https://www.rad.cvm.gov.br/ENET/documentos/EspecificacaoArquivoXML_DemonstracaoFinanceiraPadronizada.xlsx`.

### 2.4 B3 — mercado e índices
- **COTA­HIST (histórico de preços):** `https://bvmf.bmfbovespa.com.br/MarketData/Arquivos/COTAHIST_AAAA.zip` (TXT, sem token).
- **BrAPI.dev (preços+fundamentais):** `https://brapi.dev/api/quote/{TICKER}?modules=...` (token gratuito por volume).
- **ISE B3 (Índice de Sustentabilidade):** https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-sustentabilidade/indice-de-sustentabilidade-empresarial-ise-b3.htm
  - Carteira 2026 (69 empresas): Auren, Axia Energia, Cemig, Copel, CPFL, Eneva, Engie, Equatorial, ISA Energia, Motiva. Engie #5 (score 90,51), CPFL #7, Copel #10.
  - Critérios: score ISE ≥ corte, mínimo por tema, qualitativa ≥70%, **RepRisk RRI ≤50**, **CDP-Climate ≥ "C"**, mínimos do setor; 7 dimensões (inclui Mudança do Clima).
  - Metodologia (PDF): `https://www.b3.com.br/data/files/B2/F2/C9/24/98E615107623A41592D828A8/ISE-Metodologia-pt-br.pdf` | Carteira: `https://iseb3.com.br/carteira-iseb3`.
- **IEE (Índice Energia Elétrica):** https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-segmentos-e-setoriais/indice-de-energia-eletrica-iee-b3.htm
- **RI da B3:** https://ri.b3.com.br (DFs, releases, fatos relevantes de todas as listadas).

### 2.5 Empresas do setor elétrico presentes na base consolidada CVM
Cemig (+Cemig GT/Transmissão/Distribuição), CPFL Energia (+CPFL Renováveis/Geração/Transmissão/Piratininga), Neoenergia (COELBA, CELPE, COSERN), Copel (+GT/Distribuição), Engie Brasil, CESP, Eneva, Equatorial Energia, Auren Energia (+Operações/Participações), Alupar, Energisa (+Transmissão), Light (em RJ), CEB, CEEE-D, CELGPAR, EPR Infraestrutura PR, **Axia Energia Sul (ex-CGT Eletrosul)**, Rio Paranapanema / AES Brasil, Serena Geração, Celesc, Vibra Energia, **Taesa (Transmissora Aliança)**. **Eletrobras não apareceu** na DFP 2024 verificada. ISA CTEEP sob "ISA Energia".

---

## 3. FONTES — DADOS REGULATÓRIOS E OPERACIONAIS (ANEEL, ONS, EPE, CCEE, BNDES)

### 3.1 ANEEL Dados Abertos (CKAN)
- **Portal:** https://dadosabertos.aneel.gov.br — API CKAN v3: `https://dadosabertos.aneel.gov.br/api/3/action/` (`package_list`, `package_search`, `datastore_search_sql`). Formatos: CSV, XML, Parquet, JSON. Licença ODbL.
- **Indicadores de continuidade DEC/FEC:** https://dadosabertos.aneel.gov.br/dataset/indicadores-coletivos-de-continuidade-dec-e-fec — CSV/Parquet por subárea, 2000–presente (atualização mensal). Bench de qualidade entre distribuidoras.
- **SIGA (Banco de Informações de Geração):** https://dadosabertos.aneel.gov.br/dataset/siga-sistema-de-informacoes-de-geracao-da-aneel — CSV mensal + diário (`siga-empreendimentos-geracao-diario.csv`); painel: https://www.aneel.gov.br/siga. **Granularidade por usina**: fonte, potência, concessionária, município, status, data de operação → **rastreia o investimento/expansão por empresa.**
- **Geração Distribuída (MMGD):** https://dadosabertos.aneel.gov.br/dataset/relacao-de-empreendimentos-de-geracao-distribuida — ZIP ~105 MiB (sem datastore; download do arquivo).
- **Tarifas:** https://dadosabertos.aneel.gov.br/dataset/tarifas-distribuidoras-energia-eletrica | Componentes: `https://dadosabertos.aneel.gov.br/dataset/componentes-tarifarias` (datastore SQL, resource_id `e8717aa8-2521-453f-bf16-fbb9a16eea39`).
- **SAMP (mercado das distribuidoras):** https://dadosabertos.aneel.gov.br/pt_BR/dataset/samp — consumo/receita por distribuidora, 2003–presente.
- **INDGER (indicadores gerenciais):** https://dadosabertos.aneel.gov.br/pt_BR/dataset/indger-indicadores-gerenciais-da-distribuicao
- **Painel interativo (dashboards):** https://portalrelatorios.aneel.gov.br/indicadoresDistribuicao
- **Dados geoespaciais:** https://dadosabertos-aneel.opendata.arcgis.com/ (Shapefile, GeoJSON, Feature Service).
- **API de Outorgas (governo federal):** https://www.gov.br/conecta/catalogo/apis/outorga (API REST JSON, consulta por CEG).

### 3.2 ONS Dados Abertos
- **Portal:** https://dados.ons.org.br — 83 datasets; CSV/XLSX/Parquet/JSON; CC-BY; arquivos em S3 (`ons-aws-prod-opendata`). Notebooks: https://github.com/ONSBR/DadosAbertos
- **Geração por usina (horária):** https://dados.ons.org.br/dataset/geracao-usina-2 — 2000–presente, por usina, base horária → **fator de capacidade real de parques por empresa.**
- **Balanço por subsistema:** https://dados.ons.org.br/dataset/balanco-energia-subsistema
- **Fator de capacidade eólico/solar:** https://dados.ons.org.br/dataset/fator-capacidade-2
- **Capacidade instalada:** https://dados.ons.org.br/dataset/capacidade-geracao

### 3.3 EPE
- **BEN (Balanço Energético Nacional):** https://www.epe.gov.br/pt/publicacoes-dados-abertos/publicacoes/balanco-energetico-nacional-ben | Dados abertos: https://www.epe.gov.br/pt/publicacoes-dados-abertos/dados-abertos/dados-abertos-do-balanço-energético-nacional-ben | Dashboard: https://dashboard.epe.gov.br/apps/ben/ — **XLSX** (matrizes), 1970–presente, por fonte e UF.
- **Anuário Estatístico de Energia Elétrica:** https://www.epe.gov.br/pt/publicacoes-dados-abertos/publicacoes/anuario-estatistico-de-energia-eletrica — XLSX.
- **PDE (Plano Decenal de Expansão):** https://www.epe.gov.br/pt/publicacoes-dados-abertos/publicacoes/plano-decenal-de-expansao-de-energia-2035 — PDF + XLSX suplementar; projeções de expansão por fonte; referência para comparar investimentos declarados × metas nacionais.
- **EPE Interativa:** https://www.epe.gov.br/pt/abcdenergia/epe-interativa

### 3.4 CCEE
- **Dados abertos:** https://dadosabertos.ccee.org.br — API CKAN. PLD histórico, energia incentivada (CCEAR), balanço mensal, contas setoriais (CDE, CCC, RGR), InfoMercado.
- **Mercado mensal:** https://www.ccee.org.br/dados-e-analises/dados-mercado-mensal

### 3.5 BNDES (financiamento de transição)
- **Dados abertos:** https://dadosabertos.bndes.gov.br — CSV + API CKAN, ODbL. **Encoding Windows-1252.**
- **Operações de financiamento:** https://dadosabertos.bndes.gov.br/dataset/operacoes-financiamento — por operação: valor, subsetor BNDES ("Energia Elétrica", códigos CNAE D3511581–D3511598), produto (Finem/Finame), UF; desde 2002.
- **Desembolsos:** https://dadosabertos.bndes.gov.br/dataset/desembolsos — desde 1995, por setor CNAE/subsetor BNDES → **fluxo financeiro público para energia limpa vs fóssil.**
- Finem Energia (condições): http://www.bndes.gov.br/wps/portal/site/home/financiamento/produto/bndes-finem-energia

### 3.6 Emissões (governo)
- **SIRENE (MCTI):** https://sireneorganizacionais.mcti.gov.br/emissoes — inventário nacional por setor (1990–presente) + inventários organizacionais voluntários. Exportação Excel; sem API.
- **Fator de emissão da matriz elétrica (MCTI, Decreto 9.172/2017 art. 6º II):** essencial para Escopo 2 padronizado.
- **SBCE (mercado de carbono, Lei 15.042/2024; Decreto 12.768/2025):** https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2024/lei/l15042.htm — UTEs >25 k tCO2e/ano; ainda não operacional (set/2026).

### 3.7 Complementos
- **PB GHG Protocol — Registro Público de Emissões (FGVces):** https://registropublicodeemissoes.fgv.br/ (programa: https://eaesp.fgv.br/centros/centro-estudos-sustentabilidade/projetos/programa-brasileiro-ghg-protocol) — 674 organizações, >7.000 inventários; Escopos 1 e 2 obrigatórios, 3 opcional; download individual de PDF/XLSX; **sem API** (scraping).
- **Projeto Dados Abertos do Setor Elétrico (Python):** https://github.com/diegonerii/Dados-Abertos-Setor-Eletrico-Brasileiro (unifica ANEEL/ONS/CCEE).

---

## 4. FONTES — RELATÓRIOS DE SUSTENTABILIDADE / ESG POR EMPRESA (documentos diretos)

> Padrões observados nos relatórios FY2025: GRI + SASB (IF-EU) + ISSB/IFRS parcial + TCFD; vários com asseguração limitada por auditoria externa. Links diretos confirmados (set/2026).

| Empresa | Relatório (exercício) | URL direta | Landing/arquivo |
| :-- | :-- | :-- | :-- |
| **Taesa** | RAS 2025 (18ª ed.; GRI, SASB, dupla materialidade GRI 3/IFRS S1) | https://ri.taesa.com.br/wp-content/uploads/2018/11/Relatorio-de-Sustentabilidade-da-TAESA-2025.pdf | https://ri.taesa.com.br/outros-documentos/relatorio-de-sustentabilidade-2025/ |
| **Cemig** | RAS 2025 (GRI+SASB) | https://www.cemig.com.br/wp-content/uploads/2026/06/ras-2025.pdf | https://www.cemig.com.br/sustentabilidade |
| Cemig | Inventário GEE 2025 | https://www.cemig.com.br/wp-content/uploads/2026/06/gee-2026.pdf | |
| Cemig | Relatório TCFD 2025 | https://www.cemig.com.br/wp-content/uploads/2025/07/tcfd-2025.pdf | |
| Cemig | Plano de Ação Climática | https://www.cemig.com.br/wp-content/uploads/2026/04/plano-acao-climatica.pdf | |
| **Engie Brasil** | RS 2025 (GRI+ISSB+SASB+TCFD+TNFD; >R$6 bi investidos; 12,4 GW) | https://www.engie.com.br/wp-content/uploads/2026/04/ENGIE_RS2025_PT.pdf | https://ri.engie.com.br |
| **CPFL** | RA 2025 (GRI+SASB+relato integrado; SBTi validado; CDP Double A) | https://www.grupocpfl.com.br/sites/default/files/2026-03/CPFL2025_v06.pdf | https://ri.cpfl.com.br |
| **Neoenergia** | RAS 2025 (GRI p.112, SASB p.120, asseguração p.127) | https://www.neoenergia.com/documents/d/guest/relatorio-de-sustentabilidade-neoenergia-2025 | https://ri.neoenergia.com |
| Neoenergia | Inventário GEE 2025 | https://www.neoenergia.com/documents/d/guest/inventario_de_gee_2025 | |
| **ISA Energia Brasil (CTEEP)** | RAS 2025 (plano de transição climática; CAPEX R$5,1 bi +40,4%) | https://s3.sa-east-1.amazonaws.com/static.cteep.aatb.com.br/Arquivos/Download/relatorio-anual-isaenergia-2025.pdf | https://ri.isaenergiabrasil.com.br/pt/sustentabilidade/relatorio-anual-de-sustentabilidade (arquivo 2013–2025) |
| ISA Energia | Net Zero 2050 | https://www.isaenergiabrasil.com.br/sustentabilidade/net-zero-2050 | |
| **Eneva** | Relato Integrado 2025 + Databook ESG (xlsx) | https://www.eneva.com.br/sustentabilidade/relato-integrado/ | Idem (arquivo 2019–2024) |
| **Copel** | Relato Integrado 2025 | https://copelsustentabilidade.com/gestao-da-sustentabilidade/publicacoes-e-documentos-de-sustentabilidade/relatorios/relato-integrado/ | Base: https://api.mziq.com/mzfilemanager/v2/d/16a31b1b-5ecd-4214-a2e0-308a2393e330/18189167-784a-8f83-9eba-53328069d985?origin=2 |
| **Auren** | RA 2025 (publicado 30/04/2026; dupla materialidade IFRS S1/S2) | RA 2024 Exe.: https://www.aurenenergia.com.br/wp-content/uploads/2025/08/Auren-Relatorio-Anual-2024-Resumo-Executivo.pdf | https://ri.aurenenergia.com.br/esg/relatorio-anual-e-de-sustentabilidade-auren/ |
| **Eletrobras** | RA 2024 (RA 2025 ainda não publicado em set/2026) | https://eletrobras.com/pt/Documents/Eletrobras_RA_2024.pdf | https://www.eletrobras.com/pt/Paginas/Relatorio-Anual.aspx |
| Eletrobras | Resumo Executivo RA 2024 | https://eletrobras.com/pt/Documents/Eletrobras_RA_2024_Resumo_Executivo.pdf | |
| **Celesc** | Arquivo de relatórios GRI | https://www.celesc.com.br/arquivos/relatorios/ (ex.: `relatorio-sustentabilidade-2021.pdf`) | https://ri.celesc.com.br/a-celesc/sustentabilidade/ |
| **Equatorial** | 10ª ed. Relatório de Sustentabilidade (dez/2025) | (URL dinâmica MZ — buscar em RI) | https://ri.equatorialenergia.com.br |

**Metas SBTi / net zero confirmadas:** Cemig (SBTi validada jan/2025; net zero 2040 base 2021; -69,4% absoluta, -75,8% intensidade; CDP A List; Selo Ouro GHG 23/24/25; ICO2 B3) · Neoenergia (SBTi net zero 2039 validado 2025, base 2021) · CPFL (descarbonização SBTi validada; CDP Double A) · Copel (metas alinhadas a SBTi; carbono neutro 2030 escopo 1) · ISA Energia (net zero 2050) · Eneva (Selo Ouro GHG 5º ano; intensidade 0,37 tCO2e/MWh). Confirmar Engie, Equatorial, Taesa, Auren, Eletrobras em `sciencebasedtargets.org/companies-taking-action`.

**Dica operacional:** vários relatórios são hospedados em plataformas **MZ Group (`api.mziq.com/...mzfilemanager...`)** com URLs dinâmicas — o crawler deve renderizar/inspecionar HTML ou usar as landing pages.

---

## 5. FRAMEWORKS REGULATÓRIOS (resumo — detalhe em FRAMEWORKS.md)

| Framework | Status set/2026 | Relevância para CI de transição |
| :-- | :-- | :-- |
| **IFRS S1/S2 (ISSB)** | Vigente desde 01/01/2024 | Metrics de GHG, CAPEX climático, preço interno de carbono, remuneração atrelada a clima |
| **CVM Res. 193/2023 → 244/2026** | Obrigatório **revogado**; "pratique ou explique" desde 01/01/2027 | Lembrar: inclusão deve separar "quem divulga" vs "quem justifica não-divulgar" |
| **TCFD** | Dissolvido (10/2023), legado informacional | Checklist de 11 disclosures p/ extração semântica |
| **GRI** | G4 Electric Utilities (EU1–EU14); setorial "Power" em desenvolvimento | EU1 capacidade por fonte, EU2 geração líquida, EU3 clientes, EU4 km de linha |
| **SASB IF-EU** | Vigente, sob ISSB; revisão 2026 | **Melhor padrão por-indústria**: códigos fixos IF-EU-110a, 240a, 420a, 000.A–E → extração tabelar sem LLM |
| **CSRD/ESRS (UE)** | Omnibus I (EU/2026/470) em vigor; ESRS revisados adotados 03/07/2026 (FY2027+) | E1-5 mix de energia, E1-6 intensidade GHG por receita; datapoints XBRL |
| **EU Taxonomy** | Em vigor | **KPI de %CAPEX/Turnover/OpEx alinhado** — a métrica de "quanto investe em verde" |
| **TSB (Brasil)** | Decreto 12.705/2025; voluntária, depois mandatória | Futura comparação UE↔BR (transmissão como atividade habilitadora) |
| **IFRS Sustainability Taxonomy / ESRS XBRL** | Taxonomias publicadas | Modelo de datapoints para schemas Pydantic |

---

## 6. FERRAMENTAS E PIPELINE (extração/automação)

### 6.1 PDF e extração de tabelas
- **Docling** (IBM, MIT, ativo) — melhor para tabelas/relatórios financeiros; também parseia XBRL. https://github.com/DS4SD/docling
- **MinerU** (custom license) https://github.com/opendatalab/MinerU · **Marker** (Apache-2.0, reescrita v2/2026) https://github.com/datalab-to/marker · **MarkItDown** https://github.com/microsoft/markitdown · **pdfplumber/Camelot/Tabula/PyMuPDF** · **GROBID** (artigos, menos para relatórios).
- **Benchmark:** doccrush/document-parser-benchmark (Marker ~4.1, Docling ~3.3, MinerU ~3.3, MarkItDown ~1.65 de score) — confirmar no repositório.

### 6.2 Extração estruturada por LLM
- **LlamaParse** (pydantic-schema JSON) · **Instructor/Pydantic v2** (structured output) · **DeepEval** (LLM-as-judge p/ validação) · FinDocMind (multi-agente Pydantic+SQLAlchemy).

### 6.3 XBRL / CVM
- **Arelle** (Apache-2.0, validador certificado, SEC/ESEF; testado p/ CVM) https://github.com/Arelle/Arelle · py-xbrl · edgartools. *Nota: como a CVM não usa XBRL padrão, o uso de Arelle limita-se a iXBRL de jurisdições estrangeiras e à validação de taxonomia.*
- **Libs CVM Brasil:** `cvm-sqlite` (https://github.com/eduresser/cvm-sqlite), `brFinance_v2` (https://github.com/gustavo-ribeiro-santiago/brFinance_v2), `Global-Data-Finance` (https://github.com/jordanestralioto/Global-Data-Finance — DFP/ITR/FRE+COTAHIST→Parquet), `pycvm`, `cvmpy`, `brazilfi`, `dadosbr` (+MCP), `dados-b3-mcp`.

### 6.4 Datasets ESG abertos
- **TPI (Transition Pathway Initiative)** — metodologia/avaliação pública de utilities: https://www.transitionpathwayinitiative.org
- **CDP** — portal aberto; dados corporativos completos pagos. **SBTi** — dashboard empresas com meta: https://sciencebasedtargets.org/companies-taking-action
- World Bank ESG (país), ClimateWatch, OpenNetZero/Exerica (API grátis p/ S&P500).

### 6.5 RAG/Q&A sobre documentos financeiros
- **RAGFlow** (Apache-2.0, ativo; parsers MinerU/Docling) https://github.com/infiniflow/ragflow · Haystack 2 · Khoj. *Weaviate Verba: arquivado (não usar).*

---

## 7. FORMATO DE DADOS — MAPA PARA INGESTÃO

| Fonte | Formato | Acesso | Chave de junção |
| :-- | :-- | :-- | :-- |
| CVM DFP/ITR | CSV (`;`, Latin-1) | zip direto / API CKAN | CNPJ_CIA + CD_CVM |
| CVM CAD | CSV | direto | CNPJ → SETOR "Energia Elétrica" |
| CVM FRE/FCA | CSV/ZIP | direto | CD_CVM (+ item ESG 2.7) |
| ANEEL DEC/FEC, SIGA, SAMP, tarifas | CSV/Parquet/XML | API CKAN `datastore_search_sql` | distribuidora/concessionária (CNPJ) |
| ONS | CSV/XLSX/Parquet (S3) | direto | usina (código ONS ↔ CEG)
| EPE BEN/Anuário/PDE | XLSX/PDF | download | nacional/UF (não por empresa) |
| CCEE | CSV | API CKAN | agente |
| BNDES | CSV (Windows-1252) | API CKAN | CNAE D35 / subsetor BNDES |
| SIRENE / RPE FGV | Web/PDF/XLSX | scraping/export | organização/CNPJ |
| Relatórios ESG | PDF (MZ, wp-content…) | parser Docling/pdfplumber | CNPJ + ano-acessível |
| ISE B3 | Web/PDF (metodologia) | scraping | ticker + CNPJ |

---

## 8. MÉTRICAS HÍBRIDAS DE INTELIGÊNCIA COMPARATIVA (base para o painel)

Cruzamentos propostos (financeiro × físico × ESG), todos rastreáveis a documento/página:

- **Intensidade carbônica financeira:** `tCO2e (S1+S2) ÷ Receita Líquida` — CVM 193 (DFP) × inventário GHG.
- **Intensidade física:** `tCO2e ÷ GWh gerado` — inventário GHG × ONS/SIGA. (Eneva: 0,37 tCO2e/MWh como referência.)
- **CAPEX de transição (proxy):** conta `6.02.01` (DFC-MI) no DFP; refinar com EU Taxonomy %CapEx-aligned / releases de RI por segmento.
- **Eficiência do CAPEX verde:** `ΔEBITDA ÷ Investimento em transição`.
- **Alavancagem do mix:** `% de capacidade renovável nova (SIGA: usinas em construção/autorizadas) ÷ CAPEX declarado`.
- **Performance real de ativos:** fator de capacidade eólico/solar real (ONS) vs planejado (PDE/leilões).
- **Exposição regulatória a carbono:** potência térmica instalada (SIGA) × precificação futura (SBCE).
- **Posicionamento tarifário & qualidade:** TUSD/TE × DEC/FEC como proxy de reinvestimento em rede.
- **Rastreabilidade ESG:** content index GRI (raster de disclosures atendidas) + content index SASB IF-EU (extração tabelar sem LLM).

---

## 9. LIMITAÇÕES E RISCOS VERIFICADOS

1. **Encoding:** CVM Latin-1; BNDES Windows-1252 → decoding obrigatório na ingestão.
2. **Eletrobras fora da base DFP 2024** — tratar por CNPJ/ano e checar subsidiárias e entidades pós-privatização.
3. **Anomalias de disponibilidade** no filesystem da CVM (2025 404, 2026 vazio) — validar catálogo × arquivo.
4. **Relatórios MZ (Equatorial, Copel, Auren)** têm URLs dinâmicas → landing pages + HTML parsing.
5. **PBE GHG Protocol sem API** (scraping) e inventários voluntários (amostra não exaustiva).
6. **"Pratique ou explique" (CVM 244/26):** universo de arquivantes deixa de ser exaustivo — modelar os dois grupos.
7. **SBCE não operacional** ainda — monitorar (fator BAU futuro para UTEs).
8. Datas: `DT_REFER` refere-se ao ano-base; atualizações semanais/mensais por portal.

---

## 10. PRÓXIMOS PASSOS SUGERIDOS

1. Baixar `cad_cia_aberta.csv` → selecionar `SETOR="Energia Elétrica"`, `STATUS=ATIVO` → lista-mestra de CNPJ/CD_CVM.
2. Ingerir DFP/ITR 2019–2025 com `cvm-sqlite`/`Global-Data-Finance`; extrair CAPEX (`6.02.01`) e endividamento.
3. Baixar SIGA + ONS (capacidade e geração por usina) por CNPJ/concessionária → base física.
4. Baixar inventários GHG (RPE FGV) e dados ISE B3 → camada ESG quantitativa.
5. Coletar relatórios ESG/PIs das empresas (Tabela da seção 4) → Docling (+ VLM para tabelas/imagens).
6. Extrair structured output (Instructor/Pydantic) com schemas modelados nos **datapoints ESRS + códigos SASB IF-EU + IFRS S2**.
7. Carregar em DuckDB/pgvector com citação (documento+página) → RAG com guardrails → painel comparativo.

---

## ANEXO A — LINKS MESTRES (agrupados)

**Financeiro:** dados.cvm.gov.br · dados.cvm.gov.br/dataset/cia_aberta-doc-dfp · /cia_aberta-doc-itr · /cia_aberta-cad · /cia_aberta-doc-fre · /cia_aberta-doc-fca · cvm.gov.br/misc/InventarioBasesCVM.pdf · bvmf.bmfbovespa.com.br/MarketData/Arquivos/COTAHIST_AAAA.zip · brapi.dev · ri.b3.com.br · iseb3.com.br · b3.com.br (IEE)

**Regulatório/operacional:** dadosabertos.aneel.gov.br · andel.gov.br/siga · portalrelatorios.aneel.gov.br · dados.ons.org.br · github.com/ONSBR/DadosAbertos · epe.gov.br (BEN/Anuário/PDE, dashboard.epe.gov.br/apps/ben) · dadosabertos.ccee.org.br · dadosabertos.bndes.gov.br · sireneorganizacionais.mcti.gov.br/emissoes · registropublicodeemissoes.fgv.br · ralabc.aneel.gov.br

**Relatórios ESG (diretos):** tabela da seção 4 (Taesa, Cemig, Engie, CPFL, Neoenergia, ISA Energia, Eneva, Copel, Auren, Eletrobras, Celesc, Equatorial).

**Frameworks:** ifrs.org (S1/S2 + taxonomy digital) · conteudo.cvm.gov.br/legislacao/resolucoes/resol193.html · globalreporting.org/standards/sector-program · sasb.ifrs.org · eur-lex (CSRD/ESRS/EU Taxonomy) · ec.europa.eu/sustainable-finance-taxonomy/wizard · Decreto 12.705/2025 (TSB) · fsb-tcfd.org

**Ferramentas:** github.com/DS4SD/docling · github.com/opendatalab/MinerU · github.com/datalab-to/marker · github.com/microsoft/markitdown · github.com/Arelle/Arelle · github.com/infiniflow/ragflow · github.com/eduresser/cvm-sqlite · github.com/gustavo-ribeiro-santiago/brFinance_v2 · github.com/jordanestralioto/Global-Data-Finance · github.com/diegonerii/Dados-Abertos-Setor-Eletrico-Brasileiro · sciencebasedtargets.org/companies-taking-action · transitionpathwayinitiative.org