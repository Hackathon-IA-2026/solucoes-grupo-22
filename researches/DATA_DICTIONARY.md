# Dicionário de dados — formato e variáveis por fonte

Marcação de proveniência de cada bloco:

- **[lido]** — cabeçalho/colunas lidos direto do arquivo baixado (set/2026)
- **[subagente]** — reportado por subagente que baixou o arquivo; não reconferido
- **[não inspecionado]** — só descrito em documentação/busca

Prefixos ANEEL/ONS: `Dsc`=descrição, `Sig`=sigla, `Num`=número, `Mda`=medida, `Vlr`=valor, `Dat`=data, `Cod`=código, `Ide`=identificador.

## 1. CVM — dados financeiros (CSV `;`, ISO-8859-1, decimal `.`)

**DFP (anual) e ITR (trimestral)** — ZIP com 19 CSVs. `_con_` = consolidado, `_ind_` = individual; demonstrativos: BPA, BPP, DRE, DRA, DFC_MD, DFC_MI, DMPL, DVA, + `composicao_capital` e `parecer`. **[lido]** para DFP 2024 (BPA, DVA, DRE); **[subagente]** para ITR (mesma estrutura).

```
CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;
ORDEM_EXERC;DT_INI_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA
```
BPA (conferido) não tem `DT_INI_EXERC` (é posição, não período).

O indicador é uma **linha por conta** (`CD_CONTA`), não uma coluna. Contas de nível superior (`ST_CONTA_FIXA=S`) são iguais entre empresas:

| Indicador | `CD_CONTA` | Observação |
|---|---|---|
| Receita líquida | `3.01` (DRE) | |
| ≈EBIT | `3.05` (DRE) | EBITDA = `3.05` + D&A (`6.01.01.02` no DFC-MI) |
| Lucro líquido | `3.11` (DRE) | |
| Dívida bruta | `2.01.04` + `2.02.01` (BPP) | debêntures = subconta `.02` |
| Provisão ambiental/desativação | `2.01.06.02.03`, `2.02.04.02.03` (BPP) | só aparece quando a empresa reporta |
| CAPEX | `6.02.02` imobilizado, `6.02.03` intangível, `6.02.04` ativo de contrato/concessão (DFC-MI) | **conta e rótulo variam por empresa**; outras branches usam `6.02.01` — ver `README.md`, errata 3 |

**CAD** — cadastro mestre, 1 linha/companhia, 47 colunas **[lido]**. Úteis: `CNPJ_CIA, DENOM_SOCIAL, SIT, CD_CVM, SETOR_ATIV ("Energia Elétrica"), CONTROLE_ACIONARIO, CNPJ_AUDITOR, AUDITOR, UF, MUN`.

**FRE** — ~36 CSVs, só governança/capital/pessoas (acionistas, administradores, remuneração, diversidade) **[subagente]**. Risco climático (item 4.1) e política de sustentabilidade (1.8/2.7) **não estão em CSV**: só no documento completo via `LINK_DOC` do CSV-índice.

**IPE** — índice de documentos eventuais, 1 linha/documento; campo de categoria com valores como "Relatório de Sustentabilidade" e "Relato Integrado", e `Link_Download` para o PDF (exige `User-Agent`) **[subagente]**.

## 2. ANEEL — dados abertos (CSV `;`)

