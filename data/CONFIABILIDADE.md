# Confiabilidade dos dados do CoppeZIP

Levantamento de 26/09/2026. Cobre as 52 tabelas e visões do `coppezip.duckdb`, os 32 PDFs indexados no `docs.duckdb` e o
acervo `dados_hackathon` do Drive (documentos das 11 empresas e `dados_estruturados/`). Para cada dado: fonte oficial,
como chega ao projeto, que tipo de dado é, como foi validado e o que se sabe de ruim sobre ele.

Como foi feito: leitura do código (`data/baixar.py`, `data/construir.py`, `data/indexar_docs.py`), do catálogo
([`DADOS.md`](DADOS.md), gerado em 25/09/2026), dos testes e da regressão, mais as checagens independentes da seção 4.
O banco em si não foi aberto nesta revisão (não está nesta máquina): o número de linhas vem do `DADOS.md`.

## 1. Resumo

| | Situação |
|---|---|
| Origem | Todos os dados vêm de órgãos oficiais (CVM, ANEEL, ONS, BNDES, Banco Central, ANBIMA/B3, SEC) ou de documentos publicados pelas próprias empresas. Nenhum dado é de agregador comercial. |
| Links das fontes | 104 URLs citadas no código e no catálogo testadas em 26/09/2026: todas respondem (seção 4.1). |
| Números financeiros | 13 valores esperados pelos testes e pela regressão conferidos contra os dados abertos da CVM baixados hoje: 13 iguais (seção 4.2). |
| Reprodutibilidade | 35 tabelas saem só de arquivos que o `baixar.py` baixa de URL oficial fixa. **14 tabelas dependem só de 12 arquivos que existem apenas no Drive do projeto**, sem URL nem data de coleta registradas no repositório, e outras 3 misturam as duas origens (seção 2.2). |
| Documentos (PDF) | **17 dos 32 PDFs indexados citam só a página inicial do site da empresa**, não o arquivo. Para 10 deles o acervo do Drive tem candidatos a link direto, 5 sem ambiguidade (seção 5). |
| Estimativas | 3 tabelas são estimativas da plataforma e estão marcadas como tal no catálogo (`curtailment_por_dono_mensal`, `curtailment_por_grupo_mensal` e os limites de `dec_fec_distribuidora_anual`). |
| Acervo do Drive | 10.269 documentos com hash SHA-256 de cada arquivo e link de origem; 4 links mortos na origem e 17 arquivos marcados como inúteis (seção 3). |

## 2. Banco `coppezip.duckdb`

### 2.1 Como ler as tabelas abaixo

- **Tipo**
  - **A**: dado oficial, só com tipo, unidade ou formato de CNPJ ajustados.
  - **B**: dado oficial com agregação ou cálculo da plataforma; a fórmula está na coluna `fonte` ou nas ressalvas do catálogo.
  - **C**: estimativa, com rateio ou aproximação.
- **Natureza**, isto é, quem produz o número na origem:
  - *auditado*: demonstração anual com parecer de auditor;
  - *revisado*: ITR, com revisão limitada;
  - *declarado*: o agente informa ao regulador, sem auditoria;
  - *medido*: operador do sistema;
  - *regulatório*: ato ou cadastro do regulador;
  - *mercado*: registro de mercado.
- **Chega por**: `baixar.py` quando a URL está fixa no código; **Drive** quando o arquivo vem do Drive `CoppeZIP-dados-brutos` pelo rclone.
- **Validação**: teste em `proper_mcps/dados/test_server.py` (T) ou caso em `eval/regressao.py` (R) que confere valor da tabela contra a fonte.

### 2.2 Tabelas que dependem só do Drive (sem URL no código)

Estes arquivos entram no banco, mas o repositório não guarda de onde nem quando foram baixados. O conjunto oficial
correspondente foi localizado nos catálogos CKAN em 26/09/2026. Registrar URL, data de coleta e SHA-256 de cada um é a
primeira recomendação da seção 6.

