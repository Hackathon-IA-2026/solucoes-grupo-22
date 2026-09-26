# FRAMEWORKS & REGULAÇÕES DE DIVULGAÇÃO: Relatório de Pesquisa para Inteligência Comparativa da Transição Energética

**Projeto:** EnergyNexus (Equipe ZIP)
**Data:** Setembro de 2026
**Escopo:** Frameworks e regulamentações internacionais e brasileiras que governo/impositório de divulgação de dados financeiros e de sustentabilidade no setor elétrico, avaliando a **automatabilidade** de cada fonte para o motor de inteligência comparativa.

> **⚠️ ATENÇÃO — Correções críticas às premissas anteriores (FINDINGS.md):**
> 1. **Resolução CVM 244/2026 (29/05/2026) REVOGOU a obrigatoriedade da Resolução CVM 193.** O relatório ISSB saiu do regime obrigatório para o regime "pratique ou explique" (com firmeza de comparabilidade). O FINDINGS.md (linha 98) está desatualizado ao afirmar "obrigatória a partir de 2026 ... em XBRL".
> 2. **GRI 11 NÃO é de elétricas.** GRI 11 é *Oil and Gas* (GRI 12 = Coal, GRI 13 = Agriculture, GRI 14 = Mining). O setor elétrico usa o *GRI G4 Electric Utilities Sector Disclosures* (EU1–EU14) e o Sector Program da GRI inclui o setor **"Power production and energy utilities"** na lista priorizada, mas o padrão setorial ainda **não foi desenvolvido**.
> 3. **Formato XBRL do relatório da CVM 193 não foi confirmado.** O arquivamento é feito por sistema eletrônico da CVM como documento; o dado estruturado existe no FRE (aberto em CSV/XML) e a taxonomia digital existe para IFRS S2 (ISSB) e ESRS (EFRAG), mas não para o relatório em si.

---

## ÍNDICE DE FRAMEWORKS

| # | Framework | Autoridade | Status / Vigência | Foco para Transição Energética |
| :-- | :-- | :-- | :-- | :-- |
| 1 | ISSB IFRS S1/S2 | ISSB / IFRS Foundation | Vigente desde 01/01/2024; base global (IOSCO) | Clima, riscos de transição e físicos, Scope 1/2/3 |
| 2 | Resolução CVM 193/2023 (Br) | CVM + CBPS | Voluntário (2024+); obrigatoriedade **revogada em 2026**; "pratique ou explique" desde 2027 | Adoção IFRS S1/S2 no Brasil |
| 3 | TCFD | FSB (dissolvido em 10/2023) | Encerrado; migrado ao ISSB | 11 recomendações (governança, estratégia, risco, métricas) |
| 4 | GRI | GSSB / GRI | Contínuo; setoriais GRI 11–14 publicados | Impactos; G4 Electric Utilities (EU1–EU14) |
| 5 | SASB Electric Utilities & Power Generators | SASB / IFRS Foundation (ISSB) | Vigente; projeto renováveis "transicionado ao ISSB"; revisão 2026 em curso | IF-EU-110a, 240a, 420a etc. |
| 6 | CSRD / ESRS (EU) | EC / EFRAG | Diretiva 2022/2464; **Omnibus I (EU/2026/470) em vigor desde 18/03/2026**; ESRS revisados adotados 03/07/2026 (aplicam FY2027+) | ESRS E1 clima, energia e GHG |
| 7 | EU Taxonomy | EC (Reg. 2020/852; 2021/2139; 2021/2178) | Em vigor desde 2022; KPIs Turnover/CapEx/OpEx | Métrica comparável de "verde" (aligned vs eligible) |
| 8 | Taxonomia Sustentável Brasileira (TSB) | Ministério da Fazenda / CITSB | Decreto 12.705/2025; 2 fases (voluntária → mandatória) | Critérios TSC/DNSH para renováveis e transmissão |
| 9 | Dados digitais / XBRL | ISSB, EFRAG, CVM | IFRS Sustainability Taxonomy (04/2024); ESRS XBRL em revisão; CVM dados abertos | Base para automação e extração estruturada |

---

## 1. ISSB — IFRS S1 (Requisitos Gerais) e IFRS S2 (Clima)