| Dataset | Colunas principais **[lido]** |
|---|---|
| **SIGA** (23 col.) | `CodCEG, IdeNucleoCEG, NomEmpreendimento, SigUFPrincipal, SigTipoGeracao, DscFaseUsina, DscOrigemCombustivel, DscTipoOutorga, DatEntradaOperacao, MdaPotenciaOutorgadaKw, MdaPotenciaFiscalizadaKw, MdaGarantiaFisicaKw, NumCoordNEmpreendimento, NumCoordEEmpreendimento, DscPropriRegimePariticipacao, DscSubBacia, DscMuninicpios` — CNPJ do titular só embutido em texto livre |
| **DEC/FEC** | `SigAgente, NumCNPJ, IdeConjUndConsumidoras, DscConjUndConsumidoras, SigIndicador, AnoIndice, NumPeriodoIndice, VlrIndiceEnviado` |
| **Tarifas homologadas** | `DscREH, SigAgente, NumCNPJDistribuidora, DatInicioVigencia, DatFimVigencia, DscSubGrupo, DscModalidadeTarifaria, DscClasse, DscSubClasse, NomPostoTarifario, VlrTUSD, VlrTE` |
| **P&D (Lei 9.991)** | `SigAgente, NumCPFCNPJ, DscTituloProjeto, SigSegmentoSetorEletrico, SigTemaProjeto, SigFasInovacaoProjeto, VlrCustoTotalPrevisto, VlrCustoTotalAuditado, AnoCadastroPropostaProjeto, DatConclusaoProjeto` |
| **PEE** (eficiência) | `NomAgente, IdeEmpresaProponenteProjeto, DscTipologia, VlrCustoTotal, VlrEnergiaEconomizadaTotal, VlrRetiradaDemandaPontaTotal` — **sem CNPJ**, só nome |
| **Leilões de geração** | `NumLeilao, DscTipoLeilao, CodCEG, SigTipoGeracao, DscFonteEnergia, MdaPotenciaInstaladaMW, VlrPrecoLeilao, VlrDesagio, VlrInvestimentoPrevisto, MdaDuracaoContrato, DscEmpresaVencedora` |
| **PDD** (plano de desenvolvimento da distribuição) | `SigAgente, NumCPFCNPJ, AnoReferencia, DscTipoObra, DscTipoObraClasse, VlrTotalPlanejado, VlrTotalRealizado` |
| **SIGET — Contrato Agente** | `IdeCcd, IdAgente, NumCNPJ, DscRazaoSocial, SigUF, NomMunicipio` — arquivo completo lido: 413 linhas, 305 CNPJs, **ISO-8859-1** |
| **SIGET — Empreendimento/Obra/Módulo** | `IdeCcd` (junta com Agente), `IdeEpd, NomEpd, DscSituacaoEpd, DscObr, NomMdl, SigTipMdl, VlrHisRct` — arquivo completo lido: 6.225 linhas, UTF-8, campos com quebra de linha entre aspas. O join por `IdeCcd` casa 100% dos módulos. **`VlrHisRct` não está confirmado como RAP**: o mesmo valor se repete em todos os módulos de um empreendimento e, mesmo deduplicando por `IdeEpd`, a soma dá R$ 322 bi (o RAP anual do setor é da ordem de R$ 55 bi, segundo `FINDINGS-muse-spark-1.2.md`), então provavelmente há mais de um valor histórico por empreendimento. Conferir no dicionário da ANEEL antes de usar |
| **MMGD** (geração distribuída) | **[lido]** em 25/09/2026: ver seção 10.1 |
| **Ciefse/RIT** | **[não inspecionado]** (Parquet/CSV, Power BI) |

Chaves: CNPJ (`NumCNPJ`, `NumCPFCNPJ`, `NumCNPJDistribuidora`) nas tabelas financeiras/regulatórias; `CodCEG` nas físicas (SIGA, leilões, ONS).

## 3. ONS (Parquet e CSV, S3 `ons-aws-prod-opendata`)

| Dataset | Colunas **[lido]** |
|---|---|
| **Capacidade de geração** | `id_subsistema, nom_estado, nom_agenteproprietario, nom_agenteoperador, nom_tipousina, nom_usina, ceg, nom_unidadegeradora, nom_combustivel, dat_entradaoperacao, dat_desativacao, val_potenciaefetiva` |
| **Curtailment eólico (COFF)** | `nom_usina, ceg, din_instante, val_geracao, val_geracaolimitada, val_disponibilidade, val_geracaoreferencia, cod_razaorestricao, cod_origemrestricao, dsc_restricao, nom_agenteoperador, val_geracaonaorealizadaapurada` |
| **CMO semi-horário (Parquet)** | `id_subsistema, nom_subsistema, din_instante, val_cmo` — 2020–2026, quatro subsistemas por meia hora. `val_cmo` é texto decimal com ponto, em R$/MWh. |
| **EAR diário por subsistema (Parquet)** | `id_subsistema, nom_subsistema, ear_data, ear_max_subsistema, ear_verif_subsistema_mwmes, ear_verif_subsistema_percentual` — 2000–2026, quatro subsistemas por dia. A data e os valores numéricos vêm como texto, com decimal ponto. |
| Geração horária por usina, ENA, carga, balanço, intercâmbio | **[lido]** em 25/09/2026: ver seção 10.2 (a geração por usina passou a ser publicada por mês a partir de 2022) |

Chave: `ceg` (cruza com `CodCEG` da ANEEL).