| Arquivo em `data/` | Tabelas | Conjunto oficial correspondente |
|---|---|---|
| `raw/aneel_ons_epe_bndes/siga.csv` | `usinas`, `usinas_proprietarios`, `capacidade_por_proprietario` (e, por elas, `capacidade_por_grupo` e curtailment por dono/grupo) | https://dadosabertos.aneel.gov.br/dataset/siga-sistema-de-informacoes-de-geracao-da-aneel |
| `raw/aneel_ons_epe_bndes/leiloes.csv` | `leiloes_geracao` | https://dadosabertos.aneel.gov.br/dataset/resultado-de-leiloes |
| `raw/aneel_ons_epe_bndes/siget_agente.csv`, `siget_empreendimento_obra_modulo.csv` | `transmissao_contratos`, `transmissao_empreendimentos` | https://dadosabertos.aneel.gov.br/dataset/sistema-de-gestao-da-transmissao-siget |
| `raw/aneel_ons_epe_bndes/tarifas.csv` | `tarifas_distribuicao` | https://dadosabertos.aneel.gov.br/dataset/tarifas-distribuidoras-energia-eletrica |
| `raw/aneel_ons_epe_bndes/pdd.csv` | `pdd_investimentos` | https://dadosabertos.aneel.gov.br/dataset/pdd |
| `raw/aneel_ons_epe_bndes/ped.csv` | `ped_projetos` | https://dadosabertos.aneel.gov.br/dataset/projetos-de-p-d-em-energia-eletrica |
| `raw/aneel_ons_epe_bndes/pee.csv` | `pee_projetos` | https://dadosabertos.aneel.gov.br/dataset/projetos-de-eficiencia-energetica |
| `raw/aneel_ons_epe_bndes/naoauto_full.csv` | `bndes_operacoes` | https://dadosabertos.bndes.gov.br/dataset/operacoes-financiamento |
| `parquet/reg_decfec.parquet` | `compensacoes_continuidade` | ANEEL, continuidade (provável: https://dadosabertos.aneel.gov.br/dataset/indicadores-coletivos-de-continuidade-dec-e-fec; confirmar) |
| `parquet/reg_capacidade.parquet` | `ons_capacidade` | https://dados.ons.org.br/dataset/capacidade-geracao |
| `raw/cvm/anbima_deb.xlsx` | `debentures_incentivadas` | Planilha da ANBIMA de debêntures incentivadas; sem URL registrada; dados até 04/2024 |

### 2.3 CVM (companhias abertas)

Fonte: https://dados.cvm.gov.br/dados/CIA_ABERTA (cadastro, FCA, DFP 2020–2025, ITR 2024–2026). Tudo chega pelo
`baixar.py`. O filtro de empresas é o setor "Energia Elétrica" do cadastro (151 CNPJs), que inclui as 11 empresas do
acervo.

| Tabela | Linhas | Tipo | Natureza | Validação | Ressalvas que importam |
|---|---:|---|---|---|---|
| `empresas` | 151 | A | regulatório | T (busca) | Uma linha por CNPJ, deduplicada (o cadastro repete CNPJs). |
| `empresas_apelidos` | 153 | B | regulatório + curadoria | T (8 termos, 2 casos de apelido) | Parte dos apelidos é uma lista escrita à mão em `construir.py` (`APELIDOS`). |
| `contas_cvm` | 312.693 | A | auditado | T, R | Só `ORDEM_EXERC = ÚLTIMO` e a última versão entregue; escala MIL aplicada; despesas negativas. Só 2020 em diante. |
| `kpis_financeiros` | 652 | B | auditado + cálculo | T (Equatorial 2024), R (8 casos) | EBITDA calculado (EBIT 3.05 + D&A da DFC), não o ajustado da empresa. CAPEX e custo de construção são achados por texto da descrição da conta. Dívida bruta sem arrendamentos. |
| `contas_cvm_trimestral` | 462.169 | A | revisado | T | A DFC do ITR é acumulada no ano; o 4º trimestre só existe na DFP. |
| `kpis_trimestrais` | 879 | B | revisado + cálculo | T (Taesa), R (1 caso) | 12 meses = acumulado do ano + DFP anterior − acumulado do mesmo trimestre anterior; só existe quando há os três. |

### 2.4 ANEEL

| Tabela | Linhas | Tipo | Natureza | Chega por | Fonte oficial | Validação | Ressalvas que importam |
|---|---:|---|---|---|---|---|---|
| `agentes_aneel` | 9.956 | A | regulatório | baixar.py | [Agentes do Setor Elétrico](https://dadosabertos.aneel.gov.br/dataset/agentes-do-setor-eletrico) | — | Sem dados financeiros. |
| `usinas` | 25.133 | A | regulatório | **Drive** | SIGA | T (potência numérica) | Potência em kW. |
| `usinas_proprietarios` | 25.466 | B | regulatório | **Drive** | SIGA, campo de texto dos donos | — | CNPJ e percentual extraídos por expressão regular de um campo de texto livre. |
| `capacidade_por_proprietario` | visão | B | regulatório + cálculo | **Drive** | SIGA | — | Titular direto (SPE), não grupo. |
| `capacidade_por_grupo` | 7.026 | B | regulatório + cálculo | Drive + baixar.py | SIGA + Composição Societária | T (Engie), R | ~12% da potência em operação fica fora (dono sem declaração societária). |
| `leiloes_geracao` | 1.552 | A | regulatório | **Drive** | Resultado de leilões | T (consulta), R | Só geração; vencedor sem CNPJ. |
| `transmissao_contratos` | 413 | A | regulatório | **Drive** | SIGET | — | |
| `transmissao_empreendimentos` | 16.262 | A | regulatório | **Drive** | SIGET | — | `valor_historico_receita_brl` **não é RAP** (repete por módulo; soma implausível). |
| `rap_transmissao_modulos` | 47.392 | A | regulatório | baixar.py | [SIGET, lista prévia do reajuste](https://dadosabertos.aneel.gov.br/dataset/sistema-de-gestao-da-transmissao-siget) | T, R | Lista **prévia**, sem Parcela de Ajuste: pode diferir da RAP que a empresa divulga. |
| `rap_transmissao_concessionaria` | visão | B | regulatório + soma | baixar.py | idem | T | 100% da concessão. |
| `rap_por_grupo` | visão | B | regulatório + cálculo | baixar.py | SIGET + Composição Societária | — | Concessionárias sem declaração societária ficam de fora. |
| `composicao_societaria` | 73.056 | A/B | declarado | baixar.py | [Composição Societária (Polímero)](https://dadosabertos.aneel.gov.br/dataset/composicao-societaria-polimero) | T (Taesa/ETAU) | Declaração do próprio agente; `na_cadeia_de_controle` e `controlador_final` são calculados. |
| `participacoes_societarias` | 49.322 | B | declarado + cálculo | baixar.py | idem | T | Participação limitada a 100% quando a declaração repete sócio. |
| `grupos_economicos` | 4.253 | B | declarado + cálculo | baixar.py | idem | T | Declaração mais recente de cada agente. |
| `tarifas_distribuicao` | 327.493 | A | regulatório | **Drive** | Tarifas homologadas | R (Enel SP) | Sigla da distribuidora pode ser antiga; filtrar por CNPJ. |
| `mercado_distribuidoras_mensal` | 85.343 | A | declarado | baixar.py | [SAMP](https://dadosabertos.aneel.gov.br/dataset/samp) | T | **Erros de declaração na fonte** (ex.: Cemig D, Residencial, jul e out/2025, receita ~10×). Meses recentes são revistos. |
| `gd_mmgd` | 66.826 | B | declarado | baixar.py | [Geração Distribuída](https://dadosabertos.aneel.gov.br/dataset/relacao-de-empreendimentos-de-geracao-distribuida) | T (Acre) | `mes_cadastro` é a última atualização cadastral, não a data de conexão. |
| `expansao_geracao` | 2.246 | A | regulatório | baixar.py | [RALIE](https://dadosabertos.aneel.gov.br/dataset/ralie-relatorio-de-acompanhamento-da-expansao-da-oferta-de-geracao-de-energia-eletrica) | T | Datas previstas são revistas todo mês. |
| `bandeiras_tarifarias` | 141 | A | regulatório | baixar.py | [Bandeiras Tarifárias](https://dadosabertos.aneel.gov.br/dataset/bandeiras-tarifarias) | T | R$/MWh. |
| `continuidade_conjuntos` | 5.108.332 | A | declarado | baixar.py | Indicadores coletivos de continuidade | — | |
| `continuidade_limites` | 263.401 | A | regulatório | baixar.py | idem | — | |
| `indicadores_codigos` | 484 | A | regulatório | baixar.py | Domínio dos indicadores | T | |
| `dec_fec_distribuidora_anual` | visão | B/**C** | declarado + cálculo | baixar.py | idem | T, R (Enel SP) | DEC/FEC aproximam o oficial (±0,01); **os limites são estimativa da plataforma**, não o limite global oficial. |
| `compensacoes_continuidade` | 10.015.978 | A | declarado | **Drive** | continuidade (confirmar conjunto) | T (códigos) | |
| `ranking_continuidade` | 235 | A/B | regulatório | baixar.py | [Ranking de Continuidade (gov.br)](https://www.gov.br/aneel/pt-br/centrais-de-conteudos/relatorios-e-indicadores/distribuicao/ranking-de-continuidade) | T, R | Lido de tabela HTML; CNPJ ligado pela razão social (vazio quando não casa). |
| `pdd_investimentos` | 5.484 | A | declarado | **Drive** | PDD | — | |
| `ped_projetos` | 3.997 | A | declarado | **Drive** | P&D | — | Projetos antigos com título e custo vazios. |
| `pee_projetos` | 8.230 | A | declarado | **Drive** | PEE | — | Sem CNPJ. |

### 2.5 ONS

Todos os conjuntos vêm do catálogo https://dados.ons.org.br (Parquet no S3 `ons-aws-prod-opendata`). Natureza: *medido*
(ou programado, no caso do CMO do dia seguinte). O ONS revisa arquivos recentes.

| Tabela | Linhas | Tipo | Chega por | Validação | Ressalvas que importam |
|---|---:|---|---|---|---|
| `ons_cmo_semihora` | 464.064 | A | baixar.py | T (ago/2026 contra o Parquet) | Não é PLD. O arquivo de 2026 **não tem 09/08/2026**. |
| `ons_cmo_mensal` | 324 | B | baixar.py | T, R | Média aritmética dos intervalos; ver `dias_ausentes`. |
| `ons_ear_diario` | 39.052 | A | baixar.py | T (ago/2026 contra o Parquet) | MWmês. |
| `ons_carga_diaria` | 39.053 | A | baixar.py | T | MW médio. |
| `ons_ena_diaria` | 8.372 | A | baixar.py | T | Desde 2021. |
| `ons_geracao_fonte_mensal` | 705 | B | baixar.py | T | Soma do balanço horário; térmica inclui nuclear. |
| `ons_geracao_usina_mensal` | 51.155 | B | baixar.py | T | Só usinas com dado no ONS; MMGD é estimativa do ONS. |
| `ons_intercambio_mensal` | 206 | B | baixar.py | — | |
| `ons_curtailment_semihora` | visão | A | baixar.py | — | |
| `ons_curtailment_mensal` | 9.027 | B | baixar.py | R (2 casos) | Energia cortada = GNRa × 0,5 h. |
| `ons_conjuntos_usinas` | 1.615 | A | baixar.py | — | Mapa de um único mês (ago/2026). |
| `ons_capacidade` | 5.678 | A | **Drive** | — | Agente sem CNPJ. |
| `curtailment_por_dono_mensal` | visão | **C** | baixar.py + Drive | — | **Estimativa**: o ONS apura por conjunto; a plataforma rateia por potência e participação. |
| `curtailment_por_grupo_mensal` | visão | **C** | baixar.py + Drive | — | **Estimativa** sobre a anterior. |

### 2.6 Crédito, financiamento e macro

| Tabela | Linhas | Tipo | Natureza | Chega por | Fonte oficial | Validação | Ressalvas que importam |
|---|---:|---|---|---|---|---|---|
| `debentures_snd` | 10.008 | A/B | mercado | baixar.py | [SND, Características das Debêntures](https://www.debentures.com.br/exploreosnd/consultaadados/emissoesdedebentures/caracteristicas_r.asp) | T, R (Taesa) | Saldo ≈ principal (sem juros acumulados); só o vencimento final. |
| `debentures_incentivadas` | 777 | A | mercado | **Drive** | Planilha ANBIMA | R (Taesa) | **Parada em 04/2024**; emissora sem CNPJ; escala mudou em 2018 (já convertida). Para dados atuais, preferir `debentures_snd`. |
| `bndes_operacoes` | 23.815 | A | registro do financiador | **Drive** | BNDES, operações de financiamento | R | CNPJ do tomador (muitas vezes SPE). |
| `indicadores_macro_mensal` | 321 | A/B | oficial | baixar.py | Banco Central, SGS: séries 433, 13522, 189, 4390, 4391, 432, 3698 (https://api.bcb.gov.br) | T | IGP-M 12 meses acumulado pela plataforma; mês corrente parcial. |

### 2.7 Documentos indexados (`docs.duckdb`)

32 PDFs listados em [`documentos.csv`](documentos.csv): relatórios de sustentabilidade, relatos integrados e
relatórios anuais de 18 empresas, mais 4 referências (Resoluções CVM 193 e 244, BEN 2026 da EPE e nota
metodológica do SEEG 13).

- **Natureza:** documento da empresa. É autodeclarado; só é auditado quando o próprio relatório traz asseguração.
- **Tipo:** A. O texto é extraído por página com PyMuPDF, sem OCR. A busca combina palavras (BM25) e embeddings (multilingual-e5-large).
- **Validação:** 3 casos de regressão exigem citação de página (inventário GEE da Cemig, meta da Engie e Resolução CVM 244).
- **Rastreabilidade:** cada trecho guarda arquivo e página. Mas **17 dos 32 PDFs têm como `url` só a página inicial ou a listagem do site** (seção 5). Nesses casos a citação não leva ao arquivo exato.

## 3. Acervo do Drive (`dados_hackathon`)

Documentos públicos das 11 empresas (Axia, Cemig, Copel, CPFL, Energisa, Eneva, Engie, Equatorial, ISA Energia,
Neoenergia e Taesa), baixados em setembro de 2026. Só as categorias do núcleo: financeiro, sustentabilidade,
investimento, governança e dívida.

### 3.1 De onde vem cada documento

| Fonte | Documentos | O que é | Link de origem |
|---|---:|---|---|
| CVM/IPE | 8.837 | Documentos eventuais: fatos relevantes, releases, DFs completas em PDF, propostas da administração, relatórios de agente fiduciário e de rating, escrituras etc. | `rad.cvm.gov.br/ENET/frmDownloadDocumento.aspx?...` (índice: https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/) |
| CVM/ITR | 517 | Pacote ENET das demonstrações trimestrais, 2011+ | `rad.cvm.gov.br/ENETCONSULTA/...` (índice: DOC/ITR) |
| CVM/DFP | 176 | Pacote ENET das demonstrações anuais, 2010+ | idem (índice: DOC/DFP) |
| CVM/FRE | 187 | Formulário de Referência, 2010+ | idem (índice: DOC/FRE) |
| CVM/FCA | 187 | Formulário Cadastral, 2010+ | idem (índice: DOC/FCA) |
| SEC/EDGAR | 112 | 20-F de Axia, Cemig, Copel e CPFL | https://www.sec.gov/edgar |
| Site RI | 253 | Relatórios anuais, de sustentabilidade e integrados | Sites de RI (api.mziq.com, eletrobras.com, ri.cpfl.com.br, engie.com.br, ri.isaenergiabrasil.com.br, cemig.com.br, ri.taesa.com.br, eneva.com.br, neoenergia.com, equatorialenergia.com.br) |
| **Total** | **10.269** | 27,8 GB | |

Por empresa: de 678 (Neoenergia) a 1.324 (Axia) documentos. O documento mais antigo é de 2000 (Axia); os mais recentes
são de 2026.

### 3.2 Rastreabilidade e integridade

- `_indice/manifesto.csv` guarda, para cada documento, `doc_id`, empresa, categoria, tipo, ano, datas, **link de origem**,
  caminho local, tamanho e **SHA-256**. O SHA-256 está preenchido em 100% dos arquivos baixados. O `doc_id` aparece no nome
  do arquivo e leva de volta ao link, que é a âncora de citação.
- A lista do que baixar (`_indice/checklist_documentos.csv`) segue regras fixas aplicadas aos índices de dados abertos
  da CVM:
  - DFP, ITR, FRE e FCA: última versão de cada data de referência;
  - IPE: tudo, menos posições de valores mobiliários e contratos de indenidade;
  - site de RI: relatórios listados um a um.
- As linhas da Taesa foram geradas por `data/acervo/checklist_taesa.py` com essas mesmas regras. Antes, as regras foram
  conferidas contra as linhas já existentes:
  - DFP, ITR, FRE e FCA de ISA e Cemig: 100% iguais;
  - IPE das 10 empresas: 23.387 de 23.447 documentos iguais (99,7%). Os 60 que a regra inclui e o levantamento
    original não tem são quase todos Relatórios de Proventos de 2022 a 2025; o motivo da exclusão não foi identificado.
- O download da Taesa (942 documentos) terminou sem erro em 26/09/2026.

### 3.3 Problemas conhecidos (coluna `observacao` do manifesto)

| Situação | Qtd | O que fazer |
|---|---:|---|
| Duplicata idêntica de outro `doc_id` (mesmo SHA-256) | 96 | Ignorar na indexação, para não contar duas vezes. |
| Página HTML no lugar do relatório (Energisa 2005–2013 em Flash, revista Copel 2018) | 11 | Conteúdo não recuperado. |
| PDF em branco na origem (relatórios de proventos: 4 de dez/2022 e 1 da Taesa de jan/2023) | 5 | Sem conteúdo. |
| 20-F de 2001 da Copel entregue em papel à SEC | 1 | Só existe o aviso. |
| Link quebrado na origem (Copel RA 2010, Energisa RA 2014 e 2015, Neoenergia RS 2016) | 4 | Não baixados; tentados de novo em 26/09/2026 e continuam fora do ar. |

Outras armadilhas para quem for usar os arquivos:

- **Formatos que não são PDF**, só em `1_financeiro/`:
  - 693 `.zip`, pacotes ENET de DFP e ITR. Contêm um PDF completo, XML com as contas e o texto em base64, e `.xlsx` a partir de 2020;
  - 110 `.htm` e 2 `.txt`, os 20-F da SEC;
  - 26 `.doc` e 8 `.docx`, documentos antigos em Word.
  - Para busca textual, usar o PDF de dentro do zip.
- **PDFs dos zips ENET completados com bytes zero** até 8 MiB. Não estão cortados: o de 2025 da Taesa vai até
  "PÁGINA 118 de 118".
- **Nomes antigos** (Eletrobras, Tractebel, CTEEP, MPX): usar o CNPJ ou o `empresa_id`.
- **Taesa e Cemig:** a Cemig controla a Taesa em conjunto com a ISA. Parte do resultado da Taesa aparece na DFP da Cemig
  por equivalência patrimonial, então não se pode somar lucro ou RAP das duas sem tratar isso.

### 3.4 `dados_estruturados/`

- **Conteúdo:** CSVs com as contas de DFP (2010–2025) e ITR (2011–2026) das 11 empresas. Separador `;`, UTF-8, coluna `EMPRESA_ID`.
- **Origem:** os zips anuais de https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/{DFP,ITR}/DADOS/, regenerados em 26/09/2026 por `data/acervo/dados_estruturados.py`.
- **Relação com o projeto:** é a mesma fonte das tabelas `contas_cvm` e `contas_cvm_trimestral`, com mais anos e menos empresas.
- **Cuidados de uso:**
  - filtrar `ORDEM_EXERC = 'ÚLTIMO'`;
  - no ITR, escolher entre trimestre isolado e acumulado pelo `DT_INI_EXERC`;
  - todos os valores estão em R$ mil.

## 4. Checagens independentes feitas neste levantamento (26/09/2026)

### 4.1 Links das fontes

Foram testadas 104 URLs:
- 55 do `baixar.py`, incluindo 7 séries do Banco Central e 10 catálogos do ONS e da ANEEL;
- 32 do `documentos.csv`;
- 17 do `DADOS.md`.

Resultado: 103 responderam HTTP 200. O único 404 foi um falso positivo, causado por um `;` colado ao link na tabela do
`DADOS.md`; sem esse caractere, a URL responde. Nenhuma fonte saiu do ar.

### 4.2 Números do projeto contra a CVM

Os valores esperados pelos testes e pela regressão foram recalculados a partir dos CSVs da CVM baixados hoje (consolidado,
`ÚLTIMO`, mesmas contas e mesma regra de D&A do `construir.py`):

| Onde | Valor | Esperado | CVM (26/09/2026) | Confere |
|---|---|---|---|---|
| R `empresa-taesa` | Taesa, receita líquida 2025 | ~4,6 bi | 4,6241 bi | sim |
| R `empresa-eletrobras` | Axia, lucro líquido 2024 | 10,37–10,38 bi | 10,3808 bi | sim |
| R `escala-axia` | Axia, receita líquida 2024 | 40,17–40,18 bi | 40,1816 bi | sim |
| R `ebitda-equatorial` | Equatorial, EBITDA 2024 | ~11,3 bi | 11,3937 bi | sim |
| R `serie-receita` | Equatorial, receita 2020 | 17,89 bi | 17,8901 bi | sim |
| R `serie-receita` | Equatorial, receita 2025 | 52,07 bi | 52,0738 bi | sim |
| R `alavancagem-comparada` | Equatorial, dív. líq./EBITDA 2025 | 3,90× | 3,90× | sim |
| R `alavancagem-comparada` | Taesa, dív. líq./EBITDA 2025 | 3,66× | 3,66× | sim |
| R `trimestre-taesa` | Taesa, receita 2T26 | 1,067–1,068 bi | 1,0676 bi | sim |
| T `indicadores_equatorial_2024` | Equatorial 2024, receita | 45.366.675.000 | 45.366.675.000 | sim |
| T | Equatorial 2024, EBIT | 8.636.463.000 | 8.636.463.000 | sim |
| T | Equatorial 2024, lucro líquido | 3.767.805.000 | 3.767.805.000 | sim |
| T | Equatorial 2024, dívida bruta | 55.827.078.000 | 55.827.078.000 | sim |

### 4.3 O que já é validado de forma contínua no projeto

- `proper_mcps/dados/test_server.py` tem 23 testes.
- **22 tabelas conferidas contra o arquivo oficial:** `usinas`, `dec_fec_distribuidora_anual`, `indicadores_codigos`,
  `ons_cmo_*`, `ons_ear_diario`, `rap_transmissao_*`, `grupos_economicos`, `participacoes_societarias`,
  `capacidade_por_grupo`, `mercado_distribuidoras_mensal`, `gd_mmgd`, `bandeiras_tarifarias`,
  `indicadores_macro_mensal`, `ranking_continuidade`, as quatro séries do ONS, `debentures_snd` e `expansao_geracao`.
- **As ferramentas também são testadas:** `indicadores_financeiros` (Equatorial e Taesa), `buscar_empresa`, e o
  `consultar_sql`, que recusa números digitados pelo modelo em vez de lidos da base.
- `eval/regressao.py` tem 27 perguntas com resposta conhecida feitas ao chat de verdade, incluindo uma sobre dado
  inexistente (PLD), que verifica se o modelo admite que não tem o dado.
- **Sem teste nem caso de regressão:**
  - `agentes_aneel`
  - `transmissao_contratos`
  - `transmissao_empreendimentos`
  - `continuidade_conjuntos`
  - `continuidade_limites`
  - `pdd_investimentos`
  - `ped_projetos`
  - `pee_projetos`
  - `ons_intercambio_mensal`
  - `ons_conjuntos_usinas`
  - `ons_capacidade`
  - `curtailment_por_dono_mensal`
  - `curtailment_por_grupo_mensal`
  - `rap_por_grupo`
  - `capacidade_por_proprietario`
  - `usinas_proprietarios`

## 5. PDFs indexados sem link direto

| Arquivo | `url` atual | Link direto candidato (acervo do Drive) |
|---|---|---|
| `cemig_ras2024.pdf` | página inicial | https://www.cemig.com.br/wp-content/uploads/2025/07/Relatorio-Anual-de-Sustentabilidade-2024.pdf |
| `copel_ri2024.pdf` | listagem | 3 arquivos de 2024 no acervo (api.mziq.com); conferir pelo tamanho |
| `copel_ri2025.pdf` | listagem | 3 arquivos de 2025 no acervo (api.mziq.com); conferir pelo tamanho |
| `copel_materialidade_2023_2025.pdf` | página inicial | 4 arquivos de 2023 no acervo; conferir |
| `cpfl_ra24.pdf` | página inicial | 2 arquivos de 2024 em ri.cpfl.com.br; conferir |
| `eneva_ri2025.pdf` | página de RI | https://www.eneva.com.br/documents/32/RI_Eneva2025_PT_31Jul26.pdf |
| `engie_rs2024.pdf` | página inicial | https://www.engie.com.br/wp-content/uploads/2025/04/Engie_RS2024_PT.pdf |
| `isacteep_ras2024.pdf` | página de RI | https://ri.isaenergiabrasil.com.br/Arquivos/Download/relatorio-anual-isacteep-2024.pdf |
| `neoenergia_ras2024.pdf` | listagem | o acervo tem o relatório anual à ANEEL de 2024; conferir se é o mesmo documento |
| `taesa_rs2024.pdf` | página de RI | https://ri.taesa.com.br/wp-content/uploads/2018/11/TAESA-Relatorio-de-Sustentabilidade-2024.pdf |
| `axia_ras2025.pdf` | página do relatório (HTML) | sem correspondente no acervo |
| `equatorial_rs2024.pdf`, `equatorial_rs2025.pdf` | listagem | sem correspondente no acervo |
| `alupar_rs2023.pdf`, `alupar_rs2025.pdf`, `auren_ra2024.pdf`, `celesc_rs2025.pdf` | página inicial | empresas fora do acervo |

"Candidato" significa mesma empresa, ano e tipo. Antes de trocar a `url`, é preciso confirmar que é o mesmo arquivo,
comparando tamanho ou SHA-256 com o PDF em `data/raw/pdfs_esg/`.

## 6. Lacunas e recomendações (em ordem de prioridade)

1. **Registrar a origem dos 12 arquivos que só estão no Drive** (seção 2.2), dos quais dependem 14 tabelas: URL
   oficial, data de coleta e SHA-256 de cada arquivo. O melhor é passar a coletá-los pelo `baixar.py`, como já é feito
   com o resto. Enquanto isso, não dá para refazer esses dados a partir do código nem saber de que data eles são.
2. **Manifesto do `data/raw/`**: uma lista com arquivo, URL, data de coleta e SHA-256, como a do acervo do Drive. Assim a
   base passa a responder "de quando é este número?".
3. **Links diretos no `documentos.csv`** para os 17 PDFs da seção 5, começando pelos 5 com link já identificado.
4. **`debentures_incentivadas` está parada em 04/2024.** O modelo deve preferir `debentures_snd` para qualquer coisa
   recente, e isso pode entrar nas ressalvas da tabela.
5. **Cabeçalho do `DADOS.md` desatualizado.** Ele cita `platform/documentar_banco.py`, `platform/build_duckdb.py` e
   `research/DATA_DICTIONARY.md`, mas os arquivos atuais são `data/documentar.py`, `data/construir.py` e
   `researches/DATA_DICTIONARY.md`.
6. **Testes para as 16 tabelas sem validação** (seção 4.3), começando pelas usadas em respostas de grupo:
   `rap_por_grupo`, `usinas_proprietarios` e as de curtailment por dono e por grupo.
7. **Histórico financeiro** (opcional): a CVM publica DFP desde 2010 e ITR desde 2011 no mesmo formato. Se o histórico
   entrar, é preciso registrar as quebras contábeis nas ressalvas: CPC 47 / IFRS 15 em 2018, que mudou a receita e o
   ativo de contrato das transmissoras, e IFRS 16 em 2019, que trouxe os arrendamentos para o passivo. Também é preciso
   validar a detecção de CAPEX e D&A por texto nos anos antigos.
8. **Manter as estimativas marcadas.** Curtailment por dono e grupo e limites de DEC/FEC por distribuidora devem
   continuar aparecendo como estimativa nas respostas, como o catálogo já orienta.