- **Name:** IFRS S1 "General Requirements for Disclosure of Sustainability-related Financial Information"; IFRS S2 "Climate-related Disclosures".
- **Authority:** International Sustainability Standards Board (ISSB) — IFRS Foundation; recomendado pela IOSCO e endossado como baseline global.
- **URL (links verificados neste levantamento):**
  - Navigator ISSB: http://ifrs.org/issued-standards/ifrs-sustainability-standards-navigator/ifrs-s2-climate-related-disclosures
  - IFRS S2 + accompanying guidance (Acompanhamento "IG"): https://www.ifrs.org/content/dam/ifrs/publications/html-standards-issb/english/2023/issued/issbs2-ag.html
  - Perfil de adoção do Brasil: https://www.ifrs.org/content/dam/ifrs/publications/sustainability-jurisdictions/pdf-profiles/brazil-ifrs-profile.pdf
- **Relevance:** É o núcleo do regime brasileiro (via CVM 193/CBPS) e do quadro global; em elétricas, é a fonte primária para riscos físicos (seca/hidrologia, tempestades) e de transição (preço de carbono, repowering, P&D renovável), capital alocado para transição, preço interno de carbono e remuneração atrelada a metas climáticas.
- **Key metrics (IFRS S2, §29 e métricas cross-industry):** Emissões brutas GHG Scope 1, Scope 2 (métodos location e market) e Scope 3 (em tCO2e), intensidade de GHG; **métricas de transição (categoria a)**, incluindo % de receita/ativos/atividades vulneráveis à transição; **capital de deployment** para clima (CapEx/OpEx/financiamento); preço interno de carbono; % de remuneração de executivos vinculada a considerações climáticas; metas (base year, target year, KPI).
- **Data format:** Normas em texto (HTML/PDF); associada à **IFRS Sustainability Disclosure Taxonomy** (XBRL) publicada em 30/04/2024, interoperável com a IFRS Accounting Taxonomy.
- **Automatability:** ALTA — as métricas de IFRS S2 (GHG, alvos, CapEx climático, preço interno de carbono, remuneração) são taggeáveis em XBRL; os divulgadores publicam em PDF/HTML. Para o EnergyNexus: extração por documento (Docling + Instructor) com validação contra taxonomia; comparabilidade direta entre empresas que usam ISSB (padrão único de apresentação em 4 pilares).

---

## 2. BRASIL — Resolução CVM 193/2023 (IFRS S1/S2 via CBPS) e Resolução CVM 244/2026