**CMO e EAR [lido]:** arquivos anuais Parquet do catálogo oficial do ONS em
https://dados.ons.org.br/dataset/cmo-semi-horario e
https://dados.ons.org.br/dataset/ear-diario-por-subsistema. Parquet é binário colunar,
sem codificação de texto nem separador CSV; os campos de texto são UTF-8. A coleta lista
recursos Parquet na API CKAN oficial, guarda o arquivo original em `raw/ons/` e não
sobrescreve versões já baixadas sem `--forcar`. Em 2026, `id_subsistema` de EAR traz
espaço final em `N ` e `S `; aplicar `trim` antes de agrupar. `SE` corresponde ao
Sudeste/Centro-Oeste. EAR é expressa em **MWmês**, não em MW ou MWh, e seu percentual
é o valor reportado pelo ONS. CMO é em **R$/MWh**; não confundir com PLD de liquidação.
O arquivo corrente de CMO pode incluir o dia seguinte programado, e ambas as séries
podem ser revisadas pelo ONS. O arquivo CMO 2026 coletado omite 09/08/2026 em todos
os subsistemas: agosto tem 30 dias e 1.440 intervalos, não 31 dias. A média mensal
da plataforma é aritmética dos intervalos disponíveis, sem ponderação pela carga
entre intervalos; o CMO semihorário do subsistema já pondera as barras pelas
respectivas cargas segundo o ONS. `dias_ausentes` no catálogo identifica meses incompletos.

## 4. EPE (XLSX) **[lido]**

- **Anuário — Dados brutos** (aba única): `Data, TipoConsumidor, Sistema, UF, Setor Econômico N1–N3, Tipo Tensão N1–N3, Faixa de Consumo N1–N2, Consumidores, Consumo` — consumo por UF/setor, **sem empresa**.
- **PDE 2035 — Transmissão**: `Estudo, Tipo do Empreendimento, Região Geoelétrica, UF Origem, UF Destino, Nome do Empreendimento, Itens de obra, Status, Data de Necessidade, km Total, Potência Total, Contratação, SIGET.codDMSE, Total Investimento (2025) R$/1000, datas de tendência por cenário`.

## 5. BNDES (CSV `;`, **CP1252** — converter com `iconv`) **[lido]**

- **Operações não automáticas** (34 col.): `cliente, cnpj, descricao_do_projeto, uf, municipio, numero_do_contrato, data_da_contratacao, valor_contratado_reais, valor_desembolsado_reais, custo_financeiro, juros, prazo_carencia_meses, prazo_amortizacao_meses, produto, instrumento_financeiro, inovacao, setor_cnae, subsetor_cnae_nome, setor_bndes, subsetor_bndes, porte_do_cliente, natureza_do_cliente, tipo_de_garantia, situacao_do_contrato`. CNPJ com pontuação, igual ao da CVM. Valores numéricos usam vírgula decimal.
- **Desembolsos mensais**: `ano, mes, forma_de_apoio, produto, instrumento_financeiro, porte_de_empresa, regiao, uf, municipio, setor_cnae, setor_bndes, subsetor_bndes, desembolsos_reais` — sem CNPJ.

## 6. B3 e ANBIMA **[subagente]**

- **B3 `GetPortfolioDay`** (JSON, API não documentada): códigos `IEEX` (IEE), `ISEE` (ISE), `ICO2`, `UTIL`. Campos: `cod` (ticker), `asset`, `type`, `part` (peso %), `theoricalQty`. Só composição de carteira.
- **ANBIMA — debêntures incentivadas (Lei 12.431)** (XLSX, 3 abas): emissor, código CETIP, valor total (R$ mil), spread, indexador, setor.

## 7. CCEE **[subagente]**

CSV atrás de WAF (Akamai): `curl` recebe 403 (reconferido em 25/09/2026: a API CKAN `dadosabertos.ccee.org.br/api/3/action/...` e o painel de preços devolvem a página "Acesso bloqueado", então o PLD continua fora da base); funcionou via fetch com fingerprint de navegador. PLD horário (submercado, hora, R$/MWh), consumo ACL×ACR (nacional), geração UHE/MRE (por nome de parcela, sem CNPJ). Colunas exatas não conferidas.

## 8. Relatórios de sustentabilidade (PDF, texto nativo)

Sem colunas: os indicadores precisam de um schema de extração. O que apareceu nos 11 PDFs lidos pelo subagente (com página): Escopo 1/2/3 (tCO2e), meta net zero (ano), CAPEX total, frameworks declarados (GRI/SASB/TCFD/ISSB), auditor de asseguração, e a página do índice remissivo GRI/SASB. Números e páginas por empresa estão em `FINDINGS-claude-sonnet-5.md` §3.2. Exceção estruturada: a Eneva publica Databook ESG em XLSX.

