# Dados do EnergyNexus

Tabelas e visões do `coppezip.duckdb` em 25/09/2026, geradas do catálogo por `data/documentar.py`. Não edite à mão: descrição, fonte e ressalvas vêm do catálogo em `data/construir.py`, o mesmo texto que o modelo lê. O formato dos arquivos brutos de cada fonte está em `researches/DATA_DICTIONARY.md`.

| Tabela | Linhas | Descrição | Fonte |
|---|---:|---|---|
| [`agentes_aneel`](#agentes_aneel) | 9.956 | Cadastro de agentes da ANEEL: CNPJ, sigla e razão social de geradoras, transmissoras, distribuidoras e comercializadoras (inclusive as que não são companhias abertas). Use para achar o CNPJ de uma empresa que não está em empresas. | ANEEL, Agentes do Setor Elétrico, https://dadosabertos.aneel.gov.br/dataset/agentes-do-setor-eletrico |
| [`bandeiras_tarifarias`](#bandeiras_tarifarias) | 141 | Bandeira tarifária acionada pela ANEEL em cada mês (Verde, Amarela, Vermelha P1, Vermelha P2, Escassez Hídrica) e o adicional cobrado na conta, em R$/MWh, desde 2015. | ANEEL, Bandeiras Tarifárias - Acionamento, https://dadosabertos.aneel.gov.br/dataset/bandeiras-tarifarias |
| [`bndes_operacoes`](#bndes_operacoes) | 23.815 | Operações de financiamento não automáticas do BNDES (contratos diretos e indiretos), com cliente, CNPJ, projeto, valores contratado e desembolsado em R$, custo e prazos. setor_eletrico marca geração, transmissão e distribuição. | BNDES dados abertos, operações não automáticas |
| [`capacidade_por_grupo`](#capacidade_por_grupo) | 7.026 | Capacidade de geração (SIGA) atribuída a cada grupo ou empresa participante, direta ou indiretamente, por origem, tipo e fase. potencia_proporcional_mw = potência × participação do dono na usina × participação indireta do participante no dono (visão proporcional); potencia_controlada_mw = potência × participação do dono, só nas usinas cujo dono o participante controla (visão consolidada). Para ranking de grupos filtre fase = 'Operação' e agrupe por chave_participante. | ANEEL SIGA e Composição Societária (Polímero); cálculo desta plataforma |
| [`capacidade_por_proprietario`](#capacidade_por_proprietario) | visão | Capacidade instalada em MW por dono (CNPJ), origem, tipo e fase, já ponderada pela participação de cada dono. | ANEEL SIGA |
| [`compensacoes_continuidade`](#compensacoes_continuidade) | 10.015.978 | Compensações pagas pelas distribuidoras aos consumidores por violação dos limites de continuidade, por conjunto e mês: PGU* = valor pago em R$, QTU* = quantidade de unidades compensadas (a coluna descricao explica cada código). | ANEEL, compensação por violação de continuidade |
| [`composicao_societaria`](#composicao_societaria) | 73.056 | Cadeia societária declarada à ANEEL por cada agente do setor (usina, transmissora, distribuidora), da declaração mais recente: sócios diretos (nivel 1) e indiretos (nivel 2, 3...) até o controlador final. participacao_indireta_pct é a participação efetiva do sócio no agente (já multiplicada ao longo da cadeia). Para somar por grupo use participacoes_societarias, grupos_economicos e capacidade_por_grupo. | ANEEL, Composição Societária (Polímero), https://dadosabertos.aneel.gov.br/dataset/composicao-societaria-polimero |
| [`contas_cvm`](#contas_cvm) | 312.693 | Todas as contas das demonstrações financeiras anuais (DFP) das empresas do setor, de 2020 em diante, já em R$ (escala MIL aplicada), última versão entregue. demonstrativo: BPA, BPP, DRE, DFC_MI, DFC_MD, DVA; escopo: consolidado ou individual. Prefira kpis_financeiros para indicadores prontos. | CVM, DFP (dados.cvm.gov.br) |
| [`contas_cvm_trimestral`](#contas_cvm_trimestral) | 462.169 | Contas das demonstrações trimestrais (ITR) de 2024 em diante, em R$: periodo = trimestre (só os 3 meses), acumulado (desde janeiro) ou saldo (balanço no fim do trimestre). O 4º trimestre não existe no ITR: está na DFP anual. | CVM, ITR (dados.cvm.gov.br) |
| [`continuidade_conjuntos`](#continuidade_conjuntos) | 5.108.332 | Indicadores de continuidade por conjunto de consumidores e mês (2020 em diante): DEC em horas e FEC em interrupções, com os componentes (programada, externa, dia crítico...) e NumCon (número de consumidores do conjunto). | ANEEL, indicadores coletivos de continuidade |
| [`continuidade_limites`](#continuidade_limites) | 263.401 | Limites regulatórios anuais de DEC e FEC por conjunto de consumidores, definidos pela ANEEL. | ANEEL |
| [`curtailment_por_dono_mensal`](#curtailment_por_dono_mensal) | visão | Estimativa da energia cortada (curtailment) por dono de usina (CNPJ) e mês, eólica e solar. | ONS e ANEEL SIGA; cálculo desta plataforma |
| [`curtailment_por_grupo_mensal`](#curtailment_por_grupo_mensal) | visão | Estimativa da energia eólica e solar cortada (curtailment) por grupo econômico e mês: proporcional à participação indireta do grupo em cada SPE e controlada (100% das SPEs que o grupo controla). | ONS, ANEEL SIGA e Composição Societária; cálculo desta plataforma |
| [`debentures_incentivadas`](#debentures_incentivadas) | 777 | Emissões de debêntures incentivadas de infraestrutura (Lei 12.431), com emissora, código, valor em R$, taxa e indexador. setor = 'Energia Elétrica' para o setor. | ANBIMA, planilha de debêntures incentivadas (até 04/2024) |
| [`debentures_snd`](#debentures_snd) | 10.008 | Todas as debêntures registradas no SND (Sistema Nacional de Debêntures), com CNPJ da emissora, data de emissão e de vencimento, indexador (DI, IPCA, PRE...) e taxa, se é incentivada (Lei 12.431), garantia, quantidade e saldo em mercado. setor_eletrico marca emissoras do setor (CVM ou agentes da ANEEL). Use para cronograma de vencimentos e custo da dívida em debêntures de uma empresa (filtre situacao = 'Registrado' para as vigentes). | SND/ANBIMA, Características das Debêntures, https://www.debentures.com.br/exploreosnd/consultaadados/emissoesdedebentures/caracteristicas_r.asp |
| [`dec_fec_distribuidora_anual`](#dec_fec_distribuidora_anual) | visão | DEC (horas) e FEC (interrupções) anuais de cada distribuidora, com os limites da ANEEL e o número médio de consumidores, de 2020 em diante. | ANEEL, indicadores coletivos de continuidade; cálculo desta plataforma |
| [`empresas`](#empresas) | 151 | Companhias abertas do setor elétrico registradas na CVM (uma linha por CNPJ). Use buscar_empresa para achar o CNPJ. | CVM, cadastro de companhias abertas (cad_cia_aberta.csv) |
| [`empresas_apelidos`](#empresas_apelidos) | 153 | Apelidos, marcas, nomes antigos e tickers da B3 de cada empresa, ligados ao CNPJ (base da ferramenta buscar_empresa). | CVM FCA (valores mobiliários negociados) e lista curada de apelidos |
| [`expansao_geracao`](#expansao_geracao) | 2.246 | Usinas outorgadas ainda não concluídas acompanhadas pela ANEEL (RALIE): potência, situação da obra (em andamento, não iniciada, paralisada), viabilidade, situação do cronograma e datas de entrada em operação outorgada (ato de outorga) e prevista pela fiscalização da ANEEL, por unidade geradora. Use para a expansão da oferta e atrasos; os donos com CNPJ estão em usinas_proprietarios pelo ceg. | ANEEL, RALIE, https://dadosabertos.aneel.gov.br/dataset/ralie-relatorio-de-acompanhamento-da-expansao-da-oferta-de-geracao-de-energia-eletrica |
| [`gd_mmgd`](#gd_mmgd) | 66.826 | Micro e minigeração distribuída (MMGD, painéis solares em telhados e usinas de até 5 MW na rede da distribuidora) agregada por distribuidora, UF, classe de consumo, fonte, porte, modalidade e mês de cadastro: número de empreendimentos e potência instalada em MW. Some tudo para o total conectado; filtre mes_cadastro para a evolução. | ANEEL, Relação de Empreendimentos de Geração Distribuída, https://dadosabertos.aneel.gov.br/dataset/relacao-de-empreendimentos-de-geracao-distribuida |
| [`grupos_economicos`](#grupos_economicos) | 4.253 | Grupo econômico de cada agente do setor (uma linha por CNPJ): controladores diretos com participação, controladores finais (topo da cadeia de controle, podem ser vários quando o controle é compartilhado) e a companhia aberta do setor (CVM) que controla o agente, a mais próxima dele na cadeia (holding_cvm), que costuma ser o grupo como o mercado o chama (ex.: SPE da Taesa -> Taesa; Coelba -> Neoenergia). Use para dizer a que grupo pertence uma SPE, usina ou concessão. | ANEEL, Composição Societária (Polímero); cálculo desta plataforma |
| [`indicadores_codigos`](#indicadores_codigos) | 484 | Significado dos códigos de indicadores de qualidade da ANEEL (DEC, FEC e componentes; PGU* e QTU* das compensações). | ANEEL, domínio dos indicadores de continuidade |
| [`indicadores_macro_mensal`](#indicadores_macro_mensal) | 321 | Indicadores macroeconômicos mensais do Banco Central desde 2000: IPCA do mês e em 12 meses, IGP-M do mês e em 12 meses (índices de reajuste de tarifas e RAP), Selic e CDI acumulados no mês, meta Selic no fim do mês (% ao ano) e dólar PTAX de venda médio do mês. Use para contexto de tarifas, RAP e custo da dívida. | Banco Central, SGS (api.bcb.gov.br): séries 433 (IPCA), 13522 (IPCA 12 meses), 189 (IGP-M), 4390 (Selic mensal), 4391 (CDI mensal), 432 (meta Selic), 3698 (dólar PTAX venda, média mensal) |
| [`kpis_financeiros`](#kpis_financeiros) | 652 | Indicadores financeiros anuais por empresa (2020 em diante), em R$, prontos para comparar: receita, EBIT, EBITDA calculado, lucro, dívida bruta e líquida, caixa, CAPEX, dividendos, margens, alavancagem, cobertura de juros e ROE. Usa o consolidado quando a empresa o publica. | CVM DFP; cálculo desta plataforma a partir das contas indicadas na coluna fonte |
| [`kpis_trimestrais`](#kpis_trimestrais) | 879 | Indicadores trimestrais (ITR) de 2024 em diante: receita, EBIT e lucro do trimestre e acumulados no ano, EBITDA, valores dos últimos 12 meses, dívida bruta e líquida no fim do trimestre, dívida líquida/EBITDA 12 meses e investimento acumulado. É o dado mais recente da base (a DFP anual vai até 2025). | CVM ITR e DFP; cálculo desta plataforma |
| [`leiloes_geracao`](#leiloes_geracao) | 1.552 | Resultados dos leilões de GERAÇÃO de energia (2005 em diante): empreendimento, fonte, potência, preço, deságio, investimento previsto e vencedor. | ANEEL, resultado de leilões de geração |
| [`mercado_distribuidoras_mensal`](#mercado_distribuidoras_mensal) | 85.343 | Mercado e faturamento mensal de cada distribuidora por classe de consumo (Residencial, Comercial, Industrial, Rural...) e mercado (CATIVO, LIVRE, GERAÇÃO, SUPRIMENTO), de 2020 em diante: consumidores, energia faturada em MWh, receitas de energia, demanda e bandeiras, tributos e a tarifa média sem tributos em R$/MWh. Para a tarifa média do ano some receita_energia_brl + receita_demanda_brl e divida pela soma de energia_tusd_mwh (não tire média das médias mensais). | ANEEL, SAMP - Sistema de Acompanhamento de Informações de Mercado, https://dadosabertos.aneel.gov.br/dataset/samp |
| [`ons_capacidade`](#ons_capacidade) | 5.678 | Unidades geradoras despachadas pelo ONS com agente proprietário e potência efetiva em MW. | ONS, capacidade instalada |
| [`ons_carga_diaria`](#ons_carga_diaria) | 39.053 | Carga de energia diária do SIN por subsistema (N, NE, S, SE = Sudeste/Centro-Oeste), em MW médio, desde 2000. Energia do dia em MWh = carga_mwmed × 24. | ONS, Carga de Energia, https://dados.ons.org.br/dataset/carga-energia |
| [`ons_cmo_mensal`](#ons_cmo_mensal) | 324 | CMO médio mensal do ONS por subsistema (N, NE, S, SE), em R$/MWh, desde 2020. SE corresponde ao subsistema Sudeste/Centro-Oeste; o arquivo do ONS o rotula SUDESTE, mas não há submercado Centro-Oeste separado. Cada linha é um subsistema-mês; cmo_medio_brl_mwh é a média aritmética dos intervalos semihorários. Use dias_ausentes, dias_com_dados e intervalos para avaliar cobertura antes de comparar meses; um mês com dias_ausentes > 0 não tem média mensal completa. | ONS, CMO Semi-Horário, https://dados.ons.org.br/dataset/cmo-semi-horario; média calculada pela plataforma |
| [`ons_cmo_semihora`](#ons_cmo_semihora) | 464.064 | CMO (Custo Marginal de Operação) do ONS por subsistema e instante semihorário, desde 2020. SE corresponde ao subsistema Sudeste/Centro-Oeste, embora o arquivo o rotule SUDESTE. Para comparar meses e submercados use ons_cmo_mensal; para horários e extremos use esta tabela. | ONS, CMO Semi-Horário, https://dados.ons.org.br/dataset/cmo-semi-horario |
| [`ons_conjuntos_usinas`](#ons_conjuntos_usinas) | 1.615 | Usinas eólicas e solares que formam cada conjunto do ONS (id_conjunto = id_ons de ons_curtailment_mensal), com o CEG de cada usina. | ONS, detalhamento por usina dos cortes de geração (ago/2026) |
| [`ons_curtailment_mensal`](#ons_curtailment_mensal) | 9.027 | Cortes de geração (curtailment) por usina e mês: geração, geração de referência e energia cortada em MWh, e % cortado. fonte = eólica (2023 em diante) ou solar (abr/2024 em diante). | ONS, restrição de operação por constrained-off (GNRa = geração não realizada apurada) |
| [`ons_curtailment_semihora`](#ons_curtailment_semihora) | visão | Cortes de geração eólica (2023 em diante) e solar (abr/2024 em diante) por usina e meia hora, em MW médio: geração verificada, geração de referência e geração não realizada apurada (GNRa). | ONS, restrição de operação por constrained-off |
| [`ons_ear_diario`](#ons_ear_diario) | 39.052 | Energia armazenada (EAR) diária nos reservatórios por subsistema do ONS, desde 2000. SE corresponde ao subsistema Sudeste/Centro-Oeste, embora o arquivo o rotule SUDESTE. Cada linha é um subsistema e uma data; traz a EAR verificada em MWmês, sua capacidade máxima em MWmês e o percentual de armazenamento. Útil para avaliar risco hidrológico e contexto do CMO. | ONS, EAR Diário por Subsistema, https://dados.ons.org.br/dataset/ear-diario-por-subsistema |
| [`ons_ena_diaria`](#ons_ena_diaria) | 8.372 | Energia Natural Afluente (ENA) diária por subsistema, em MW médio e em % da média de longo termo (MLT), desde 2021: mede quanta água chega aos reservatórios. Abaixo de 100% da MLT = afluência abaixo da média histórica. | ONS, ENA Diário por Subsistema, https://dados.ons.org.br/dataset/ena-diario-por-subsistema |
| [`ons_geracao_fonte_mensal`](#ons_geracao_fonte_mensal) | 705 | Geração mensal por fonte (hidráulica, térmica, eólica, solar) e carga por subsistema (N, NE, S, SE e SIN), em MWh, desde 2015, somando o balanço horário do ONS. Use para matriz de geração, participação das renováveis e exportação do Nordeste. subsistema 'SIN' é o total do sistema. | ONS, Balanço de Energia nos Subsistemas, https://dados.ons.org.br/dataset/balanco-energia-subsistema |
| [`ons_geracao_usina_mensal`](#ons_geracao_usina_mensal) | 51.155 | Geração verificada mensal de cada usina despachada ou monitorada pelo ONS, em MWh, desde 2020 (soma da geração horária). ceg liga com usinas e usinas_proprietarios (use o núcleo do CEG, sem o sufixo de versão); para fator de capacidade divida por potência × horas. | ONS, Geração por Usina em Base Horária, https://dados.ons.org.br/dataset/geracao-usina-2 |
| [`ons_intercambio_mensal`](#ons_intercambio_mensal) | 206 | Intercâmbio mensal de energia entre subsistemas (origem -> destino), verificado e programado, em MWh, desde 2023, somando os valores horários do ONS. | ONS, Intercâmbio Nacional, https://dados.ons.org.br/dataset/intercambio-nacional |
| [`participacoes_societarias`](#participacoes_societarias) | 49.322 | Participação direta e indireta de cada empresa ou pessoa em cada agente do setor (uma linha por agente e participante), somando todos os caminhos da cadeia societária. na_cadeia_de_controle = o participante controla o agente, direta ou indiretamente. Inclui o próprio agente com 100%. Serve para somar ativos por grupo: junte cnpj_agente com o CNPJ do dono (usinas_proprietarios.cnpj, rap_transmissao_modulos.cnpj...). | ANEEL, Composição Societária (Polímero); cálculo desta plataforma |
| [`pdd_investimentos`](#pdd_investimentos) | 5.484 | Plano de Desenvolvimento da Distribuição: investimento planejado e realizado por distribuidora, ano e tipo de obra. | ANEEL PDD |
| [`ped_projetos`](#ped_projetos) | 3.997 | Projetos do programa de P&D regulado da ANEEL por empresa: tema, segmento, situação e custo. | ANEEL P&D |
| [`pee_projetos`](#pee_projetos) | 8.230 | Projetos do Programa de Eficiência Energética (PEE) da ANEEL por distribuidora: tipologia, custo, energia economizada. | ANEEL PEE |
| [`ranking_continuidade`](#ranking_continuidade) | 235 | Ranking oficial de continuidade da ANEEL: posição de cada distribuidora pelo Desempenho Global de Continuidade (DGC), de 2021 a 2025, separado em dois grupos de porte. DGC é a média dos DEC e FEC apurados divididos pelos limites: quanto menor, melhor; abaixo de 1 = dentro dos limites. | ANEEL, Ranking de Continuidade, https://www.gov.br/aneel/pt-br/centrais-de-conteudos/relatorios-e-indicadores/distribuicao/ranking-de-continuidade |
| [`rap_por_grupo`](#rap_por_grupo) | visão | RAP de transmissão atribuída a cada grupo ou empresa: proporcional à participação indireta em cada concessionária e controlada (100% das concessionárias que o grupo controla), por situação (Ativa ou Prevista), em R$ por ano. Para a RAP das concessões em nome da própria empresa (sem SPEs e participações) use rap_transmissao_concessionaria filtrando o cnpj. | ANEEL SIGET (RAP) e Composição Societária; cálculo desta plataforma |
| [`rap_transmissao_concessionaria`](#rap_transmissao_concessionaria) | visão | RAP das transmissoras somada por concessionária (com CNPJ), contrato e situação (Ativa ou Prevista), em R$ por ano, no ciclo da coluna ciclo_tarifario. | ANEEL SIGET, Lista de Módulos Prévia - Reajuste RAP; soma desta plataforma |
| [`rap_transmissao_modulos`](#rap_transmissao_modulos) | 47.392 | Receita Anual Permitida (RAP) das transmissoras por módulo de transmissão (linha, subestação, equipamento), da lista prévia do reajuste da ANEEL: concessionária com CNPJ, contrato, tipo de receita e situação. rap_ciclo_brl é o valor do módulo no ciclo tarifário da coluna ciclo_tarifario; some por concessionária ou contrato (ou use rap_transmissao_concessionaria). situacao 'Ativa' = receita em vigor; 'Prevista' = obra ainda não em operação. | ANEEL SIGET, Lista de Módulos Prévia - Reajuste RAP, https://dadosabertos.aneel.gov.br/dataset/sistema-de-gestao-da-transmissao-siget |
| [`tarifas_distribuicao`](#tarifas_distribuicao) | 327.493 | Tarifas homologadas das distribuidoras (TUSD e TE) por resolução, vigência, subgrupo (B1 residencial, A4...), modalidade, classe e posto. Para a tarifa atual filtre fim_vigencia >= current_date. | ANEEL, tarifas homologadas |
| [`transmissao_contratos`](#transmissao_contratos) | 413 | Contratos de concessão de transmissão (SIGET/ANEEL) com a concessionária e o CNPJ. | ANEEL SIGET |
| [`transmissao_empreendimentos`](#transmissao_empreendimentos) | 16.262 | Empreendimentos, obras e módulos de transmissão por contrato (linhas, subestações), com situação e datas. | ANEEL SIGET |
| [`usinas`](#usinas) | 25.133 | Usinas de geração do Brasil (SIGA/ANEEL), uma linha por usina: tipo (UHE, PCH, CGH, EOL, UFV, UTE, UTN), fase (Operação, Construção, Construção não iniciada), origem (Hídrica, Eólica, Solar, Fóssil, Biomassa, Nuclear), potência em kW. | ANEEL SIGA (dados abertos), data em data_base |
| [`usinas_proprietarios`](#usinas_proprietarios) | 25.466 | Donos de cada usina do SIGA com CNPJ e percentual de participação (uma linha por usina e dono). regime: PIE (produtor independente), APE (autoprodutor), SP (serviço público), REG (registro). | ANEEL SIGA, campo DscPropriRegimePariticipacao |

## agentes_aneel

Cadastro de agentes da ANEEL: CNPJ, sigla e razão social de geradoras, transmissoras, distribuidoras e comercializadoras (inclusive as que não são companhias abertas). Use para achar o CNPJ de uma empresa que não está em empresas.

- Fonte: ANEEL, Agentes do Setor Elétrico, https://dadosabertos.aneel.gov.br/dataset/agentes-do-setor-eletrico
- Linhas: 9.956
- Ressalvas: cadastro, sem dados financeiros; um agente pode ter mais de um papel (geração, transmissão...)

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `sigla` | VARCHAR |
| `razao_social` | VARCHAR |
| `ativo` | BOOLEAN |
| `geracao` | BOOLEAN |
| `transmissao` | BOOLEAN |
| `distribuicao` | BOOLEAN |
| `comercializacao` | BOOLEAN |
| `data_base` | DATE |

## bandeiras_tarifarias

Bandeira tarifária acionada pela ANEEL em cada mês (Verde, Amarela, Vermelha P1, Vermelha P2, Escassez Hídrica) e o adicional cobrado na conta, em R$/MWh, desde 2015.

- Fonte: ANEEL, Bandeiras Tarifárias - Acionamento, https://dadosabertos.aneel.gov.br/dataset/bandeiras-tarifarias
- Linhas: 141
- Ressalvas: adicional em R$/MWh (divida por 10 para R$ por 100 kWh); vale para o consumidor cativo do SIN

| Coluna | Tipo |
|---|---|
| `mes` | DATE |
| `bandeira` | VARCHAR |
| `adicional_brl_mwh` | DOUBLE |

## bndes_operacoes

Operações de financiamento não automáticas do BNDES (contratos diretos e indiretos), com cliente, CNPJ, projeto, valores contratado e desembolsado em R$, custo e prazos. setor_eletrico marca geração, transmissão e distribuição.

- Fonte: BNDES dados abertos, operações não automáticas
- Linhas: 23.815
- Ressalvas: CNPJ é do tomador (muitas vezes SPE do grupo)

| Coluna | Tipo |
|---|---|
| `cliente` | VARCHAR |
| `cnpj` | VARCHAR |
| `projeto` | VARCHAR |
| `uf` | VARCHAR |
| `municipio` | VARCHAR |
| `data_contratacao` | DATE |
| `valor_contratado_brl` | DOUBLE |
| `valor_desembolsado_brl` | DOUBLE |
| `fonte_recurso` | VARCHAR |
| `custo_financeiro` | VARCHAR |
| `juros_pct_aa` | DOUBLE |
| `carencia_meses` | INTEGER |
| `amortizacao_meses` | INTEGER |
| `modalidade` | VARCHAR |
| `forma_apoio` | VARCHAR |
| `produto` | VARCHAR |
| `instrumento` | VARCHAR |
| `inovacao` | VARCHAR |
| `subsetor_cnae` | VARCHAR |
| `subsetor_bndes` | VARCHAR |
| `porte` | VARCHAR |
| `situacao` | VARCHAR |
| `setor_eletrico` | BOOLEAN |

## capacidade_por_grupo

Capacidade de geração (SIGA) atribuída a cada grupo ou empresa participante, direta ou indiretamente, por origem, tipo e fase. potencia_proporcional_mw = potência × participação do dono na usina × participação indireta do participante no dono (visão proporcional); potencia_controlada_mw = potência × participação do dono, só nas usinas cujo dono o participante controla (visão consolidada). Para ranking de grupos filtre fase = 'Operação' e agrupe por chave_participante.

- Fonte: ANEEL SIGA e Composição Societária (Polímero); cálculo desta plataforma
- Linhas: 7.026
- Ressalvas: um mesmo grupo aparece em vários níveis (holding brasileira, subholding, controladora estrangeira): escolha o CNPJ ou nome do grupo e não some níveis diferentes. Usinas cujo dono não declarou composição à ANEEL ficam de fora (cerca de 12% da potência em operação). Titulares com CPF não entram

| Coluna | Tipo |
|---|---|
| `chave_participante` | VARCHAR |
| `cnpj_participante` | VARCHAR |
| `participante` | VARCHAR |
| `origem` | VARCHAR |
| `tipo_geracao` | VARCHAR |
| `fase` | VARCHAR |
| `usinas` | BIGINT |
| `potencia_proporcional_mw` | DOUBLE |
| `potencia_controlada_mw` | DOUBLE |
| `controlador_final_de_algum_agente` | BOOLEAN |

## capacidade_por_proprietario

Capacidade instalada em MW por dono (CNPJ), origem, tipo e fase, já ponderada pela participação de cada dono.

- Fonte: ANEEL SIGA
- Linhas: visão
- Ressalvas: titular direto; grupos aparecem espalhados em SPEs

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `proprietario` | VARCHAR |
| `origem` | VARCHAR |
| `tipo_geracao` | VARCHAR |
| `fase` | VARCHAR |
| `usinas` | BIGINT |
| `potencia_mw` | DOUBLE |
| `data_base` | DATE |
| `fonte` | VARCHAR |

## compensacoes_continuidade

Compensações pagas pelas distribuidoras aos consumidores por violação dos limites de continuidade, por conjunto e mês: PGU* = valor pago em R$, QTU* = quantidade de unidades compensadas (a coluna descricao explica cada código).

- Fonte: ANEEL, compensação por violação de continuidade
- Linhas: 10.015.978
- Ressalvas: para DEC e FEC use dec_fec_distribuidora_anual

| Coluna | Tipo |
|---|---|
| `distribuidora` | VARCHAR |
| `cnpj` | VARCHAR |
| `id_conjunto` | VARCHAR |
| `conjunto` | VARCHAR |
| `indicador` | VARCHAR |
| `descricao` | VARCHAR |
| `ano` | INTEGER |
| `mes` | INTEGER |
| `valor` | DOUBLE |

## composicao_societaria

Cadeia societária declarada à ANEEL por cada agente do setor (usina, transmissora, distribuidora), da declaração mais recente: sócios diretos (nivel 1) e indiretos (nivel 2, 3...) até o controlador final. participacao_indireta_pct é a participação efetiva do sócio no agente (já multiplicada ao longo da cadeia). Para somar por grupo use participacoes_societarias, grupos_economicos e capacidade_por_grupo.

- Fonte: ANEEL, Composição Societária (Polímero), https://dadosabertos.aneel.gov.br/dataset/composicao-societaria-polimero
- Linhas: 73.056
- Ressalvas: declaração do próprio agente (REN 948/2021), trimestral; ano e trimestre indicam a declaração usada. O mesmo sócio pode aparecer em mais de um ramo; CPF de pessoa física não é publicado aqui (só o nome). na_cadeia_de_controle e controlador_final são calculados pela plataforma a partir do tipo de sócio

| Coluna | Tipo |
|---|---|
| `cnpj_agente` | VARCHAR |
| `agente` | VARCHAR |
| `ano` | BIGINT |
| `trimestre` | BIGINT |
| `nivel` | BIGINT |
| `cnpj_pai` | VARCHAR |
| `pai` | VARCHAR |
| `cnpj_socio` | VARCHAR |
| `socio` | VARCHAR |
| `tipo_socio` | VARCHAR |
| `participacao_indireta_pct` | DOUBLE |
| `na_cadeia_de_controle` | BOOLEAN |
| `controlador_final` | BOOLEAN |
| `perfil` | VARCHAR |
| `governo` | BOOLEAN |
| `estrangeiro` | BOOLEAN |
| `data_base` | DATE |

## contas_cvm

Todas as contas das demonstrações financeiras anuais (DFP) das empresas do setor, de 2020 em diante, já em R$ (escala MIL aplicada), última versão entregue. demonstrativo: BPA, BPP, DRE, DFC_MI, DFC_MD, DVA; escopo: consolidado ou individual. Prefira kpis_financeiros para indicadores prontos.

- Fonte: CVM, DFP (dados.cvm.gov.br)
- Linhas: 312.693
- Ressalvas: valores em reais; despesas e saídas de caixa vêm negativas

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `cd_cvm` | VARCHAR |
| `empresa` | VARCHAR |
| `ano` | BIGINT |
| `data_referencia` | DATE |
| `demonstrativo` | VARCHAR |
| `escopo` | VARCHAR |
| `cd_conta` | VARCHAR |
| `ds_conta` | VARCHAR |
| `valor_brl` | DOUBLE |
| `versao` | INTEGER |
| `fonte` | VARCHAR |

## contas_cvm_trimestral

Contas das demonstrações trimestrais (ITR) de 2024 em diante, em R$: periodo = trimestre (só os 3 meses), acumulado (desde janeiro) ou saldo (balanço no fim do trimestre). O 4º trimestre não existe no ITR: está na DFP anual.

- Fonte: CVM, ITR (dados.cvm.gov.br)
- Linhas: 462.169
- Ressalvas: valores em reais; despesas e saídas de caixa vêm negativas; a DFC do ITR é acumulada

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `cd_cvm` | VARCHAR |
| `empresa` | VARCHAR |
| `data_referencia` | DATE |
| `ano` | BIGINT |
| `trimestre` | BIGINT |
| `demonstrativo` | VARCHAR |
| `escopo` | VARCHAR |
| `periodo` | VARCHAR |
| `inicio_periodo` | DATE |
| `fim_periodo` | DATE |
| `cd_conta` | VARCHAR |
| `ds_conta` | VARCHAR |
| `valor_brl` | DOUBLE |
| `versao` | INTEGER |
| `fonte` | VARCHAR |

## continuidade_conjuntos

Indicadores de continuidade por conjunto de consumidores e mês (2020 em diante): DEC em horas e FEC em interrupções, com os componentes (programada, externa, dia crítico...) e NumCon (número de consumidores do conjunto).

- Fonte: ANEEL, indicadores coletivos de continuidade
- Linhas: 5.108.332
- Ressalvas: para a distribuidora inteira use dec_fec_distribuidora_anual

| Coluna | Tipo |
|---|---|
| `distribuidora` | VARCHAR |
| `cnpj` | VARCHAR |
| `id_conjunto` | BIGINT |
| `conjunto` | VARCHAR |
| `indicador` | VARCHAR |
| `descricao` | VARCHAR |
| `ano` | BIGINT |
| `mes` | BIGINT |
| `valor` | DOUBLE |

## continuidade_limites

Limites regulatórios anuais de DEC e FEC por conjunto de consumidores, definidos pela ANEEL.

- Fonte: ANEEL
- Linhas: 263.401

| Coluna | Tipo |
|---|---|
| `distribuidora` | VARCHAR |
| `cnpj` | VARCHAR |
| `id_conjunto` | BIGINT |
| `conjunto` | VARCHAR |
| `indicador` | VARCHAR |
| `ano` | INTEGER |
| `limite` | DOUBLE |

## curtailment_por_dono_mensal

Estimativa da energia cortada (curtailment) por dono de usina (CNPJ) e mês, eólica e solar.

- Fonte: ONS e ANEEL SIGA; cálculo desta plataforma
- Linhas: visão
- Ressalvas: ESTIMATIVA: o ONS apura o corte por conjunto; aqui ele é dividido pela potência das usinas e pela participação de cada dono; o dono é o titular direto (SPE)

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `proprietario` | VARCHAR |
| `fonte` | VARCHAR |
| `mes` | DATE |
| `energia_cortada_mwh_estimada` | DOUBLE |
| `referencia_mwh_estimada` | DOUBLE |
| `fonte_calculo` | VARCHAR |

## curtailment_por_grupo_mensal

Estimativa da energia eólica e solar cortada (curtailment) por grupo econômico e mês: proporcional à participação indireta do grupo em cada SPE e controlada (100% das SPEs que o grupo controla).

- Fonte: ONS, ANEEL SIGA e Composição Societária; cálculo desta plataforma
- Linhas: visão
- Ressalvas: ESTIMATIVA sobre curtailment_por_dono_mensal (o ONS apura o corte por conjunto de usinas). O mesmo grupo aparece em vários níveis: não some chaves diferentes do mesmo grupo

| Coluna | Tipo |
|---|---|
| `chave_participante` | VARCHAR |
| `cnpj_participante` | VARCHAR |
| `participante` | VARCHAR |
| `fonte` | VARCHAR |
| `mes` | DATE |
| `energia_cortada_mwh_proporcional` | DOUBLE |
| `referencia_mwh_proporcional` | DOUBLE |
| `energia_cortada_mwh_controlada` | DOUBLE |
| `referencia_mwh_controlada` | DOUBLE |

## debentures_incentivadas

Emissões de debêntures incentivadas de infraestrutura (Lei 12.431), com emissora, código, valor em R$, taxa e indexador. setor = 'Energia Elétrica' para o setor.

- Fonte: ANBIMA, planilha de debêntures incentivadas (até 04/2024)
- Linhas: 777
- Ressalvas: emissora é texto (sem CNPJ); dados até abril de 2024; na planilha original o art. 2º mistura R$ milhões (até 2017) e R$ mil (2018 em diante), já convertidos para R$ aqui

| Coluna | Tipo |
|---|---|
| `artigo` | VARCHAR |
| `data_emissao` | DATE |
| `data_vencimento` | DATE |
| `emissora` | VARCHAR |
| `codigo_cetip` | VARCHAR |
| `valor_brl` | DOUBLE |
| `taxa_ou_spread_pct` | DOUBLE |
| `indexador` | VARCHAR |
| `setor` | VARCHAR |

## debentures_snd

Todas as debêntures registradas no SND (Sistema Nacional de Debêntures), com CNPJ da emissora, data de emissão e de vencimento, indexador (DI, IPCA, PRE...) e taxa, se é incentivada (Lei 12.431), garantia, quantidade e saldo em mercado. setor_eletrico marca emissoras do setor (CVM ou agentes da ANEEL). Use para cronograma de vencimentos e custo da dívida em debêntures de uma empresa (filtre situacao = 'Registrado' para as vigentes).

- Fonte: SND/ANBIMA, Características das Debêntures, https://www.debentures.com.br/exploreosnd/consultaadados/emissoesdedebentures/caracteristicas_r.asp
- Linhas: 10.008
- Ressalvas: saldo_em_mercado_brl = quantidade em mercado × valor nominal atualizado na data_valor_nominal_atual, sem juros acumulados (aproxima o principal, não o valor contábil); não inclui amortizações futuras por data (só o vencimento final); taxa_juros_pct_aa é a sobretaxa ou taxa pré conforme o índice (ex.: DI + 1,2% ou IPCA + 6%), e percentual_indice é o % do índice (ex.: 100% do DI). SPEs de um grupo emitem com CNPJ próprio: junte com participacoes_societarias para somar por grupo

| Coluna | Tipo |
|---|---|
| `codigo` | VARCHAR |
| `emissora` | VARCHAR |
| `cnpj` | VARCHAR |
| `setor_eletrico` | BOOLEAN |
| `situacao` | VARCHAR |
| `emissao` | VARCHAR |
| `serie` | VARCHAR |
| `isin` | VARCHAR |
| `data_emissao` | DATE |
| `data_vencimento` | DATE |
| `data_saida_ou_novo_vencimento` | DATE |
| `motivo_saida` | VARCHAR |
| `indice` | VARCHAR |
| `percentual_indice` | DOUBLE |
| `taxa_juros_pct_aa` | DOUBLE |
| `incentivada_lei_12431` | BOOLEAN |
| `garantia` | VARCHAR |
| `quantidade_emitida` | BIGINT |
| `quantidade_em_mercado` | BIGINT |
| `valor_nominal_emissao_brl` | DOUBLE |
| `valor_nominal_atual_brl` | DOUBLE |
| `data_valor_nominal_atual` | DATE |
| `volume_emitido_brl` | DOUBLE |
| `saldo_em_mercado_brl` | DOUBLE |
| `permite_resgate_antecipado` | BOOLEAN |
| `coordenador_lider` | VARCHAR |
| `agente_fiduciario` | VARCHAR |

## dec_fec_distribuidora_anual

DEC (horas) e FEC (interrupções) anuais de cada distribuidora, com os limites da ANEEL e o número médio de consumidores, de 2020 em diante.

- Fonte: ANEEL, indicadores coletivos de continuidade; cálculo desta plataforma
- Linhas: visão
- Ressalvas: média dos conjuntos ponderada por consumidores e somada nos meses: aproxima o valor oficial (pode diferir em 0,01 do publicado pela distribuidora). Os limites são médias ponderadas dos limites dos conjuntos, calculadas por esta plataforma, não o limite global oficial. Confira meses (ano corrente é parcial)

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `distribuidora` | VARCHAR |
| `ano` | BIGINT |
| `meses` | BIGINT |
| `dec_horas` | DOUBLE |
| `fec_interrupcoes` | DOUBLE |
| `dec_limite_medio_ponderado_horas` | DOUBLE |
| `fec_limite_medio_ponderado` | DOUBLE |
| `consumidores_medios` | DOUBLE |
| `fonte` | VARCHAR |

## empresas

Companhias abertas do setor elétrico registradas na CVM (uma linha por CNPJ). Use buscar_empresa para achar o CNPJ.

- Fonte: CVM, cadastro de companhias abertas (cad_cia_aberta.csv)
- Linhas: 151

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `nome_social` | VARCHAR |
| `nome_comercial` | VARCHAR |
| `cd_cvm` | VARCHAR |
| `situacao` | VARCHAR |
| `setor` | VARCHAR |
| `controle_acionario` | VARCHAR |
| `uf` | VARCHAR |
| `municipio` | VARCHAR |
| `auditor` | VARCHAR |

## empresas_apelidos

Apelidos, marcas, nomes antigos e tickers da B3 de cada empresa, ligados ao CNPJ (base da ferramenta buscar_empresa).

- Fonte: CVM FCA (valores mobiliários negociados) e lista curada de apelidos
- Linhas: 153

| Coluna | Tipo |
|---|---|
| `apelido` | VARCHAR |
| `cnpj` | VARCHAR |
| `tipo` | VARCHAR |
| `observacao` | VARCHAR |

## expansao_geracao

Usinas outorgadas ainda não concluídas acompanhadas pela ANEEL (RALIE): potência, situação da obra (em andamento, não iniciada, paralisada), viabilidade, situação do cronograma e datas de entrada em operação outorgada (ato de outorga) e prevista pela fiscalização da ANEEL, por unidade geradora. Use para a expansão da oferta e atrasos; os donos com CNPJ estão em usinas_proprietarios pelo ceg.

- Fonte: ANEEL, RALIE, https://dadosabertos.aneel.gov.br/dataset/ralie-relatorio-de-acompanhamento-da-expansao-da-oferta-de-geracao-de-energia-eletrica
- Linhas: 2.246
- Ressalvas: potência em MW; datas previstas pela ANEEL (SFG) podem ser revistas a cada mês; primeira/última = primeira e última unidade geradora da usina

| Coluna | Tipo |
|---|---|
| `ceg` | VARCHAR |
| `nome` | VARCHAR |
| `uf` | VARCHAR |
| `origem` | VARCHAR |
| `tipo_geracao` | VARCHAR |
| `potencia_outorgada_mw` | DOUBLE |
| `proprietarios_texto` | VARCHAR |
| `situacao_obra` | VARCHAR |
| `viabilidade` | VARCHAR |
| `situacao_cronograma` | VARCHAR |
| `comercializacao` | VARCHAR |
| `sistema` | VARCHAR |
| `complexo` | VARCHAR |
| `previsao_inicio_obra` | DATE |
| `inicio_obra_realizado` | DATE |
| `unidades` | BIGINT |
| `primeira_operacao_outorgada` | DATE |
| `ultima_operacao_outorgada` | DATE |
| `primeira_operacao_prevista_aneel` | DATE |
| `ultima_operacao_prevista_aneel` | DATE |
| `licenca_instalacao` | VARCHAR |
| `tipo_outorga` | VARCHAR |
| `justificativa` | VARCHAR |
| `data_base` | DATE |

## gd_mmgd

Micro e minigeração distribuída (MMGD, painéis solares em telhados e usinas de até 5 MW na rede da distribuidora) agregada por distribuidora, UF, classe de consumo, fonte, porte, modalidade e mês de cadastro: número de empreendimentos e potência instalada em MW. Some tudo para o total conectado; filtre mes_cadastro para a evolução.

- Fonte: ANEEL, Relação de Empreendimentos de Geração Distribuída, https://dadosabertos.aneel.gov.br/dataset/relacao-de-empreendimentos-de-geracao-distribuida
- Linhas: 66.826
- Ressalvas: mes_cadastro é a data da última atualização cadastral do empreendimento (aproxima a data de conexão, mas pode ser posterior); a base é uma fotografia do estoque conectado em periodo_referencia. Titulares (CPF/CNPJ) não entram

| Coluna | Tipo |
|---|---|
| `cnpj_distribuidora` | VARCHAR |
| `distribuidora` | VARCHAR |
| `uf` | VARCHAR |
| `classe` | VARCHAR |
| `tipo_geracao` | VARCHAR |
| `fonte` | VARCHAR |
| `porte` | VARCHAR |
| `modalidade` | VARCHAR |
| `mes_cadastro` | DATE |
| `empreendimentos` | BIGINT |
| `potencia_mw` | DOUBLE |
| `ucs_recebem_credito` | HUGEINT |
| `periodo_referencia` | VARCHAR |

## grupos_economicos

Grupo econômico de cada agente do setor (uma linha por CNPJ): controladores diretos com participação, controladores finais (topo da cadeia de controle, podem ser vários quando o controle é compartilhado) e a companhia aberta do setor (CVM) que controla o agente, a mais próxima dele na cadeia (holding_cvm), que costuma ser o grupo como o mercado o chama (ex.: SPE da Taesa -> Taesa; Coelba -> Neoenergia). Use para dizer a que grupo pertence uma SPE, usina ou concessão.

- Fonte: ANEEL, Composição Societária (Polímero); cálculo desta plataforma
- Linhas: 4.253
- Ressalvas: controladores_finais pode ser um governo, fundo ou empresa estrangeira; holding_cvm é vazia quando nenhuma companhia aberta do setor controla o agente. Declaração mais recente de cada agente (ano, trimestre)

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `agente` | VARCHAR |
| `controladores_diretos` | VARCHAR |
| `controladores_finais` | VARCHAR |
| `cnpj_controladores_finais` | VARCHAR |
| `holding_cvm` | VARCHAR |
| `cnpj_holding_cvm` | VARCHAR |
| `ano` | BIGINT |
| `trimestre` | BIGINT |

## indicadores_codigos

Significado dos códigos de indicadores de qualidade da ANEEL (DEC, FEC e componentes; PGU* e QTU* das compensações).

- Fonte: ANEEL, domínio dos indicadores de continuidade
- Linhas: 484

| Coluna | Tipo |
|---|---|
| `indicador` | VARCHAR |
| `descricao` | VARCHAR |

## indicadores_macro_mensal

Indicadores macroeconômicos mensais do Banco Central desde 2000: IPCA do mês e em 12 meses, IGP-M do mês e em 12 meses (índices de reajuste de tarifas e RAP), Selic e CDI acumulados no mês, meta Selic no fim do mês (% ao ano) e dólar PTAX de venda médio do mês. Use para contexto de tarifas, RAP e custo da dívida.

- Fonte: Banco Central, SGS (api.bcb.gov.br): séries 433 (IPCA), 13522 (IPCA 12 meses), 189 (IGP-M), 4390 (Selic mensal), 4391 (CDI mensal), 432 (meta Selic), 3698 (dólar PTAX venda, média mensal)
- Linhas: 321
- Ressalvas: IPCA, IGP-M, Selic e CDI do mês em % no mês (não anualizados); igpm_12m_pct é acumulado pela plataforma; o mês corrente pode estar vazio ou parcial (Selic e CDI acumulados até o último dia útil publicado)

| Coluna | Tipo |
|---|---|
| `mes` | DATE |
| `ipca_mes_pct` | DOUBLE |
| `ipca_12m_pct` | DOUBLE |
| `igpm_mes_pct` | DOUBLE |
| `igpm_12m_pct` | DOUBLE |
| `selic_mes_pct` | DOUBLE |
| `cdi_mes_pct` | DOUBLE |
| `selic_meta_fim_mes_pct_aa` | DOUBLE |
| `dolar_ptax_medio_brl` | DOUBLE |

## kpis_financeiros

Indicadores financeiros anuais por empresa (2020 em diante), em R$, prontos para comparar: receita, EBIT, EBITDA calculado, lucro, dívida bruta e líquida, caixa, CAPEX, dividendos, margens, alavancagem, cobertura de juros e ROE. Usa o consolidado quando a empresa o publica.

- Fonte: CVM DFP; cálculo desta plataforma a partir das contas indicadas na coluna fonte
- Linhas: 652
- Ressalvas: EBITDA = EBIT (3.05) + depreciação e amortização da DFC; pode diferir do EBITDA ajustado que a empresa divulga. 3.05 é EBIT, nunca chame de EBITDA. Dívida bruta = empréstimos, financiamentos e debêntures (2.01.04 + 2.02.01), sem arrendamentos. capex_brl soma as saídas de caixa de imobilizado, intangível e ativo de contrato (6.02, contas em contas_capex). Concessões (IFRS 15 / ICPC 01) lançam a obra como custo de construção: custo_construcao_concessao_brl. Para 'quanto investiu', use investimento_total_brl (o maior dos dois, sem somar para não contar duas vezes).

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `empresa` | VARCHAR |
| `ano` | BIGINT |
| `escopo` | VARCHAR |
| `receita_liquida_brl` | DOUBLE |
| `ebit_brl` | DOUBLE |
| `depreciacao_amortizacao_brl` | DOUBLE |
| `ebitda_brl` | DOUBLE |
| `resultado_financeiro_brl` | DOUBLE |
| `despesas_financeiras_brl` | DOUBLE |
| `lucro_liquido_brl` | DOUBLE |
| `ativo_total_brl` | DOUBLE |
| `patrimonio_liquido_brl` | DOUBLE |
| `divida_bruta_brl` | DOUBLE |
| `caixa_aplicacoes_brl` | DOUBLE |
| `divida_liquida_brl` | DOUBLE |
| `caixa_operacional_brl` | DOUBLE |
| `capex_brl` | DOUBLE |
| `custo_construcao_concessao_brl` | DOUBLE |
| `investimento_total_brl` | DOUBLE |
| `dividendos_jcp_pagos_brl` | DOUBLE |
| `margem_ebit_pct` | DOUBLE |
| `margem_ebitda_pct` | DOUBLE |
| `margem_liquida_pct` | DOUBLE |
| `divida_liquida_ebitda` | DOUBLE |
| `cobertura_juros_ebitda` | DOUBLE |
| `roe_pct` | DOUBLE |
| `contas_capex` | VARCHAR |
| `fonte` | VARCHAR |

## kpis_trimestrais

Indicadores trimestrais (ITR) de 2024 em diante: receita, EBIT e lucro do trimestre e acumulados no ano, EBITDA, valores dos últimos 12 meses, dívida bruta e líquida no fim do trimestre, dívida líquida/EBITDA 12 meses e investimento acumulado. É o dado mais recente da base (a DFP anual vai até 2025).

- Fonte: CVM ITR e DFP; cálculo desta plataforma
- Linhas: 879
- Ressalvas: 12 meses só existem quando há o ITR do mesmo trimestre do ano anterior; EBITDA = EBIT + depreciação e amortização da DFC; investimento_acumulado_brl segue a regra de investimento_total_brl

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `empresa` | VARCHAR |
| `ano` | BIGINT |
| `trimestre` | BIGINT |
| `data_referencia` | DATE |
| `escopo` | VARCHAR |
| `receita_liquida_trimestre_brl` | DOUBLE |
| `ebit_trimestre_brl` | DOUBLE |
| `lucro_trimestre_brl` | DOUBLE |
| `receita_liquida_acumulada_brl` | DOUBLE |
| `ebit_acumulado_brl` | DOUBLE |
| `ebitda_acumulado_brl` | DOUBLE |
| `lucro_acumulado_brl` | DOUBLE |
| `receita_liquida_12m_brl` | DOUBLE |
| `ebitda_12m_brl` | DOUBLE |
| `lucro_12m_brl` | DOUBLE |
| `divida_bruta_brl` | DOUBLE |
| `caixa_aplicacoes_brl` | DOUBLE |
| `divida_liquida_brl` | DOUBLE |
| `divida_liquida_ebitda_12m` | DOUBLE |
| `patrimonio_liquido_brl` | DOUBLE |
| `capex_acumulado_brl` | DOUBLE |
| `custo_construcao_acumulado_brl` | DOUBLE |
| `investimento_acumulado_brl` | DOUBLE |
| `fonte` | VARCHAR |

## leiloes_geracao

Resultados dos leilões de GERAÇÃO de energia (2005 em diante): empreendimento, fonte, potência, preço, deságio, investimento previsto e vencedor.

- Fonte: ANEEL, resultado de leilões de geração
- Linhas: 1.552
- Ressalvas: só geração; leilões de transmissão não estão nesta tabela. vencedor é texto (não tem CNPJ)

| Coluna | Tipo |
|---|---|
| `ano` | INTEGER |
| `data_leilao` | DATE |
| `numero_leilao` | VARCHAR |
| `leilao_ccee` | VARCHAR |
| `tipo_leilao` | VARCHAR |
| `empreendimento` | VARCHAR |
| `ceg` | VARCHAR |
| `tipo_geracao` | VARCHAR |
| `fonte_energia` | VARCHAR |
| `detalhe_fonte` | VARCHAR |
| `potencia_mw` | DOUBLE |
| `garantia_fisica_mwmed` | DOUBLE |
| `energia_vendida_mwmed` | DOUBLE |
| `preco_teto_brl_mwh` | DOUBLE |
| `preco_leilao_brl_mwh` | DOUBLE |
| `desagio_pct` | DOUBLE |
| `investimento_previsto_brl` | DOUBLE |
| `duracao_contrato_anos` | INTEGER |
| `uf` | VARCHAR |
| `vencedor` | VARCHAR |
| `data_base` | DATE |

## mercado_distribuidoras_mensal

Mercado e faturamento mensal de cada distribuidora por classe de consumo (Residencial, Comercial, Industrial, Rural...) e mercado (CATIVO, LIVRE, GERAÇÃO, SUPRIMENTO), de 2020 em diante: consumidores, energia faturada em MWh, receitas de energia, demanda e bandeiras, tributos e a tarifa média sem tributos em R$/MWh. Para a tarifa média do ano some receita_energia_brl + receita_demanda_brl e divida pela soma de energia_tusd_mwh (não tire média das médias mensais).

- Fonte: ANEEL, SAMP - Sistema de Acompanhamento de Informações de Mercado, https://dadosabertos.aneel.gov.br/dataset/samp
- Linhas: 85.343
- Ressalvas: dado declarado pela distribuidora ao SAMP; mercado LIVRE paga só a TUSD (fio): não compare a tarifa média do livre com a do cativo. Receitas sem ICMS e PIS/COFINS; refaturamentos entram nas energias e receitas mas não no número de consumidores. O ano corrente é parcial e meses recentes podem ser revistos. Há erros de declaração na fonte (ex.: Cemig D, Residencial, jul/2025 e out/2025, receita de energia ~10 vezes o normal): confira a tarifa média mês a mês antes de somar o ano e aponte meses discrepantes

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `distribuidora` | VARCHAR |
| `mes` | DATE |
| `classe` | VARCHAR |
| `mercado` | VARCHAR |
| `consumidores` | DOUBLE |
| `energia_tusd_mwh` | DOUBLE |
| `energia_te_mwh` | DOUBLE |
| `energia_injetada_gd_mwh` | DOUBLE |
| `energia_compensada_gd_mwh` | DOUBLE |
| `receita_energia_brl` | DOUBLE |
| `receita_demanda_brl` | DOUBLE |
| `receita_bandeiras_brl` | DOUBLE |
| `icms_brl` | DOUBLE |
| `pis_cofins_brl` | DOUBLE |
| `tarifa_media_sem_tributos_brl_mwh` | DOUBLE |

## ons_capacidade

Unidades geradoras despachadas pelo ONS com agente proprietário e potência efetiva em MW.

- Fonte: ONS, capacidade instalada
- Linhas: 5.678
- Ressalvas: agente sem CNPJ; ceg liga com usinas

| Coluna | Tipo |
|---|---|
| `subsistema` | VARCHAR |
| `uf` | VARCHAR |
| `agente_proprietario` | VARCHAR |
| `tipo_usina` | VARCHAR |
| `usina` | VARCHAR |
| `ceg` | VARCHAR |
| `unidade_geradora` | VARCHAR |
| `combustivel` | VARCHAR |
| `entrada_operacao` | DATE |
| `desativacao` | DATE |
| `potencia_efetiva_mw` | DOUBLE |

## ons_carga_diaria

Carga de energia diária do SIN por subsistema (N, NE, S, SE = Sudeste/Centro-Oeste), em MW médio, desde 2000. Energia do dia em MWh = carga_mwmed × 24.

- Fonte: ONS, Carga de Energia, https://dados.ons.org.br/dataset/carga-energia
- Linhas: 39.053
- Ressalvas: MW médio (média do dia), não MWh; inclui estimativa de micro e minigeração conforme a metodologia do ONS; dados recentes podem ser revistos

| Coluna | Tipo |
|---|---|
| `subsistema` | VARCHAR |
| `data` | DATE |
| `carga_mwmed` | DOUBLE |

## ons_cmo_mensal

CMO médio mensal do ONS por subsistema (N, NE, S, SE), em R$/MWh, desde 2020. SE corresponde ao subsistema Sudeste/Centro-Oeste; o arquivo do ONS o rotula SUDESTE, mas não há submercado Centro-Oeste separado. Cada linha é um subsistema-mês; cmo_medio_brl_mwh é a média aritmética dos intervalos semihorários. Use dias_ausentes, dias_com_dados e intervalos para avaliar cobertura antes de comparar meses; um mês com dias_ausentes > 0 não tem média mensal completa.

- Fonte: ONS, CMO Semi-Horário, https://dados.ons.org.br/dataset/cmo-semi-horario; média calculada pela plataforma
- Linhas: 324
- Ressalvas: Não é PLD nem preço spot de liquidação. A média mensal dá o mesmo peso a cada intervalo, sem ponderação pela carga entre intervalos; o CMO semihorário do subsistema publicado pelo ONS já pondera os CMOs das barras pelas respectivas cargas. Meses com menos dias ou intervalos são parciais; arquivos do ONS podem ser revisados, inclusive para o dia seguinte.

| Coluna | Tipo |
|---|---|
| `subsistema` | VARCHAR |
| `nome_subsistema` | VARCHAR |
| `mes` | DATE |
| `cmo_medio_brl_mwh` | DOUBLE |
| `cmo_minimo_brl_mwh` | DOUBLE |
| `cmo_maximo_brl_mwh` | DOUBLE |
| `intervalos` | BIGINT |
| `dias_com_dados` | BIGINT |
| `dias_esperados` | BIGINT |
| `dias_ausentes` | BIGINT |

## ons_cmo_semihora

CMO (Custo Marginal de Operação) do ONS por subsistema e instante semihorário, desde 2020. SE corresponde ao subsistema Sudeste/Centro-Oeste, embora o arquivo o rotule SUDESTE. Para comparar meses e submercados use ons_cmo_mensal; para horários e extremos use esta tabela.

- Fonte: ONS, CMO Semi-Horário, https://dados.ons.org.br/dataset/cmo-semi-horario
- Linhas: 464.064
- Ressalvas: CMO em R$/MWh calculado pelo DESSEM; não é PLD nem preço recebido por gerador. A série pode conter valores negativos e extremos; o ONS pode revisar os arquivos. O mês corrente e o dia seguinte podem estar incompletos ou programados.

| Coluna | Tipo |
|---|---|
| `subsistema` | VARCHAR |
| `nome_subsistema` | VARCHAR |
| `instante` | TIMESTAMP |
| `cmo_brl_mwh` | DOUBLE |

## ons_conjuntos_usinas

Usinas eólicas e solares que formam cada conjunto do ONS (id_conjunto = id_ons de ons_curtailment_mensal), com o CEG de cada usina.

- Fonte: ONS, detalhamento por usina dos cortes de geração (ago/2026)
- Linhas: 1.615
- Ressalvas: mapa de um mês; o CEG liga com usinas pelo núcleo, sem o sufixo de versão

| Coluna | Tipo |
|---|---|
| `fonte` | VARCHAR |
| `id_conjunto` | VARCHAR |
| `conjunto` | VARCHAR |
| `id_usina` | VARCHAR |
| `usina` | VARCHAR |
| `ceg` | VARCHAR |

## ons_curtailment_mensal

Cortes de geração (curtailment) por usina e mês: geração, geração de referência e energia cortada em MWh, e % cortado. fonte = eólica (2023 em diante) ou solar (abr/2024 em diante).

- Fonte: ONS, restrição de operação por constrained-off (GNRa = geração não realizada apurada)
- Linhas: 9.027
- Ressalvas: energia cortada = GNRa × 0,5 h; motivos em ons_curtailment_semihora.razao: REL indisponibilidade externa (rede), CNF confiabilidade, ENE razão energética (sobra de oferta), PAR parecer de acesso; ceg liga com usinas e donos; o mês corrente é parcial

| Coluna | Tipo |
|---|---|
| `fonte` | VARCHAR |
| `subsistema` | VARCHAR |
| `uf` | VARCHAR |
| `usina` | VARCHAR |
| `id_ons` | VARCHAR |
| `ceg` | VARCHAR |
| `agente_operador` | VARCHAR |
| `mes` | DATE |
| `geracao_mwh` | DOUBLE |
| `referencia_mwh` | DOUBLE |
| `energia_cortada_mwh` | DOUBLE |
| `corte_pct` | DOUBLE |

## ons_curtailment_semihora

Cortes de geração eólica (2023 em diante) e solar (abr/2024 em diante) por usina e meia hora, em MW médio: geração verificada, geração de referência e geração não realizada apurada (GNRa).

- Fonte: ONS, restrição de operação por constrained-off
- Linhas: visão
- Ressalvas: para séries e rankings use ons_curtailment_mensal

| Coluna | Tipo |
|---|---|
| `fonte` | VARCHAR |
| `subsistema` | VARCHAR |
| `uf` | VARCHAR |
| `usina` | VARCHAR |
| `id_ons` | VARCHAR |
| `ceg` | VARCHAR |
| `instante` | TIMESTAMP |
| `geracao_mwmed` | DOUBLE |
| `referencia_mwmed` | DOUBLE |
| `nao_realizada_mwmed` | DOUBLE |
| `razao` | VARCHAR |
| `agente_operador` | VARCHAR |

## ons_ear_diario

Energia armazenada (EAR) diária nos reservatórios por subsistema do ONS, desde 2000. SE corresponde ao subsistema Sudeste/Centro-Oeste, embora o arquivo o rotule SUDESTE. Cada linha é um subsistema e uma data; traz a EAR verificada em MWmês, sua capacidade máxima em MWmês e o percentual de armazenamento. Útil para avaliar risco hidrológico e contexto do CMO.

- Fonte: ONS, EAR Diário por Subsistema, https://dados.ons.org.br/dataset/ear-diario-por-subsistema
- Linhas: 39.052
- Ressalvas: MWmês é unidade de energia armazenada do ONS, não potência em MW nem geração em MWh. O percentual é o valor publicado pelo ONS; a EAR considera cascatas entre subsistemas. Dados recentes podem ser revisados; não são armazenamento de uma empresa ou usina específica.

| Coluna | Tipo |
|---|---|
| `subsistema` | VARCHAR |
| `nome_subsistema` | VARCHAR |
| `data` | DATE |
| `ear_maxima_mwmes` | DOUBLE |
| `ear_verificada_mwmes` | DOUBLE |
| `ear_verificada_pct` | DOUBLE |

## ons_ena_diaria

Energia Natural Afluente (ENA) diária por subsistema, em MW médio e em % da média de longo termo (MLT), desde 2021: mede quanta água chega aos reservatórios. Abaixo de 100% da MLT = afluência abaixo da média histórica.

- Fonte: ONS, ENA Diário por Subsistema, https://dados.ons.org.br/dataset/ena-diario-por-subsistema
- Linhas: 8.372
- Ressalvas: SE = Sudeste/Centro-Oeste; para média mensal faça a média dos dias; dados recentes podem ser revistos

| Coluna | Tipo |
|---|---|
| `subsistema` | VARCHAR |
| `data` | DATE |
| `ena_bruta_mwmed` | DOUBLE |
| `ena_bruta_pct_mlt` | DOUBLE |
| `ena_armazenavel_mwmed` | DOUBLE |
| `ena_armazenavel_pct_mlt` | DOUBLE |

## ons_geracao_fonte_mensal

Geração mensal por fonte (hidráulica, térmica, eólica, solar) e carga por subsistema (N, NE, S, SE e SIN), em MWh, desde 2015, somando o balanço horário do ONS. Use para matriz de geração, participação das renováveis e exportação do Nordeste. subsistema 'SIN' é o total do sistema.

- Fonte: ONS, Balanço de Energia nos Subsistemas, https://dados.ons.org.br/dataset/balanco-energia-subsistema
- Linhas: 705
- Ressalvas: térmica inclui nuclear; solar é a centralizada despachada pelo ONS (a micro e minigeração entra abatendo a carga); intercâmbio positivo = exportação do subsistema; mês corrente parcial (veja horas)

| Coluna | Tipo |
|---|---|
| `subsistema` | VARCHAR |
| `mes` | DATE |
| `hidraulica_mwh` | DOUBLE |
| `termica_mwh` | DOUBLE |
| `eolica_mwh` | DOUBLE |
| `solar_mwh` | DOUBLE |
| `geracao_total_mwh` | DOUBLE |
| `carga_mwh` | DOUBLE |
| `intercambio_liquido_mwh` | DOUBLE |
| `horas` | BIGINT |

## ons_geracao_usina_mensal

Geração verificada mensal de cada usina despachada ou monitorada pelo ONS, em MWh, desde 2020 (soma da geração horária). ceg liga com usinas e usinas_proprietarios (use o núcleo do CEG, sem o sufixo de versão); para fator de capacidade divida por potência × horas.

- Fonte: ONS, Geração por Usina em Base Horária, https://dados.ons.org.br/dataset/geracao-usina-2
- Linhas: 51.155
- Ressalvas: só usinas do SIN com dado no ONS (Tipo I, II e conjuntos); 'Pequenas Usinas (MMGD)' são estimativas agregadas por estado; conjuntos eólicos e solares aparecem com o nome do conjunto e sem ceg; mês corrente parcial

| Coluna | Tipo |
|---|---|
| `subsistema` | VARCHAR |
| `uf` | VARCHAR |
| `usina` | VARCHAR |
| `ceg` | VARCHAR |
| `id_ons` | VARCHAR |
| `tipo_usina` | VARCHAR |
| `combustivel` | VARCHAR |
| `modalidade` | VARCHAR |
| `mes` | DATE |
| `geracao_mwh` | DOUBLE |
| `horas` | BIGINT |

## ons_intercambio_mensal

Intercâmbio mensal de energia entre subsistemas (origem -> destino), verificado e programado, em MWh, desde 2023, somando os valores horários do ONS.

- Fonte: ONS, Intercâmbio Nacional, https://dados.ons.org.br/dataset/intercambio-nacional
- Linhas: 206
- Ressalvas: valor negativo = fluxo no sentido destino -> origem; mês corrente parcial

| Coluna | Tipo |
|---|---|
| `origem` | VARCHAR |
| `destino` | VARCHAR |
| `mes` | DATE |
| `intercambio_verificado_mwh` | DOUBLE |
| `intercambio_programado_mwh` | DOUBLE |
| `horas` | BIGINT |

## participacoes_societarias

Participação direta e indireta de cada empresa ou pessoa em cada agente do setor (uma linha por agente e participante), somando todos os caminhos da cadeia societária. na_cadeia_de_controle = o participante controla o agente, direta ou indiretamente. Inclui o próprio agente com 100%. Serve para somar ativos por grupo: junte cnpj_agente com o CNPJ do dono (usinas_proprietarios.cnpj, rap_transmissao_modulos.cnpj...).

- Fonte: ANEEL, Composição Societária (Polímero); cálculo desta plataforma
- Linhas: 49.322
- Ressalvas: chave_participante = CNPJ, ou '#NOME' para estrangeiros e pessoas sem CNPJ. Ações em bolsa e tesouraria ficam de fora. Participação limitada a 100% quando a declaração repete um sócio

| Coluna | Tipo |
|---|---|
| `cnpj_agente` | VARCHAR |
| `agente` | VARCHAR |
| `cnpj_participante` | VARCHAR |
| `participante` | VARCHAR |
| `chave_participante` | VARCHAR |
| `participacao_indireta_pct` | DOUBLE |
| `nivel` | BIGINT |
| `na_cadeia_de_controle` | BOOLEAN |
| `controlador_final` | BOOLEAN |
| `perfil` | VARCHAR |
| `governo` | BOOLEAN |
| `estrangeiro` | BOOLEAN |
| `ano` | BIGINT |
| `trimestre` | BIGINT |

## pdd_investimentos

Plano de Desenvolvimento da Distribuição: investimento planejado e realizado por distribuidora, ano e tipo de obra.

- Fonte: ANEEL PDD
- Linhas: 5.484

| Coluna | Tipo |
|---|---|
| `distribuidora` | VARCHAR |
| `cnpj` | VARCHAR |
| `uf` | VARCHAR |
| `regiao` | VARCHAR |
| `ano` | INTEGER |
| `tipo_obra` | VARCHAR |
| `classe_obra` | VARCHAR |
| `planejado_brl` | DOUBLE |
| `realizado_brl` | DOUBLE |

## ped_projetos

Projetos do programa de P&D regulado da ANEEL por empresa: tema, segmento, situação e custo.

- Fonte: ANEEL P&D
- Linhas: 3.997
- Ressalvas: muitos projetos antigos têm título e custo vazios

| Coluna | Tipo |
|---|---|
| `codigo` | VARCHAR |
| `situacao` | VARCHAR |
| `empresa` | VARCHAR |
| `sigla` | VARCHAR |
| `cnpj` | VARCHAR |
| `titulo` | VARCHAR |
| `chamada_estrategica` | VARCHAR |
| `segmento` | VARCHAR |
| `tema` | VARCHAR |
| `fase_inovacao` | VARCHAR |
| `tipo_produto` | VARCHAR |
| `duracao_meses` | INTEGER |
| `custo_previsto_brl` | DOUBLE |
| `custo_auditado_brl` | DOUBLE |
| `ano_cadastro` | INTEGER |
| `data_conclusao` | DATE |

## pee_projetos

Projetos do Programa de Eficiência Energética (PEE) da ANEEL por distribuidora: tipologia, custo, energia economizada.

- Fonte: ANEEL PEE
- Linhas: 8.230
- Ressalvas: sem CNPJ: filtre por empresa (ILIKE)

| Coluna | Tipo |
|---|---|
| `codigo` | VARCHAR |
| `empresa` | VARCHAR |
| `titulo` | VARCHAR |
| `tipologia` | VARCHAR |
| `custo_total_brl` | DOUBLE |
| `rcb` | DOUBLE |
| `energia_economizada_mwh` | DOUBLE |
| `demanda_retirada_ponta_kw` | DOUBLE |
| `inicio` | DATE |
| `conclusao` | DATE |

## ranking_continuidade

Ranking oficial de continuidade da ANEEL: posição de cada distribuidora pelo Desempenho Global de Continuidade (DGC), de 2021 a 2025, separado em dois grupos de porte. DGC é a média dos DEC e FEC apurados divididos pelos limites: quanto menor, melhor; abaixo de 1 = dentro dos limites.

- Fonte: ANEEL, Ranking de Continuidade, https://www.gov.br/aneel/pt-br/centrais-de-conteudos/relatorios-e-indicadores/distribuicao/ranking-de-continuidade
- Linhas: 235
- Ressalvas: posição dentro do grupo de porte (empates têm a mesma posição); cnpj ligado pela razão social ao cadastro de agentes da ANEEL, vazio quando o nome não casou; o ano é o dos indicadores, publicado no ano seguinte

| Coluna | Tipo |
|---|---|
| `ano` | INTEGER |
| `porte` | VARCHAR |
| `posicao` | INTEGER |
| `dgc` | DOUBLE |
| `sigla` | VARCHAR |
| `empresa` | VARCHAR |
| `cnpj` | VARCHAR |
| `regiao` | VARCHAR |

## rap_por_grupo

RAP de transmissão atribuída a cada grupo ou empresa: proporcional à participação indireta em cada concessionária e controlada (100% das concessionárias que o grupo controla), por situação (Ativa ou Prevista), em R$ por ano. Para a RAP das concessões em nome da própria empresa (sem SPEs e participações) use rap_transmissao_concessionaria filtrando o cnpj.

- Fonte: ANEEL SIGET (RAP) e Composição Societária; cálculo desta plataforma
- Linhas: visão
- Ressalvas: lista prévia do reajuste, sem Parcela de Ajuste; concessionárias sem declaração societária ficam fora; um grupo aparece em vários níveis (não some chaves diferentes)

| Coluna | Tipo |
|---|---|
| `chave_participante` | VARCHAR |
| `cnpj_participante` | VARCHAR |
| `participante` | VARCHAR |
| `situacao` | VARCHAR |
| `ciclo_tarifario` | VARCHAR |
| `contratos` | BIGINT |
| `rap_proporcional_brl` | DOUBLE |
| `rap_controlada_brl` | DOUBLE |

## rap_transmissao_concessionaria

RAP das transmissoras somada por concessionária (com CNPJ), contrato e situação (Ativa ou Prevista), em R$ por ano, no ciclo da coluna ciclo_tarifario.

- Fonte: ANEEL SIGET, Lista de Módulos Prévia - Reajuste RAP; soma desta plataforma
- Linhas: visão
- Ressalvas: lista prévia, sem Parcela de Ajuste; 100% da concessão. Para RAP por grupo use rap_por_grupo

| Coluna | Tipo |
|---|---|
| `concessionaria` | VARCHAR |
| `cnpj` | VARCHAR |
| `contrato` | VARCHAR |
| `situacao` | VARCHAR |
| `ciclo_tarifario` | VARCHAR |
| `rap_ciclo_brl` | DOUBLE |
| `modulos` | BIGINT |
| `tipos_receita` | VARCHAR |

## rap_transmissao_modulos

Receita Anual Permitida (RAP) das transmissoras por módulo de transmissão (linha, subestação, equipamento), da lista prévia do reajuste da ANEEL: concessionária com CNPJ, contrato, tipo de receita e situação. rap_ciclo_brl é o valor do módulo no ciclo tarifário da coluna ciclo_tarifario; some por concessionária ou contrato (ou use rap_transmissao_concessionaria). situacao 'Ativa' = receita em vigor; 'Prevista' = obra ainda não em operação.

- Fonte: ANEEL SIGET, Lista de Módulos Prévia - Reajuste RAP, https://dadosabertos.aneel.gov.br/dataset/sistema-de-gestao-da-transmissao-siget
- Linhas: 47.392
- Ressalvas: lista PRÉVIA ao reajuste (não é a resolução homologatória) e sem a Parcela de Ajuste (PA): pode diferir da RAP divulgada pela empresa. Valores de 100% da concessão (não proporcionais à participação do grupo; para isso junte com participacoes_societarias). Tipos: RBSE e RPC = instalações antigas prorrogadas (Lei 12.783); RBL = licitadas; RBNI = reforços e melhorias autorizados; RMEL = melhorias; sufixo A/P = prevista. Some Ativa e Prevista separadamente

| Coluna | Tipo |
|---|---|
| `concessionaria` | VARCHAR |
| `cnpj` | VARCHAR |
| `contrato` | VARCHAR |
| `tipo_receita` | VARCHAR |
| `situacao` | VARCHAR |
| `id_receita` | BIGINT |
| `id_modulo` | BIGINT |
| `modulo` | VARCHAR |
| `instalacao` | VARCHAR |
| `uf` | VARCHAR |
| `classificacao` | VARCHAR |
| `tipo_uso` | VARCHAR |
| `codigo_ons_empreendimento` | VARCHAR |
| `rap_ciclo_brl` | DOUBLE |
| `ciclo_tarifario` | VARCHAR |
| `data_referencia_ciclo` | DATE |
| `rap_ato_legal_brl` | DOUBLE |
| `data_referencia_ato` | DATE |
| `ato_rap` | VARCHAR |
| `indice_reajuste` | VARCHAR |
| `inicio_vigencia` | DATE |
| `fim_vigencia` | DATE |
| `data_operacao_comercial` | DATE |
| `data_prevista` | DATE |
| `usuario_exclusivo` | VARCHAR |
| `data_base` | DATE |

## tarifas_distribuicao

Tarifas homologadas das distribuidoras (TUSD e TE) por resolução, vigência, subgrupo (B1 residencial, A4...), modalidade, classe e posto. Para a tarifa atual filtre fim_vigencia >= current_date.

- Fonte: ANEEL, tarifas homologadas
- Linhas: 327.493
- Ressalvas: tusd e te na unidade da coluna unidade (R$/MWh ou R$/kW); a sigla da distribuidora pode ser antiga (ELETROPAULO = Enel SP): prefira filtrar por cnpj

| Coluna | Tipo |
|---|---|
| `resolucao` | VARCHAR |
| `distribuidora` | VARCHAR |
| `cnpj` | VARCHAR |
| `inicio_vigencia` | DATE |
| `fim_vigencia` | DATE |
| `base_tarifaria` | VARCHAR |
| `subgrupo` | VARCHAR |
| `modalidade` | VARCHAR |
| `classe` | VARCHAR |
| `subclasse` | VARCHAR |
| `detalhe` | VARCHAR |
| `posto` | VARCHAR |
| `unidade` | VARCHAR |
| `tusd` | DOUBLE |
| `te` | DOUBLE |

## transmissao_contratos

Contratos de concessão de transmissão (SIGET/ANEEL) com a concessionária e o CNPJ.

- Fonte: ANEEL SIGET
- Linhas: 413

| Coluna | Tipo |
|---|---|
| `id_contrato` | VARCHAR |
| `tipo_contrato` | VARCHAR |
| `numero_contrato` | VARCHAR |
| `data_assinatura` | DATE |
| `data_fim` | DATE |
| `cnpj` | VARCHAR |
| `concessionaria` | VARCHAR |
| `uf` | VARCHAR |
| `data_base` | DATE |

## transmissao_empreendimentos

Empreendimentos, obras e módulos de transmissão por contrato (linhas, subestações), com situação e datas.

- Fonte: ANEEL SIGET
- Linhas: 16.262
- Ressalvas: valor_historico_receita_brl se repete em todos os módulos do mesmo empreendimento e NÃO é RAP confirmado: não some nem chame de RAP

| Coluna | Tipo |
|---|---|
| `id_contrato` | VARCHAR |
| `cnpj` | VARCHAR |
| `concessionaria` | VARCHAR |
| `empreendimento` | VARCHAR |
| `descricao` | VARCHAR |
| `situacao` | VARCHAR |
| `data_operacao_comercial` | DATE |
| `obra` | VARCHAR |
| `situacao_obra` | VARCHAR |
| `modulo` | VARCHAR |
| `tipo_modulo` | VARCHAR |
| `classificacao_modulo` | VARCHAR |
| `valor_historico_receita_brl` | DOUBLE |
| `fim_concessao` | DATE |

## usinas

Usinas de geração do Brasil (SIGA/ANEEL), uma linha por usina: tipo (UHE, PCH, CGH, EOL, UFV, UTE, UTN), fase (Operação, Construção, Construção não iniciada), origem (Hídrica, Eólica, Solar, Fóssil, Biomassa, Nuclear), potência em kW.

- Fonte: ANEEL SIGA (dados abertos), data em data_base
- Linhas: 25.133
- Ressalvas: potência em kW (divida por 1000 para MW); donos em usinas_proprietarios

| Coluna | Tipo |
|---|---|
| `ceg` | VARCHAR |
| `nome` | VARCHAR |
| `uf` | VARCHAR |
| `tipo_geracao` | VARCHAR |
| `fase` | VARCHAR |
| `origem` | VARCHAR |
| `fonte_energia` | VARCHAR |
| `tipo_outorga` | VARCHAR |
| `data_entrada_operacao` | DATE |
| `potencia_outorgada_kw` | DOUBLE |
| `potencia_fiscalizada_kw` | DOUBLE |
| `garantia_fisica_kw` | DOUBLE |
| `latitude` | DOUBLE |
| `longitude` | DOUBLE |
| `sub_bacia` | VARCHAR |
| `municipios` | VARCHAR |
| `proprietarios_texto` | VARCHAR |
| `data_base` | DATE |

## usinas_proprietarios

Donos de cada usina do SIGA com CNPJ e percentual de participação (uma linha por usina e dono). regime: PIE (produtor independente), APE (autoprodutor), SP (serviço público), REG (registro).

- Fonte: ANEEL SIGA, campo DscPropriRegimePariticipacao
- Linhas: 25.466
- Ressalvas: o dono é o titular direto, muitas vezes uma SPE: para um grupo, procure pelo nome (ILIKE) ou some as SPEs; o SIGA não traz o controlador final

| Coluna | Tipo |
|---|---|
| `ceg` | VARCHAR |
| `cnpj` | VARCHAR |
| `proprietario` | VARCHAR |
| `participacao_pct` | DOUBLE |
| `regime` | VARCHAR |