- **Name:** Resolução CVM nº 193, de 20/10/2023, com alterações das Resoluções CVM 219/24, 227/25 e **244/26** (texto consolidado extraído na íntegra neste levantamento).
- **Authority:** Comissão de Valores Mobiliários (CVM), com normas emitidas pelo Comitê Brasileiro de Pronunciamentos de Sustentabilidade (CBPS — CBPS 01 = IFRS S1, CBPS 02 = IFRS S2) e aprovadas pela CVM.
- **URL (verificadas):**
  - Página oficial: https://conteudo.cvm.gov.br/legislacao/resolucoes/resol193.html
  - Texto consolidado (PDF): https://conteudo.cvm.gov.br/export/sites/cvm/legislacao/resolucoes/anexos/100/resol193consolid.pdf
  - Texto consolidado (DOC): https://conteudo.cvm.gov.br/legislacao/resolucoes/anexos/100/resol193consolid.docx
  - Res. CVM 244/2026 (HTML/PDF/DOC listado na página de Resoluções): https://conteudo.cvm.gov.br/legislacao/resolucoes.html
  - Análises: Demarest (https://www.demarest.com.br/resolucao-cvm-no-244-divulgacao-de-informacoes-de-sustentabilidade-deixa-de-ser-obrigatoria) e Migalhas (https://www.migalhas.com.br/depeso/457269/resolucao-cvm-244-26-do-dever-obrigatorio-ao-dever-de-explicar)
- **Relevance:** Marco regulatório central para companhias abertas brasileiras (inclusive todas as ~11 elétricas mapeadas no FINDINGS.md). Exige relatório de informações financeiras relacionadas à sustentabilidade em padrão ISSB e **asseguração por auditor independente registrado na CVM**.
- **Key metrics / obrigações (texto consolidado):**
  - **Art. 1º** — Adoção **voluntária** desde exercícios iniciados em/ou após 01/01/2024 (companhias abertas, fundos de investimento e securitizadoras), usando normas do ISSB em inglês até a internalização pelo CBPS (red. 227/25); declaração por comunicado ao mercado até 31/12/2024 (voluntário FY2024) ou 31/12/2025 (voluntário FY2025).
  - **Art. 1º §4º (red. 244/26)** — Quem optar por divulgar deve publicar por **no mínimo 3 exercícios consecutivos** (regra de estabilidade; elimina a "obrigação para sempre").
  - **Art. 1º §5º (244/26)** — Para interromper o reporte voluntário, aviso via comunicado ao mercado até a data do arquivamento das demonstrações financeiras anuais do exercício anterior.
  - **Art. 2º — REVOGADO pela Res. CVM 244/26.** O regime mandatório (a partir de 01/01/2026) deixou de existir.
  - **Art. 3º, parágrafo único (red. 244/26)** — A partir de **01/01/2027**, a companhia aberta que optar por **não** arquivar relatório de sustentabilidade deverá **justificar por comunicado ao mercado** (até a data do arquivamento das demonstrações financeiras anuais), descrevendo os motivos da Administração — regime "**pratique ou explique**".
  - **Art. 4º** — Periodicidade ≥ à das demonstrações financeiras anuais; relatório **identificado objetivamente e segregado** das demais informações e das DFs; base de consolidação.
  - **Art. 5º (red. 244/26)** — Arquivamento por **sistema eletrônico na página da CVM**: (I) 1º exercício: mesma data de entrega do **Formulário de Referência (FRE)**; (II) a partir do 2º exercício: até **3 meses** do encerramento do exercício **ou** mesma data de envio das demonstrações financeiras (o que ocorrer primeiro).
  - **Art. 6º** — **Asseguração independente**: asseguração **limitada** até FY2025; asseguração **razoável** a partir de exercícios iniciados em/ou após 01/01/2026 (para quem divulgar).
  - **Regime Fácil (Res. CVM 232/2025)** — isenção mantida para companhias menores.
- **Data format:** Arquivamento eletrônico (documento). **XBRL não confirmado** para o relatório em si; a base estruturada disponível é o FRE (formulário) em **dados abertos** (CSV/ZIP) no portal `dados.cvm.gov.br` (dataset `cia_aberta-doc-fre`).
- **Automatability:** MÉDIA a ALTA.
  - **Risco de comparabilidade:** com o "pratique ou explique", o **universo de arquivantes deixa de ser exaustivo** (CFC, Ofício 920/2026, aponta risco de "universo autorreferenciado" e fragmentação). Para o EnergyNexus, o critério de inclusão de empresas deve considerar **quem divulga** + quem justifica a não divulgação (também informação de valor competitivo).
  - O MRV de prazos (mesma data do FRE; vínculo com DFs anuais) permite **automação de calendário** (datas-limite = FRE).
  - Assuntos "comprar/contratar" em 2027: justificativas devem ser capturadas como **textos livres** (NLP) nas comunicações ao mercado.

---

## 3. TCFD (recomendações — legado informacional)

- **Name:** Task Force on Climate-related Financial Disclosures (TCFD).
- **Authority:** Financial Stability Board (FSB); **dissolvida em 12/10/2023**; FSB pediu ao IFRS Foundation a continuidade do monitoramento.
- **URL:** https://www.fsb-tcfd.org/about (arquivo).
- **Relevance:** 11 disclosures em 4 pilares (Governança, Estratégia, Gestão de Riscos, Métricas e Metas) — ainda é o esqueleto conceitual usado por bancos/empresas e herdado pelo IFRS S2 (dashboard que mapeia TCFD→IFRS S2).
- **Key metrics:** riscos físicos e de transição; cenários climáticos (ex.: 2 °C ou inferior); alvos de redução de Scope 1/2/3; alinhamento de clima em Orçamento de Capital.
- **Data format / Automatability:** Relatórios em PDF; MÉDIA; texto narrativo com baixa padronização — útil como *checklist* de extração semântica (perguntas binárias) e gatilho para triagem (empresas que declaram "em conformidade com TCFD").

---

## 4. GRI (com o Sector Program e o caso elétrico)

- **Name:** GRI Standards; setoriais **GRI 11 (Oil and Gas)**, **GRI 12 (Coal)**, GRI 13 (Agriculture), GRI 14 (Mining); legado **GRI G4 Electric Utilities Sector Disclosures (EU1–EU14)**.
- **Authority:** Global Sustainability Standards Board (GSSB) / GRI.
- **URL (verificadas):**
  - Sector Program: http://globalreporting.org/standards/sector-program
  - Lista priorizada Rev. 4 (aprovada em 19/11/2025): https://www.globalreporting.org/media/g03foy3c/gri-list-of-prioritized-sectors-approved-2025.pdf
  - Descrição do programa: https://www.globalreporting.org/media/mx4fjq5g/gri-sector-program-description_2026.pdf
  - Exemplo real (AEP 2025, usa GRI + setorial elétrica): https://docs.aep.com/docs/sustainability/2025_AEP_GRI_and_SASB_Report.pdf
- **Relevance (com a correção das premissas):**
  - O setor elétrico está na lista priorizada como **"Power production and energy utilities"** (geração, transmissão, distribuição e gás), separado de "Water and waste services"; a GSSB (fev/2022) decidiu **fundir renováveis** no mesmo setor refletindo a integração eólico/solar nas utilities. **Porém, o setor standard não foi ainda desenvolvido** (em desenvolvimento: têxteis e serviços financeiros).
  - Na prática, as elétricas relatam com **GRI G4 Electric Utilities**: EU1 (capacidade instalada por fonte), EU2 (energia líquida gerada), EU3 (nº de clientes por segmento), EU4 (extensão de linhas de transmissão), EU5 (alocação de allowances de carbono), EU6 (programas de eficiência energética em clientes), EU7–EU14 (P&D, reduções de carga, etc.).
  - Topic Standards de GHG e energia: GRI 305-1/2/3/4/5/7; GRI 302 (Energia 2016); novos GRI 102 (Climate Change 2025) e GRI 103 (Energy 2025), alinhados aos setoriais publicados (v1.1).
- **Key metrics:** capacidade instalada (MW) por fonte; geração líquida (GWh) e intensidade; vendas a cliente (nº de consumidores); extensão de rede (km); perdas; emissões GHG; eficiência energética em demanda.
- **Data format / Automatability:** PDFs de relatórios de sustentabilidade + content indexes GRI. MÉDIA — métricas EU1–EU4/EU8 são **quantitativas e tabelares** (ótimas para Docling/TableFormer), mas a publicação é livre; sem taxonomia mandatória. Para comparabilidade cross-section, melhor usar o content index GRI (raster de atendimento por disclosure).

---

## 5. SASB — Electric Utilities & Power Generators (IF-EU)

- **Name:** SASB Sustainability Accounting Standard — "Electric Utilities & Power Generators".
- **Authority:** SASB Standards Board, agora sob stewardship do **ISSB/IFRS Foundation** (integrado em 01/08/2022; projeto de renováveis "Transitioned to the ISSB"). Acreditado em várias jurisdições (usado por National Grid, Avangrid, AEP, Black Hills, CLP, etc.).
- **URL (verificadas):**
  - Projeto renováveis: https://sasb.ifrs.org/standards/process/projects/renewable-energy-in-electric-utilities-power-generators-industry
  - Texto do padrão (PDF referência, versão 2018): https://www.cooperative.com/programs-services/government-relations/regulatory-issues/Documents/Electric_Utilities_Power_Generators_Standard_2018.pdf
  - Exemplos de mapeamento (National Grid): https://www.nationalgrid.com/document/576646/download e (Black Hills) https://www.blackhillsenergy.com/sites/blackhillsenergy.com/files/2024-SASB-Disclosure.pdf
- **Relevance:** é o padrão **por indústria** mais comparável para elétricas; os códigos de métrica são os *identificadores* perfeitos para o motor de CI (mapeamento estável por tópico).
- **Key metrics — mapeamento completo dos códigos IF-EU:**
  - **GHG Emissions & Energy Resource Planning (IF-EU-110a)**
    - IF-EU-110a.1 — Emissões brutas globais Scope 1 (%) + % coberto por (2) regulamentações limitantes e (3) reportantes de emissões. *Revisão 2026: alinhado ao parágrafo IFRS S2 29(a).*
    - IF-EU-110a.2 — GHG associado a entregas de energia (power deliveries), em tCO2e. *Revisão 2026: passa a cobrir (1) perdas de T&D e (2) energia comprada líquida (Scope 2).*
    - IF-EU-110a.3 — Discussão da estratégia de curto/longo prazo para gerenciar Scope 1 e metas (qualitativa). *Revisão 2026: removida, incorporada à IF-EU-110a.7 (métrica qualitativa sobre como riscos climáticos influenciam decisões de capital).*
    - IF-EU-110a.4 — (1) nº de clientes em mercados sujeitos a RPS (Renewable Portfolio Standards) e (2) % de cumprimento da meta RPS por mercado. **É a métrica "transition-ready" citada no projeto ISSB (com limitações de comparabilidade internacional).**
  - **Air Quality:** IF-EU-120a.1 (NOx, SOx); IF-EU-150a.1 (Amount of CCPs gerado, % reciclado), IF-EU-150a.2 (impoundments de CCR), IF-EU-150a.3 (políticas de gestão de CCP).
  - **Energy Affordability:** IF-EU-240a.1 (tarifa média por segmento — residencial/comercial/industrial, $/kWh); IF-EU-240a.2 (conta típica de 500 e 1.000 kWh); IF-EU-240a.3 (desconexões por não pagamento, % religadas em 30 dias); IF-EU-240a.4 (impacto de fatores externos na acessibilidade).
  - **Workforce Health & Safety:** IF-EU-320a.1 (TRIR, taxa de fatalidade, NMFR).
  - **End-Use Efficiency & Demand:** IF-EU-420a.1 (% da receita sujeita a rate structures decoupled/LRAM); IF-EU-420a.2 (% da carga em smart grid); IF-EU-420a.3 (economias de energia por medidas de eficiência, MWh).
  - **Grid Resiliency:** (incidents de compliance NERC-CIP).
  - **Activity metrics:** IF-EU-000.A (clientes res./com./ind.), IF-EU-000.B (energia entregue por segmento, MWh), IF-EU-000.C (extensão de linhas de transmissão/distribuição, km), IF-EU-000.D (geração total MWh, % por fonte, % em mercado regulado), IF-EU-000.E (energia comprada no atacado, MWh).
- **Data format / Automatability:** **ALTA** — códigos fixos + unidades definidas; empresas publicam content indexes (tabelas) com esses códigos. Extração por regex/tabela dos content indexes (não precisa LLM para JSON via mapping table). Observação: o ISSB está **revisando o padrão** (FRC/TAC, jun/2026) — o EnergyNexus deve manter o mapeamento atualizável.

---

## 6. EU — CSRD / ESRS (com atualização completa de 2026)

- **Name:** Corporate Sustainability Reporting Directive — **Diretiva (UE) 2022/2464**; padrões **ESRS** (Delegated Regulation 2023/2772); **ESRS revisados adotados em 03/07/2026**; **Omnibus I = Diretiva (UE) 2026/470 (em vigor desde 18/03/2026)**.
- **Authority:** European Commission / EFRAG (desenvolvimento técnico).
- **URL (verificadas):**
  - Diretiva no EUR-Lex: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2464
  - ESRS 2023 (Reg. 2023/2772): https://eur-lex.europa.eu/legal-content/EN-HU/ALL?from=EN&uri=CELEX%3A32023R2772
  - EC — Corporate sustainability reporting (status 2026): http://finance.ec.europa.eu/financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en
  - Omnibus em vigor (Weil/Baker): https://www.weil.com/-/media/files/pdfs/2026/march/the-omnibus-i-directive-now-in-force.pdf
  - ESRS revisados adotados 03/07/2026 (EC): https://finance.ec.europa.eu/news/commission-adopts-revised-sustainability-reporting-standards-reduce-administrative-burdens-eu-2026-07-03_en ; (EFRAG) https://www.efrag.org/en/news-and-calendar/news/european-commission-publishes-delegated-act-on-revised-esrs-and-voluntary-sustainability-reporting
  - EFRAG XBRL/datapoints revisados (08/2026): https://www.efrag.org/en/news-and-calendar/news/efrag-secretariat-releases-2026-draft-list-of-datapoints-for-revised-esrs
  - Draft ESRS E1 (nov/2022, para referência): https://www.efrag.org/sites/default/files/sites/webpublishing/SiteAssets/08%20Draft%20ESRS%20E1%20Climate%20Change%20November%202022.pdf
- **Relevance:** Principal regime na Europa para elétricas com operação/ações na UE; base comparativa com a Taxonomia da UE.
- **Status cronológico 2026 (atualizado):**
  - **Wave 1** (grandes PIEs > 500 empregados, listadas): relatório piloto **FY2024** (publicado 2025).
  - **Omnibus I (EU/2026/470, em vigor 18/03/2026):** escopo reduzido para empresas grandes com **>1.000 empregados E receita líquida >€450M** — muitas empresas das Waves 2/3 **saem do escopo**; transposição pelos Estados-membros até **19/03/2027**; requisitos para grupos extra-UE com presença relevante na UE >€450M + filial/subsidiária >€200M (aplicação FY2028, publico 2029; padrões ESRS-TC em desenvolvimento — expectativa de adoção 2027).
  - **Requisito de padrões setoriais removido** pelo Omnibus; substituído por **guia setorial opcional** (não normas) — a UE deixou de mandar ESRS setorial obrigatório.
  - **ESRS revisados** adotados pela Comissão em **03/07/2026** (mais curtos, -60% datapoints mandatórios, -70% total, custos ~-30%); aplicam a **exercícios iniciados a partir de 01/01/2027**, com early adoption em FY2026; sujeitos a escrutínio do PE/Council (2+2 meses).
  - Padrão voluntário para empresas abaixo do limiar (base VSME) com **value-chain cap** também adotado em 03/07/2026.
  - **Datapoints e XBRL:** EFRAG publicou a **2026 Draft List of ESRS Datapoints** (28/08/2026) e prepara a **taxonomia XBRL revisada** para consulta — base digital para automação.
- **Key metrics de clima (ESRS E1):** E1-5 (consumo e mix de energia: total, fóssil, nuclear, renováveis, em MWh/GWh e %); E1-6 (emissões brutas Scope 1/2/3 em tCO2e + **intensidade de GHG baseada na receita líquida**); E1-1 plano de transição; E1-3 alvos; E1-7 GHG removals. (Referência da versão 2023.)
- **Data format / Automatability:** **ALTA** — ESRS tem **datapoints codificados** (datapoint list) + taxonomia XBRL (digital tagging mandatório na UE); o EnergyNexus pode espelhar o *ESRS datapoint model* para schema de extração estruturada do ISSB/CVM.

---

## 7. EU Taxonomy (regime de classificação + KPIs)

- **Name:** Regulamento (UE) 2020/852; Delegated Climate Act **2021/2139** (atividades elegíveis/contribuição substancial); Delegated Disclosure Act **2021/2178** (KPIs); alterações de simplificação pós-Omnibus.
- **Authority:** European Commission.
- **URL (verificadas):** Calculadora oficial e templates — https://ec.europa.eu/sustainable-finance-taxonomy/wizard ; Reg. 2021/2139 via EUR-Lex (CELEX 32021R2139).
- **Relevance:** Única métrica **comparativa de transição** com definição binária de elegibilidade/alinhamento — o "share de CAPEX/Turnover/OpEx alinhado à taxonomia" permite ranquear empresas comparando os mesmos critérios (SBTi/EU-). Para elétricas: geração, transmissão (atividade habilitadora), armazenamento, renovação de redes, produção de hidrogênio verde, energia nuclear e gás fóssil (com critérios de phase-out).
- **Key metrics / KPIs:** **Turnover alignment** (% da receita elegível+alinhada); **CapEx alignment** (% CAPEX em ativos verdes — chave para o KPI de "CAPEX transição" do EnergyNexus); **OpEx alignment**; relato separado de **eligible vs aligned**; anexo com templates de tabelas.
- **Data format / Automatability:** **ALTA/ALTA** — tabelas padronizadas de KPI + categorização obrigatória; permite mapeamento por atividade NACE + critérios. Observação: a "taxonomia" brasileira (TSB) está desenhada para interoperar conceitualmente.

---

## 8. BRASIL — TSB (Taxonomia Sustentável Brasileira)

- **Name:** Taxonomia Sustentável Brasileira (TSB).
- **Authority:** Ministério da Fazenda + Comitê Interinstitucional da Taxonomia Sustentável Brasileira (**CITSB**, instituído pelo Decreto 11.961/2024; disciplinado pela Portaria MF 1.039/2026); formalizada pelo **Decreto 12.705/2025** (31/10/2025) como instrumento do Plano de Transformação Ecológica.
- **URL (verificadas):**
  - Decreto 12.705/2025: https://legislacao.presidencia.gov.br/ficha?%2Flegisla%2Flegislacao.nsf%2FViw_Identificacao%2FDEC%2012.705-2025&OpenDocument
  - Decreto 11.961/2024: https://antigo.mctic.gov.br/mctic/opencms/legislacao/decretos/Decreto_n_11961_de_22032024.html
  - CEBDS — versão EN da TSB para consulta: https://cebds.org/wp-content/uploads/2025/11/TSB-EN.pdf
- **Relevance:** Futura classificação de atividades "verdes" brasileiras com os 6 objetivos ambientais (clima, água, biodiversidade, circularidade, poluição, oceanos), critérios de **contribuição substancial (TSC)**, **Do No Significant Harm (DNSH)** e salvaguardas sociais; atividades relevantes para elétricas: geração renovável, **transmissão (atividade habilitadora)**, redes inteligentes e storage — alinhada conceitualmente à Taxonomia UE (permite comparáveis UE↔BR).
- **Implementation:** 2 fases (até 3 anos): **voluntária** primeiro e, após regulamentação, **mandatória**; o Decreto 12.705 define que o uso obrigatório será calibrado por regulação.
- **Data format / Automatability:** Em construção; documento de consulta (PDF) — metadados de taxonomia não publicados ainda. MÉDIA (futura): quando publicada, será mapeável tal como a UE.

---

## 9. Dados digitais e taxonomias XBRL

| Item | O que é | Status / URL | Uso no EnergyNexus |
| :-- | :-- | :-- | :-- |
| **IFRS Sustainability Disclosure Taxonomy** | Taxonomia XBRL das normas ISSB S1/S2 | Publicada 30/04/2024 — https://www.ifrs.org/news-and-events/news/2024/04/issb-publishes-its-digital-sustainability-taxonomy | Schema de tipos de dados (GHG, alvos, CapEx climático) para extração e validação |
| **ESRS XBRL Taxonomy + Datapoint List** | Tagging digital mandatório na UE | Datapoints revisados 28/08/2026 (EFRAG); taxonomia revisada em consulta — https://www.efrag.org/en/news-and-calendar/news/efrag-secretariat-releases-2026-draft-list-of-datapoints-for-revised-esrs | Modelo de datapoints normalize por framework |
| **CVM dados abertos — FRE** | FRE (formulário regulatório com item ESG 2.7) | `dados.cvm.gov.br/dataset/cia_aberta-doc-fre` — CSV/ZIP (aberto 2026, atualizado 24/08/2026) | Baseline de governança ESGS (perguntas binárias de ESG e clima) |
| **CVM — relatório ISSB (CVM 193/244)** | Arquivamento eletrônico de documento | Sistema CVM; prazo 1º ano = FRE; 2º ano = 3 meses | Coleta por calendário; parsing de PDF; captura de justificativas "pratique ou explique" |
| **ANEEL dados abertos (CKAN)** | SIGA/BIG geração, P&D/EE, DEC/FEC, perdas | https://dadosabertos.aneel.gov.br/ (CSV/XML/PDF + API) | Fato físico de transição (MW por fonte, P&D, perdas) — já mapeado no FINDINGS.md |
| **Registro Público de Emissões (PB GHG Protocol/FGV)** | Inventários auditados em XLSX/PDF | https://registrodeemissoes.fgv.br/ | Emissões verdes (Scope 1/2/3, SF6) com selo Ouro |

---

## 10. IMPLICAÇÕES E RECOMENDAÇÕES PARA O ENERGYNEXUS

1. **Regra de inclusão de empresas:** com a CVM 244/26, o universo de arquivantes é **voluntário**. O motor deve separar: (a) empresas que divulgam relatório ISSB; (b) empresas que justificaram a não divulgação (comunicado ao mercado) — ambas são sinais competitivos.
2. **Unir a dupla CVM+CVM nacional:** mapear cada métrica do IFRS S2/CBPS 02 para o código SASB IF-EU (ex.: Scope 1 → IF-EU-110a.1; energia gerada por fonte → IF-EU-000.D; tarifa média → IF-EU-240a.1; RPS/renovável → IF-EU-110a.4) e para a Taxonomia UE/TSB (CapEx alinhado %). Isso dá a "camada comparável" trans-framework.
3. **Camada física (ANEEL/ONS)** permanece a base de verdade para MW por fonte, DEC/FEC, perdas e curtailment — independente do regime de disclosure mudar.
4. **Automação diferenciada:**
   - IF-EU content indexes: extração **sem LLM** (tabela → JSON via code).
   - ESRS: extração guiada por datapoints + XBRL.
   - "Comply or explain" CVM: NLP para motivos de não divulgação.
   - FRE 2.7: dados abertos estruturados (sem PDF).
5. **Monitorar:** revisão ISSB do SASB IF-EU (2026), ESRS revisados (vigência FY2027), e a fase mandatória da TSB (Decreto 12.705/2025).
6. **Corrigir no FINDINGS.md:** a linha sobre "obrigatória a partir de 2026 em XBRL" (CVM 193) e o entendimento de "GRI 11 = setor elétrico".

---

## ANEXO — Fontes primárias verificadas (URLs curadas)

| Framework | Link |
| :-- | :-- |
| ISSB IFRS S2 | http://ifrs.org/issued-standards/ifrs-sustainability-standards-navigator/ifrs-s2-climate-related-disclosures |
| IFRS S2 + guidance | https://www.ifrs.org/content/dam/ifrs/publications/html-standards-issb/english/2023/issued/issbs2-ag.html |
| IFRS Sustainability Taxonomy | https://www.ifrs.org/news-and-events/news/2024/04/issb-publishes-its-digital-sustainability-taxonomy |
| CVM 193 (página) | https://conteudo.cvm.gov.br/legislacao/resolucoes/resol193.html |
| CVM 193 (consolidado PDF) | https://conteudo.cvm.gov.br/export/sites/cvm/legislacao/resolucoes/anexos/100/resol193consolid.pdf |
| CVM 193 (consolidado DOCX) | https://conteudo.cvm.gov.br/legislacao/resolucoes/anexos/100/resol193consolid.docx |
| TCFD | https://www.fsb-tcfd.org/about |
| GRI Sector Program | http://globalreporting.org/standards/sector-program |
| GRI lista priorizada Rev.4 | https://www.globalreporting.org/media/g03foy3c/gri-list-of-prioritized-sectors-approved-2025.pdf |
| SASB projeto renováveis | https://sasb.ifrs.org/standards/process/projects/renewable-energy-in-electric-utilities-power-generators-industry |
| SASB IF-EU 2018 (PDF) | https://www.cooperative.com/programs-services/government-relations/regulatory-issues/Documents/Electric_Utilities_Power_Generators_Standard_2018.pdf |
| AEP 2025 GRI+SASB | https://docs.aep.com/docs/sustainability/2025_AEP_GRI_and_SASB_Report.pdf |
| CSRD (EC página oficial) | http://finance.ec.europa.eu/financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en |
| Omnibus I em vigor | https://www.weil.com/-/media/files/pdfs/2026/march/the-omnibus-i-directive-now-in-force.pdf |
| ESRS revisados (adotados 03/07/2026) | https://finance.ec.europa.eu/news/commission-adopts-revised-sustainability-reporting-standards-reduce-administrative-burdens-eu-2026-07-03_en |
| EFRAG datapoints 2026 | https://www.efrag.org/en/news-and-calendar/news/efrag-secretariat-releases-2026-draft-list-of-datapoints-for-revised-esrs |
| EU Taxonomy Calculator | https://ec.europa.eu/sustainable-finance-taxonomy/wizard |
| Decreto 12.705/2025 | https://legislacao.presidencia.gov.br/ficha?%2Flegisla%2Flegislacao.nsf%2FViw_Identificacao%2FDEC%2012.705-2025&OpenDocument |
| CVM dados abertos (FRE) | https://dados.cvm.gov.br/dataset/cia_aberta-doc-fre |
| CEM/NEOE exemplo FRE | https://www.rad.cvm.gov.br/ENET/frmGerenciaPaginaFRE.aspx |