## 9. Armadilhas confirmadas ao cruzar as fontes

Teste em DuckDB (CVM CAD + DRE + DFC-MI + BPP 2024, junção por CNPJ com BNDES):

1. **Sinal do CAPEX**: contas do DFC são saída de caixa, portanto negativas; usar valor absoluto antes de exibir.
2. **CAPEX 0** para Equatorial, Copel e Engie com `6.02.02+6.02.03` — provável registro em `6.02.04`. Casar por `DS_CONTA`, não só por código.
3. **CAD duplica CNPJ** (CPFL, Copel, EDP, Engie apareceram 2–3× com `SIT=ATIVO`): deduplicar antes de usar como dimensão.
4. `VERSAO`: manter a maior por `CNPJ_CIA`+`DT_REFER`; `ESCALA_MOEDA` (MIL/UNIDADE) varia entre empresas do mesmo arquivo; `ORDEM_EXERC` vale "ÚLTIMO"/"PENÚLTIMO" (acento, Latin-1).
5. Encodings: CVM ISO-8859-1; BNDES CP1252; ANEEL SIGA, tarifas e SIGET obra/módulo em UTF-8, mas **SIGET contrato-agente em ISO-8859-1** (conferido com `file`); ONS em UTF-8.
6. SIGET obra/módulo tem quebras de linha dentro de campos entre aspas: no DuckDB o sniffer falha; use `parallel=false` (e `escape='"'`).

Resultado ilustrativo do teste (DFP 2024, R$ milhões; CAPEX = `6.02.02+6.02.03`, negativo = saída, 0 = conta não usada; **não usar como número final**):

| Empresa | Receita líq. | CAPEX | Dívida bruta | Contratos BNDES | Desembolsado BNDES |
|---|---:|---:|---:|---:|---:|
| Neoenergia | 48.993 | -5.608 | 52.600 | — | — |
| Equatorial | 45.367 | 0 | 55.827 | — | — |
| CPFL Energia | 42.628 | -5.054 | 28.788 | — | — |
| Axia Energia | 40.182 | -3.087 | 75.803 | 13 | 4.054 |
| Cemig | 39.820 | -920 | 12.279 | 2 | 512 |
| Engie Brasil | 11.219 | 0 | 23.648 | 12 | 2.807 |

O CAD tinha 120 registros ativos de "Energia Elétrica"; 1.185 CNPJs com contrato BNDES do subsetor. O script não foi versionado (rodou em diretório temporário da sessão).

## 10. Bases acrescentadas em 25/09/2026 **[lido]**

Todas baixadas por `platform/baixar_dados.py` (`--fonte aneel`, `--fonte bcb`, `--fonte ons-series`) para `raw/<fonte>/` e
carregadas por `platform/build_duckdb.py`. Descrição, fonte e ressalvas de cada tabela estão em `platform/DADOS.md`.

### 10.1 ANEEL (dadosabertos.aneel.gov.br e gov.br)

