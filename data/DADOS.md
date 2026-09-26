# Dados do EnergyNexus

Tabelas e visões do `energynexus.duckdb` em 26/09/2026, geradas do catálogo por `data/documentar.py`. Não edite à mão: descrição, fonte e ressalvas vêm do catálogo em `data/construir.py`, o mesmo texto que o modelo lê. O formato dos arquivos brutos de cada fonte está em `data/raw/README.md`.

| Tabela | Linhas | Descrição | Fonte |
|---|---:|---|---|
| [`agentes_aneel`](#agentes_aneel) | 9.956 | Cadastro de agentes da ANEEL: CNPJ, sigla e razão social de geradoras, transmissoras, distribuidoras e comercializadoras (inclusive as que não são companhias abertas). Use para achar o CNPJ de uma empresa que não está em empresas. | ANEEL, Agentes do Setor Elétrico, https://dadosabertos.aneel.gov.br/dataset/agentes-do-setor-eletrico |
| [`b3_iee_carteira`](#b3_iee_carteira) | 12 | Carteira teórica do IEE (Índice de Energia Elétrica da B3) na data data_carteira: as ações do setor elétrico que compõem o índice, com o peso de cada uma em % e a quantidade teórica. É o universo de comparação do mercado para o setor: quem está no índice, e quanto cada empresa pesa. cnpj vem do ticker (empresas_apelidos) quando a empresa tem registro na CVM. | B3, API de índices (GetPortfolioDay, índice IEEX), https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-segmentos-e-setoriais/indice-de-energia-eletrica-iee-b3.htm |
| [`balanco_energia_distribuidoras`](#balanco_energia_distribuidoras) | 549.552 | Balanço mensal de energia de cada distribuidora desde 2003, em MWh: disponibilidades (energia recebida, injetada, geração própria), requisitos (energia vendida e entregue por mercado) e saldo (perdas técnicas, não técnicas e totais, medidas e faturadas). fluxo = Disponibilidades, Requisitos ou Saldo; modalidade é a linha do balanço; rubrica detalha a modalidade; medida diz se é energia medida, faturada, calculada ou gerada e o nível de tensão. Para perdas prontas use perdas_distribuicao_anual. | ANEEL, SAMP - balanço de energia, https://dadosabertos.aneel.gov.br/dataset/samp |
| [`bandeiras_tarifarias`](#bandeiras_tarifarias) | 141 | Bandeira tarifária acionada pela ANEEL em cada mês (Verde, Amarela, Vermelha P1, Vermelha P2, Escassez Hídrica) e o adicional cobrado na conta, em R$/MWh, desde 2015. | ANEEL, Bandeiras Tarifárias - Acionamento, https://dadosabertos.aneel.gov.br/dataset/bandeiras-tarifarias |
| [`bandeiras_tarifarias_valores`](#bandeiras_tarifarias_valores) | 27 | Tabela de adicionais das bandeiras tarifárias: quanto cada bandeira custa, em R$/MWh, a partir de cada resolução homologatória da ANEEL (2015 em diante). É o preço da bandeira; qual bandeira valeu em cada mês está em bandeiras_tarifarias. | ANEEL, Bandeiras Tarifárias - Adicional, https://dadosabertos.aneel.gov.br/dataset/bandeiras-tarifarias |
| [`bndes_desembolsos_setor_mensal`](#bndes_desembolsos_setor_mensal) | 1.500 | Desembolsos totais do BNDES por mês e macro-setor CNAE (Agropecuária, Indústria extrativa, Indústria de transformação, Comércio e serviços), em R$, desde janeiro de 1995. Uma linha por mês e setor: some por ano para o desembolso anual do banco, ou filtre o setor para a série setorial. Serve de denominador para pôr o financiamento do setor elétrico (bndes_operacoes) em perspectiva. | BNDES dados abertos, desembolsos por setor CNAE (valores da origem em R$ milhões, convertidos para R$ aqui) |
| [`bndes_operacoes`](#bndes_operacoes) | 23.815 | Operações de financiamento não automáticas do BNDES (contratos diretos e indiretos), com cliente, CNPJ, projeto, valores contratado e desembolsado em R$, custo e prazos. setor_eletrico marca geração, transmissão e distribuição. | BNDES dados abertos, operações não automáticas |
| [`capacidade_por_grupo`](#capacidade_por_grupo) | 7.010 | Capacidade de geração (SIGA) atribuída a cada grupo ou empresa participante, direta ou indiretamente, por origem, tipo e fase. potencia_proporcional_mw = potência × participação do dono na usina × participação indireta do participante no dono (visão proporcional); potencia_controlada_mw = potência × participação do dono, só nas usinas cujo dono o participante controla (visão consolidada). Para ranking de grupos filtre fase = 'Operação' e agrupe por chave_participante. | ANEEL SIGA e Composição Societária (Polímero); cálculo desta plataforma |
| [`capacidade_por_proprietario`](#capacidade_por_proprietario) | visão | Capacidade instalada em MW por dono (CNPJ), origem, tipo e fase, já ponderada pela participação de cada dono. | ANEEL SIGA |
| [`capital_social_acoes`](#capital_social_acoes) | 1.531 | Quantidade de ações de cada empresa em cada data de referência (DFP anual e ITR trimestral): ordinárias, preferenciais, total, o que está em tesouraria e as ações em circulação (total menos tesouraria). Serve para lucro por ação e para peso de cada classe. | CVM DFP e ITR, composição do capital |
| [`compensacoes_continuidade`](#compensacoes_continuidade) | 10.015.978 | Compensações pagas pelas distribuidoras aos consumidores por violação dos limites de continuidade, por conjunto e mês: PGU* = valor pago em R$, QTU* = quantidade de unidades compensadas (a coluna descricao explica cada código). | ANEEL, compensação por violação de continuidade |
| [`composicao_societaria`](#composicao_societaria) | 73.056 | Cadeia societária declarada à ANEEL por cada agente do setor (usina, transmissora, distribuidora), da declaração mais recente: sócios diretos (nivel 1) e indiretos (nivel 2, 3...) até o controlador final. participacao_indireta_pct é a participação efetiva do sócio no agente (já multiplicada ao longo da cadeia). Para somar por grupo use participacoes_societarias, grupos_economicos e capacidade_por_grupo. | ANEEL, Composição Societária (Polímero), https://dadosabertos.aneel.gov.br/dataset/composicao-societaria-polimero |
| [`contas_cvm`](#contas_cvm) | 318.528 | Todas as contas das demonstrações financeiras anuais (DFP) das empresas do setor, de 2020 em diante, já em R$ (escala MIL aplicada), última versão entregue. demonstrativo: BPA e BPP (balanço), DRE, DRA (resultado abrangente), DFC_MI e DFC_MD (fluxo de caixa), DVA; escopo: consolidado ou individual. As mutações do patrimônio líquido estão em mutacoes_patrimonio_liquido. Prefira kpis_financeiros para indicadores prontos. | CVM, DFP (dados.cvm.gov.br) |
| [`contas_cvm_trimestral`](#contas_cvm_trimestral) | 474.590 | Contas das demonstrações trimestrais (ITR) de 2024 em diante, em R$: periodo = trimestre (só os 3 meses), acumulado (desde janeiro) ou saldo (balanço no fim do trimestre). O 4º trimestre não existe no ITR: está na DFP anual. | CVM, ITR (dados.cvm.gov.br) |
| [`continuidade_conjuntos`](#continuidade_conjuntos) | 5.108.332 | Indicadores de continuidade por conjunto de consumidores e mês (2020 em diante): DEC em horas e FEC em interrupções, com os componentes (programada, externa, dia crítico...) e NumCon (número de consumidores do conjunto). | ANEEL, indicadores coletivos de continuidade |
| [`continuidade_limites`](#continuidade_limites) | 263.401 | Limites regulatórios anuais de DEC e FEC por conjunto de consumidores, definidos pela ANEEL. Compare com continuidade_conjuntos (o realizado) para ver quem estourou o limite. | ANEEL |
| [`curtailment_por_dono_mensal`](#curtailment_por_dono_mensal) | visão | Estimativa da energia cortada (curtailment) por dono de usina (CNPJ) e mês, eólica e solar. | ONS e ANEEL SIGA; cálculo desta plataforma |
| [`curtailment_por_grupo_mensal`](#curtailment_por_grupo_mensal) | visão | Estimativa da energia eólica e solar cortada (curtailment) por grupo econômico e mês: proporcional à participação indireta do grupo em cada SPE e controlada (100% das SPEs que o grupo controla). | ONS, ANEEL SIGA e Composição Societária; cálculo desta plataforma |
| [`debentures_incentivadas`](#debentures_incentivadas) | 777 | Emissões de debêntures incentivadas de infraestrutura (Lei 12.431), com emissora, código, valor em R$, taxa e indexador. setor = 'Energia Elétrica' para o setor. | ANBIMA, planilha de debêntures incentivadas (até 04/2024) |
| [`debentures_snd`](#debentures_snd) | 10.008 | Todas as debêntures registradas no SND (Sistema Nacional de Debêntures), com CNPJ da emissora, data de emissão e de vencimento, indexador (DI, IPCA, PRE...) e taxa, se é incentivada (Lei 12.431), garantia, quantidade e saldo em mercado. Três marcas de origem, independentes: emissora_cvm (1.283 debêntures de companhia de energia registrada na CVM, tabela empresas), concessionaria_aneel (1.146, agente de transmissão ou distribuição) e gerador_ou_autoprodutor_aneel (2.624, tem outorga de geração — inclui AUTOPRODUTOR industrial, que gera para a própria fábrica). setor_eletrico = emissora_cvm OR concessionaria_aneel (1.629 debêntures). Use para cronograma de vencimentos e custo da dívida em debêntures de uma empresa (filtre situacao = 'Registrado' para as vigentes). | SND/ANBIMA, Características das Debêntures, https://www.debentures.com.br/exploreosnd/consultaadados/emissoesdedebentures/caracteristicas_r.asp |
| [`dec_fec_distribuidora_anual`](#dec_fec_distribuidora_anual) | visão | DEC (horas) e FEC (interrupções) anuais de cada distribuidora, com os limites da ANEEL e o número médio de consumidores, de 2020 em diante. | ANEEL, indicadores coletivos de continuidade; cálculo desta plataforma |
| [`dicionario_cvm`](#dicionario_cvm) | 146 | Dicionário de dados da CVM: o que significa cada campo dos arquivos de DFP e ITR (CD_CONTA, ESCALA_MOEDA, ORDEM_EXERC, GRUPO_DFP, ST_CONTA_FIXA...), com a descrição oficial, o domínio e o tipo. demonstrativo diz a que arquivo o campo pertence: BPA e BPP (balanço patrimonial ativo e passivo), DRE, DRA, DFC_MI e DFC_MD (fluxo de caixa indireto e direto), DVA, DMPL, composicao_capital, parecer e indice_documentos. Consulte aqui antes de interpretar as colunas cruas de contas_cvm e contas_cvm_trimestral. | CVM, dicionário de dados dos pacotes de DFP (cvm/meta_dfp/*.txt) |
| [`documentos_cvm`](#documentos_cvm) | 2.123 | Documentos que cada empresa entregou à CVM (DFP anual, ITR trimestral e FCA cadastral), com a data de recebimento, a versão e o link para baixar o documento original no sistema RAD da CVM. | CVM, índice de documentos dos pacotes DFP, ITR e FCA |
| [`empresas`](#empresas) | 151 | Companhias abertas do setor elétrico registradas na CVM (uma linha por CNPJ). Use buscar_empresa para achar o CNPJ. | CVM, cadastro de companhias abertas (cad_cia_aberta.csv) |
| [`empresas_apelidos`](#empresas_apelidos) | 153 | Apelidos, marcas, nomes antigos e tickers da B3 de cada empresa, ligados ao CNPJ (base da ferramenta buscar_empresa). | CVM FCA (valores mobiliários negociados) e lista curada de apelidos |
| [`empresas_auditoria`](#empresas_auditoria) | 188 | Auditores independentes de cada empresa (uma linha por período de atuação): firma, CNPJ, código CVM, responsável técnico e datas de início e fim. Serve para ver troca de auditor e tempo de casa. | CVM FCA, formulário cadastral (dados.cvm.gov.br) |
| [`empresas_cadastro_fca`](#empresas_cadastro_fca) | 115 | Cadastro declarado pela própria empresa no FCA: nome atual e anterior, data de constituição, registro na CVM, situação do emissor, espécie de controle acionário, atividade, fim do exercício social e site. Complementa empresas. | CVM FCA, formulário cadastral (dados.cvm.gov.br) |
| [`empresas_contatos`](#empresas_contatos) | 476 | Endereços e contatos declarados no FCA, numa tabela só: categoria = endereço (sede e correspondência), DRI (diretor de relações com investidores), escriturador ou departamento de acionistas. Traz logradouro, cidade, UF, CEP, telefone e e-mail. | CVM FCA, formulário cadastral (dados.cvm.gov.br) |
| [`empresas_divulgacao`](#empresas_divulgacao) | 240 | Jornais e canais em que cada empresa publica seus atos societários, por UF. | CVM FCA, formulário cadastral (dados.cvm.gov.br) |
| [`empresas_negociacao_exterior`](#empresas_negociacao_exterior) | 8 | Países onde os papéis da empresa também são negociados (ADR, listagem no exterior) e a data de admissão. | CVM FCA, formulário cadastral (dados.cvm.gov.br) |
| [`empresas_valores_mobiliarios`](#empresas_valores_mobiliarios) | 161 | Valores mobiliários de cada empresa (ações ON/PN, units, debêntures, BDR...): ticker, mercado, bolsa, segmento de listagem e datas de início e fim de negociação. em_negociacao = true quando não há data de fim. | CVM FCA, formulário cadastral (dados.cvm.gov.br) |
| [`expansao_geracao`](#expansao_geracao) | 2.246 | Usinas outorgadas ainda não concluídas acompanhadas pela ANEEL (RALIE): potência, situação da obra (em andamento, não iniciada, paralisada), viabilidade, situação do cronograma e datas de entrada em operação outorgada (ato de outorga) e prevista pela fiscalização da ANEEL, por unidade geradora. Use para a expansão da oferta e atrasos; os donos com CNPJ estão em usinas_proprietarios pelo ceg. | ANEEL, RALIE, https://dadosabertos.aneel.gov.br/dataset/ralie-relatorio-de-acompanhamento-da-expansao-da-oferta-de-geracao-de-energia-eletrica |
| [`gd_mmgd`](#gd_mmgd) | 66.826 | Micro e minigeração distribuída (MMGD, painéis solares em telhados e usinas de até 5 MW na rede da distribuidora) agregada por distribuidora, UF, classe de consumo, fonte, porte, modalidade e mês de cadastro: número de empreendimentos e potência instalada em MW. Some tudo para o total conectado; filtre mes_cadastro para a evolução. | ANEEL, Relação de Empreendimentos de Geração Distribuída, https://dadosabertos.aneel.gov.br/dataset/relacao-de-empreendimentos-de-geracao-distribuida |
| [`grupos_economicos`](#grupos_economicos) | 4.253 | Grupo econômico de cada agente do setor (uma linha por CNPJ): controladores diretos com participação, controladores finais (topo da cadeia de controle, podem ser vários quando o controle é compartilhado) e a companhia aberta do setor (CVM) que controla o agente, a mais próxima dele na cadeia (holding_cvm), que costuma ser o grupo como o mercado o chama (ex.: SPE da Taesa -> Taesa; Coelba -> Neoenergia). Use para dizer a que grupo pertence uma SPE, usina ou concessão. | ANEEL, Composição Societária (Polímero); cálculo desta plataforma |
| [`indicadores_codigos`](#indicadores_codigos) | 484 | Significado dos códigos de indicadores de qualidade da ANEEL (DEC, FEC e componentes; PGU* e QTU* das compensações). | ANEEL, domínio dos indicadores de continuidade |
| [`indicadores_macro_mensal`](#indicadores_macro_mensal) | 321 | Indicadores macroeconômicos mensais do Banco Central desde 2000: IPCA do mês e em 12 meses, IGP-M do mês e em 12 meses (índices de reajuste de tarifas e RAP), Selic e CDI acumulados no mês, meta Selic no fim do mês (% ao ano) e dólar PTAX de venda médio do mês. Use para contexto de tarifas, RAP e custo da dívida. | Banco Central, SGS (api.bcb.gov.br): séries 433 (IPCA), 13522 (IPCA 12 meses), 189 (IGP-M), 4390 (Selic mensal), 4391 (CDI mensal), 432 (meta Selic), 3698 (dólar PTAX venda, média mensal) |
| [`kpis_financeiros`](#kpis_financeiros) | 652 | Indicadores financeiros anuais por empresa (2020 em diante), em R$, prontos para comparar: receita, EBIT, EBITDA calculado, lucro, dívida bruta e líquida, caixa, CAPEX, dividendos, margens, alavancagem, cobertura de juros e ROE. Usa o consolidado quando a empresa o publica. | CVM DFP; cálculo desta plataforma a partir das contas indicadas na coluna fonte |
| [`kpis_trimestrais`](#kpis_trimestrais) | 879 | Indicadores trimestrais (ITR) de 2024 em diante: receita, EBIT e lucro do trimestre e acumulados no ano, EBITDA, valores dos últimos 12 meses, dívida bruta e líquida no fim do trimestre, dívida líquida/EBITDA 12 meses e investimento acumulado. É o dado mais recente da base (a DFP anual vai até 2025). | CVM ITR e DFP; cálculo desta plataforma |
| [`leiloes_geracao`](#leiloes_geracao) | 1.552 | Resultados dos leilões de GERAÇÃO de energia (2005 em diante): empreendimento, fonte, potência, preço, deságio, investimento previsto e vencedor. | ANEEL, resultado de leilões de geração |
| [`mercado_distribuidoras_mensal`](#mercado_distribuidoras_mensal) | 85.343 | Mercado e faturamento mensal de cada distribuidora por classe de consumo (Residencial, Comercial, Industrial, Rural...) e mercado (CATIVO, LIVRE, GERAÇÃO, SUPRIMENTO, DISTRIBUIÇÃO), de 2020 em diante: consumidores, energia faturada em MWh, receitas de energia, demanda e bandeiras, tributos e a tarifa média sem tributos em R$/MWh. Para a tarifa média do ano some receita_energia_brl + receita_demanda_brl e divida pela soma de energia_tusd_mwh (não tire média das médias mensais). | ANEEL, SAMP - Sistema de Acompanhamento de Informações de Mercado, https://dadosabertos.aneel.gov.br/dataset/samp |
| [`mutacoes_patrimonio_liquido`](#mutacoes_patrimonio_liquido) | 466.684 | Demonstração das mutações do patrimônio líquido (DMPL), anual (DFP) e trimestral (ITR), em R$: cada linha é um movimento (conta 5.xx, como saldos iniciais, lucro do período, dividendos, aumento de capital) numa coluna do PL (coluna_pl: Capital Social Integralizado, Reservas de Lucro, Lucros Acumulados, Patrimônio Líquido Consolidado...). | CVM DFP e ITR, arquivos DMPL |
| [`ons_capacidade`](#ons_capacidade) | 5.678 | Unidades geradoras despachadas pelo ONS com agente proprietário e potência efetiva em MW. modalidade_operacao diz como o ONS trata a unidade: TIPO I é despacho centralizado (143,6 GW das 207,2 GW da tabela) e TIPO II-A, II-B e II-C são as demais modalidades de operação. agente_operador é quem opera (pode diferir do proprietário). | ONS, capacidade instalada |
| [`ons_carga_diaria`](#ons_carga_diaria) | 39.057 | Carga de energia diária do SIN por subsistema (N, NE, S, SE = Sudeste/Centro-Oeste), em MW médio, desde 2000. Energia do dia em MWh = carga_mwmed × 24. | ONS, Carga de Energia, https://dados.ons.org.br/dataset/carga-energia |
| [`ons_cmo_mensal`](#ons_cmo_mensal) | 324 | CMO médio mensal do ONS por subsistema (N, NE, S, SE), em R$/MWh, desde 2020. SE corresponde ao subsistema Sudeste/Centro-Oeste; o arquivo do ONS o rotula SUDESTE, mas não há submercado Centro-Oeste separado. Cada linha é um subsistema-mês; cmo_medio_brl_mwh é a média aritmética dos intervalos semihorários. Use dias_ausentes, dias_com_dados e intervalos para avaliar cobertura antes de comparar meses; um mês com dias_ausentes > 0 não tem média mensal completa. | ONS, CMO Semi-Horário, https://dados.ons.org.br/dataset/cmo-semi-horario; média calculada pela plataforma |
| [`ons_cmo_semihora`](#ons_cmo_semihora) | 464.256 | CMO (Custo Marginal de Operação) do ONS por subsistema e instante semihorário, desde 2020. SE corresponde ao subsistema Sudeste/Centro-Oeste, embora o arquivo o rotule SUDESTE. Para comparar meses e submercados use ons_cmo_mensal; para horários e extremos use esta tabela. | ONS, CMO Semi-Horário, https://dados.ons.org.br/dataset/cmo-semi-horario |
| [`ons_conjuntos_usinas`](#ons_conjuntos_usinas) | 1.615 | Usinas eólicas e solares que formam cada conjunto do ONS (id_conjunto = id_ons de ons_curtailment_mensal), com o CEG de cada usina. | ONS, detalhamento por usina dos cortes de geração (ago/2026) |
| [`ons_curtailment_mensal`](#ons_curtailment_mensal) | 9.027 | Cortes de geração (curtailment) por usina e mês: geração, geração de referência e energia cortada em MWh, e % cortado. fonte = eólica (2023 em diante) ou solar (abr/2024 em diante). | ONS, restrição de operação por constrained-off (GNRa = geração não realizada apurada) |
| [`ons_curtailment_motivo_mensal`](#ons_curtailment_motivo_mensal) | 33.926 | Energia cortada (curtailment) por usina, mês e MOTIVO do corte, em MWh. razao: ENE razão energética (sobra de oferta, sem quem consuma), CNF confiabilidade (limite de segurança elétrica), REL indisponibilidade externa (equipamento da rede fora), PAR parecer de acesso. origem: SIS restrição sistêmica (do SIN como um todo) ou LOC restrição local (da rede onde a usina está). razao e origem nulos são as meias horas SEM restrição, em que a usina gerou livremente: filtre razao IS NOT NULL para olhar só os cortes (as linhas sem razão somam 0,001 TWh de corte contra 78,6 TWh das com razão). restricao_predominante nomeia a linha ou o controle que causou o corte com mais frequência no mês. | ONS, restrição de operação por constrained-off (cod_razaorestricao, cod_origemrestricao e dsc_restricao) |
| [`ons_curtailment_semihora`](#ons_curtailment_semihora) | visão | Cortes de geração eólica (2023 em diante) e solar (abr/2024 em diante) por usina e meia hora, em MW médio: geração verificada, geração de referência e geração não realizada apurada (GNRa), com o motivo do corte (razao e origem), o texto da restrição e o ponto de conexão. | ONS, restrição de operação por constrained-off |
| [`ons_ear_diario`](#ons_ear_diario) | 39.056 | Energia armazenada (EAR) diária nos reservatórios por subsistema do ONS, desde 2000. SE corresponde ao subsistema Sudeste/Centro-Oeste, embora o arquivo o rotule SUDESTE. Cada linha é um subsistema e uma data; traz a EAR verificada em MWmês, sua capacidade máxima em MWmês e o percentual de armazenamento. Útil para avaliar risco hidrológico e contexto do CMO. | ONS, EAR Diário por Subsistema, https://dados.ons.org.br/dataset/ear-diario-por-subsistema |
| [`ons_ena_diaria`](#ons_ena_diaria) | 8.372 | Energia Natural Afluente (ENA) diária por subsistema, em MW médio e em % da média de longo termo (MLT), desde 2021: mede quanta água chega aos reservatórios. Abaixo de 100% da MLT = afluência abaixo da média histórica. | ONS, ENA Diário por Subsistema, https://dados.ons.org.br/dataset/ena-diario-por-subsistema |
| [`ons_geracao_fonte_mensal`](#ons_geracao_fonte_mensal) | 705 | Geração mensal por fonte (hidráulica, térmica, eólica, solar) e carga por subsistema (N, NE, S, SE e SIN), em MWh, desde 2015, somando o balanço horário do ONS. Use para matriz de geração, participação das renováveis e exportação do Nordeste. subsistema 'SIN' é o total do sistema. | ONS, Balanço de Energia nos Subsistemas, https://dados.ons.org.br/dataset/balanco-energia-subsistema |
| [`ons_geracao_usina_mensal`](#ons_geracao_usina_mensal) | 51.155 | Geração verificada mensal de cada usina despachada ou monitorada pelo ONS, em MWh, desde 2020 (soma da geração horária). ceg liga com usinas e usinas_proprietarios (use o núcleo do CEG, sem o sufixo de versão); para fator de capacidade divida por potência × horas. | ONS, Geração por Usina em Base Horária, https://dados.ons.org.br/dataset/geracao-usina-2 |
| [`ons_intercambio_mensal`](#ons_intercambio_mensal) | 206 | Intercâmbio mensal de energia entre subsistemas (origem -> destino), verificado e programado, em MWh, desde 2023, somando os valores horários do ONS. | ONS, Intercâmbio Nacional, https://dados.ons.org.br/dataset/intercambio-nacional |
| [`pareceres_auditoria`](#pareceres_auditoria) | 6.303 | Relatório do auditor independente e declarações dos diretores e do conselho fiscal que acompanham cada DFP e ITR, com o texto completo. tipo_relatorio diz se o parecer é sem ressalva, com ressalva, com ênfase ou adverso. | CVM DFP e ITR, arquivos de parecer |
| [`participacoes_societarias`](#participacoes_societarias) | 49.322 | Participação direta e indireta de cada empresa ou pessoa em cada agente do setor (uma linha por agente e participante), somando todos os caminhos da cadeia societária. na_cadeia_de_controle = o participante controla o agente, direta ou indiretamente. Inclui o próprio agente com 100%. Serve para somar ativos por grupo: junte cnpj_agente com o CNPJ do dono (usinas_proprietarios.cnpj, rap_transmissao_modulos.cnpj...). | ANEEL, Composição Societária (Polímero); cálculo desta plataforma |
| [`pdd_investimentos`](#pdd_investimentos) | 5.484 | Plano de Desenvolvimento da Distribuição: investimento planejado e realizado por distribuidora, ano e tipo de obra. | ANEEL PDD |
| [`ped_projetos`](#ped_projetos) | 3.997 | Projetos do programa de P&D regulado da ANEEL por empresa: tema, segmento, situação e custo. | ANEEL P&D |
| [`pee_projetos`](#pee_projetos) | 8.230 | Projetos do Programa de Eficiência Energética (PEE) da ANEEL por distribuidora: tipologia, custo, energia economizada. | ANEEL PEE |
| [`perdas_distribuicao_anual`](#perdas_distribuicao_anual) | visão | Perdas de energia de cada distribuidora por ano: energia injetada na rede, perdas totais, técnicas (rede) e não técnicas (furto e fraude) em MWh, as perdas faturadas na tarifa e as perdas medidas como % da energia injetada. meses_declarados diz quantos meses do ano a distribuidora declarou (12 = ano completo). | ANEEL, SAMP - balanço de energia |
| [`ranking_continuidade`](#ranking_continuidade) | 235 | Ranking oficial de continuidade da ANEEL: posição de cada distribuidora pelo Desempenho Global de Continuidade (DGC), de 2021 a 2025, separado em dois grupos de porte. DGC é a média dos DEC e FEC apurados divididos pelos limites: quanto menor, melhor; abaixo de 1 = dentro dos limites. | ANEEL, Ranking de Continuidade, https://www.gov.br/aneel/pt-br/centrais-de-conteudos/relatorios-e-indicadores/distribuicao/ranking-de-continuidade |
| [`rap_por_grupo`](#rap_por_grupo) | visão | RAP de transmissão atribuída a cada grupo ou empresa: proporcional à participação indireta em cada concessionária e controlada (100% das concessionárias que o grupo controla), por situação (Ativa ou Prevista), em R$ por ano. Para a RAP das concessões em nome da própria empresa (sem SPEs e participações) use rap_transmissao_concessionaria filtrando o cnpj. | ANEEL SIGET (RAP) e Composição Societária; cálculo desta plataforma |
| [`rap_transmissao_concessionaria`](#rap_transmissao_concessionaria) | visão | RAP das transmissoras somada por concessionária (com CNPJ), contrato e situação (Ativa ou Prevista), em R$ por ano, no ciclo da coluna ciclo_tarifario. | ANEEL SIGET, Lista de Módulos Prévia - Reajuste RAP; soma desta plataforma |
| [`rap_transmissao_modulos`](#rap_transmissao_modulos) | 47.392 | Receita Anual Permitida (RAP) das transmissoras por módulo de transmissão (linha, subestação, equipamento), da lista prévia do reajuste da ANEEL: concessionária com CNPJ, contrato, tipo de receita e situação. rap_ciclo_brl é o valor do módulo no ciclo tarifário da coluna ciclo_tarifario; some por concessionária ou contrato (ou use rap_transmissao_concessionaria). situacao 'Ativa' = receita em vigor; 'Prevista' = obra ainda não em operação. | ANEEL SIGET, Lista de Módulos Prévia - Reajuste RAP, https://dadosabertos.aneel.gov.br/dataset/sistema-de-gestao-da-transmissao-siget |
| [`tarifas_distribuicao`](#tarifas_distribuicao) | 328.083 | Tarifas homologadas das distribuidoras (TUSD e TE) por resolução, vigência, subgrupo (B1 residencial, A4...), modalidade, classe e posto. Para a tarifa atual filtre fim_vigencia >= current_date. | ANEEL, tarifas homologadas |
| [`transmissao_atos_legais`](#transmissao_atos_legais) | 1.652 | Atos legais (resoluções autorizativas e despachos da ANEEL) que autorizaram reforços, melhorias e ampliações de transmissão, um por empreendimento: número e tipo do ato, data de publicação, ementa (o texto que diz o que foi autorizado) e link do cedoc, com o contrato de concessão, o CNPJ da concessionária e o prazo fixado. prazo_ato_legal é a data de entrada em operação que o ato determinou e data_operacao_comercial é a que valeu: compare as duas para medir atraso (903 dos 1.652 empreendimentos entraram depois do prazo, mediana de 24 dias). Para o texto do ato use link; para a RAP que o ato fixou, junte ato_rap em rap_transmissao_modulos. | ANEEL SIGET, Resolução x Contrato x Agente, https://dadosabertos.aneel.gov.br/dataset/sistema-de-gestao-da-transmissao-siget |
| [`transmissao_contratos`](#transmissao_contratos) | 413 | Contratos de concessão de transmissão (SIGET/ANEEL) com a concessionária e o CNPJ. data_assinatura é a data em que o contrato foi assinado e data_fim é quando a concessão vence. | ANEEL SIGET |
| [`transmissao_empreendimentos`](#transmissao_empreendimentos) | 16.262 | Empreendimentos, obras e módulos de transmissão por contrato (linhas, subestações), com situação e datas. | ANEEL SIGET |
| [`transmissao_termos_liberacao`](#transmissao_termos_liberacao) | 14.887 | Termos de Liberação (TL) emitidos pelo ONS para obras de transmissão, um por obra: o TL atesta que a obra entrou em operação e é o documento que autoriza a ANEEL a incluir a receita dela no reajuste. Traz a concessionária com CNPJ, o contrato, o ato legal que autorizou a obra, o número e a data do TL, o ciclo tarifário em que a receita entrou e a obra e o módulo de transmissão liberados. Use para saber QUANDO cada obra passou a receber: junte id_modulo com rap_transmissao_modulos.id_modulo para o valor da RAP (14.500 das 14.887 obras casam) e codigo_ato com transmissao_atos_legais.codigo_ato para a ementa da autorização. | ANEEL SIGET, Termos de Liberação processados no reajuste da RAP, https://dadosabertos.aneel.gov.br/dataset/sistema-de-gestao-da-transmissao-siget |
| [`usinas`](#usinas) | 25.045 | Usinas de geração do Brasil (SIGA/ANEEL), uma linha por usina: tipo (UHE, PCH, CGH, EOL, UFV, UTE, UTN), fase (Operação, Construção, Construção não iniciada), origem (Hídrica, Eólica, Solar, Fóssil, Biomassa, Nuclear), potência em kW. combustivel é o insumo detalhado (Óleo Diesel, Bagaço de Cana de Açúcar, Casca de Arroz...), mais fino que fonte_energia. fim_vigencia_outorga é quando a outorga (registro, autorização ou concessão) vence. | ANEEL SIGA (dados abertos), data em data_base |
| [`usinas_proprietarios`](#usinas_proprietarios) | 25.378 | Donos de cada usina do SIGA com CNPJ e percentual de participação (uma linha por usina e dono). regime: PIE (produtor independente), APE (autoprodutor), SP (serviço público), REG (registro). | ANEEL SIGA, campo DscPropriRegimePariticipacao |

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

## b3_iee_carteira

Carteira teórica do IEE (Índice de Energia Elétrica da B3) na data data_carteira: as ações do setor elétrico que compõem o índice, com o peso de cada uma em % e a quantidade teórica. É o universo de comparação do mercado para o setor: quem está no índice, e quanto cada empresa pesa. cnpj vem do ticker (empresas_apelidos) quando a empresa tem registro na CVM.

- Fonte: B3, API de índices (GetPortfolioDay, índice IEEX), https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-segmentos-e-setoriais/indice-de-energia-eletrica-iee-b3.htm
- Linhas: 12
- Ressalvas: é uma FOTOGRAFIA de um dia, não uma série histórica: a API só devolve a carteira vigente, e a B3 rebalanceia o índice a cada quadrimestre (jan, mai, set). Não é o valor (pontos) do índice nem preço de ação. participacao_pct soma 100. Só ações listadas: subsidiárias e empresas fechadas do setor não aparecem

| Coluna | Tipo |
|---|---|
| `data_carteira` | DATE |
| `ticker` | VARCHAR |
| `empresa_b3` | VARCHAR |
| `tipo_acao` | VARCHAR |
| `participacao_pct` | DOUBLE |
| `quantidade_teorica` | DOUBLE |
| `quantidade_teorica_total_indice` | DOUBLE |
| `cnpj` | VARCHAR |

## balanco_energia_distribuidoras

Balanço mensal de energia de cada distribuidora desde 2003, em MWh: disponibilidades (energia recebida, injetada, geração própria), requisitos (energia vendida e entregue por mercado) e saldo (perdas técnicas, não técnicas e totais, medidas e faturadas). fluxo = Disponibilidades, Requisitos ou Saldo; modalidade é a linha do balanço; rubrica detalha a modalidade; medida diz se é energia medida, faturada, calculada ou gerada e o nível de tensão. Para perdas prontas use perdas_distribuicao_anual.

- Fonte: ANEEL, SAMP - balanço de energia, https://dadosabertos.aneel.gov.br/dataset/samp
- Linhas: 549.552
- Ressalvas: NÃO some energia_mwh sem filtrar: as rubricas terminadas em TOTAL e a medida 'Total (todos os níveis de tensão)' já somam as linhas de detalhe, e 'Perdas Totais' já é técnicas + não técnicas. Perdas aparecem em duas versões (valor medido e valor faturado). O ano corrente é parcial; o CNPJ 07.732.105/0001-84 aparece em 2007 com dois agentes diferentes na fonte

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `distribuidora` | VARCHAR |
| `classificacao` | VARCHAR |
| `ano` | INTEGER |
| `mes` | INTEGER |
| `competencia` | DATE |
| `fluxo` | VARCHAR |
| `modalidade` | VARCHAR |
| `rubrica` | VARCHAR |
| `medida` | VARCHAR |
| `energia_mwh` | DOUBLE |

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

## bandeiras_tarifarias_valores

Tabela de adicionais das bandeiras tarifárias: quanto cada bandeira custa, em R$/MWh, a partir de cada resolução homologatória da ANEEL (2015 em diante). É o preço da bandeira; qual bandeira valeu em cada mês está em bandeiras_tarifarias.

- Fonte: ANEEL, Bandeiras Tarifárias - Adicional, https://dadosabertos.aneel.gov.br/dataset/bandeiras-tarifarias
- Linhas: 27
- Ressalvas: vigora até a resolução seguinte (não há data de fim na fonte); a bandeira verde não aparece porque o adicional é zero. NÃO é série anual: só existe linha nas datas em que a ANEEL reviu o valor (2015, 2016, 2017, 2018, 2019 duas vezes, 2021 duas vezes, 2022 e 2024), e a ausência de 2020 e 2023 significa que o valor não mudou nesses anos. Para saber a bandeira e o adicional de um mês use bandeiras_tarifarias, que é mensal e completa

| Coluna | Tipo |
|---|---|
| `resolucao` | VARCHAR |
| `inicio_vigencia` | DATE |
| `bandeira` | VARCHAR |
| `adicional_brl_mwh` | DOUBLE |

## bndes_desembolsos_setor_mensal

Desembolsos totais do BNDES por mês e macro-setor CNAE (Agropecuária, Indústria extrativa, Indústria de transformação, Comércio e serviços), em R$, desde janeiro de 1995. Uma linha por mês e setor: some por ano para o desembolso anual do banco, ou filtre o setor para a série setorial. Serve de denominador para pôr o financiamento do setor elétrico (bndes_operacoes) em perspectiva.

- Fonte: BNDES dados abertos, desembolsos por setor CNAE (valores da origem em R$ milhões, convertidos para R$ aqui)
- Linhas: 1.500
- Ressalvas: são só QUATRO macro-setores: energia elétrica NÃO aparece separada (ela está dentro de 'Comércio e serviços', onde o BNDES classifica eletricidade e gás). Para o setor elétrico use bndes_operacoes, que é a carteira não automática por contrato e não fecha com estes totais. Valores nominais, sem correção pela inflação: não compare 1995 com 2026 sem deflacionar (use indicadores_macro_mensal). O último mês do arquivo é março de 2026

| Coluna | Tipo |
|---|---|
| `ano` | INTEGER |
| `mes` | INTEGER |
| `competencia` | DATE |
| `setor` | VARCHAR |
| `desembolso_brl` | DOUBLE |

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
- Linhas: 7.010
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

## capital_social_acoes

Quantidade de ações de cada empresa em cada data de referência (DFP anual e ITR trimestral): ordinárias, preferenciais, total, o que está em tesouraria e as ações em circulação (total menos tesouraria). Serve para lucro por ação e para peso de cada classe.

- Fonte: CVM DFP e ITR, composição do capital
- Linhas: 1.531
- Ressalvas: quantidade de ações, não valor; o capital social em R$ está no BPP (2.03.01)

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `empresa` | VARCHAR |
| `documento` | VARCHAR |
| `data_referencia` | DATE |
| `ano` | BIGINT |
| `trimestre` | BIGINT |
| `acoes_ordinarias` | BIGINT |
| `acoes_preferenciais` | BIGINT |
| `acoes_total` | BIGINT |
| `acoes_ordinarias_tesouraria` | BIGINT |
| `acoes_preferenciais_tesouraria` | BIGINT |
| `acoes_tesouraria` | BIGINT |
| `acoes_em_circulacao` | BIGINT |
| `versao` | INTEGER |
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

Todas as contas das demonstrações financeiras anuais (DFP) das empresas do setor, de 2020 em diante, já em R$ (escala MIL aplicada), última versão entregue. demonstrativo: BPA e BPP (balanço), DRE, DRA (resultado abrangente), DFC_MI e DFC_MD (fluxo de caixa), DVA; escopo: consolidado ou individual. As mutações do patrimônio líquido estão em mutacoes_patrimonio_liquido. Prefira kpis_financeiros para indicadores prontos.

- Fonte: CVM, DFP (dados.cvm.gov.br)
- Linhas: 318.528
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
- Linhas: 474.590
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

Limites regulatórios anuais de DEC e FEC por conjunto de consumidores, definidos pela ANEEL. Compare com continuidade_conjuntos (o realizado) para ver quem estourou o limite.

- Fonte: ANEEL
- Linhas: 263.401
- Ressalvas: a série útil começa em 1997: a única linha de 1990 é erro de digitação da ANEEL no arquivo de origem (EDP ES, conjunto GUACUI, FEC) e 1996 tem só 78 linhas contra ~9.600 em 1997, então filtre ano >= 1997 para comparar anos. Traz anos futuros (até 2032), que são limites já definidos e não realizado

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

Todas as debêntures registradas no SND (Sistema Nacional de Debêntures), com CNPJ da emissora, data de emissão e de vencimento, indexador (DI, IPCA, PRE...) e taxa, se é incentivada (Lei 12.431), garantia, quantidade e saldo em mercado. Três marcas de origem, independentes: emissora_cvm (1.283 debêntures de companhia de energia registrada na CVM, tabela empresas), concessionaria_aneel (1.146, agente de transmissão ou distribuição) e gerador_ou_autoprodutor_aneel (2.624, tem outorga de geração — inclui AUTOPRODUTOR industrial, que gera para a própria fábrica). setor_eletrico = emissora_cvm OR concessionaria_aneel (1.629 debêntures). Use para cronograma de vencimentos e custo da dívida em debêntures de uma empresa (filtre situacao = 'Registrado' para as vigentes).

- Fonte: SND/ANBIMA, Características das Debêntures, https://www.debentures.com.br/exploreosnd/consultaadados/emissoesdedebentures/caracteristicas_r.asp
- Linhas: 10.008
- Ressalvas: saldo_em_mercado_brl = quantidade em mercado × valor nominal atualizado na data_valor_nominal_atual, sem juros acumulados (aproxima o principal, não o valor contábil); não inclui amortizações futuras por data (só o vencimento final); taxa_juros_pct_aa é a sobretaxa ou taxa pré conforme o índice (ex.: DI + 1,2% ou IPCA + 6%), e percentual_indice é o % do índice (ex.: 100% do DI). SPEs de um grupo emitem com CNPJ próprio: junte com participacoes_societarias para somar por grupo. 4 debêntures da VESTE (LLIS10, LLIS17, LLIS18 e LLIS20) vêm com data_vencimento 31/12/9999 no SND, que é o marcador de vencimento não definido: filtre data_vencimento < DATE '2100-01-01' antes de montar cronograma de vencimentos. NÃO use gerador_ou_autoprodutor_aneel como 'empresa de energia': ele inclui autoprodutor industrial, e é por isso que Vale, Sabesp e Suzano aparecem marcados ali (1.686 debêntures só têm essa marca)

| Coluna | Tipo |
|---|---|
| `codigo` | VARCHAR |
| `emissora` | VARCHAR |
| `cnpj` | VARCHAR |
| `emissora_cvm` | BOOLEAN |
| `concessionaria_aneel` | BOOLEAN |
| `gerador_ou_autoprodutor_aneel` | BOOLEAN |
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

## dicionario_cvm

Dicionário de dados da CVM: o que significa cada campo dos arquivos de DFP e ITR (CD_CONTA, ESCALA_MOEDA, ORDEM_EXERC, GRUPO_DFP, ST_CONTA_FIXA...), com a descrição oficial, o domínio e o tipo. demonstrativo diz a que arquivo o campo pertence: BPA e BPP (balanço patrimonial ativo e passivo), DRE, DRA, DFC_MI e DFC_MD (fluxo de caixa indireto e direto), DVA, DMPL, composicao_capital, parecer e indice_documentos. Consulte aqui antes de interpretar as colunas cruas de contas_cvm e contas_cvm_trimestral.

- Fonte: CVM, dicionário de dados dos pacotes de DFP (cvm/meta_dfp/*.txt)
- Linhas: 146
- Ressalvas: é a documentação do arquivo ANUAL (DFP); o ITR usa os mesmos campos, com a exceção conhecida do tipo do relatório do auditor (TP_RELAT_AUD na DFP, TP_RELAT_ESP no ITR). tamanho vale para campos de texto e data; nos numéricos o tamanho vem como precisao e escala (casas decimais). Descreve os CSVs crus da CVM, não as colunas já renomeadas das tabelas desta plataforma

| Coluna | Tipo |
|---|---|
| `demonstrativo` | VARCHAR |
| `arquivo` | VARCHAR |
| `campo` | VARCHAR |
| `descricao` | VARCHAR |
| `dominio` | VARCHAR |
| `tipo_dados` | VARCHAR |
| `tamanho` | INTEGER |
| `precisao` | INTEGER |
| `escala` | INTEGER |

## documentos_cvm

Documentos que cada empresa entregou à CVM (DFP anual, ITR trimestral e FCA cadastral), com a data de recebimento, a versão e o link para baixar o documento original no sistema RAD da CVM.

- Fonte: CVM, índice de documentos dos pacotes DFP, ITR e FCA
- Linhas: 2.123
- Ressalvas: só as categorias DFP, ITR e FCA; o link abre o documento completo no site da CVM (rad.cvm.gov.br)

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `empresa` | VARCHAR |
| `cd_cvm` | VARCHAR |
| `categoria` | VARCHAR |
| `data_referencia` | DATE |
| `ano` | BIGINT |
| `trimestre` | BIGINT |
| `versao` | INTEGER |
| `id_documento` | VARCHAR |
| `data_recebimento` | DATE |
| `link` | VARCHAR |

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

## empresas_auditoria

Auditores independentes de cada empresa (uma linha por período de atuação): firma, CNPJ, código CVM, responsável técnico e datas de início e fim. Serve para ver troca de auditor e tempo de casa.

- Fonte: CVM FCA, formulário cadastral (dados.cvm.gov.br)
- Linhas: 188
- Ressalvas: só as empresas de energia elétrica (tabela empresas), na entrega mais recente de cada uma; o CPF do responsável técnico não é carregado (dado pessoal). fim_responsavel é NULL em TODAS as linhas porque a CVM não publica esse campo no FCA (vem vazio nas 1.041 linhas do arquivo): NÃO leia o nulo como 'o responsável técnico continua em atividade'. Para o auditor, fim_auditor é preenchido

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `empresa` | VARCHAR |
| `auditor` | VARCHAR |
| `cnpj_auditor` | VARCHAR |
| `cd_cvm_auditor` | VARCHAR |
| `origem_auditor` | VARCHAR |
| `inicio_auditor` | DATE |
| `fim_auditor` | DATE |
| `responsavel_tecnico` | VARCHAR |
| `inicio_responsavel` | DATE |
| `fim_responsavel` | DATE |
| `data_referencia` | DATE |
| `versao` | INTEGER |

## empresas_cadastro_fca

Cadastro declarado pela própria empresa no FCA: nome atual e anterior, data de constituição, registro na CVM, situação do emissor, espécie de controle acionário, atividade, fim do exercício social e site. Complementa empresas.

- Fonte: CVM FCA, formulário cadastral (dados.cvm.gov.br)
- Linhas: 115
- Ressalvas: só as empresas de energia elétrica (tabela empresas), na entrega mais recente de cada uma; o que a empresa declarou, não o cadastro operacional da CVM (tabela empresas)

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `nome_empresarial` | VARCHAR |
| `nome_anterior` | VARCHAR |
| `data_nome_atual` | DATE |
| `data_constituicao` | DATE |
| `cd_cvm` | VARCHAR |
| `data_registro_cvm` | DATE |
| `categoria_registro` | VARCHAR |
| `situacao_registro` | VARCHAR |
| `situacao_emissor` | VARCHAR |
| `data_situacao_emissor` | DATE |
| `controle_acionario` | VARCHAR |
| `setor_atividade` | VARCHAR |
| `descricao_atividade` | VARCHAR |
| `pais_origem` | VARCHAR |
| `pais_custodia` | VARCHAR |
| `dia_fim_exercicio_social` | INTEGER |
| `mes_fim_exercicio_social` | INTEGER |
| `pagina_web` | VARCHAR |
| `data_referencia` | DATE |
| `versao` | INTEGER |

## empresas_contatos

Endereços e contatos declarados no FCA, numa tabela só: categoria = endereço (sede e correspondência), DRI (diretor de relações com investidores), escriturador ou departamento de acionistas. Traz logradouro, cidade, UF, CEP, telefone e e-mail.

- Fonte: CVM FCA, formulário cadastral (dados.cvm.gov.br)
- Linhas: 476
- Ressalvas: só as empresas de energia elétrica (tabela empresas), na entrega mais recente de cada uma; o CPF do DRI não é carregado (dado pessoal)

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `empresa` | VARCHAR |
| `categoria` | VARCHAR |
| `contato` | VARCHAR |
| `cargo_ou_documento` | VARCHAR |
| `tipo_endereco` | VARCHAR |
| `logradouro` | VARCHAR |
| `complemento` | VARCHAR |
| `bairro` | VARCHAR |
| `cidade` | VARCHAR |
| `uf` | VARCHAR |
| `pais` | VARCHAR |
| `cep` | VARCHAR |
| `telefone` | VARCHAR |
| `email` | VARCHAR |
| `inicio` | DATE |
| `fim` | DATE |
| `data_referencia` | DATE |
| `versao` | INTEGER |

## empresas_divulgacao

Jornais e canais em que cada empresa publica seus atos societários, por UF.

- Fonte: CVM FCA, formulário cadastral (dados.cvm.gov.br)
- Linhas: 240
- Ressalvas: só as empresas de energia elétrica (tabela empresas), na entrega mais recente de cada uma

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `empresa` | VARCHAR |
| `canal` | VARCHAR |
| `uf` | VARCHAR |
| `data_referencia` | DATE |
| `versao` | INTEGER |

## empresas_negociacao_exterior

Países onde os papéis da empresa também são negociados (ADR, listagem no exterior) e a data de admissão.

- Fonte: CVM FCA, formulário cadastral (dados.cvm.gov.br)
- Linhas: 8
- Ressalvas: só as empresas de energia elétrica (tabela empresas), na entrega mais recente de cada uma

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `empresa` | VARCHAR |
| `pais` | VARCHAR |
| `data_admissao` | DATE |
| `data_referencia` | DATE |
| `versao` | INTEGER |

## empresas_valores_mobiliarios

Valores mobiliários de cada empresa (ações ON/PN, units, debêntures, BDR...): ticker, mercado, bolsa, segmento de listagem e datas de início e fim de negociação. em_negociacao = true quando não há data de fim.

- Fonte: CVM FCA, formulário cadastral (dados.cvm.gov.br)
- Linhas: 161
- Ressalvas: só as empresas de energia elétrica (tabela empresas), na entrega mais recente de cada uma; papéis sem código de negociação (debêntures, notas) também aparecem, com ticker nulo. composicao_bdr_unit só se aplica a BDR unit e por isso vem preenchida em 3 das 161 linhas: nulo aqui significa 'não é BDR unit', não dado faltando

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `empresa` | VARCHAR |
| `valor_mobiliario` | VARCHAR |
| `ticker` | VARCHAR |
| `classe_preferencial` | VARCHAR |
| `sigla_classe_preferencial` | VARCHAR |
| `composicao_bdr_unit` | VARCHAR |
| `mercado` | VARCHAR |
| `entidade_administradora` | VARCHAR |
| `segmento` | VARCHAR |
| `inicio_negociacao` | DATE |
| `fim_negociacao` | DATE |
| `inicio_listagem` | DATE |
| `fim_listagem` | DATE |
| `em_negociacao` | BOOLEAN |
| `data_referencia` | DATE |
| `versao` | INTEGER |

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
- Ressalvas: mes_cadastro é a data da última atualização cadastral do empreendimento (aproxima a data de conexão, mas pode ser posterior) e é NULL em 16 empreendimentos, onde a ANEEL gravou o marcador 01/01/1900 em vez da data; a base é uma fotografia do estoque conectado em periodo_referencia. Titulares (CPF/CNPJ) não entram

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
- Ressalvas: EBITDA = EBIT (3.05) + depreciação e amortização da DFC; pode diferir do EBITDA ajustado que a empresa divulga. 3.05 é EBIT, nunca chame de EBITDA. Dívida bruta = empréstimos, financiamentos e debêntures (2.01.04 + 2.02.01), sem arrendamentos. capex_brl soma as saídas de caixa de imobilizado, intangível e ativo de contrato (6.02, contas em contas_capex). Concessões (IFRS 15 / ICPC 01) lançam a obra como custo de construção: custo_construcao_concessao_brl. Para 'quanto investiu', use investimento_total_brl (o maior dos dois, sem somar para não contar duas vezes). sinal_custo_invertido = true nas 2 linhas em que a empresa entregou à CVM o custo (3.02) com sinal POSITIVO e propagou o erro para baixo (Itapebi 2021 e Equatorial Pará 2025, as duas só com demonstração individual): o lucro bruto sai maior que a receita, então margem_ebit_pct, margem_ebitda_pct, margem_liquida_pct e divida_liquida_ebitda vêm NULL nessas linhas. ebit_brl, lucro_liquido_brl, roe_pct e cobertura_juros_ebitda ainda carregam o erro ali (Equatorial PA 2025: EBIT de R$ 20,0 bi contra receita de R$ 12,2 bi e ROE de 371%) — descarte a linha em vez de usá-la. São os valores que a empresa publicou e ficam como estão: NÃO inverta o sinal por conta própria. Outras empresas erraram o sinal só no individual (AES Tietê 2020, CPFL Energia 2024, Rio Alto 2024) e não aparecem aqui porque esta tabela usa o consolidado, que veio certo.

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
| `sinal_custo_invertido` | BOOLEAN |
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
- Ressalvas: só geração; leilões de transmissão não estão nesta tabela. vencedor é texto (não tem CNPJ). O conjunto aberto da ANEEL cobre 2005-2019, 2021, 2022 e 2025: faltam 2020, 2023 e 2024, e a falta é do conjunto, NÃO quer dizer que não houve leilão nesses anos (houve). Não conclua queda de contratação a partir de um ano ausente

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

Mercado e faturamento mensal de cada distribuidora por classe de consumo (Residencial, Comercial, Industrial, Rural...) e mercado (CATIVO, LIVRE, GERAÇÃO, SUPRIMENTO, DISTRIBUIÇÃO), de 2020 em diante: consumidores, energia faturada em MWh, receitas de energia, demanda e bandeiras, tributos e a tarifa média sem tributos em R$/MWh. Para a tarifa média do ano some receita_energia_brl + receita_demanda_brl e divida pela soma de energia_tusd_mwh (não tire média das médias mensais).

- Fonte: ANEEL, SAMP - Sistema de Acompanhamento de Informações de Mercado, https://dadosabertos.aneel.gov.br/dataset/samp
- Linhas: 85.343
- Ressalvas: dado declarado pela distribuidora ao SAMP; mercado LIVRE paga só a TUSD (fio): não compare a tarifa média do livre com a do cativo. SEMPRE filtre mercado: somar a tabela inteira mistura consumo final (CATIVO e LIVRE) com energia repassada a outro agente (DISTRIBUIÇÃO, 2.846 linhas, e SUPRIMENTO, 1.235), o que conta a mesma energia duas vezes; GERAÇÃO não tem energia faturada. Receitas sem ICMS e PIS/COFINS; refaturamentos entram nas energias e receitas mas não no número de consumidores. O ano corrente é parcial e meses recentes podem ser revistos. tarifa_media_suspeita = true quando a tarifa do mês passa de 3x a mediana da própria série (distribuidora, classe e mercado): é erro de declaração na fonte, como Cemig D Residencial em jul/2025 e out/2025 — descarte esses meses antes de somar o ano ou some receita e energia do ano e divida no fim. mes_repetido = true quando o mês repete consumidores E receita de energia do mês anterior, sinal de declaração copiada: não leia como estabilidade real. As duas marcas são NULL onde não há como comparar (mes_repetido no primeiro mês de cada série, 5.173 linhas; tarifa_media_suspeita onde a tarifa é nula, 5.810 linhas, quase todas do mercado GERAÇÃO): use 'NOT coalesce(marca, false)' e não 'NOT marca', que descartaria essas linhas em silêncio

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
| `tarifa_media_suspeita` | BOOLEAN |
| `mes_repetido` | BOOLEAN |

## mutacoes_patrimonio_liquido

Demonstração das mutações do patrimônio líquido (DMPL), anual (DFP) e trimestral (ITR), em R$: cada linha é um movimento (conta 5.xx, como saldos iniciais, lucro do período, dividendos, aumento de capital) numa coluna do PL (coluna_pl: Capital Social Integralizado, Reservas de Lucro, Lucros Acumulados, Patrimônio Líquido Consolidado...).

- Fonte: CVM DFP e ITR, arquivos DMPL
- Linhas: 466.684
- Ressalvas: não some as colunas: coluna_pl já inclui totais (Patrimônio Líquido) junto com as partes. Fica fora de contas_cvm justamente para não contar duas vezes

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `cd_cvm` | VARCHAR |
| `empresa` | VARCHAR |
| `documento` | VARCHAR |
| `data_referencia` | DATE |
| `ano` | BIGINT |
| `trimestre` | BIGINT |
| `escopo` | VARCHAR |
| `coluna_pl` | VARCHAR |
| `cd_conta` | VARCHAR |
| `ds_conta` | VARCHAR |
| `inicio_periodo` | DATE |
| `fim_periodo` | DATE |
| `valor_brl` | DOUBLE |
| `versao` | INTEGER |
| `fonte` | VARCHAR |

## ons_capacidade

Unidades geradoras despachadas pelo ONS com agente proprietário e potência efetiva em MW. modalidade_operacao diz como o ONS trata a unidade: TIPO I é despacho centralizado (143,6 GW das 207,2 GW da tabela) e TIPO II-A, II-B e II-C são as demais modalidades de operação. agente_operador é quem opera (pode diferir do proprietário).

- Fonte: ONS, capacidade instalada
- Linhas: 5.678
- Ressalvas: agente sem CNPJ; ceg liga com usinas. É a capacidade que o ONS acompanha (SIN), menor que a do SIGA, que inclui usinas fora do SIN

| Coluna | Tipo |
|---|---|
| `subsistema` | VARCHAR |
| `uf` | VARCHAR |
| `agente_proprietario` | VARCHAR |
| `agente_operador` | VARCHAR |
| `modalidade_operacao` | VARCHAR |
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
- Linhas: 39.057
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
- Linhas: 464.256
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
- Ressalvas: energia cortada = GNRa × 0,5 h; motivos em ons_curtailment_motivo_mensal e em ons_curtailment_semihora.razao: REL indisponibilidade externa (rede), CNF confiabilidade, ENE razão energética (sobra de oferta), PAR parecer de acesso; ceg liga com usinas e donos; o mês corrente é parcial

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

## ons_curtailment_motivo_mensal

Energia cortada (curtailment) por usina, mês e MOTIVO do corte, em MWh. razao: ENE razão energética (sobra de oferta, sem quem consuma), CNF confiabilidade (limite de segurança elétrica), REL indisponibilidade externa (equipamento da rede fora), PAR parecer de acesso. origem: SIS restrição sistêmica (do SIN como um todo) ou LOC restrição local (da rede onde a usina está). razao e origem nulos são as meias horas SEM restrição, em que a usina gerou livremente: filtre razao IS NOT NULL para olhar só os cortes (as linhas sem razão somam 0,001 TWh de corte contra 78,6 TWh das com razão). restricao_predominante nomeia a linha ou o controle que causou o corte com mais frequência no mês.

- Fonte: ONS, restrição de operação por constrained-off (cod_razaorestricao, cod_origemrestricao e dsc_restricao)
- Linhas: 33.926
- Ressalvas: energia cortada = GNRa × 0,5 h. NÃO some esta tabela junto com ons_curtailment_mensal: são a mesma energia, aqui quebrada por motivo (somando os motivos de uma usina-mês você volta ao total de lá). referencia_mwh também é quebrada por motivo e por isso não é o total de referência do mês. minutos_restricao é o campo do ONS somado nos intervalos, não é tempo de parada da usina. restricao_predominante só existe de junho/2025 em diante (o ONS passou a publicar dsc_restricao então): antes disso vem nula e restricoes_distintas = 0. Série de 2023 em diante; o mês corrente é parcial e o ONS revisa os arquivos recentes

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
| `razao` | VARCHAR |
| `origem` | VARCHAR |
| `energia_cortada_mwh` | DOUBLE |
| `referencia_mwh` | DOUBLE |
| `minutos_restricao` | HUGEINT |
| `intervalos` | BIGINT |
| `restricoes_distintas` | BIGINT |
| `restricao_predominante` | VARCHAR |

## ons_curtailment_semihora

Cortes de geração eólica (2023 em diante) e solar (abr/2024 em diante) por usina e meia hora, em MW médio: geração verificada, geração de referência e geração não realizada apurada (GNRa), com o motivo do corte (razao e origem), o texto da restrição e o ponto de conexão.

- Fonte: ONS, restrição de operação por constrained-off
- Linhas: visão
- Ressalvas: para séries e rankings use ons_curtailment_mensal; por motivo, ons_curtailment_motivo_mensal

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
| `origem` | VARCHAR |
| `restricao` | VARCHAR |
| `ponto_conexao` | VARCHAR |
| `minutos_restricao` | BIGINT |
| `agente_operador` | VARCHAR |

## ons_ear_diario

Energia armazenada (EAR) diária nos reservatórios por subsistema do ONS, desde 2000. SE corresponde ao subsistema Sudeste/Centro-Oeste, embora o arquivo o rotule SUDESTE. Cada linha é um subsistema e uma data; traz a EAR verificada em MWmês, sua capacidade máxima em MWmês e o percentual de armazenamento. Útil para avaliar risco hidrológico e contexto do CMO.

- Fonte: ONS, EAR Diário por Subsistema, https://dados.ons.org.br/dataset/ear-diario-por-subsistema
- Linhas: 39.056
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

## pareceres_auditoria

Relatório do auditor independente e declarações dos diretores e do conselho fiscal que acompanham cada DFP e ITR, com o texto completo. tipo_relatorio diz se o parecer é sem ressalva, com ressalva, com ênfase ou adverso.

- Fonte: CVM DFP e ITR, arquivos de parecer
- Linhas: 6.303
- Ressalvas: texto como entregue pela empresa (sem formatação); o tipo do relatório vem de TP_RELAT_AUD na DFP e TP_RELAT_ESP no ITR

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `empresa` | VARCHAR |
| `documento` | VARCHAR |
| `data_referencia` | DATE |
| `ano` | BIGINT |
| `trimestre` | BIGINT |
| `tipo_relatorio` | VARCHAR |
| `tipo_declaracao` | VARCHAR |
| `item` | INTEGER |
| `texto` | VARCHAR |
| `versao` | INTEGER |
| `fonte` | VARCHAR |

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

## perdas_distribuicao_anual

Perdas de energia de cada distribuidora por ano: energia injetada na rede, perdas totais, técnicas (rede) e não técnicas (furto e fraude) em MWh, as perdas faturadas na tarifa e as perdas medidas como % da energia injetada. meses_declarados diz quantos meses do ano a distribuidora declarou (12 = ano completo).

- Fonte: ANEEL, SAMP - balanço de energia
- Linhas: visão
- Ressalvas: compare só linhas com meses_declarados = 12; perdas_pct usa as perdas medidas, perdas_faturadas_mwh é o que entra na tarifa, e o limite regulatório de perdas definido pela ANEEL não está aqui. Cooperativas e permissionárias pequenas declaram de forma inconsistente (há perdas_pct negativa ou acima de 100%): para rankings filtre classificacao = 'Concessionária' e energia_injetada_mwh alta. perdas_tecnicas_mwh + perdas_nao_tecnicas_mwh só fecha com perdas_totais_mwh quando os três vêm dos mesmos meses

| Coluna | Tipo |
|---|---|
| `cnpj` | VARCHAR |
| `distribuidora` | VARCHAR |
| `classificacao` | VARCHAR |
| `ano` | INTEGER |
| `meses_declarados` | BIGINT |
| `energia_injetada_mwh` | DOUBLE |
| `perdas_totais_mwh` | DOUBLE |
| `perdas_tecnicas_mwh` | DOUBLE |
| `perdas_nao_tecnicas_mwh` | DOUBLE |
| `perdas_faturadas_mwh` | DOUBLE |
| `perdas_pct` | DOUBLE |

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
- Linhas: 328.083
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

## transmissao_atos_legais

Atos legais (resoluções autorizativas e despachos da ANEEL) que autorizaram reforços, melhorias e ampliações de transmissão, um por empreendimento: número e tipo do ato, data de publicação, ementa (o texto que diz o que foi autorizado) e link do cedoc, com o contrato de concessão, o CNPJ da concessionária e o prazo fixado. prazo_ato_legal é a data de entrada em operação que o ato determinou e data_operacao_comercial é a que valeu: compare as duas para medir atraso (903 dos 1.652 empreendimentos entraram depois do prazo, mediana de 24 dias). Para o texto do ato use link; para a RAP que o ato fixou, junte ato_rap em rap_transmissao_modulos.

- Fonte: ANEEL SIGET, Resolução x Contrato x Agente, https://dadosabertos.aneel.gov.br/dataset/sistema-de-gestao-da-transmissao-siget
- Linhas: 1.652
- Ressalvas: cobre só empreendimentos com ato legal de autorização (reforços, melhorias e ampliações): são 1.652 empreendimentos de 164 contratos, contra os 2.352 de transmissao_empreendimentos, e nenhuma linha do contrato original licitado. Todos os contratos são do tipo CCO (Contrato de Concessão). data_operacao_efetiva vem vazia nos 193 empreendimentos 'Em andamento' e em 62 'Em Operação'. Não some nada: não há valor de receita aqui

| Coluna | Tipo |
|---|---|
| `codigo_ato` | VARCHAR |
| `numero_ato` | VARCHAR |
| `tipo_ato` | VARCHAR |
| `data_assinatura_ato` | DATE |
| `data_emissao_ato` | DATE |
| `data_publicacao_ato` | DATE |
| `ementa` | VARCHAR |
| `link` | VARCHAR |
| `id_documento` | BIGINT |
| `id_contrato` | BIGINT |
| `numero_contrato` | VARCHAR |
| `cnpj` | VARCHAR |
| `concessionaria` | VARCHAR |
| `uf` | VARCHAR |
| `data_assinatura_contrato` | DATE |
| `fim_concessao` | DATE |
| `id_empreendimento` | BIGINT |
| `codigo_ons_empreendimento` | VARCHAR |
| `empreendimento` | VARCHAR |
| `descricao` | VARCHAR |
| `situacao` | VARCHAR |
| `prazo_ato_legal` | DATE |
| `data_operacao_comercial` | DATE |
| `data_operacao_efetiva` | DATE |
| `data_base` | DATE |

## transmissao_contratos

Contratos de concessão de transmissão (SIGET/ANEEL) com a concessionária e o CNPJ. data_assinatura é a data em que o contrato foi assinado e data_fim é quando a concessão vence.

- Fonte: ANEEL SIGET
- Linhas: 413
- Ressalvas: data_assinatura NÃO é uma série anual: é a data do contrato, e não há contrato assinado em 1998, 1999, 2003 nem 2025 (a lacuna é do cadastro da ANEEL, não desta plataforma). Os atos legais que autorizaram reforços e ampliações de cada contrato estão em transmissao_atos_legais

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

## transmissao_termos_liberacao

Termos de Liberação (TL) emitidos pelo ONS para obras de transmissão, um por obra: o TL atesta que a obra entrou em operação e é o documento que autoriza a ANEEL a incluir a receita dela no reajuste. Traz a concessionária com CNPJ, o contrato, o ato legal que autorizou a obra, o número e a data do TL, o ciclo tarifário em que a receita entrou e a obra e o módulo de transmissão liberados. Use para saber QUANDO cada obra passou a receber: junte id_modulo com rap_transmissao_modulos.id_modulo para o valor da RAP (14.500 das 14.887 obras casam) e codigo_ato com transmissao_atos_legais.codigo_ato para a ementa da autorização.

- Fonte: ANEEL SIGET, Termos de Liberação processados no reajuste da RAP, https://dadosabertos.aneel.gov.br/dataset/sistema-de-gestao-da-transmissao-siget
- Linhas: 14.887
- Ressalvas: uma linha por OBRA (id_obra é único nas 14.887 linhas), não por TL nem por módulo: um TL libera várias obras (6.652 TLs) e um módulo pode aparecer em várias obras e ciclos (13.820 módulos distintos), então contar linhas conta obras liberadas, não termos. Ciclos tarifários de 2010-2011 a 2026-2027 (TLs assinados desde 2006, mas o arquivo só traz os processados nesses ciclos). codigo_ato é nulo nas 9.464 obras do contrato licitado original, que não passam por ato autorizativo, e das 5.423 com ato 5.394 casam com transmissao_atos_legais. Não tem valor de receita: a RAP está em rap_transmissao_modulos

| Coluna | Tipo |
|---|---|
| `concessionaria` | VARCHAR |
| `cnpj` | VARCHAR |
| `contrato` | VARCHAR |
| `ato_legal` | VARCHAR |
| `codigo_ato` | VARCHAR |
| `termo_liberacao` | VARCHAR |
| `data_termo_liberacao` | DATE |
| `ciclo_tarifario` | VARCHAR |
| `id_obra` | BIGINT |
| `obra` | VARCHAR |
| `id_modulo` | BIGINT |
| `modulo` | VARCHAR |
| `codigo_ons_empreendimento` | VARCHAR |
| `data_base` | DATE |

## usinas

Usinas de geração do Brasil (SIGA/ANEEL), uma linha por usina: tipo (UHE, PCH, CGH, EOL, UFV, UTE, UTN), fase (Operação, Construção, Construção não iniciada), origem (Hídrica, Eólica, Solar, Fóssil, Biomassa, Nuclear), potência em kW. combustivel é o insumo detalhado (Óleo Diesel, Bagaço de Cana de Açúcar, Casca de Arroz...), mais fino que fonte_energia. fim_vigencia_outorga é quando a outorga (registro, autorização ou concessão) vence.

- Fonte: ANEEL SIGA (dados abertos), data em data_base
- Linhas: 25.045
- Ressalvas: potência em kW (divida por 1000 para MW); donos em usinas_proprietarios. garantia_fisica_kw é a energia assegurada da usina, não a potência (em Itaipu ela supera a potência instalada da parte brasileira, por causa do tratado). geracao_qualificada (cogeração qualificada) só está declarada para parte das usinas: false significa 'Não' ou campo em branco no SIGA. data_entrada_operacao é NULL em 2.398 usinas: a ANEEL preenche 03/01/1900 quando não há data (quase todas em 'Construção não iniciada'), e esse marcador foi anulado aqui. As datas anteriores a 1950 que sobram são reais (143 CGH, PCH, UHE e UTE antigas)

| Coluna | Tipo |
|---|---|
| `ceg` | VARCHAR |
| `nome` | VARCHAR |
| `uf` | VARCHAR |
| `tipo_geracao` | VARCHAR |
| `fase` | VARCHAR |
| `origem` | VARCHAR |
| `fonte_energia` | VARCHAR |
| `combustivel` | VARCHAR |
| `tipo_outorga` | VARCHAR |
| `data_entrada_operacao` | DATE |
| `potencia_outorgada_kw` | DOUBLE |
| `potencia_fiscalizada_kw` | DOUBLE |
| `garantia_fisica_kw` | DOUBLE |
| `latitude` | DOUBLE |
| `longitude` | DOUBLE |
| `sub_bacia` | VARCHAR |
| `municipios` | VARCHAR |
| `inicio_vigencia_outorga` | DATE |
| `fim_vigencia_outorga` | DATE |
| `geracao_qualificada` | BOOLEAN |
| `proprietarios_texto` | VARCHAR |
| `data_base` | DATE |

## usinas_proprietarios

Donos de cada usina do SIGA com CNPJ e percentual de participação (uma linha por usina e dono). regime: PIE (produtor independente), APE (autoprodutor), SP (serviço público), REG (registro).

- Fonte: ANEEL SIGA, campo DscPropriRegimePariticipacao
- Linhas: 25.378
- Ressalvas: o dono é o titular direto, muitas vezes uma SPE: para um grupo, procure pelo nome (ILIKE) ou some as SPEs; o SIGA não traz o controlador final

| Coluna | Tipo |
|---|---|
| `ceg` | VARCHAR |
| `cnpj` | VARCHAR |
| `proprietario` | VARCHAR |
| `participacao_pct` | DOUBLE |
| `regime` | VARCHAR |