| Arquivo em `raw/` | Formato | Colunas usadas | Observações |
|---|---|---|---|
| `aneel/societaria/composicao-societaria-polimero.parquet` | Parquet, 1,1 mi de linhas | `AnoExercicio, IdcTrimestreFormulario, NumNivelCadeiaSocietaria, NumCPFCNPJPaiCadeiaSocietaria, NomRazSocPaiCadeiaSocietaria, DscTipoCadeiaSocietaria, NumCPFCNPJSocio, NomRazaoSocialSocio, PctParticipacaoNivelAcima, IdcPerfilSocietario, IdcGoverno, IdcEmpresaEstrangeira, NumOrdemCadeiaSocietaria` | Cada declaração é uma árvore contígua em `NumOrdemCadeiaSocietaria`: a linha de nível 0 ("Inicio de Composicao Societaria") traz o agente em `NumCPFCNPJSocio`; as seguintes, os sócios de nível 1, 2... com o CNPJ do pai. `PctParticipacaoNivelAcima` é a participação **efetiva no agente da raiz** (ex.: ETAU: Taesa 75,62%; ISA via Taesa 11,25% = 75,62% × 14,88%), não a participação no pai; os níveis 1 somam 100% em todas as 4.253 árvores mais recentes. As linhas não seguem ordem de busca em profundidade: o pai se acha pelo CNPJ/nome e pelo nível. `NumCPFCNPJPaiCadeiaSocietaria` é inteiro (sem zeros à esquerda). Perfil `DC` = ações em bolsa/tesouraria; `PF` traz CPF (não levado ao banco). Algumas declarações repetem o mesmo sócio (soma > 100%): a plataforma remove linhas idênticas e limita a 100% |
| `aneel/siget_rap/siget-lista-modulos-previa-reajuste-rap.csv` | CSV `;`, **CP1252**, CRLF, 47.392 linhas | `SigConcessionariaReceita, NumContratoReceita, NumCNPJConcessionariaMdl, NumContratoModulo, NomTipoReceita, DcsSitRAP, IdeRct, IdeMdl, NomModulo, VlrRAPCiclo, QtdAnosCcoTar, DatRefCiclo, VlrRAPAtoLegal, NumAtoRAP, SigIndice` | Uma linha por módulo e receita; `VlrRAPCiclo` é o valor **do módulo** (decimal com vírgula) e a soma de todas as linhas `Ativa` dá R$ 55,5 bi. `NumCNPJConcessionariaRct` vem quase sempre vazio ou com CNPJ de outro agente: o CNPJ da receita sai do módulo do mesmo contrato (`NumContratoModulo = NumContratoReceita`), que é único para os 411 contratos. Em 25/09/2026 o arquivo trazia `QtdAnosCcoTar = 2027-2028` e `DatRefCiclo = 2027-06-01` em todas as linhas. Sem Parcela de Ajuste |
| `aneel/mmgd/empreendimento-geracao-distribuida.parquet` | Parquet, 4,66 mi de linhas (106 MB) | `NumCNPJDistribuidora, SigAgente, SigUF, DscClasseConsumo, SigTipoGeracao, DscFonteGeracao, DscPorte, DscModalidadeHabilitado, DthAtualizaCadastralEmpreend, MdaPotenciaInstaladaKW, QtdUCRecebeCredito, AnmPeriodoReferencia` | Uma linha por empreendimento; `NumCPFCNPJ` do titular (inclui CPF) não é carregado: a tabela é agregada. `DthAtualizaCadastralEmpreend` é a última atualização cadastral (há datas 1900-01-01). Total em 09/2026: 54,0 GW |
| `aneel/ralie/ralie-usina-atual.csv`, `ralie-unidade-geradora-atual.csv` | CSV `;`, UTF-8, CRLF | usina: `CodCEG, NomEmpreendimento, MdaPotenciaOutorgadaKw (vírgula), DscSituacaoObra, DscViabilidade, DscSituacaoCronograma, DatPrevisaoInicioObra...`; UG: `CodCEG, NumUgUsina, DatUGInicioOpComerOutorgado, DatPrevisaoOpComercialSFG` | 2.246 usinas e 76.591 unidades geradoras; a data prevista de operação está só no arquivo de unidades geradoras |
| `aneel/samp/samp-AAAA.parquet` (2020–2026) | Parquet, ~1,4 mi de linhas por ano | `NumCNPJAgenteDistribuidora, SigAgenteDistribuidora, NomTipoMercado, DscClasseConsumoMercado, DscOpcaoEnergia, DscDetalheMercado, DatCompetencia, VlrMercado` | Formato longo: `DscDetalheMercado` diz o que é `VlrMercado` (Receita Energia (R$), Energia TUSD (kWh), Energia TE (kWh), Número de consumidores — às vezes com C maiúsculo —, ICMS, PIS/COFINS...). Tipos de mercado com "Refaturamento" são correções. Há erros de declaração (Cemig D, residencial, jul e out/2025: receita ~10 vezes o normal) |
| `aneel/samp/samp-balanco.parquet` | Parquet | balanço energético das distribuidoras | baixado, ainda não carregado no banco |
| `aneel/bandeiras/bandeira-tarifaria-acionamento.csv`, `-adicional.csv` | CSV `;`, UTF-8 | `DatCompetencia, NomBandeiraAcionada, VlrAdicionalBandeira` (R$/MWh, vírgula) | desde 01/2015 |
| `aneel/agentes/agentes-setor-eletrico.csv` | CSV `;`, UTF-8 | `NumCnpj, SigPessoa, NomRazaoSocial, IdcAtivo, IdcComercializacao, IdcDistribuicao, IdcGeracao, IdcTransmissao` | 9.956 agentes com CNPJ; alguns nomes vêm entre `''` |
| `aneel/ranking_continuidade/ranking_AAAA.html` (2021–2025) | HTML do gov.br | tabela I (mais de 400 mil UCs) e II (até 400 mil): posição, DGC, sigla, empresa, região | 2019 e 2020 não existem nesse endereço (404). DGC com vírgula; "-" quando não apurado. A razão social casa com o cadastro de agentes para achar o CNPJ (2 nomes antigos sem CNPJ) |

### 10.2 ONS (dados.ons.org.br, Parquet no S3 `ons-aws-prod-opendata`)

| Pasta em `raw/ons/` | Conjunto | Colunas | Observações |
|---|---|---|---|
| `carga_energia_diaria/CARGA_ENERGIA_AAAA.parquet` | carga-energia (2000–2026) | `id_subsistema, nom_subsistema, din_instante, val_cargaenergiamwmed` | MW médio do dia |
| `ena_diario_subsistema/ENA_DIARIO_SUBSISTEMA_AAAA.parquet` | ena-diario-por-subsistema (2021–2026 em Parquet) | `id_subsistema, ena_data (texto), ena_bruta_regiao_mwmed, ena_bruta_regiao_percentualmlt, ena_armazenavel_regiao_mwmed, ena_armazenavel_regiao_percentualmlt` | `id_subsistema` com espaço final (`N `); anos anteriores a 2021 só em CSV, não baixados |
| `balanco_energia_subsistema/BALANCO_ENERGIA_SUBSISTEMA_AAAA.parquet` | balanco-energia-subsistema (2015–2026) | `id_subsistema, din_instante, val_gerhidraulica, val_gertermica, val_gereolica, val_gersolar, val_carga, val_intercambio` | horário, MW médio (soma de 1 h = MWh); valores como texto em alguns anos; `id_subsistema` com espaços e linha `SIN` de total |
| `intercambio_nacional/INTERCAMBIO_NACIONAL_AAAA.parquet` | intercambio-nacional (2023–2026) | `din_instante, id_subsistema_origem, id_subsistema_destino, val_intercambiomwmed, val_intercambioprogmwmed` | horário; valores como texto |
| `geracao_usina/GERACAO_USINA-2_AAAA[_MM].parquet` | geracao-usina-2 (2020 em diante; anual até 2021, mensal a partir de 2022) | `din_instante, id_subsistema, id_estado, cod_modalidadeoperacao, nom_tipousina, nom_tipocombustivel, nom_usina, id_ons, ceg, val_geracao` | horário em MW médio (texto em alguns arquivos); `ceg` = '-' em conjuntos e nas "Pequenas Usinas (MMGD)"; 2025 soma 701 TWh; 326 MB de 2020 a 09/2026 |

### 10.3 Banco Central (SGS)

`raw/bcb/sgs_<código>_<nome>.json`, da API `https://api.bcb.gov.br/dados/serie/bcdata.sgs.<código>/dados?formato=json&dataInicial=...&dataFinal=...`
(janelas de 10 anos; a API às vezes devolve uma página HTML de erro, e a coleta tenta de novo). Cada ponto é
`{"data": "dd/mm/aaaa", "valor": "0.33"}` com ponto decimal. Séries: 433 IPCA (% no mês), 13522 IPCA 12 meses,
189 IGP-M (% no mês), 4390 Selic acumulada no mês, 4391 CDI acumulado no mês, 432 meta Selic (% a.a., diária e
publicada até a próxima reunião do Copom) e 3698 dólar PTAX venda (média mensal).

### 10.4 SND — debêntures (ANBIMA/B3)

`raw/snd/debentures_caracteristicas.xls`: apesar da extensão, é **texto separado por tabulação em Latin-1**, exportado
por `caracteristicas_e.asp?tip_deb=publicas&` em debentures.com.br. As 4 primeiras linhas são aviso e data de geração;
a 5ª é o cabeçalho (86 colunas, com espaços nas bordas e "Unidade Monetaria" repetida). Colunas usadas: `Codigo do Ativo,
Empresa, CNPJ, Situacao (Registrado/Excluído), Data de Emissao, Data de Vencimento, indice, Percentual
Multiplicador/Rentabilidade, Juros Criterio Novo - Taxa, Deb. Incent. (Lei 12.431), Quantidade Emitida, Quantidade em
Mercado (com zeros à esquerda), Valor Nominal na Emissao, Valor Nominal Atual, Data Ult. VNA`. 10.008 debêntures;
vencidas ainda podem aparecer como "Registrado" com quantidade em mercado zero. Não há cronograma de amortização por data.
