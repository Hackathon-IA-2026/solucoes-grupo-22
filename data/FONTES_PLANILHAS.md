# Fontes em planilha ainda fora do banco

Especificação de **leitura** de quatro fontes em planilha que estão em `data/raw/` e ainda não entram no
`energynexus.duckdb`. Este documento não implementa nada: ele diz, aba por aba, o que ler, como ler, com que nome, em que
tipo, em que formato (longo) e com que ressalvas. Quem escreve o `data/construir.py` é outra frente.

Tudo que está aqui saiu de leitura real dos arquivos. As receitas foram executadas; a contagem de linhas e as 5 linhas
de amostra de cada tabela são a saída verdadeira dos scripts de sondagem (§3). Onde uma aba não abriu ou uma leitura
falhou, o erro exato está transcrito.

As quatro fontes:

| # | Arquivo em `data/raw/` | Tamanho | O que é |
|---|---|---|---|
| 1 | `aneel_ons_epe_bndes/anuario_dados_brutos.xlsx` | 24 MB | Anuário Estatístico de Energia Elétrica da EPE, base bruta de consumo mensal |
| 2 | `aneel_ons_epe_bndes/pde2035_dados.zip` | 12 pastas de trabalho | Dados das figuras e tabelas do Plano Decenal de Expansão de Energia 2035 (EPE/MME) |
| 3 | `aneel_ons_epe_bndes/pde2035_transmissao.xlsx` | 140 KB | Lista obra a obra da expansão da transmissão do PDE 2035 |
| 4 | `cvm/deb_incentivadas.xls` | 116 KB | Portarias autorizativas e emissões de debêntures incentivadas da Lei 12.431 (ANBIMA e ministérios) |

## 1. Resumo: quantas abas existem, quantas eu recomendo

| Fonte | Abas no arquivo | Abas recomendadas | Tabelas propostas |
|---|---:|---:|---:|
| 1 — Anuário EPE | 1 | 1 | 1 |
| 2 — PDE 2035 (12 pastas) | 254 | 39 | 31 |
| 3 — Transmissão do PDE 2035 | 1 | 1 | 1 |
| 4 — Debêntures incentivadas (portarias) | 1 | 1 | 1 |
| **Total** | **257** | **42** | **34** |

Das 254 abas da fonte 2: **12** são a aba `Índice` (uma por pasta), **4** são a aba oculta
`ESRI_MAPINFO_SHEET` (capítulos 03, 05, 07 e 08; `sheet_state = 'hidden'`, sem dados de interesse) e **238** são abas
de dados, uma por figura ou tabela do relatório. Recomendo 39 dessas 238.

Abas de dados por capítulo e quantas recomendo:

| Pasta | Abas de dados | Recomendadas | Tabelas | Seção | Tema das tabelas |
|---|---:|---:|---:|---|---|
| 01 Economia e Demografia | 11 | 0 | 0 | §8.1 | — |
| 02 Demanda de Energia | 27 | 4 | 4 | §5.1 | carga, demanda máxima, curva horária, crescimento por classe |
| 03 Geração Centralizada de Energia Elétrica | 47 | 11 | 9 | §5.2 | capacidade, demanda por subsistema, MMGD, custos, expansão, CMO, geração, concessões |
| 04 Transmissão de Energia Elétrica | 16 | 10 | 5 | §5.3 | cargas de conexão, investimento, expansão física, recortes, contratos vincendos |
| 05 Produção de Petróleo e Gás Natural | 26 | 0 | 0 | §8.1 | — |
| 06 Abastecimento de Derivados de Petróleo | 21 | 0 | 0 | §8.1 | — |
| 07 Gás Natural | 7 | 2 | 1 | §5.4 | demanda de gás (recorte termelétrico) |
| 08 Oferta de Biocombustíveis | 26 | 0 | 0 | §8.1 | — |
| 09 Eficiência Energética e RED | 33 | 6 | 6 | §5.5 | RED, MMGD por cenário/UF/segmento, autoprodução |
| 10 Análise Socioambiental | 7 | 2 | 2 | §5.6 | emissões por setor e recorte elétrico |
| 11 Transição Energética | 3 | 1 | 1 | §5.7 | minerais críticos |
| 12 Consolidação dos Resultados | 14 | 3 | 3 | §5.8 | geração total, investimentos, indicadores |
| **Total** | **238** | **39** | **31** | | |

Onde o número de tabelas é menor que o de abas recomendadas, é porque abas com o mesmo cabeçalho foram **empilhadas
em uma tabela só** com uma coluna discriminadora: `epe_pde2035_transmissao_expansao_fisica` (2 abas),
`epe_pde2035_transmissao_investimento_recorte` (5 abas), `epe_pde2035_custos_referencia_fonte` (3 abas),
`epe_pde2035_demanda_gas_natural` (2 abas).

### Por que 39 e não 238

A plataforma é inteligência do **setor elétrico** brasileiro. Apliquei, nesta ordem, os critérios: (a) demanda e
consumo de eletricidade; (b) expansão da geração; (c) expansão da transmissão; (d) geração distribuída e eficiência;
(e) transição energética e emissões; (f) consolidação dos resultados. Petróleo, gás e biocombustíveis entram **só onde
tocam a geração elétrica** — na prática só a demanda termelétrica de gás natural (Figuras 7-5 e 7-6), porque é ela que
amarra a expansão das UTEs a gás do capítulo 03. Os capítulos 05 (produção de petróleo e gás), 06 (derivados) e 08
(biocombustíveis) ficam fora inteiros: são a cadeia de combustíveis líquidos, não o setor elétrico. O capítulo 01
(economia e demografia) fica fora porque os indicadores macro que importam para o setor (PIB, população, intensidade
elétrica) já vêm consolidados na `Tabela 12-1`, que eu recomendo.

Dentro dos capítulos elétricos, o que sobrou de fora é, quase todo, resultado intermediário de simulação: séries de
2.000 cenários do modelo NEWAVE, curvas de permanência, verificação de critérios de suprimento (CVaR CMO, CVaR ENS,
CVaR PNS, LOLP) mês a mês, e distribuições de intercâmbio com 24.006 linhas. São o diagnóstico de atendimento do
plano, não a série que um analista de setor elétrico consulta. O detalhe aba por aba está em §8.

## 2. Convenções adotadas

Seguem as do `data/construir.py`: nome de tabela e de coluna em português, sem acento, `snake_case`; unidade no nome da
coluna (`energia_gwh`, `potencia_mw`, `valor_brl_milhoes`, `emissao_mtco2eq`); cada tabela entra no catálogo por
`tabela(nome, sql, descricao, fonte, ressalvas)`; sem fallback (se o arquivo ou a aba não existir, a construção falha).

**Formato longo.** O padrão da EPE é a aba larga: uma linha por ano e uma coluna por série (cenário, fonte, setor). O
padrão do banco é longo. Toda aba larga vira longa por `UNPIVOT`, com as colunas de identificação, uma coluna de
categoria e uma de valor. O padrão que uso em 12 das 31 tabelas do PDE é este (é a função `por_ano` do script
`05_receitas_finais.py`):

```sql
WITH bruto AS (SELECT * FROM read_xlsx('<arquivo>', sheet='<aba>', range='<A6:K40>', header=true,
                                       all_varchar=true, empty_as_varchar=true)
               WHERE TRY_CAST("Ano" AS INTEGER) BETWEEN 1990 AND 2100)
SELECT CAST(ano AS INTEGER) AS ano,
       replace(<coluna_categoria>, '<sufixo de unidade>', '') AS <coluna_categoria>,
       TRY_CAST(valor AS DOUBLE) AS <coluna_valor>
FROM (UNPIVOT (SELECT "Ano" AS ano, * EXCLUDE ("Ano") FROM bruto)
      ON COLUMNS(* EXCLUDE (ano)) INTO NAME <coluna_categoria> VALUE valor)
WHERE valor IS NOT NULL
ORDER BY ano, <coluna_categoria>
```

**Números.** Nenhuma destas planilhas tem número em formato brasileiro. Nos `.xlsx` (fontes 1, 2 e 3) as células são
numéricas de verdade; com `all_varchar=true` o DuckDB as devolve com ponto decimal (`'0.15713'`). Portanto:

> **Não use a macro `num_br` em nenhuma destas quatro fontes.** `num_br` apaga o ponto (tratando-o como separador de
> milhar) e transformaria `0.15713` em `15713`. Use `TRY_CAST(x AS DOUBLE)` e, para contagens,
> `CAST(TRY_CAST(x AS DOUBLE) AS INTEGER)` (o equivalente da macro `inteiro`, necessário porque o Excel guarda até
> contagem como `1.0`).

**Datas.** Três casos, todos verificados:

- Fonte 1: a coluna `Data` é um `DOUBLE` no formato `yyyymmdd` (`20110101`). Converta com
  `strptime(CAST(CAST("Data" AS BIGINT) AS VARCHAR), '%Y%m%d')::DATE`. A macro `data_br` não serve.
- Fonte 2: nas abas cujo eixo é mês (Figuras 3-29 e 4-29) a célula é uma data do Excel. Com `all_varchar=true` o
  DuckDB devolve **o serial cru como texto** (`'46023'`), e `CAST(... AS DATE)` dá NULL. Converta com
  `DATE '1899-12-30' + TRY_CAST(x AS INTEGER)`. Foi exatamente este o bug que fez duas receitas voltarem 0 linha
  antes da correção.
- Fonte 3: as duas colunas de data são texto `'mm/aaaa'` (`'01/2018'`); use `try_strptime(x, '%m/%Y')::DATE`.
- Fonte 4: o `.xls` guarda data como serial numérico; com `xlrd`, use
  `datetime.date(*xlrd.xldate_as_tuple(v, livro.datemode)[:3])`.

**Leitura das abas do PDE com `read_xlsx` (DuckDB 1.5.5).** Três armadilhas medidas:

1. `range` precisa ser um intervalo completo. `range='A6'` falha com
   `Binder Error: Invalid range 'A6' specified`. Use `range='A6:K40'`.
2. Quase toda aba tem nota de rodapé em texto abaixo dos dados. Sem `all_varchar`, a leitura morre em
   `Invalid Input Error: read_xlsx: Failed to parse cell 'A19': Could not convert string 'Nota:' to DOUBLE`. A
   receita padrão usa `all_varchar=true, empty_as_varchar=true` e descarta o rodapé com
   `WHERE TRY_CAST("Ano" AS INTEGER) BETWEEN 1990 AND 2100` (ou o filtro equivalente da aba), depois tipa por
   `TRY_CAST`. `stop_at_empty` não resolve: ele não corta um `range` mais largo que os dados.
3. Células mescladas praticamente não existem. Das 254 abas, só três têm mescla: `Tabela 12-1` (`N6:P6`),
   `Tabela 12-9` (18 mesclas) e `Tabela 12-11` (2). Das abas que recomendo, só a `Tabela 12-1` tem — e é exatamente a
   parte que eu descarto (o rótulo "Variação média anual" sobre três colunas).

**O `.xls` da fonte 4 o DuckDB não lê.** Os dois caminhos falham:

```
st_read     -> IO Error: Could not open GDAL dataset at: .../cvm/deb_incentivadas.xls
read_xlsx   -> IO Error: Failed to open zip for reading
```

`file` confirma `Composite Document File V2 Document` (OLE2/BIFF, o `.xls` antigo). A leitura tem de ser em Python com
**`xlrd`** (testei a 2.0.2), que **é dependência nova**: o `data/construir.py` hoje importa só
`csv, glob, os, re, shutil, tempfile, zipfile, duckdb, openpyxl`.

**Layout uniforme das abas do PDE.** Verificado nas 254 abas: L1 `Índice` (link de volta), L2 vazia, L3 identificação e
título da figura, L4 `Fonte:` e a fonte, L5 vazia, **L6 cabeçalho** (em quatro tabelas do capítulo 12 o cabeçalho
ocupa L6+L7), dados de L7 em diante, e opcionalmente uma linha vazia, `Nota:`/`Notas:` e as notas. Por isso a receita
padrão começa em `A6`.

## 3. Como reproduzir

Os scripts de sondagem ficam **fora do repositório**, em
`/impa/home/a/al.richard.viana/.claude/jobs/cbd32df1/tmp/epe/`, e rodam com o interpretador do projeto
(`.runtime/venv/bin/python`, que tem `duckdb`, `openpyxl` e — instalado nesta sondagem — `xlrd` e `pandas`):

| Script | O que faz | Saída |
|---|---|---|
| `01_inventario.py` | inventário de todas as abas: dimensão, `sheet_state`, mesclas, 8 primeiras linhas | `out_pde_inventario.txt`, `out_transmissao.txt` |
| `02_dump_abas.py` | despeja N linhas de abas escolhidas | — |
| `04_deb_incentivadas.py` | lê o `.xls` da fonte 4 com `xlrd`, tipa, confere e testa a ligação com o banco | `out_deb.txt`, `out_deb2.txt` |
| `05_receitas_finais.py` | **as 33 receitas SQL deste documento**; imprime colunas, tipos, contagem e 5 linhas de cada | `out_receitas.txt` |
| `06_cabecalhos.py` | título (L3), fonte (L4), cabeçalho e últimas linhas úteis de cada aba recomendada | `out_cabecalhos.txt` |
| `07_verificacoes.py` | materializa 8 tabelas e confere contra o banco (`ATTACH ... (READ_ONLY)`) | `out_verificacoes.txt`, `out_verif2.txt` |
| `08_titulos_excluidos.py`, `09_anuario.py` | títulos das abas que não recomendo; inventário do Anuário | `out_titulos*.txt` |

`python 05_receitas_finais.py [filtro]` roda uma receita ou todas. A última execução completa terminou em
`RESUMO: 33 receitas ok, 0 falharam, de 33 no total`. O banco foi aberto **sempre** com
`ATTACH '<caminho>' AS b (READ_ONLY)` — ele está em uso por outros processos.

A fonte 2 é um zip; as receitas leem as 12 pastas já extraídas. Na implementação, extraia para um diretório temporário
(o `construir.py` já faz isso com `zipfile` + `tempfile` em outras fontes) e leia de lá; os nomes dos arquivos dentro
do zip são, com acento e espaço:

```
PDE 2035_Dados_Capítulo 01_Economia e Demografia.xlsx
PDE 2035_Dados_Capítulo 02_Demanda de Energia.xlsx
PDE 2035_Dados_Capítulo 03_Geração Centralizada de Energia Elétrica.xlsx
PDE 2035_Dados_Capítulo 04_Transmissão de Energia Elétrica.xlsx
PDE 2035_Dados_Capítulo 05_Produção de Petróleo e Gás Natural.xlsx
PDE 2035_Dados_Capítulo 06_Abastecimento de Derivados de Petróleo.xlsx
PDE 2035_Dados_Capítulo 07_Gás Natural.xlsx
PDE 2035_Dados_Capítulo 08_Oferta de Biocombustíveis.xlsx
PDE 2035_Dados_Capítulo 09_Eficiência Energética e Recursos Energéticos Distribuídos.xlsx
PDE 2035_Dados_Capítulo 10_Análise Socioambiental.xlsx
PDE 2035_Dados_Capítulo 11_Transição Energética.xlsx
PDE 2035_Dados_Capítulo 12_Consolidação dos Resultados.xlsx
```

## 4. Fonte 1 — Anuário Estatístico da EPE

Arquivo: `data/raw/aneel_ons_epe_bndes/anuario_dados_brutos.xlsx`. Uma aba visível, `Sheet1`, dimensão
`A1:N423752`: cabeçalho em **L1**, dados em **L2:L423752** (423.751 linhas), **sem rodapé** (conferi a última linha:
`(20211201, 'Cativo', 'Sudeste / Centro-Oeste', 'DF', 'Consumo Próprio', ...)`, é dado). Sem célula mesclada.

### `epe_anuario_consumo_mensal`

Consumo e número de consumidores de energia elétrica por mês, UF, subsistema, tipo de consumidor (cativo/livre),
classe de consumo, nível de tensão e faixa de consumo.

| Coluna na planilha | Coluna proposta | Tipo | Observação |
|---|---|---|---|
| `Data` | `mes` | DATE | `DOUBLE` em `yyyymmdd`; sempre dia 1 |
| `TipoConsumidor` | `tipo_consumidor` | VARCHAR | `Cativo`, `Livre` |
| `Sistema` | `subsistema` | VARCHAR | `Sudeste / Centro-Oeste`, `Sul`, `Nordeste`, `Norte Interligado`, `Sistemas Isolados` |
| `UF` | `uf` | VARCHAR | sigla |
| `Setor Econômico - N1` | `classe` | VARCHAR | 8 valores: Residencial, Industrial, Comercial, Rural, Poder Público, Iluminação Pública, Serviço Público, Consumo Próprio |
| `Setor Econômico - N2` | `subclasse` | VARCHAR | `nullif(x, 'TOTAL')` |
| `Setor Econômico - N3` | `subclasse_detalhe` | VARCHAR | `nullif(x, 'TOTAL')` |
| `Tipo Tensão - N1` | `grupo_tensao` | VARCHAR | `A - Alta Tensão`, `B - Baixa Tensão` |
| `Tipo Tensão - N2` | `subgrupo_tensao` | VARCHAR | `nullif(x, 'TOTAL')`; ex.: `A-4 - 2,3 a 25 kV` |
| `Tipo Tensão - N3` | `subgrupo_tensao_detalhe` | VARCHAR | `nullif(x, 'TOTAL')` |
| `Faixa de Consumo N1` | `faixa_consumo` | VARCHAR | `Convencional`, `Baixa Renda`, `Alta Tensão`, `Não Aplicável` |
| `Faixa de Consumo N2` | `faixa_consumo_detalhe` | VARCHAR | faixa em kWh (`0-30 kWh`, `31-100 kWh`, ... `501-1000 kWh`) |
| `Consumidores` | `consumidores` | BIGINT | **estoque do mês**, não fluxo |
| `Consumo` | `consumo_mwh` | DOUBLE | **MWh** |

Já é formato longo: uma linha por mês e combinação de atributos. Não precisa `UNPIVOT`.

**Ressalvas que o analista precisa ler**

- **Realizado, não projeção.** Cobre 01/2011 a 12/2025 (`min(mes) = 2011-01-01`, `max(mes) = 2025-12-01`).
- **A unidade é MWh**, não GWh nem TWh — a planilha não diz. Deduzi somando: 2011 = 433,02 milhões de MWh,
  2024 = 561,57, 2025 = 566,75. O Anuário publicado da EPE traz 561,5 TWh para o consumo total de 2024, o que fecha
  com a soma em MWh dividida por 10⁶.
- **`consumidores` é estoque mensal: não some ao longo dos meses.** Para o número de consumidores do ano, use a média
  (`sum(consumidores)/12`): 93,29 milhões em 2024, 94,83 milhões em 2025.
- `'TOTAL'` nas colunas N2/N3 significa "sem desagregação neste nível", não um total a somar. Anulei com `nullif`;
  quem somar sem anular conta duas vezes.
- Buracos e sinais: **14.640** linhas com `consumo_mwh` NULL, **5.882** com `consumidores` NULL e **876** com
  `consumo_mwh` negativo (ajuste retroativo da distribuidora). Filtre antes de agregar.
- **Não é comparável direto com o que o banco já tem.** `mercado_distribuidoras_mensal` (85.343 linhas, SAMP/ANEEL,
  2020 em diante) é por distribuidora e inclui faturamento; esta é por UF/subsistema/faixa de consumo e vai a 2011.
  `ons_carga_diaria` (39.057) é carga do SIN em MW médio, que inclui perdas e não é consumo faturado. Os três números
  não fecham entre si e não devem ser misturados na mesma série.

**No banco**: complementa. Não existe nenhuma tabela `epe_*`; e nenhuma tabela do banco tem consumo de eletricidade
por faixa de consumo, por classe com três níveis de detalhe, nem série anterior a 2020.

**Receita testada** (423.751 linhas):

```sql
SELECT strptime(CAST(CAST("Data" AS BIGINT) AS VARCHAR), '%Y%m%d')::DATE AS mes,
       "TipoConsumidor" AS tipo_consumidor, "Sistema" AS subsistema, "UF" AS uf,
       "Setor Econômico - N1" AS classe, nullif("Setor Econômico - N2", 'TOTAL') AS subclasse,
       nullif("Setor Econômico - N3", 'TOTAL') AS subclasse_detalhe,
       "Tipo Tensão - N1" AS grupo_tensao, nullif("Tipo Tensão - N2", 'TOTAL') AS subgrupo_tensao,
       nullif("Tipo Tensão - N3", 'TOTAL') AS subgrupo_tensao_detalhe,
       "Faixa de Consumo N1" AS faixa_consumo, "Faixa de Consumo N2" AS faixa_consumo_detalhe,
       CAST("Consumidores" AS BIGINT) AS consumidores, "Consumo" AS consumo_mwh
FROM read_xlsx('data/raw/aneel_ons_epe_bndes/anuario_dados_brutos.xlsx', sheet='Sheet1', header=true)
```

Saída real (5 primeiras linhas de `LINHAS: 423751`):

```
(2011-01-01, 'Cativo', 'Sudeste / Centro-Oeste', 'RO', 'Residencial', 'Convencional (Excepto Baixa Renda)', None, 'A - Alta Tensão', None, None, 'Alta Tensão', 'Alta Tensão', 1, 10.0)
(2011-02-01, 'Cativo', 'Sudeste / Centro-Oeste', 'RO', 'Residencial', 'Convencional (Excepto Baixa Renda)', None, 'A - Alta Tensão', None, None, 'Alta Tensão', 'Alta Tensão', 1, 8.0)
(2011-03-01, 'Cativo', 'Sudeste / Centro-Oeste', 'RO', 'Residencial', 'Convencional (Excepto Baixa Renda)', None, 'A - Alta Tensão', None, None, 'Alta Tensão', 'Alta Tensão', 1, 9.0)
(2011-04-01, 'Cativo', 'Sudeste / Centro-Oeste', 'RO', 'Residencial', 'Convencional (Excepto Baixa Renda)', None, 'A - Alta Tensão', None, None, 'Alta Tensão', 'Alta Tensão', 1, 10.0)
(2011-05-01, 'Cativo', 'Sudeste / Centro-Oeste', 'RO', 'Residencial', 'Convencional (Excepto Baixa Renda)', None, 'A - Alta Tensão', None, None, 'Alta Tensão', 'Alta Tensão', 1, 8.0)
```

Nota: esta é a única receita que lê tipada (sem `all_varchar`) — é o que prova que não há rodapé de texto: se
houvesse, a inferência de `DOUBLE` na coluna `Data` teria falhado.

## 5. Fonte 2 — PDE 2035 (`pde2035_dados.zip`)

Arquivo: `data/raw/aneel_ons_epe_bndes/pde2035_dados.zip`, 12 pastas de trabalho (§3). 31 tabelas propostas, a
partir de 39 abas. Todas seguem o layout de §2: cabeçalho em L6, dados de L7 em diante.

Para não repetir o mesmo `read_xlsx` 39 vezes, as receitas abaixo usam as duas abreviações do script
`05_receitas_finais.py`:

- **`x(cap, 'aba', 'range')`** expande para
  `read_xlsx('<pasta do capítulo cap>', sheet='<aba>', range='<range>', header=true, all_varchar=true, empty_as_varchar=true)`.
- **`por_ano(tabela, cap, 'aba', 'range', <coluna_categoria>, <coluna_valor>, '<sufixo>', excluir=...)`** expande
  para o SQL de despivotamento de §2.

Exemplo do que `x` gera, expandido (é o SQL que rodou para a primeira tabela do capítulo 2):

```sql
read_xlsx('.../PDE 2035_Dados_Capítulo 02_Demanda de Energia.xlsx', sheet='Figura 2-25', range='A6:D40',
          header=true, all_varchar=true, empty_as_varchar=true)
```

Ressalva que vale para **todas** as 31 tabelas desta fonte e não se repetirá em cada uma:

> São **projeções**, não realizado. O ano-base é **2025** e o horizonte vai a 2035 (a de transmissão vai a 2038). Os
> valores monetários estão em **reais de 2025** (a `Tabela 12-10` declara na nota 9 a taxa de câmbio referencial
> `R$ 6,10 / US$ (dez/2024)`). Nenhuma série do PDE deve ser encadeada com série realizada do banco
> (ANEEL, ONS, CCEE) na mesma coluna: o PDE parte da base de dezembro de 2025 e reprojeta o histórico recente.
> Todo número vem de rodada do modelo de expansão da EPE com premissas do Cenário de Referência, salvo onde a
> própria coluna nomeia outro cenário.

### 5.1 Capítulo 02 — Demanda de Energia

#### `epe_pde2035_carga_energia_cenario`

Carga de energia do SIN projetada nos três cenários de demanda.

**Aba** `Figura 2-25` · título L3 `Figura 2‑25 | Carga de energia: Cenário de referência x cenários alternativos` ·
fonte L4 `Elaboração EPE.` · cabeçalho L6 · dados **L7:L17** (11 anos) · sem rodapé · sem mescla.

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `Ano` | `ano` | INTEGER |
| `Cenário Superior (GWmédio)`, `Cenário Referência (GWmédio)`, `Cenário Inferior (GWmédio)` | `cenario` | VARCHAR |
| (valor das três colunas) | `carga_gwmed` | DOUBLE |

**Largo → longo**: `UNPIVOT` das três colunas de cenário; id = `ano`; categoria = `cenario` (o sufixo `' (GWmédio)'`
sai por `replace`); valor = `carga_gwmed`. 11 anos × 3 cenários = 33 linhas.

**Ressalvas**: é **carga**, não consumo — inclui perdas e é medida em GW médio, então não compara com
`consumo_mwh` do Anuário nem com `consumo_rede_twh` de `epe_pde2035_red_demanda_eletricidade` (essa é consumo na
rede em TWh). O cenário superior em 2035 (138,29 GWméd) é 20,7 % acima do de referência (114,61): ao citar "a carga
projetada" é obrigatório dizer qual cenário.

**No banco**: complementa. `ons_carga_diaria` (39.057 linhas) é carga realizada; não há projeção de carga no banco.

**Receita testada** (33 linhas):

```sql
por_ano("epe_pde2035_carga_energia_cenario", 2, "Figura 2-25", "A6:D40", "cenario", "carga_gwmed", " (GWmédio)")
```

```
(2025, 'Cenário Inferior', 81.9676595047586)
(2025, 'Cenário Referência', 82.69050823726886)
(2025, 'Cenário Superior', 83.26859103554173)
(2026, 'Cenário Inferior', 84.19683217790788)
(2026, 'Cenário Referência', 85.56906811226247)
```

#### `epe_pde2035_demanda_maxima_sin_mes`

Demanda máxima instantânea do SIN, mês a mês, nos dois anos-limite do plano.

**Aba** `Figura 2-22` · título L3 `Figura 2-22 | Demanda máxima no SIN (anos 2025 e 2035)` · fonte L4
`Elaboração EPE.` · cabeçalho L6 `Mês | 2025 (GWh/h) | 2035 (GWh/h)` · dados **L7:L18** (12 meses) · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo | Observação |
|---|---|---|---|
| `2025 (GWh/h)`, `2035 (GWh/h)` (nome da coluna) | `ano` | INTEGER | `regexp_extract(serie, '\d{4}')` |
| `Mês` | `mes` | INTEGER | nome do mês em português → número por `list_position` |
| (valor) | `demanda_maxima_gwh_h` | DOUBLE | GWh/h = GW médio na hora de ponta |

**Largo → longo**: aqui o ano está **no nome da coluna** e o mês nas linhas. `UNPIVOT` das duas colunas de ano; o ano
sai do nome por regex. 12 meses × 2 anos = 24 linhas.

**Ressalvas**: só **2025 e 2035**, não a série completa — a figura do relatório compara os extremos. O mês vem como
texto (`Janeiro`…`Dezembro`), e converti para número; se a EPE mudar a grafia (`Marco` sem cedilha, por exemplo), a
conversão devolve NULL e a receita deve falhar em vez de gravar NULL.

**No banco**: complementa. Nenhuma tabela tem demanda máxima (ponta) do SIN, nem realizada nem projetada.

**Receita testada** (24 linhas):

```sql
WITH bruto AS (SELECT * FROM x(2, 'Figura 2-22', 'A6:C40') WHERE "Mês" IS NOT NULL)
SELECT CAST(regexp_extract(serie, '\d{4}') AS INTEGER) AS ano,
       list_position(['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro',
                      'Outubro','Novembro','Dezembro'], "Mês") AS mes,
       TRY_CAST(valor AS DOUBLE) AS demanda_maxima_gwh_h
FROM (UNPIVOT bruto ON COLUMNS(* EXCLUDE ("Mês")) INTO NAME serie VALUE valor)
WHERE valor IS NOT NULL ORDER BY ano, mes
```

```
(2025, 1, 109.17965465578423)
(2025, 2, 108.69046661914328)
(2025, 3, 107.35766869015237)
(2025, 4, 101.52142093106902)
(2025, 5, 100.4626948036217)
```

#### `epe_pde2035_curva_carga_horaria`

Curva de carga horária do dia de ponta de cada mês de 2035, aberta por classe de consumo.

**Aba** `Figura 2-23` · título L3
`Figura 2-23 | Cenário referência: Curvas de carga horária nos dias de ponta por mês em 2035 (GWh/h)` · fonte L4
`Elaboração EPE.` · cabeçalho L6 `Mês | Hora | Carga (GWh/h) | Classe` · dados **L7:L1446** (1.440 linhas) ·
sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo | Observação |
|---|---|---|---|
| `Mês` | `mes` | INTEGER | abreviado (`Jan`…`Dez`) → número |
| `Hora` | `hora` | INTEGER | 0 a 23 |
| `Classe` | `classe` | VARCHAR | inclui `Perdas e Diferenças` |
| `Carga (GWh/h)` | `carga_gwh_h` | DOUBLE | |

**Já é longo** na origem — a única aba do PDE que já vem tidy. Sem `UNPIVOT`. 12 meses × 24 horas × 5 classes = 1.440.

**Ressalvas**: é **só 2035** e **só o dia de ponta** de cada mês, no cenário de referência — não é curva média nem
série horária do ano. A classe `Perdas e Diferenças` não é consumo: é o fechamento do balanço, e somar todas as
classes dá a carga, não o consumo. Aqui os meses vêm abreviados (`Jan`), diferente da `Figura 2-22` (`Janeiro`), na
mesma pasta.

**No banco**: complementa. `ons_cmo_semihora` (464.256 linhas) tem granularidade sub-horária de preço, não de carga
por classe; não há curva de carga por classe no banco.

**Receita testada** (1.440 linhas):

```sql
SELECT list_position(['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'], "Mês") AS mes,
       CAST("Hora" AS INTEGER) AS hora, "Classe" AS classe, TRY_CAST("Carga (GWh/h)" AS DOUBLE) AS carga_gwh_h
FROM x(2, 'Figura 2-23', 'A6:D2000')
WHERE "Mês" IS NOT NULL AND TRY_CAST("Hora" AS INTEGER) IS NOT NULL
ORDER BY classe, mes, hora
```

```
(1, 0, 'Comercial', 15.32534463698036)
(1, 1, 'Comercial', 14.28660844027781)
(1, 2, 'Comercial', 13.98031850594752)
(1, 3, 'Comercial', 13.68345878719277)
(1, 4, 'Comercial', 13.72372542242572)
```

#### `epe_pde2035_crescimento_consumo_classe`

Taxa média anual de crescimento do consumo de eletricidade na rede, por classe e cenário.

**Aba** `Figura 2-26` · título L3
`Figura 2‑26 | Crescimento do consumo de eletricidade na rede, por classe. Cenário de referência x cenários alternativos (% a.a.)`
· fonte L4 `Elaboração EPE.` · cabeçalho L6 · dados **L7:L10** (4 classes) · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo | Observação |
|---|---|---|---|
| `Classe` | `classe` | VARCHAR | `Residencial`, `Industrial`, `Comercial`, `Outros` |
| `Cenário Inferior/Referência/Superior (% ao ano)` | `cenario` | VARCHAR | sufixo removido |
| (valor) | `crescimento_pct_aa` | DOUBLE | **fração na planilha** (`0.03039`) → ×100 |

**Largo → longo**: `UNPIVOT` dos três cenários. 4 × 3 = 12 linhas.

**Ressalvas**: a planilha guarda **fração**, não percentual, apesar do título dizer "% a.a." — multipliquei por 100 e
arredondei em 4 casas, e é por isso que a unidade está no nome (`crescimento_pct_aa`). É taxa média do decênio
2025-2035, não taxa ano a ano. A classe `Outros` agrega Rural, Poder Público, Iluminação Pública e Serviço Público,
que no Anuário são quatro classes separadas: não dá para cruzar classe a classe com `epe_anuario_consumo_mensal`
sem reagrupar.

**No banco**: complementa; não há taxa de crescimento projetada em nenhuma tabela.

**Receita testada** (12 linhas):

```sql
WITH bruto AS (SELECT * FROM x(2, 'Figura 2-26', 'A6:D40') WHERE "Classe" IS NOT NULL)
SELECT "Classe" AS classe, replace(cenario, ' (% ao ano)', '') AS cenario,
       round(TRY_CAST(valor AS DOUBLE) * 100, 4) AS crescimento_pct_aa
FROM (UNPIVOT bruto ON COLUMNS(* EXCLUDE ("Classe")) INTO NAME cenario VALUE valor)
WHERE valor IS NOT NULL ORDER BY classe, cenario
```

```
('Comercial', 'Cenário Inferior', 3.8323)
('Comercial', 'Cenário Referência', 4.7063)
('Comercial', 'Cenário Superior', 7.8419)
('Industrial', 'Cenário Inferior', 2.1355)
('Industrial', 'Cenário Referência', 2.8367)
```

### 5.2 Capítulo 03 — Geração Centralizada

#### `epe_pde2035_capacidade_instalada_fonte`

Capacidade instalada existente e contratada do SIN, por fonte, ano a ano.

**Aba** `Figura 3-6` · título L3 `Figura 3-6 | Evolução da capacidade instalada existente e contratada do SIN (GW)` ·
fonte L4 `Elaboração EPE.` · cabeçalho L6 (11 colunas) · dados **L7:L17** · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `Ano` | `ano` | INTEGER |
| `BIOMASSA`, `CARVAO`, `DIESEL / ÓLEO`, `EOLICA`, `Solar`, `GAS`, `NUCLEAR`, `PCH`, `PCT`, `UHE` | `fonte` | VARCHAR |
| (valor) | `potencia_gw` | DOUBLE |

**Largo → longo**: `UNPIVOT` das 10 colunas de fonte; sem sufixo a remover (a unidade está só no título). 11 × 10 =
110 linhas.

**Ressalvas**

- **A grafia da fonte é a da planilha**, inconsistente de propósito: maiúsculas sem acento (`EOLICA`, `CARVAO`,
  `GAS`) convivendo com `Solar` em caixa mista, e `DIESEL / ÓLEO` com espaços em volta da barra. Não normalizei;
  quem cruzar com `usinas` (SIGA) precisa de tabela de equivalência.
- **`Solar` inclui MMGD.** Em 2025 a coluna marca 60,27 GW, contra 109,42 de UHE, 35,06 de eólica e 15,12 de gás. A
  capacidade solar **centralizada** do SIGA é uma fração disso; a diferença é micro e minigeração distribuída. Ou
  seja: esta tabela **não é comparável** com o total centralizado de `usinas`/`capacidade_por_grupo`, e somar as
  colunas com a série de MMGD (`epe_pde2035_mmgd_capacidade_cenario`) conta a MMGD duas vezes.
- `PCT` é pequena central termelétrica; `PCH` pequena central hidrelétrica. A planilha não abre a legenda.

**No banco**: complementa parcialmente e **se sobrepõe conceitualmente** a `usinas` (25.045 linhas, SIGA/ANEEL, usina
a usina, realizado) e `capacidade_por_grupo` (7.010). O que é novo é a trajetória contratada até 2035.

**Receita testada** (110 linhas):

```sql
por_ano("epe_pde2035_capacidade_instalada_fonte", 3, "Figura 3-6", "A6:K40", "fonte", "potencia_gw", "")
```

```
(2025, 'BIOMASSA', 0.15713)
(2025, 'CARVAO', 2.90042)
(2025, 'DIESEL / ÓLEO', 2.3075799999999997)
(2025, 'EOLICA', 35.062099)
(2025, 'GAS', 15.12258)
```

#### `epe_pde2035_demanda_subsistema`

Demanda projetada por subsistema e demanda máxima do SIN, cenário de referência.

**Aba** `Figura 3-7` · título L3 `Figura 3-7 | Projeções de demanda do Cenário de Referência` · fonte L4
`Elaboração EPE.` · cabeçalho L6 · dados **L7:L16** (2026-2035) · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `Ano` | `ano` | INTEGER |
| `Sudeste (MWmédio)` | `sudeste_mwmed` | DOUBLE |
| `Sul (MWmédio)` | `sul_mwmed` | DOUBLE |
| `Nordeste (MWmédio)` | `nordeste_mwmed` | DOUBLE |
| `Norte (MWmédio)` | `norte_mwmed` | DOUBLE |
| `Demanda Máxima - SIN (MW)` | `demanda_maxima_sin_mw` | DOUBLE |

**Não despivotei.** É a exceção deliberada: a última coluna está em **MW de ponta** e as quatro primeiras em **MW
médio** — despivotar jogaria duas unidades na mesma coluna de valor. Mantive larga com a unidade em cada nome.
10 linhas.

**Ressalvas**: começa em **2026**, não 2025 (a série de capacidade da `Figura 3-6` começa em 2025). `Sudeste` aqui é
o submercado Sudeste/Centro-Oeste, com nome curto; no Anuário o mesmo submercado aparece como
`Sudeste / Centro-Oeste`. Só cenário de referência.

**No banco**: complementa. Nenhuma projeção de demanda por submercado existe no banco.

**Receita testada** (10 linhas):

```sql
SELECT CAST("Ano" AS INTEGER) AS ano, TRY_CAST("Sudeste (MWmédio)" AS DOUBLE) AS sudeste_mwmed,
       TRY_CAST("Sul (MWmédio)" AS DOUBLE) AS sul_mwmed, TRY_CAST("Nordeste (MWmédio)" AS DOUBLE) AS nordeste_mwmed,
       TRY_CAST("Norte (MWmédio)" AS DOUBLE) AS norte_mwmed,
       TRY_CAST("Demanda Máxima - SIN (MW)" AS DOUBLE) AS demanda_maxima_sin_mw
FROM x(3, 'Figura 3-7', 'A6:F40') WHERE TRY_CAST("Ano" AS INTEGER) BETWEEN 1990 AND 2100 ORDER BY ano
```

```
(2026, 47797.0, 14733.0, 14226.0, 8813.263013698632, 113343.30336450785)
(2027, 49273.0, 15264.0, 14741.0, 9088.0, 117047.80422737433)
(2028, 50782.508533144166, 15819.99576103696, 15256.995904944568, 9369.981087407019, 120825.72185344872)
(2029, 52339.76708254316, 16393.0, 15788.000000000002, 9636.000000000002, 124702.66398209502)
(2030, 54225.52797834489, 16981.449972058308, 16339.682557414366, 9993.14267382717, 129183.33259527784)
```

#### `epe_pde2035_mmgd_expansao_fonte`

Expansão da micro e minigeração distribuída, em potência e em energia, por fonte.

**Aba** `Figura 3-8` · título L3 `Figura 3-8 | Expansão em capacidade e em energia da MMGD` · fonte L4
`Elaboração EPE.` · cabeçalho L6 com **duas grandezas no mesmo nome** (`Potência (MW) - Fotovoltaica`,
`Energia (MWmédio) - Fotovoltaica`, …) · dados **L7:L16** (2026-2035) · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo | Observação |
|---|---|---|---|
| `Ano` | `ano` | INTEGER | |
| sufixo do nome (`… - Fotovoltaica`) | `fonte` | VARCHAR | `Fotovoltaica`, `Eólica`, `Termelétrica`, `CGH` |
| prefixo do nome (`Potência (MW)` / `Energia (MWmédio)`) | `grandeza` | VARCHAR | `'potencia_mw'` ou `'energia_mwmed'` |
| (valor) | `valor` | DOUBLE | unidade determinada por `grandeza` |

**Largo → longo**: o cabeçalho cruza duas dimensões num único rótulo. `UNPIVOT` de todas as 10 colunas e depois
partir o nome: `regexp_replace(serie, '^(Potência \(MW\)|Energia \(MWmédio\)) - ', '')` dá a fonte, e o prefixo dá a
grandeza. As colunas `Total` de cada grandeza são descartadas (`fonte <> 'Total'`). 10 anos × 4 fontes × 2 grandezas
= 80 linhas.

**Ressalvas**: **esta é uma das três tabelas com coluna `valor` genérica** — a unidade está na coluna `grandeza`, não
no nome, porque duas unidades convivem na mesma aba (ver §9, decisão 3). Sempre filtre por `grandeza` antes de
agregar. A energia em `MWmédio` vem arredondada a inteiro na planilha (6650, 14, 159, 34) enquanto a potência tem 8
decimais: precisão diferente na mesma linha. Os totais por grandeza foram descartados e podem ser recalculados.

**No banco**: **sobrepõe-se** a `gd_mmgd` (66.826 linhas, ANEEL, unidade consumidora a unidade consumidora,
realizado). O que é novo é a projeção 2026-2035. Não encadeie as duas séries: a base ANEEL é cadastro de conexões, a
do PDE é modelo de adoção.

**Receita testada** (80 linhas):

```sql
WITH bruto AS (SELECT * FROM x(3, 'Figura 3-8', 'A6:K40') WHERE TRY_CAST("Ano" AS INTEGER) BETWEEN 1990 AND 2100)
SELECT CAST(ano AS INTEGER) AS ano,
       regexp_replace(serie, '^(Potência \(MW\)|Energia \(MWmédio\)) - ', '') AS fonte,
       CASE WHEN serie LIKE 'Potência%' THEN 'potencia_mw' ELSE 'energia_mwmed' END AS grandeza,
       TRY_CAST(valor AS DOUBLE) AS valor
FROM (UNPIVOT (SELECT "Ano" AS ano, * EXCLUDE ("Ano") FROM bruto) ON COLUMNS(* EXCLUDE (ano))
      INTO NAME serie VALUE valor)
WHERE valor IS NOT NULL AND fonte <> 'Total' ORDER BY ano, fonte, grandeza
```

```
(2026, 'CGH', 'energia_mwmed', 34.0)
(2026, 'CGH', 'potencia_mw', 73.06677293)
(2026, 'Eólica', 'energia_mwmed', 14.0)
(2026, 'Eólica', 'potencia_mw', 34.60439799)
(2026, 'Fotovoltaica', 'energia_mwmed', 6650.0)
```

#### `epe_pde2035_custos_referencia_fonte`

Parâmetros de custo de referência usados no modelo de expansão: CAPEX, O&M fixo e encargos por tecnologia.

**Três abas empilhadas**, todas com cabeçalho L6 e duas colunas:

| Aba | Título (L3) | Dados | Cabeçalho L6 | `grandeza` |
|---|---|---|---|---|
| `Figura 3-19` | Valores de investimento (CAPEX), em R$/kW, por fonte de geração ou tecnologia de armazenamento | L7:L38 | `Tipo \| Investimento (R$/kW)` | `capex_brl_kw` |
| `Figura 3-20` | Valores de custos fixos de operação e manutenção (O&M), em R$/kW por ano, … | L7:L28 | `Tipo \| O&M Anual (R$/kW.ano)` | `om_fixo_brl_kw_ano` |
| `Figura 3-21` | Valores totais de taxas, encargos e impostos, em R$/kW por ano, … | L7:L38 | `Tipo \| Encargos (R$/kW.ano)` | `encargos_brl_kw_ano` |

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| (aba de origem) | `grandeza` | VARCHAR |
| `Tipo` | `tecnologia` | VARCHAR |
| `Investimento (R$/kW)` / `O&M Anual (R$/kW.ano)` / `Encargos (R$/kW.ano)` | `valor` | DOUBLE |

**Largo → longo**: aqui a operação é `UNION ALL` das três abas, com a grandeza como literal. 32 + 22 + 32 = 86
linhas.

**Ressalvas**: segunda tabela com `valor` genérico (a unidade está em `grandeza`: R$/kW para CAPEX, R$/kW.ano para
os outros dois). **As três abas não têm a mesma lista de tecnologias**: 32, 22 e 32 linhas, e a 3-20 não abre
`Fotovoltaica` em faixas. Uma consulta que junte CAPEX e O&M pela tecnologia perde linhas — faça `LEFT JOIN`
consciente disso. As "Faixas" (`Fotovoltaica - Faixa 1/2/3`, `Bateria - Faixa 1/2/3`) são faixas de custo do modelo,
não de porte; a planilha não define os limites. São valores em **R$ de 2025**, parâmetros de entrada do modelo, não
custos observados em leilão.

**No banco**: complementa. Não há tabela de parâmetros de custo por tecnologia.

**Receita testada** (86 linhas):

```sql
SELECT 'capex_brl_kw' AS grandeza, "Tipo" AS tecnologia, TRY_CAST("Investimento (R$/kW)" AS DOUBLE) AS valor
FROM x(3, 'Figura 3-19', 'A6:B60') WHERE "Tipo" IS NOT NULL
UNION ALL
SELECT 'om_fixo_brl_kw_ano', "Tipo", TRY_CAST("O&M Anual (R$/kW.ano)" AS DOUBLE)
FROM x(3, 'Figura 3-20', 'A6:B60') WHERE "Tipo" IS NOT NULL
UNION ALL
SELECT 'encargos_brl_kw_ano', "Tipo", TRY_CAST("Encargos (R$/kW.ano)" AS DOUBLE)
FROM x(3, 'Figura 3-21', 'A6:B60') WHERE "Tipo" IS NOT NULL
ORDER BY grandeza, tecnologia
```

```
('capex_brl_kw', 'Bateria - Faixa 1', 5000.0)
('capex_brl_kw', 'Bateria - Faixa 2', 5500.0)
('capex_brl_kw', 'Bateria - Faixa 3', 6000.0)
('capex_brl_kw', 'Biocombustível', 3500.0)
('capex_brl_kw', 'Biogás', 14000.0)
```

#### `epe_pde2035_expansao_indicativa`

Expansão indicativa acumulada da geração, por fonte — o resultado central do capítulo.

**Aba** `Figura 3-23` · título L3 `Figura 3-23 | Expansão indicativa acumulada no horizonte de 2026 a 2035` · fonte
L4 `Elaboração EPE.` · cabeçalho L6 (11 colunas) · dados **L7:L16** · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `Ano` | `ano` | INTEGER |
| `Hidro (MW)`, `Eólica (MW)`, `Solar (MW)`, `UTE Flex (MW)`, `UTE Inflex (MW)`, `UTE Bio (MW)`, `Nuclear (MW)`, `Armazenamento (MW)`, `RD (MW)` | `fonte` | VARCHAR |
| (valor) | `potencia_acumulada_mw` | DOUBLE |

**Largo → longo**: `UNPIVOT` das 9 fontes, sufixo `' (MW)'` removido, coluna `Total (MW)` descartada. 10 × 9 = 90
linhas. Conferi que a soma dos 9 itens reproduz a coluna `Total (MW)` descartada em **todos os 10 anos**, com
igualdade exata (2026: 3.487,53; 2035: 69.723,513282).

> **Armadilha do filtro, medida.** Escrever `WHERE fonte NOT IN ('Total')` sobre o `UNPIVOT` **não funciona**: no
> `WHERE`, `fonte` resolve para a coluna crua produzida pelo `INTO NAME fonte` (que ainda vale `'Total (MW)'`), e não
> para o alias do `SELECT` que já removeu o sufixo. Na primeira rodada isso deixou a linha de total passar e a tabela
> veio com 100 linhas e 10 categorias, `'Total'` incluída. O filtro tem de repetir o `replace`:
> `AND replace(fonte, ' (MW)', '') NOT IN ('Total')`. A mesma correção vale para `epe_pde2035_emissoes_setor`.

**Ressalvas**

- É **acumulada**, não anual: o valor de 2035 é o total do decênio, e `2035 − 2034` dá a adição daquele ano. Somar a
  coluna ao longo dos anos é erro grosseiro.
- É **indicativa**: expansão que o modelo escolhe, não contratada. Não é comparável com `expansao_geracao`
  (2.246 linhas, RALIE/ANEEL, obras reais em andamento) nem com resultado de leilão.
- `RD` é resposta da demanda e `Armazenamento` é bateria: entram como "oferta" no modelo mas não são geração.
- Começa em **2026** (a expansão do primeiro ano do plano é a já contratada, que está na `Figura 3-6`).

**No banco**: complementa; e **atenção**, não substitui `expansao_geracao`.

**Receita testada** (90 linhas):

```sql
por_ano("epe_pde2035_expansao_indicativa", 3, "Figura 3-23", "A6:K40", "fonte",
        "potencia_acumulada_mw", " (MW)", excluir="'Total'")
```

```
(2026, 'Armazenamento', 0.0)
(2026, 'Eólica', 0.0)
(2026, 'Hidro', 0.0)
(2026, 'Nuclear', 0.0)
(2026, 'RD', 300.0)
```

#### `epe_pde2035_expansao_termica`

Abertura da expansão térmica indicativa por tipo de usina.

**Aba** `Figura 3-24` · título L3 `Figura 3-24 | Expansão indicativa acumulada das usinas térmicas` · fonte L4
`Elaboração EPE.` · cabeçalho L6 (8 colunas) · dados **L7:L16** · **rodapé L17 vazia, L18 `Nota:`, L19** com o texto
`Retrofit Térmica inclui usinas a gás natural flexíveis, carvão mineral e conversão de usinas a óleo combustível e diesel para biocombustível.`
— 3 linhas a descartar.

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `Ano` | `ano` | INTEGER |
| `Gás Natural Flexível (MW)`, `Gás Natural Inflexível (MW)`, `Retrofit Térmica (MW)`, `Retrofit Biocombustível (MW)`, `Biomassa (MW)`, `RSU (MW)`, `Carvão (MW)` | `tipo_termica` | VARCHAR |
| (valor) | `potencia_acumulada_mw` | DOUBLE |

**Largo → longo**: `UNPIVOT` das 7 colunas (não há coluna de total). 10 × 7 = 70 linhas.

**Ressalvas**: acumulada, igual à 3-23. **`Retrofit Térmica` e `Retrofit Biocombustível` são conversão de usina
existente, não usina nova** — a nota L19 é a definição oficial e precisa entrar no campo `ressalvas` do catálogo.
`Carvão` fica zerado em todo o decênio. A soma das colunas térmicas desta aba **não** iguala
`UTE Flex + UTE Inflex + UTE Bio` da 3-23, porque aqui os retrofits aparecem separados.

**No banco**: complementa.

**Receita testada** (70 linhas):

```sql
por_ano("epe_pde2035_expansao_termica", 3, "Figura 3-24", "A6:H40", "tipo_termica",
        "potencia_acumulada_mw", " (MW)")
```

```
(2026, 'Biomassa', 0.0)
(2026, 'Carvão', 0.0)
(2026, 'Gás Natural Flexível', 0.0)
(2026, 'Gás Natural Inflexível', 0.0)
(2026, 'RSU', 0.0)
```

#### `epe_pde2035_cmo_projetado_mes`

Custo marginal de operação médio projetado do submercado Sudeste/Centro-Oeste.

**Aba** `Figura 3-28` · título L3 `Figura 3-28 | Custo marginal de operação médio – Sudeste/Centro-Oeste` · fonte L4
`Elaboração EPE.` · cabeçalho L6 `Mês | Média 2026 (R$/MWh) | Média 2030 (R$/MWh) | Média 2035 (R$/MWh)` · dados
**L7:L18** · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo | Observação |
|---|---|---|---|
| nome da coluna (`Média 2026 (R$/MWh)`) | `ano` | INTEGER | `regexp_extract(serie, '\d{4}')` |
| `Mês` | `mes` | INTEGER | nome em português → número |
| — | `subsistema` | VARCHAR | literal `'SE/CO'`, vem do título |
| (valor) | `cmo_brl_mwh` | DOUBLE | R$ de 2025 por MWh |

**Largo → longo**: ano no nome da coluna, mês na linha; `UNPIVOT` das três colunas de ano. 12 × 3 = 36 linhas.

**Ressalvas**: **só três anos de corte (2026, 2030, 2035) e só o SE/CO** — a planilha não traz os outros
submercados nem os anos intermediários. É **média mensal de 2.000 séries** do modelo, não um CMO esperado de
mercado; o salto de 2030 para 2035 (dezembro: R$ 42,34 → R$ 217,53) é resultado de premissa de escassez, não
previsão de preço. O `subsistema` é literal derivado do título, não lido de célula. Em R$ de 2025: **não compare
diretamente** com `ons_cmo_mensal` (324 linhas) ou `ons_cmo_semihora` (464.256), que estão em reais correntes.

**No banco**: complementa `ons_cmo_mensal`/`ons_cmo_semihora` (realizado) com a projeção.

**Receita testada** (36 linhas):

```sql
WITH bruto AS (SELECT * FROM x(3, 'Figura 3-28', 'A6:D40') WHERE "Mês" IS NOT NULL)
SELECT CAST(regexp_extract(serie, '\d{4}') AS INTEGER) AS ano,
       list_position([...meses em português...], "Mês") AS mes,
       'SE/CO' AS subsistema, TRY_CAST(valor AS DOUBLE) AS cmo_brl_mwh
FROM (UNPIVOT bruto ON COLUMNS(* EXCLUDE ("Mês")) INTO NAME serie VALUE valor)
WHERE valor IS NOT NULL ORDER BY ano, mes
```

```
(2026, 1, 'SE/CO', 33.38)
(2026, 2, 'SE/CO', 18.45)
(2026, 3, 'SE/CO', 18.85)
(2026, 4, 'SE/CO', 15.78)
(2026, 5, 'SE/CO', 11.98)
```

#### `epe_pde2035_geracao_hidro_termica_mes`

Geração hidrelétrica e termelétrica média do SIN, mês a mês, todo o horizonte.

**Aba** `Figura 3-29` · título L3 `Figura 3-29 | Geração hidrelétrica e termelétrica média do SIN` · fonte L4
`Elaboração EPE.` · cabeçalho L6 `Mês | Geração hidrelétrica média (MWmédio) | Geração termelétrica média (MWmédio)`
· dados **L7:L126** (120 meses, 01/2026 a 12/2035) · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo | Observação |
|---|---|---|---|
| `Mês` | `mes` | DATE | **serial de data do Excel**; `DATE '1899-12-30' + inteiro` |
| `Geração hidrelétrica média (MWmédio)` | `geracao_hidraulica_mwmed` | DOUBLE | |
| `Geração termelétrica média (MWmédio)` | `geracao_termica_mwmed` | DOUBLE | |

**Não despivotei**: duas séries na mesma unidade, mas semanticamente distintas e sempre consultadas juntas; manter
larga evita um `PIVOT` de volta em toda consulta. 120 linhas.

**Ressalvas**: **esta é a aba que expõe o bug do serial de data** — com `all_varchar=true` a célula vem como
`'46023'`, e um `CAST(... AS DATE)` ingênuo devolve NULL para todas as 120 linhas (foi o que aconteceu na primeira
rodada). O filtro `TRY_CAST("Mês" AS INTEGER) > 20000` corta cabeçalho e eventual rodapé porque qualquer data a
partir de 1954 tem serial acima disso. Só hidráulica e térmica: eólica e solar não estão nesta figura, então as duas
colunas **não somam a geração total do SIN**.

**No banco**: complementa `ons_geracao_fonte_mensal` (585 linhas, realizado por fonte).

**Receita testada** (120 linhas):

```sql
SELECT DATE '1899-12-30' + TRY_CAST("Mês" AS INTEGER) AS mes,
       TRY_CAST("Geração hidrelétrica média (MWmédio)" AS DOUBLE) AS geracao_hidraulica_mwmed,
       TRY_CAST("Geração termelétrica média (MWmédio)" AS DOUBLE) AS geracao_termica_mwmed
FROM x(3, 'Figura 3-29', 'A6:C200') WHERE TRY_CAST("Mês" AS INTEGER) > 20000 ORDER BY mes
```

```
(datetime.date(2026, 1, 1), 58935.4, 4070.71)
(datetime.date(2026, 2, 1), 60041.31, 3539.9)
(datetime.date(2026, 3, 1), 60897.21, 3307.62)
(datetime.date(2026, 4, 1), 56397.05, 3297.81)
(datetime.date(2026, 5, 1), 50938.55, 2786.6)
```

#### `epe_pde2035_concessoes_vincendas`

Potência e número de contratos de concessão de geração que vencem no decênio.

**Aba** `Figura 3-31` · título L3 `Figura 3-31 | Concessões vincendas no horizonte decenal: Dados SIGA ANEEL, dez/2025`
· fonte L4 `Elaboração EPE.` · cabeçalho L6 · dados **L7:L17** · **rodapé L18 vazia, L19 `Nota:`, L20** com
`A lista de usinas com concessões vincendas no horizonte decenal encontra-se no Anexo I-6.` — 3 linhas a descartar.

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `Ano` | `ano` | INTEGER |
| `Potência Acumulada (MW)` | `potencia_acumulada_mw` | DOUBLE |
| `Número de contratos acumulados` | `contratos_acumulados` | INTEGER |

Já é longo (uma linha por ano). 11 linhas.

**Ressalvas**: **acumulada** — 15.462,16 MW e 45 contratos em 2035 são o total do período, não do ano. A base é o
**SIGA da ANEEL em dez/2025**, declarada no título: é um retrato datado, e o banco tem o SIGA atualizado em `usinas`
(25.045 linhas), que pode divergir. A lista usina a usina **não está nesta planilha** (está no Anexo I-6 do
relatório, que não é uma das quatro fontes), então não há como abrir por usina.

**No banco**: complementa `usinas`. Não há tabela de vencimento de concessão de geração.

**Receita testada** (11 linhas):

```sql
SELECT CAST("Ano" AS INTEGER) AS ano, TRY_CAST("Potência Acumulada (MW)" AS DOUBLE) AS potencia_acumulada_mw,
       CAST(TRY_CAST("Número de contratos acumulados" AS DOUBLE) AS INTEGER) AS contratos_acumulados
FROM x(3, 'Figura 3-31', 'A6:C40') WHERE TRY_CAST("Ano" AS INTEGER) BETWEEN 1990 AND 2100 ORDER BY ano
```

```
(2025, 60.0, 1)
(2026, 369.05, 5)
(2027, 2554.137, 10)
(2028, 3546.594, 16)
(2029, 4204.594, 17)
```

### 5.3 Capítulo 04 — Transmissão

#### `epe_pde2035_cargas_conexao_rede_basica`

Potência de projetos de data center e de hidrogênio/amônia com processo de conexão à Rede Básica no MME.

**Aba** `Figura 4-3` · título L3
`Figura 4-3 | Potência instalada de projetos com processo de conexão à Rede Básica no MME por UF até 2038` · fonte L4
**`MME, data base outubro de 2025.`** (é a única aba recomendada cuja fonte não é "Elaboração EPE") · cabeçalho L6 ·
dados **L7:L19** (2026-2038, 13 linhas) · sem rodapé · dimensão declarada `A1:E19`, com a coluna **E vazia**: o range
tem de ser `A6:D40`, não `A6:E40`.

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `Ano` | `ano` | INTEGER |
| `Data Center (GW)` | `data_center_gw` | DOUBLE |
| `Hidrogênio e Amônia (GW)` | `hidrogenio_amonia_gw` | DOUBLE |
| `Carga acumulada (GW)` | `carga_acumulada_gw` | DOUBLE |

**Não despivotei**: as duas primeiras colunas são adição anual e a terceira é acumulada — despivotar misturaria fluxo
e estoque na mesma coluna de valor. 13 linhas.

**Ressalvas**

- **O título mente sobre o conteúdo**: diz "por UF", mas não há coluna de UF na aba. A abertura por UF está no mapa
  da figura do relatório, não nos dados. Não prometa corte estadual a partir daqui.
- `data_center_gw` e `hidrogenio_amonia_gw` são **adições do ano**; `carga_acumulada_gw` é **estoque**. Conferindo:
  1,81068 + 0,59099 = 2,40167 = acumulado de 2026, mas em 2027 o acumulado (5,177) é maior que a soma das duas
  colunas (2,77533), ou seja o acumulado inclui carga de outras naturezas além de data center e H2. Não reconstitua o
  acumulado a partir das duas colunas.
- Vai até **2038**, três anos além do horizonte do plano. É fila de solicitação de acesso no MME em outubro de 2025 —
  **não** é carga confirmada nem contratada.

**No banco**: complementa. Não há nada sobre fila de conexão de data center ou hidrogênio.

**Receita testada** (13 linhas):

```sql
SELECT CAST("Ano" AS INTEGER) AS ano, TRY_CAST("Data Center (GW)" AS DOUBLE) AS data_center_gw,
       TRY_CAST("Hidrogênio e Amônia (GW)" AS DOUBLE) AS hidrogenio_amonia_gw,
       TRY_CAST("Carga acumulada (GW)" AS DOUBLE) AS carga_acumulada_gw
FROM x(4, 'Figura 4-3', 'A6:D40') WHERE TRY_CAST("Ano" AS INTEGER) BETWEEN 1990 AND 2100 ORDER BY ano
```

```
(2026, 1.81068, 0.59099, 2.40167)
(2027, 1.64891, 1.12642, 5.177)
(2028, 2.9265, 9.0801, 17.1836)
(2029, 6.6065, 8.477480000000002, 32.26758)
(2030, 4.429099999999998, 4.449949999999997, 41.146629999999995)
```

#### `epe_pde2035_transmissao_investimento_cenario`

Investimento acumulado em transmissão nos três cenários de expansão.

**Aba** `Figura 4-19` · título L3 `Figura 4-19 | Cenários de expansão do sistema de transmissão` · fonte L4
`Elaboração EPE.` · cabeçalho L6 `Ano | Otimista (R$ bilhões) | Referência (R$ bilhões) | Pessimista (R$ bilhões)` ·
dados **L7:L16** · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `Ano` | `ano` | INTEGER |
| `Otimista / Referência / Pessimista (R$ bilhões)` | `cenario` | VARCHAR |
| (valor) | `investimento_acumulado_brl_bilhoes` | DOUBLE |

**Largo → longo**: `UNPIVOT` dos três cenários. 10 × 3 = 30 linhas.

**Ressalvas**

- **Os cenários de transmissão têm nomes diferentes dos de demanda**: aqui são `Otimista`/`Referência`/`Pessimista`;
  no capítulo 2 são `Superior`/`Referência`/`Inferior`. **São dimensões diferentes** — o cenário de transmissão é de
  antecipação/atraso de obra, o de demanda é de crescimento econômico. Não faça `JOIN` pelo nome do cenário entre
  esta tabela e `epe_pde2035_carga_energia_cenario`.
- Acumulado, em **R$ bilhões de 2025**. O valor de 2035 (Otimista 147,83; Referência 116,90; Pessimista 98,83) é o
  total do decênio. O cenário pessimista congela em 98,83 a partir de 2032.
- Estes três números são exatamente reproduzíveis a partir de `epe_pde2035_transmissao_obras` (fonte 3), somando
  `investimento_brl` com o corte `ano_<cenário> <= 2035` — foi assim que confirmei a unidade daquela planilha (§6).

**No banco**: complementa. `transmissao_empreendimentos` (16.262 linhas) e `rap_transmissao_modulos` (47.392) são
realizado/outorgado; não há projeção de investimento.

**Receita testada** (30 linhas):

```sql
por_ano("epe_pde2035_transmissao_investimento_cenario", 4, "Figura 4-19", "A6:D40", "cenario",
        "investimento_acumulado_brl_bilhoes", " (R$ bilhões)")
```

```
(2026, 'Otimista', 23.74)
(2026, 'Pessimista', 22.72)
(2026, 'Referência', 23.03)
(2027, 'Otimista', 42.74)
(2027, 'Pessimista', 37.23)
```

#### `epe_pde2035_transmissao_expansao_fisica`

Expansão física acumulada: km de linha e MVA de transformação, por nível de tensão.

**Duas abas empilhadas**, ambas com cabeçalho L6 e dados L7:L16:

| Aba | Título (L3) | Cabeçalho L6 | `tipo_ativo` |
|---|---|---|---|
| `Figura 4-24` | Cenários de referência: Expansão física de LTs | `Ano \| 230 kV (km) \| 345 kV \| 440 kV \| 500 kV \| 800 kV \| Total (km)` | `LT` |
| `Figura 4-27` | Cenários de referência: expansão física de SEs | `Ano \| 230 kV (MVA) \| 345 kV \| 440 kV \| 500 kV \| 800 kV \| Total (MVA)` | `SE` |

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| (aba de origem) | `tipo_ativo` | VARCHAR (`LT`/`SE`) |
| `Ano` | `ano` | INTEGER |
| nome da coluna | `nivel_tensao` | VARCHAR (`230 kV`…`800 kV`) |
| valor da 4-24 | `extensao_acumulada_km` | DOUBLE |
| valor da 4-27 | `capacidade_acumulada_mva` | DOUBLE |

**Largo → longo**: `UNPIVOT` em cada aba, `UNION ALL` das duas, `Total` descartado pelo nome cru
(`nivel_tensao <> 'Total (km)'` e `<> 'Total (MVA)'` — aqui o filtro usa o rótulo com sufixo, que é o correto, ver a
armadilha em `epe_pde2035_expansao_indicativa`). 10 anos × 5 níveis × 2 tipos = 100 linhas.

**Ressalvas**: **duas colunas de valor, uma sempre NULL** — linha de `LT` tem `extensao_acumulada_km` e
`capacidade_acumulada_mva` NULL, e vice-versa. Foi a alternativa a uma coluna `valor` genérica (as unidades km e MVA
não são intercambiáveis). Acumulado em ambos os casos. É **cenário de referência apenas**. Os totais de 2035
(28.780,87 km e 89.018,32 MVA) **não batem** com a soma obra a obra da fonte 3 (28.307 km e 79.512 MVA no mesmo
recorte) — ver a ressalva em §6, é uma inconsistência da própria EPE.

**No banco**: complementa.

**Receita testada** (100 linhas):

```sql
WITH lt AS (SELECT * FROM x(4, 'Figura 4-24', 'A6:G40') WHERE <filtro de ano>),
     se AS (SELECT * FROM x(4, 'Figura 4-27', 'A6:G40') WHERE <filtro de ano>)
SELECT CAST(ano AS INTEGER) AS ano, 'LT' AS tipo_ativo, replace(nivel_tensao, ' (km)', '') AS nivel_tensao,
       TRY_CAST(valor AS DOUBLE) AS extensao_acumulada_km, NULL::DOUBLE AS capacidade_acumulada_mva
FROM (UNPIVOT (SELECT "Ano" AS ano, * EXCLUDE ("Ano") FROM lt) ON COLUMNS(* EXCLUDE (ano))
      INTO NAME nivel_tensao VALUE valor)
WHERE valor IS NOT NULL AND nivel_tensao <> 'Total (km)'
UNION ALL
SELECT CAST(ano AS INTEGER), 'SE', replace(nivel_tensao, ' (MVA)', ''), NULL::DOUBLE, TRY_CAST(valor AS DOUBLE)
FROM (UNPIVOT (SELECT "Ano" AS ano, * EXCLUDE ("Ano") FROM se) ON COLUMNS(* EXCLUDE (ano))
      INTO NAME nivel_tensao VALUE valor)
WHERE valor IS NOT NULL AND nivel_tensao <> 'Total (MVA)'
ORDER BY ano, tipo_ativo, nivel_tensao
```

```
(2026, 'LT', '230 kV', 1177.69, None)
(2026, 'LT', '345 kV', 110.0, None)
(2026, 'LT', '440 kV', 0.0, None)
(2026, 'LT', '500 kV', 3443.5, None)
(2026, 'LT', '800 kV', 0.0, None)
```

#### `epe_pde2035_transmissao_investimento_recorte`

O investimento do cenário de referência aberto por três recortes: outorga, submercado e nível de tensão.

**Cinco abas empilhadas**, todas com cabeçalho L6:

| Aba | Título (L3) | Dados | `tipo_ativo` | `recorte` |
|---|---|---|---|---|
| `Figura 4-21` | Cenários de referência: LTs e SEs com outorga e sem outorga | L7:L8 | da coluna `Categoria` (LT/SE) | `outorga` |
| `Figura 4-22` | Cenários de referência: LTs por submercado | L7:L10 | `LT` | `submercado` |
| `Figura 4-23` | Cenários de referência: LTs por nível de tensão | L7:L11 | `LT` | `nivel_tensao` |
| `Figura 4-25` | Cenários de referência: SEs por submercado | L7:L10 | `SE` | `submercado` |
| `Figura 4-26` | Cenários de referência: SEs por nível de tensão | L7:L11 | `SE` | `nivel_tensao` |

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| (aba / coluna `Categoria` da 4-21) | `tipo_ativo` | VARCHAR |
| (aba de origem) | `recorte` | VARCHAR |
| `Categoria` ou nome da coluna da 4-21 | `categoria` | VARCHAR |
| `Investimento (R$ bilhões)` / `Total`, `Com Outorga`, `Sem Outorga` | `investimento_brl_bilhoes` | DOUBLE |

**Largo → longo**: a 4-21 é larga (3 colunas de valor) e é despivotada; as outras quatro já são pares
categoria/valor e entram por `UNION ALL`. 6 + 4 + 5 + 4 + 5 = **24 linhas**.

**Ressalvas**

- **Os três recortes se sobrepõem: nunca some a tabela inteira.** Filtre sempre `recorte` e, quando `recorte =
  'outorga'`, ainda `categoria = 'Total'` é o total daquele tipo de ativo (a linha `Total` convive com
  `Com Outorga` + `Sem Outorga`, que somam o mesmo valor).
- Os recortes de submercado usam `Sudeste/Centro-Oeste`, `Nordeste`, `Sul`, `Norte` — grafia diferente da
  `Figura 3-7` (`Sudeste`) e do Anuário (`Sudeste / Centro-Oeste`, com espaços).
- `LT` inclui seccionamento? A aba não diz. A fonte 3, que é a lista obra a obra, separa `LT` de `SECC LT`; somando
  as duas dá 91,35 R$ bi, contra 77,97 aqui. Portanto **este recorte não é reconciliável** com a fonte 3 no nível de
  LT.

**No banco**: complementa.

**Receita testada** (24 linhas):

```sql
WITH outorga AS (SELECT * FROM x(4, 'Figura 4-21', 'A6:D20') WHERE "Categoria" IS NOT NULL)
SELECT "Categoria" AS tipo_ativo, 'outorga' AS recorte, replace(categoria, ' (R$ bilhões)', '') AS categoria,
       TRY_CAST(valor AS DOUBLE) AS investimento_brl_bilhoes
FROM (UNPIVOT outorga ON COLUMNS(* EXCLUDE ("Categoria")) INTO NAME categoria VALUE valor) WHERE valor IS NOT NULL
UNION ALL SELECT 'LT', 'submercado', "Categoria", TRY_CAST("Investimento (R$ bilhões)" AS DOUBLE)
  FROM x(4, 'Figura 4-22', 'A6:B20') WHERE "Categoria" IS NOT NULL
UNION ALL SELECT 'LT', 'nivel_tensao', "Categoria", TRY_CAST("Investimento (R$ bilhões)" AS DOUBLE)
  FROM x(4, 'Figura 4-23', 'A6:B20') WHERE "Categoria" IS NOT NULL
UNION ALL SELECT 'SE', 'submercado', "Categoria", TRY_CAST("Investimento (R$ bilhões)" AS DOUBLE)
  FROM x(4, 'Figura 4-25', 'A6:B20') WHERE "Categoria" IS NOT NULL
UNION ALL SELECT 'SE', 'nivel_tensao', "Categoria", TRY_CAST("Investimento (R$ bilhões)" AS DOUBLE)
  FROM x(4, 'Figura 4-26', 'A6:B20') WHERE "Categoria" IS NOT NULL
ORDER BY tipo_ativo, recorte, categoria
```

```
('LT', 'nivel_tensao', '230 kV', 10.48)
('LT', 'nivel_tensao', '345 kV', 3.55)
('LT', 'nivel_tensao', '440 kV', 0.31)
('LT', 'nivel_tensao', '500 kV', 59.69)
('LT', 'nivel_tensao', '800 kV', 2.79)
```

#### `epe_pde2035_transmissao_contratos_vincendos`

Cronograma de contratos de concessão de transmissão a vencer e a RAP correspondente.

**Aba** `Figura 4-29` · título L3 `Figura 4-29 | Contratos vincendos: Cronograma das análises de planejamento` ·
fonte L4 `Elaboração EPE.` · cabeçalho L6 `Mês | Quantidade de contratos | RAP Total (R$ milhões)` · dados
**L7:L20** (14 linhas) · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo | Observação |
|---|---|---|---|
| `Mês` | `mes` | DATE | **serial de data do Excel**, sempre dezembro |
| `Quantidade de contratos` | `contratos` | INTEGER | |
| `RAP Total (R$ milhões)` | `rap_brl_milhoes` | DOUBLE | Receita Anual Permitida |

Já é longo. 14 linhas.

**Ressalvas**: o eixo é anual apesar do cabeçalho dizer `Mês` — todos os valores caem em **dezembro** de 2022 a 2035,
e os três primeiros (2022, 2023, 2024) são **passado**, o que torna esta a única tabela do PDE que mistura realizado
com projeção. Os anos 2025 a 2027 têm zero contratos e RAP zero, e são linhas legítimas. Mesma armadilha de serial de
data da `Figura 3-29`. Em **R$ milhões de 2025**.

**No banco**: complementa `transmissao_contratos` (413 linhas, contratos de concessão reais) — ali está o contrato a
contrato, aqui o cronograma agregado que a EPE usa para planejar as reanálises.

**Receita testada** (14 linhas):

```sql
SELECT DATE '1899-12-30' + TRY_CAST("Mês" AS INTEGER) AS mes,
       CAST(TRY_CAST("Quantidade de contratos" AS DOUBLE) AS INTEGER) AS contratos,
       TRY_CAST("RAP Total (R$ milhões)" AS DOUBLE) AS rap_brl_milhoes
FROM x(4, 'Figura 4-29', 'A6:C40') WHERE TRY_CAST("Mês" AS INTEGER) > 20000 ORDER BY mes
```

```
(datetime.date(2022, 12, 1), 1, 0.0)
(datetime.date(2023, 12, 1), 1, 16.224)
(datetime.date(2024, 12, 1), 1, 76.106)
(datetime.date(2025, 12, 1), 0, 0.0)
(datetime.date(2026, 12, 1), 0, 0.0)
```

### 5.4 Capítulo 07 — Gás Natural (só o recorte termelétrico)

Do capítulo 7 recomendo **duas abas das sete**, e só por causa da coluna `Demanda Termelétrica Máxima`: é ela que
liga a expansão das UTEs a gás do capítulo 03 à infraestrutura de gás. As outras cinco abas são balanço de oferta de
gás e preço de citygate, que não servem à plataforma (§8).

#### `epe_pde2035_demanda_gas_natural`

**Duas abas empilhadas**, cabeçalho idêntico (7 colunas) em L6, dados L7:L17 (2025-2035):

| Aba | Título (L3) | `abrangencia` |
|---|---|---|
| `Figura 7-5` | Demanda total na malha integrada (milhões m³/d) | `malha integrada` |
| `Figura 7-6` | Demanda total de gás natural no Brasil (milhões m³/d) | `Brasil` |

A fonte em L4 é `Elaboração EPE` — **sem ponto final**, ao contrário de quase todas as outras abas (`Elaboração EPE.`).

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| (aba de origem) | `abrangencia` | VARCHAR |
| `Ano` | `ano` | INTEGER |
| `Demanda Industrial, Residencial, Comercial e de Transporte (milhão m³/d)` | `demanda_nao_termica_milhoes_m3_dia` | DOUBLE |
| `Demanda Termelétrica Máxima (milhão m³/d)` | `demanda_termeletrica_maxima_milhoes_m3_dia` | DOUBLE |
| `Demanda de Refinarias e FAFENs (milhão m³/d)` | `demanda_refino_milhoes_m3_dia` | DOUBLE |
| `Gás de Uso do Sistema (milhão m³/d)` | `gas_uso_sistema_milhoes_m3_dia` | DOUBLE |
| `Demanda Total Média (milhão m³/d)` | `demanda_total_media_milhoes_m3_dia` | DOUBLE |
| `Demanda Total Máxima (milhão m³/d)` | `demanda_total_maxima_milhoes_m3_dia` | DOUBLE |

**Não despivotei**: as seis colunas são componentes diferentes de um balanço, duas delas totais (média e máxima), e a
consulta natural é a linha inteira do ano. Mantive larga com a unidade em cada nome; o único despivotamento é o
`UNION ALL` das duas abrangências. 11 × 2 = 22 linhas.

**Ressalvas**

- **A termelétrica é demanda MÁXIMA, as outras são médias.** Por isso `demanda_total_media` (66 em 2025) é menor que
  `demanda_termeletrica_maxima` + as demais, e `demanda_total_maxima` (119) é outra conta. Não some as colunas.
- A diferença entre `Brasil` e `malha integrada` é a demanda fora da malha de gasodutos integrada (térmicas
  isoladas e usos locais): em 2025 a térmica máxima é 65 no Brasil e 22 na malha integrada.
- Unidade **milhões de m³/dia**, e os números são inteiros na planilha (arredondados pela EPE) — não use para
  diferença ano a ano de precisão fina.
- Sobre o critério de escolha: **não mapeei o resto do capítulo 7 nem os capítulos 05, 06 e 08** porque são a cadeia
  de petróleo, derivados e biocombustíveis. Esta tabela entra só como insumo da análise de térmicas a gás.

**No banco**: complementa; não há nada de gás natural no banco.

**Receita testada** (22 linhas):

```sql
WITH mi AS (SELECT 'malha integrada' AS abrangencia, * FROM x(7, 'Figura 7-5', 'A6:G40') WHERE <filtro de ano>),
     br AS (SELECT 'Brasil' AS abrangencia, * FROM x(7, 'Figura 7-6', 'A6:G40') WHERE <filtro de ano>),
     u AS (SELECT * FROM mi UNION ALL SELECT * FROM br)
SELECT abrangencia, CAST("Ano" AS INTEGER) AS ano,
       TRY_CAST("Demanda Industrial, Residencial, Comercial e de Transporte (milhão m³/d)" AS DOUBLE)
         AS demanda_nao_termica_milhoes_m3_dia,
       TRY_CAST("Demanda Termelétrica Máxima (milhão m³/d)" AS DOUBLE) AS demanda_termeletrica_maxima_milhoes_m3_dia,
       TRY_CAST("Demanda de Refinarias e FAFENs (milhão m³/d)" AS DOUBLE) AS demanda_refino_milhoes_m3_dia,
       TRY_CAST("Gás de Uso do Sistema (milhão m³/d)" AS DOUBLE) AS gas_uso_sistema_milhoes_m3_dia,
       TRY_CAST("Demanda Total Média (milhão m³/d)" AS DOUBLE) AS demanda_total_media_milhoes_m3_dia,
       TRY_CAST("Demanda Total Máxima (milhão m³/d)" AS DOUBLE) AS demanda_total_maxima_milhoes_m3_dia
FROM u ORDER BY abrangencia, ano
```

```
('Brasil', 2025, 40.0, 65.0, 12.0, 2.0, 66.0, 119.0)
('Brasil', 2026, 42.0, 81.0, 15.0, 2.0, 69.0, 140.0)
('Brasil', 2027, 43.0, 89.0, 15.0, 2.0, 73.0, 150.0)
('Brasil', 2028, 47.0, 96.0, 17.0, 2.0, 84.0, 162.0)
('Brasil', 2029, 48.0, 108.0, 18.0, 2.0, 94.0, 177.0)
```

### 5.5 Capítulo 09 — Eficiência Energética e Recursos Energéticos Distribuídos

#### `epe_pde2035_red_demanda_eletricidade`

A "escada" do RED: quanto do consumo potencial é abatido por eficiência, autoprodução e MMGD antes de chegar à rede.

**Aba** `Figura 9-1` · título L3 `Figura 9-1 | Contribuição do RED na demanda de eletricidade ` (com espaço final) ·
fonte L4 `Elaboração EPE` · cabeçalho L6 · dados **L7:L17** · **rodapé L18 vazia, L19 `Notas:`, L20 a L23** com 4
notas (dimensão `A1:E23`) — 6 linhas a descartar.

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `Ano` | `ano` | INTEGER |
| `Consumo Potencial (TWh)` | `consumo_potencial_twh` | DOUBLE |
| `Consumo menos EE (TWh)` | `consumo_menos_ee_twh` | DOUBLE |
| `Consumo menos EE e AP (TWh)` | `consumo_menos_ee_ap_twh` | DOUBLE |
| `Consumo menos EE, AP e MMGD (TWh)` | `consumo_rede_twh` | DOUBLE |

**Não despivotei**: as quatro colunas são estágios cumulativos de subtração, e a leitura é sempre a linha inteira.
Renomeei a última para `consumo_rede_twh` porque é ela o consumo que chega à rede — o nome original é uma fórmula.
11 linhas.

**Ressalvas** (as quatro notas do rodapé são a definição oficial e precisam ir para o campo `ressalvas`)

- `(1)` a energia solar térmica de aquecimento solar já está no consumo final, conforme o BEN 2024;
  `(2)` EE = eficiência elétrica; `(3)` AP = autoprodução não injetada na rede;
  `(4)` MMGD = micro e minigeração distribuída (injetada + não injetada).
- **As colunas são cumulativas, não componentes.** O abatimento de MMGD em 2035 é
  `consumo_menos_ee_ap_twh − consumo_rede_twh` = 818,29 − 712,18 = 106,11 TWh; o abatimento total é
  964,05 − 712,18 = 251,87 TWh. Somar as quatro colunas não significa nada.
- `consumo_rede_twh` (712,18 TWh em 2035) é a série que se compara conceitualmente com a soma do Anuário
  (566,75 milhões de MWh = 566,75 TWh em 2025 realizado), **mas com cuidado**: o Anuário é consumo faturado por
  distribuidora e consumidor livre, e aqui há 553,17 TWh para 2025. A diferença de ~13 TWh é de perímetro
  (autoprodução injetada e ajustes), não de erro.

**No banco**: complementa. Não existe visão de recursos energéticos distribuídos agregada.

**Receita testada** (11 linhas):

```sql
SELECT CAST("Ano" AS INTEGER) AS ano, TRY_CAST("Consumo Potencial (TWh)" AS DOUBLE) AS consumo_potencial_twh,
       TRY_CAST("Consumo menos EE (TWh)" AS DOUBLE) AS consumo_menos_ee_twh,
       TRY_CAST("Consumo menos EE e AP (TWh)" AS DOUBLE) AS consumo_menos_ee_ap_twh,
       TRY_CAST("Consumo menos EE, AP e MMGD (TWh)" AS DOUBLE) AS consumo_rede_twh
FROM x(9, 'Figura 9-1', 'A6:E40') WHERE TRY_CAST("Ano" AS INTEGER) BETWEEN 1990 AND 2100 ORDER BY ano
```

```
(2025, 686.0057363363954, 686.0057363363954, 607.0708614200057, 553.1711061227323)
(2026, 718.0244322107573, 709.791474865532, 626.5185620351044, 566.4534138234792)
(2027, 741.6061646773379, 729.8473533857331, 644.9892660425407, 579.4331379464928)
(2028, 766.7758328256515, 751.1223537365994, 664.061794422213, 593.0888649833576)
(2029, 793.5367873690843, 773.5965119842633, 682.8902710344497, 606.7685656655275)
```

#### `epe_pde2035_mmgd_capacidade_cenario`

Capacidade instalada de MMGD por cenário, **série histórica e projetada na mesma coluna**.

**Aba** `Figura 9-18` · título L3 `Figura 9-18 | Capacidade instalada de MMGD por cenário` · fonte L4
`Elaboração EPE.` · cabeçalho L6 `Ano | Cenário inferior (GW) | Cenário de referência (GW) | Cenário superior (GW)` ·
dados **L7:L29** (2013 a 2035, 23 anos) · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo | Observação |
|---|---|---|---|
| `Ano` | `ano` | INTEGER | 2013 a 2035 |
| `Cenário inferior/de referência/superior (GW)` | `cenario` | VARCHAR | normalizado para `inferior`/`referência`/`superior` |
| (valor) | `potencia_acumulada_gw` | DOUBLE | acumulado |

**Largo → longo**: `UNPIVOT` dos três cenários. Normalizei o rótulo com
`replace(replace(replace(lower(cenario), 'cenário ', ''), 'de ', ''), ' (gw)', '')`, o que deixa `referência` em
minúscula e com acento. 23 × 3 = 69 linhas.

**Ressalvas**

- **Mistura realizado e projetado sem coluna que os separe.** De 2013 a 2025 os três cenários têm valores
  **idênticos** (é o histórico da ANEEL); a partir de 2026 divergem. O teste para separar é justamente
  `count(DISTINCT potencia_acumulada_gw) = 1` no ano. Um analista que citar "capacidade de MMGD em 2020 segundo o
  cenário superior" está citando histórico.
- Acumulado, em GW. O cenário de referência chega a 78,10 GW em 2035, contra 61,35 (inferior) e 97,80 (superior).
- O rótulo `referência` fica com acento e minúscula; se a convenção do banco exigir `referencia` sem acento, é uma
  decisão a tomar na implementação — não a antecipei porque as outras tabelas preservam o rótulo da EPE
  (`Cenário Referência`).

**No banco**: **sobrepõe-se** a `gd_mmgd` (66.826 linhas) no trecho histórico. A série anual agregada do PDE é
derivável da base ANEEL; o valor está na projeção.

**Receita testada** (69 linhas):

```sql
WITH bruto AS (SELECT * FROM x(9, 'Figura 9-18', 'A6:D60') WHERE TRY_CAST("Ano" AS INTEGER) BETWEEN 1990 AND 2100)
SELECT CAST(ano AS INTEGER) AS ano,
       replace(replace(replace(lower(cenario), 'cenário ', ''), 'de ', ''), ' (gw)', '') AS cenario,
       TRY_CAST(valor AS DOUBLE) AS potencia_acumulada_gw
FROM (UNPIVOT (SELECT "Ano" AS ano, * EXCLUDE ("Ano") FROM bruto) ON COLUMNS(* EXCLUDE (ano))
      INTO NAME cenario VALUE valor)
WHERE valor IS NOT NULL ORDER BY ano, cenario
```

```
(2013, 'inferior', 0.00351329999935627)
(2013, 'referência', 0.00351329999935627)
(2013, 'superior', 0.00351329999935627)
(2014, 'inferior', 0.006522150015592577)
(2014, 'referência', 0.006522150015592577)
```

#### `epe_pde2035_mmgd_uf_2035`

Capacidade instalada de MMGD projetada para 2035, por UF.

**Aba** `Figura 9-19` · título L3 `Figura 9-19 | Projeção da capacidade instalada de MMGD em 2035 por UF (GW)` ·
fonte L4 `Elaboração EPE.` · cabeçalho L6 `UF | Potência (GW)` · dados **L7:L33** (27 UFs, ordenadas por potência
decrescente) · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `UF` | `uf` | VARCHAR (sigla de 2 letras) |
| `Potência (GW)` | `potencia_gw` | DOUBLE |

Já é longo. 27 linhas. O filtro `length("UF") = 2` é o que corta cabeçalho e eventual rodapé.

**Ressalvas**: **um único ano (2035) e um único cenário (referência)** — não é série. A soma das 27 UFs é a
capacidade de 2035 do cenário de referência de `epe_pde2035_mmgd_capacidade_cenario` (78,10 GW); é a única abertura
geográfica de MMGD projetada em todo o PDE. Sem `ano` como coluna: o ano está fixo no nome da tabela, decisão
deliberada para não criar uma coluna constante (ver §9).

**No banco**: complementa. `gd_mmgd` tem UF no realizado; aqui está a projeção.

**Receita testada** (27 linhas):

```sql
SELECT "UF" AS uf, TRY_CAST("Potência (GW)" AS DOUBLE) AS potencia_gw
FROM x(9, 'Figura 9-19', 'A6:B60') WHERE length("UF") = 2 ORDER BY potencia_gw DESC
```

```
('SP', 15.705525758073321)
('MG', 8.126339818463585)
('RJ', 6.168310012937775)
('RS', 5.537666652534608)
('PR', 5.273141191513219)
```

#### `epe_pde2035_mmgd_resumo_cenario`

Resumo dos três cenários de MMGD: adotantes, potência, geração e investimento.

**Aba** `Tabela 9-3` · título L3 `Tabela 9-3 | Resumo dos resultados de projeção para a MMGD` · fonte L4
`Elaboração EPE.` · cabeçalho L6 · dados **L7:L9** (3 cenários) · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `Cenário` | `cenario` | VARCHAR (`Superior`, `Referência`, `Inferior`) |
| `Adotantes (2013-2035) (milhões)` | `adotantes_milhoes` | DOUBLE |
| `Potência (2013-2035) (GW)` | `potencia_gw` | DOUBLE |
| `Geração (2035) (GWméd)` | `geracao_gwmed` | DOUBLE |
| `Investimentos (2025 a 2035) (R$ bilhões)` | `investimento_brl_bilhoes` | DOUBLE |

Não despivotei: 4 grandezas diferentes, 3 linhas. É a tabela-resumo do capítulo.

**Ressalvas**: **cada coluna tem período próprio, declarado no cabeçalho** — adotantes e potência são acumulados
2013-2035, geração é só 2035, investimento é 2025-2035. Não trate a linha como um ano. Os valores vêm com **uma casa
decimal** (12,1 / 97,8 / 15,2 / 155,9), arredondados pela EPE: `potencia_gw` aqui (78,1 no referência) é o mesmo
número que `epe_pde2035_mmgd_capacidade_cenario` traz com precisão cheia (78,09943).

**No banco**: complementa.

**Receita testada** (3 linhas):

```sql
SELECT "Cenário" AS cenario, TRY_CAST("Adotantes (2013-2035) (milhões)" AS DOUBLE) AS adotantes_milhoes,
       TRY_CAST("Potência (2013-2035) (GW)" AS DOUBLE) AS potencia_gw,
       TRY_CAST("Geração (2035) (GWméd)" AS DOUBLE) AS geracao_gwmed,
       TRY_CAST("Investimentos (2025 a 2035) (R$ bilhões)" AS DOUBLE) AS investimento_brl_bilhoes
FROM x(9, 'Tabela 9-3', 'A6:E20') WHERE "Cenário" IS NOT NULL
```

```
('Superior', 12.1, 97.8, 15.2, 155.9)
('Referência', 9.5, 78.1, 12.1, 105.7)
('Inferior', 7.5, 61.4, 9.4, 62.8)
```

#### `epe_pde2035_mmgd_segmento`

Capacidade de MMGD do cenário de referência por segmento de adotante.

**Aba** `Figura 9-20` · título L3
`Figura 9-20 | Distribuição da capacidade instalada no Cenário Referência por segmento em 2035` · fonte L4
`Elaboração EPE.` · cabeçalho L6 (6 colunas) · dados **L7:L17** (2025-2035) · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `Ano` | `ano` | INTEGER |
| `Comercial (AT) (GW)`, `Comercial (BT) (GW)`, `Comercial Remoto (AT/BT) (GW)`, `Residencial (GW)`, `Residencial Remoto (GW)` | `segmento` | VARCHAR |
| (valor) | `potencia_acumulada_gw` | DOUBLE |

**Largo → longo**: `UNPIVOT` dos 5 segmentos, sufixo `' (GW)'` removido. 11 × 5 = 55 linhas.

**Ressalvas**: o título diz "em 2035" mas a aba traz **a série 2025-2035 inteira** — o gráfico do relatório é só de
2035. Os rótulos guardam o nível de tensão entre parênteses (`(AT)`, `(BT)`, `(AT/BT)`), que sobrevive ao `replace`
porque só o sufixo `' (GW)'` é removido. "Remoto" é autoconsumo remoto/geração compartilhada. A soma dos 5 segmentos
em 2035 (78,10 GW) fecha com o cenário de referência das outras duas tabelas de MMGD.

**No banco**: complementa.

**Receita testada** (55 linhas):

```sql
por_ano("epe_pde2035_mmgd_segmento", 9, "Figura 9-20", "A6:F40", "segmento", "potencia_acumulada_gw", " (GW)")
```

```
(2025, 'Comercial (AT)', 5.795062856716294)
(2025, 'Comercial (BT)', 12.04515852702349)
(2025, 'Comercial Remoto (AT/BT)', 2.824987575959002)
(2025, 'Residencial', 15.3057887304802)
(2025, 'Residencial Remoto', 4.053296606293078)
```

#### `epe_pde2035_autoproducao_nao_injetada`

Autoprodução de eletricidade de grande porte que não é injetada na rede.

**Aba** `Figura 9-39` · título L3
`Figura 9-39 | Autoprodução de eletricidade de grande porte não injetada na rede (TWh)` · fonte L4 `EPE` (sem
"Elaboração") · cabeçalho L6 `Ano | Grandes Consumidores (TWh) | Outros (TWh)` · dados **L7:L9** (2025, 2030, 2035) ·
**rodapé L10 vazia, L11 `Notas:`, L12 e L13** com as 2 notas (dimensão `A1:C15`, L14-L15 vazias).

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `Ano` | `ano` | INTEGER |
| `Grandes Consumidores (TWh)`, `Outros (TWh)` | `segmento` | VARCHAR |
| (valor) | `energia_twh` | DOUBLE |

**Largo → longo**: `UNPIVOT` dos 2 segmentos. 3 × 2 = 6 linhas.

**Ressalvas** (as duas notas do rodapé são definição e vão para `ressalvas`)

- `(1) Grandes consumidores concentra os segmentos de siderurgia, petroquímica e papel e celulose.`
- `(2) Outros não incluem MMGD.` — portanto **esta série e a de MMGD são somáveis** sem dupla contagem, e juntas
  explicam o degrau `consumo_menos_ee_twh → consumo_rede_twh` de `epe_pde2035_red_demanda_eletricidade`.
- Só **três anos de corte** (2025, 2030, 2035), não série anual. Em `Outros`, 2035 (57,12 TWh) é **menor** que 2030
  (61,87): a série não é monótona, não extrapole.

**No banco**: complementa. Autoprodução não injetada não aparece em nenhuma base da ANEEL ou do ONS no banco.

**Receita testada** (6 linhas):

```sql
por_ano("epe_pde2035_autoproducao_nao_injetada", 9, "Figura 9-39", "A6:C20", "segmento", "energia_twh", " (TWh)")
```

```
(2025, 'Grandes Consumidores', 26.11558201758036)
(2025, 'Outros', 52.81929289880935)
(2030, 'Grandes Consumidores', 30.80084443204958)
(2030, 'Outros', 61.870676184523354)
(2035, 'Grandes Consumidores', 35.236949137038366)
```

### 5.6 Capítulo 10 — Análise Socioambiental

#### `epe_pde2035_emissoes_setor`

Emissões de GEE pela produção e uso de energia, por setor.

**Aba** `Figura 10-1` · título L3
`Figura 10-1 | Evolução da participação setorial nas emissões de GEE pela produção e uso de energia (MtCO2eq)` ·
fonte L4 `Elaboração EPE.` · cabeçalho L6 (11 colunas) · dados **L7:L10** (2005, 2025, 2030, 2035) · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `Ano` | `ano` | INTEGER |
| `Transportes`, `Industrial`, `Setor elétrico`, `Setor Energético`, `Agropecuário`, `Residencial`, `Emissões Fugitivas`, `Comercial`, `Público` (todas com sufixo ` (MtCO2eq)`) | `setor` | VARCHAR |
| (valor) | `emissao_mtco2eq` | DOUBLE |

**Largo → longo**: `UNPIVOT` dos 9 setores, sufixo `' (MtCO2eq)'` removido, `Total (MtCO2eq)` descartado **com o
filtro corrigido** (`replace(setor, ' (MtCO2eq)', '') NOT IN ('Total')` — sem isso a linha de total passa e a tabela
vem com 40 linhas e 10 categorias). 4 × 9 = 36 linhas. Conferi que a soma dos 9 setores reproduz exatamente a coluna
`Total` nos 4 anos: 316,28506 (2005), 438,428786 (2025), 487,793732 (2030), 515,846908 (2035).

**Ressalvas**

- **`2005` é o ano-base da NDC brasileira**, não uma observação do plano: a tabela compara 2005 com 2025 e projeta
  2030 e 2035. São **4 anos de corte**, não uma série.
- O `Setor elétrico` aqui (26,674 → 40,771 → 58,550 → 62,472 MtCO2eq) **inclui autoprodução e sistemas isolados** —
  a abertura está na `Figura 10-2`/`epe_pde2035_emissoes_eletricidade_recorte`, onde `SIN` (13,33 em 2025) e
  `Autoprodução` (25,24) e `Sistemas Isolados` (2,20) aparecem separados e somam 40,77. Portanto as duas tabelas
  **não** podem ser unidas na mesma coluna `setor`: uma tem `Setor elétrico` agregado, a outra o abre.
- A grafia é inconsistente na própria planilha: `Setor elétrico` (minúscula) e `Setor Energético` (maiúscula).
  Preservei.
- Unidade MtCO2**eq** (equivalente), não MtCO2. Por isso a coluna é `emissao_mtco2eq` e não `emissao_mtco2`.

**No banco**: **complementa e é inédito** — não existe nenhuma tabela de emissões no banco. Foi o que motivou
incluir o capítulo 10 apesar de não ser "setor elétrico" em sentido estrito.

**Receita testada** (36 linhas):

```sql
por_ano("epe_pde2035_emissoes_setor", 10, "Figura 10-1", "A6:K20", "setor", "emissao_mtco2eq",
        " (MtCO2eq)", excluir="'Total'")
```

```
(2005, 'Agropecuário', 15.71)
(2005, 'Comercial', 2.0004)
(2005, 'Emissões Fugitivas', 19.70701)
(2005, 'Industrial', 61.52)
(2005, 'Público', 1.7472999999999999)
```

#### `epe_pde2035_emissoes_eletricidade_recorte`

A mesma contabilidade de emissões, mas com o setor elétrico aberto em SIN, autoprodução e sistemas isolados.

**Aba** `Figura 10-2` · título L3
`Figura 10-2 | Evolução das emissões absolutas em cada setor entre 2025 e 2035 e respectivas variações percentuais no decênio`
· fonte L4 `Elaboração EPE.` · cabeçalho L6 (12 colunas) · dados **L7:L8** (2025 e 2035) · sem rodapé · sem coluna de
total.

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `Ano` | `ano` | INTEGER |
| `Transportes`, `Industrial`, `Autoprodução`, `Setor Energético`, `Agropecuário`, `SIN`, `Residencial`, `Emissões Fugitivas`, `Comercial`, `Sistemas Isolados`, `Público` (sufixo ` (MtCO2eq)`) | `segmento` | VARCHAR |
| (valor) | `emissao_mtco2eq` | DOUBLE |

**Largo → longo**: `UNPIVOT` dos 11 segmentos. 2 × 11 = 22 linhas.

**Ressalvas**: **só 2025 e 2035.** O título promete "variações percentuais no decênio", mas a variação **não está na
aba** — é calculada no gráfico; quem quiser, calcula de 2025 para 2035. `SIN` + `Autoprodução` +
`Sistemas Isolados` = `Setor elétrico` da `Figura 10-1` (13,32792 + 25,243132 + 2,199497 = 40,770549 em 2025, igual
ao valor lá). Chamei a coluna de `segmento` e não de `setor` justamente para impedir um `UNION` descuidado com a
tabela anterior.

**No banco**: complementa; inédito.

**Receita testada** (22 linhas):

```sql
por_ano("epe_pde2035_emissoes_eletricidade_recorte", 10, "Figura 10-2", "A6:L20", "segmento",
        "emissao_mtco2eq", " (MtCO2eq)")
```

```
(2025, 'Agropecuário', 22.5475151170153)
(2025, 'Autoprodução', 25.2431319506397)
(2025, 'Comercial', 2.2270916120165)
(2025, 'Emissões Fugitivas', 18.6677933687157)
(2025, 'Industrial', 85.6228733524552)
```

### 5.7 Capítulo 11 — Transição Energética

#### `epe_pde2035_minerais_criticos`

Composição mineral da capacidade instalada de geração — a demanda de minerais críticos embutida na expansão.

**Aba** `Figura 11-7` · título L3
`Figura 11-7 | Composição mineral da capacidade instalada para geração de energia elétrica no Brasil (kt)` · fonte L4
`Elaboração EPE` · cabeçalho L6 (10 colunas) · dados **L7:L8** (2025 e 2035) · sem rodapé.

| Coluna na planilha | Coluna proposta | Tipo |
|---|---|---|
| `Ano` | `ano` | INTEGER |
| `Cobre`, `Silício`, `Zinco`, `Manganês`, `Níquel`, `Cromo`, `Grafite`, `Terras Raras`, `Outros` (sufixo ` (mil t)`) | `mineral` | VARCHAR |
| (valor) | `massa_mil_t` | DOUBLE |

**Largo → longo**: `UNPIVOT` dos 9 minerais. 2 × 9 = 18 linhas.

**Ressalvas**: **só 2025 e 2035**, e é **estoque embutido no parque instalado**, não consumo anual de mineral nem
produção mineral brasileira. `Grafite` é **0,0 em 2025** e 17,61 mil t em 2035 — o zero é real (não há baterias de
grafite no parque de 2025) e não deve ser lido como dado faltante. O título diz `kt`, o cabeçalho diz `mil t`: é a
mesma unidade, e adotei a do cabeçalho no nome da coluna. `Terras Raras` e `Outros` são agregados.

**No banco**: complementa; inédito. Foi a única aba das três do capítulo 11 que recomendei (§8).

**Receita testada** (18 linhas):

```sql
por_ano("epe_pde2035_minerais_criticos", 11, "Figura 11-7", "A6:J20", "mineral", "massa_mil_t", " (mil t)")
```

```
(2025, 'Cobre', 454.7789293)
(2025, 'Cromo', 22.42420623)
(2025, 'Grafite', 0.0)
(2025, 'Manganês', 50.98469711)
(2025, 'Níquel', 23.06739912)
```

### 5.8 Capítulo 12 — Consolidação dos Resultados

As três abas deste capítulo são as únicas de todo o PDE com **cabeçalho de dois níveis, hierarquia de linhas e
totais embutidos**. São também as mais valiosas: fecham os números do plano. Cada uma exige um tratamento próprio,
descrito abaixo.

#### `epe_pde2035_geracao_eletricidade_fonte`

Geração total de eletricidade por fonte em 2025, 2030 e 2035, separando geração centralizada de autoprodução e GD.

**Aba** `Tabela 12-3` · título L3 `Tabela 12-3 | Geração total de eletricidade` · fonte L4 `Elaboração EPE.` ·
dimensão `A1:I33`.

**Estrutura de linhas, lida célula a célula:**

| Linha | Conteúdo |
|---|---|
| L6 | 1º nível do cabeçalho: `(vazio) \| 2025 \| 2025 \| 2030 \| 2030 \| 2035 \| 2035` |
| L7 | 2º nível: `(vazio) \| TWh \| % \| TWh \| % \| TWh \| %` |
| L8 | linha de seção: só a coluna A preenchida, `Geração Centralizada` |
| L9:L16 | 8 fontes centralizadas |
| L17 | `Subtotal (geração centralizada)` |
| L18 | linha de seção `Autoprodução & Geração Distribuída` |
| L19:L23 | 5 fontes |
| L24 | `Subtotal (autoprodução & GD)` |
| L25 | `' Total'` (**com espaço à esquerda**) |
| L26 | vazia |
| L27 | `Notas:` |
| L28:L31 | 4 notas |

**Cabeçalho de dois níveis, sem mescla**: L6 repete o ano em duas colunas adjacentes e L7 diz se é TWh ou %. Como não
há células mescladas (conferi: a aba não aparece no inventário de mesclas), `header=true` produziria nomes duplicados.
**Leia com `header=false` e range `A8:G25`** — pulando as duas linhas de cabeçalho — e nomeie as colunas na mão
(`A`..`G`).

| Origem | Coluna proposta | Tipo | Como se obtém |
|---|---|---|---|
| linha de seção mais próxima acima | `segmento` | VARCHAR | `last_value(... IGNORE NULLS) OVER (ORDER BY i)` sobre as linhas em que A está preenchida e B está vazia |
| coluna A | `fonte` | VARCHAR | `trim("A")` — o `trim` é obrigatório por causa do `' Total'` |
| — | `tipo_linha` | VARCHAR | `item` / `subtotal` / `total`, derivado do rótulo |
| L6 | `ano` | INTEGER | 2025 / 2030 / 2035, vindo do `UNION ALL` de três blocos |
| colunas B, D, F | `geracao_twh` | DOUBLE | |
| colunas C, E, G | `participacao_pct` | DOUBLE | valor **fracionário** na planilha; multipliquei por 100 |

16 linhas × 3 anos = **48 linhas**.

**Ressalvas**

- **`tipo_linha` existe para você poder somar sem contar duas vezes.** Use sempre `WHERE tipo_linha = 'item'` para
  agregar. Conferi que fecha: os 13 itens somam 810,623 TWh (2025), 962,874 (2030) e 1.122,135 TWh (2035) — os mesmos
  valores das linhas `Total`, e as participações somam 100,00 % nos três anos.
- A linha `Total` tem `segmento` NULL de propósito (não pertence a nenhum dos dois segmentos).
- As 4 notas são definições de escopo e precisam ir para `ressalvas`:
  `(1) Hidráulica inclui parcela importada de Itaipu.` · `(2) Biomassa inclui biodiesel.` ·
  `(3) Outros incluem Óleo Combustível, Óleo Diesel, Gás de Processo, Sistemas Isolados, RSU.` ·
  `(4) Outras Renováveis incluem gás natural, carvão e derivados, derivados de petróleo, gás de alto forno coque
  carvão, gás de aciaria e gás de enxofre e outros.` (a nota 4 fala de um rótulo que **não existe** nesta aba — é
  reaproveitada de outra tabela do relatório; registre como está, mas não a interprete como escopo de `Outros`).
- Os rótulos das fontes **não são os mesmos** de `epe_pde2035_capacidade_instalada_fonte` (lá `UHE`, `EOLICA`, `PCT`;
  aqui `Hidráulica`, `Eólica`, `Gás Natural`). Não faça `JOIN` por nome de fonte entre as duas sem uma tabela de
  correspondência feita à mão.
- **Só três anos de corte.** Não é série anual.

**No banco**: complementa. `ons_geracao_fonte_mensal` (585 linhas) é realizado e mensal, em outra taxonomia.

**Receita testada** (48 linhas) — a íntegra está em `05_receitas_finais.py`; o miolo:

```sql
WITH bruto AS (SELECT row_number() OVER () AS i, * FROM x(12, 'Tabela 12-3', 'A8:G25', header='false')),
secao AS (SELECT *, last_value(CASE WHEN "A" IS NOT NULL AND "B" IS NULL THEN "A" END IGNORE NULLS)
                      OVER (ORDER BY i) AS segmento FROM bruto),
dados AS (SELECT i, CASE WHEN trim("A") = 'Total' THEN NULL ELSE segmento END AS segmento, trim("A") AS fonte,
                 CASE WHEN trim("A") = 'Total' THEN 'total'
                      WHEN trim("A") LIKE 'Subtotal%' THEN 'subtotal' ELSE 'item' END AS tipo_linha,
                 "B" AS t2025, "C" AS p2025, "D" AS t2030, "E" AS p2030, "F" AS t2035, "G" AS p2035
          FROM secao WHERE "A" IS NOT NULL AND "B" IS NOT NULL)
SELECT segmento, fonte, tipo_linha, 2025 AS ano, TRY_CAST(t2025 AS DOUBLE) AS geracao_twh,
       round(TRY_CAST(p2025 AS DOUBLE) * 100, 4) AS participacao_pct FROM dados
UNION ALL SELECT segmento, fonte, tipo_linha, 2030, TRY_CAST(t2030 AS DOUBLE), round(TRY_CAST(p2030 AS DOUBLE)*100,4) FROM dados
UNION ALL SELECT segmento, fonte, tipo_linha, 2035, TRY_CAST(t2035 AS DOUBLE), round(TRY_CAST(p2035 AS DOUBLE)*100,4) FROM dados
ORDER BY ano, segmento NULLS LAST, tipo_linha, fonte
```

```
('Autoprodução & Geração Distribuída', 'Biomassa (biogás, bagaço de cana, lixívia e lenha)', 'item', 2025, 36.56298789885568, 4.5105)
('Autoprodução & Geração Distribuída', 'Eólica', 'item', 2025, 0.08776440456347079, 0.0108)
('Autoprodução & Geração Distribuída', 'Hidráulica', 'item', 2025, 5.795424480166379, 0.7149)
('Autoprodução & Geração Distribuída', 'Não renováveis', 'item', 2025, 35.85003494376163, 4.4225)
('Autoprodução & Geração Distribuída', 'Solar', 'item', 2025, 52.26791471547386, 6.4479)
```

#### `epe_pde2035_investimentos`

Investimento previsto no decênio 2025-2035 em toda a cadeia de energia, em árvore de três níveis.

**Aba** `Tabela 12-10` · título L3 `Tabela 12-10 | Síntese das estimativas de investimentos` · fonte L4
`Elaboração EPE.` · dimensão `A1:F48` · cabeçalho **L6** `(vazio) | R$ bilhões Período 2025-2035 | %` · dados
**L7:L37** · L38 vazia · L39 `Notas:` · **L40:L48 as 9 notas**.

**A hierarquia está na indentação da coluna A**, não em colunas separadas. Medi a largura exata em espaços
(`length("A") - length(ltrim("A"))`) e ela é discreta: **0** para os 3 grandes grupos, **7** para os subgrupos, **≥10**
para os itens folha. A linha L37 é `'\xa0TOTAL'` — indentada com um **espaço inquebrável (NBSP, U+00A0)**, não com
espaço comum; por isso ela cai no `ELSE` da minha classificação e recebe `nivel = 3`, que uso como marca do total
geral.

| Origem | Coluna proposta | Tipo |
|---|---|---|
| nível 0 mais próximo acima | `grupo` | VARCHAR (NULL na linha de total) |
| nível 1 mais próximo acima | `subgrupo` | VARCHAR (preenchido só quando `nivel = 2`) |
| coluna A sem indentação | `item` | VARCHAR |
| largura da indentação | `nivel` | INTEGER (0, 1, 2 ou 3=total) |
| `R$ bilhões Período 2025-2035` | `investimento_brl_bilhoes` | DOUBLE |
| `%` | `participacao_pct` | DOUBLE (fracionário na planilha, × 100) |

**31 linhas** (3 de nível 0, 11 de nível 1, 16 de nível 2, 1 total).

**Ressalvas**

- **Nunca some a coluna de valor sem filtrar `nivel`.** Os três níveis se contêm: `nivel = 0` já soma 3.529,889
  R$ bi, que é exatamente o `TOTAL` da linha 37; e os itens de `nivel = 2` somam o valor do seu `nivel = 1`
  (conferi em Geração Centralizada: 37,797 + 79,207 + 36,254 + 53,714 + 166,685 = 373,657).
- **Só cerca de 17 % do total é setor elétrico**: `Oferta de Energia Elétrica` 596,246 R$ bi (16,89 %) contra
  `Petróleo e Gás Natural` 2.818,416 (79,79 %) e `Oferta de Biocombustíveis Líquidos` 115,227 (3,26 %). Quem citar
  "R$ 3,5 trilhões de investimento do PDE" está citando quase tudo petróleo.
- Os rótulos **trazem o número da nota entre parênteses** (`Geração Centralizada (1)`,
  `Geração Distribuída (Micro e Minigeração) (2)`, `Transmissão (3)`). Preservei; é o que permite ligar o item à nota.
- **R$ bilhões de 2025**, e a nota 9 traz o câmbio de referência:
  `Taxa de câmbio referencial: R$ 6,10 / US$ (dez/2024)`.
- O item `Transmissão (3)` vale 116,905 R$ bi, **não** os 147,83 do cenário otimista nem os 116,90 do cenário de
  referência de `epe_pde2035_transmissao_investimento_cenario` — bate com o **cenário de referência**, e é assim que
  os dois capítulos se reconciliam.

**No banco**: complementa; inédito.

**Receita testada** (31 linhas):

```sql
WITH bruto AS (SELECT row_number() OVER () AS i, * FROM x(12, 'Tabela 12-10', 'A7:C37', header='false')
               WHERE "A" IS NOT NULL AND "B" IS NOT NULL),
niv AS (SELECT i, trim("A") AS item, "B", "C",
               CASE WHEN length("A") - length(ltrim("A")) = 0 THEN 0
                    WHEN length("A") - length(ltrim("A")) = 7 THEN 1
                    WHEN length("A") - length(ltrim("A")) >= 10 THEN 2 ELSE 3 END AS nivel FROM bruto),
arv AS (SELECT *, last_value(CASE WHEN nivel = 0 THEN item END IGNORE NULLS) OVER (ORDER BY i) AS grupo,
               last_value(CASE WHEN nivel = 1 THEN item END IGNORE NULLS) OVER (ORDER BY i) AS subgrupo FROM niv)
SELECT CASE WHEN nivel = 3 THEN NULL ELSE grupo END AS grupo, CASE WHEN nivel = 2 THEN subgrupo END AS subgrupo,
       item, nivel, TRY_CAST("B" AS DOUBLE) AS investimento_brl_bilhoes,
       round(TRY_CAST("C" AS DOUBLE) * 100, 4) AS participacao_pct
FROM arv ORDER BY i
```

```
('Oferta de Energia Elétrica', None, 'Oferta de Energia Elétrica', 0, 596.2460807146404, 16.8914)
('Oferta de Energia Elétrica', None, 'Geração Centralizada (1)', 1, 373.65724459999996, 10.5855)
('Oferta de Energia Elétrica', 'Geração Centralizada (1)', 'Bateria', 2, 37.79742115788454, 1.0708)
('Oferta de Energia Elétrica', 'Geração Centralizada (1)', 'Eólica', 2, 79.20650213242779, 2.2439)
('Oferta de Energia Elétrica', 'Geração Centralizada (1)', 'Solar Fotovoltaica', 2, 36.254038324196436, 1.0271)
```

#### `epe_pde2035_indicadores`

Os 13 indicadores macro de economia e energia do plano, ano a ano de 2025 a 2035.

**Aba** `Tabela 12-1` · título L3 `Tabela 12-1 | Indicadores: economia e energia` · fonte L4 `Elaboração EPE.` ·
dados **L8:L20** (13 linhas) · sem rodapé.

**Cabeçalho de dois níveis, este com mescla**: L6 traz `(vazio) | (vazio) | 2025 | … | 2035 |
Variação média anual`, e `Variação média anual` está **mesclado em `N6:P6`**; L7 traz, só em N/O/P, os recortes
`2025 a 2030 | 2030 a 2035 | 2025 a 2035`. Por isso leio com `header=false` e range `A8:M20`, que **descarta as três
colunas de variação** (N, O, P).

**O rótulo do indicador está na linha do meio de cada grupo de três**, não na primeira. Lido célula a célula:

```
L8  'População Residente'             | '(106 hab)'
L9   (vazio)                          | '(109 R$)'
L10 'PIB'                             | 'Número indice (2025 = 100)'
L11  (vazio)                          | 'per capita (10³ R$/hab)'
L12  (vazio)                          | '(106 tep)'
L13 'Oferta interna de energia'       | 'por PIB (tep/10³ R$)'
...
L19 'Consumo final energético'        | 'por PIB (tep/10³ R$)'
L20  (vazio)                          | 'per capita (tep/hab)'
```

Isso se resolve com `coalesce("A", lead("A") OVER (ORDER BY i), lag("A") OVER (ORDER BY i))`: para a primeira linha do
grupo o rótulo vem do `lead`, para a terceira vem do `lag`. **Não use forward-fill** (`last_value ... IGNORE NULLS`)
aqui: ele atribuiria `População Residente` à linha do PIB.

| Origem | Coluna proposta | Tipo |
|---|---|---|
| coluna A (com o `coalesce`) | `indicador` | VARCHAR |
| coluna B | `unidade` | VARCHAR |
| nome da coluna C..M | `ano` | INTEGER, via `2025 + (ascii(col) - ascii('C'))` |
| valor | `valor` | DOUBLE |

**Largo → longo**: `UNPIVOT` das 11 colunas de ano. 13 × 11 = **143 linhas**.

**Ressalvas**

- **Esta é uma das três tabelas com coluna `valor` genérica** (ver §9): as 13 séries têm 13 unidades diferentes
  (`(106 hab)`, `(109 R$)`, `Número indice (2025 = 100)`, `(TWh)`, `per capita (kWh/hab)`, `por PIB (tep/10³ R$)`…),
  e a chave é o par **`indicador` + `unidade`**, nunca `indicador` só: `PIB` aparece três vezes, com unidades
  diferentes. Qualquer consulta tem de filtrar os dois.
- As unidades vêm com o expoente em texto corrido: `(106 hab)` significa **10⁶ habitantes** e `(109 R$)` significa
  **10⁹ R$** — a formatação de superscript do Excel se perde na leitura. Registre a unidade como está e documente
  isso no `ressalvas`, senão alguém vai ler "106 habitantes".
- **Descartei as 3 colunas de `Variação média anual`** porque são derivadas e recalculáveis: conferi para
  `População Residente` que `(219,524569 / 213,816494)^(1/10) − 1 = 0,002638`, idêntico ao valor da planilha. Se as
  colunas fossem mantidas, seriam 3 "anos" falsos na coluna `ano`.
- `Oferta interna de eletricidade (TWh)` é 810,62 em 2025 e 1.122,14 em 2035 — os mesmos totais da `Tabela 12-3`.

**No banco**: complementa; inédito.

**Receita testada** (143 linhas):

```sql
WITH bruto AS (SELECT row_number() OVER () AS i, * FROM x(12, 'Tabela 12-1', 'A8:M20', header='false')),
cheio AS (SELECT i, coalesce("A", lead("A") OVER (ORDER BY i), lag("A") OVER (ORDER BY i)) AS indicador,
                 "B" AS unidade, * EXCLUDE (i, "A", "B") FROM bruto),
longo AS (UNPIVOT cheio ON COLUMNS(* EXCLUDE (i, indicador, unidade)) INTO NAME col VALUE valor)
SELECT indicador, unidade, 2025 + (ascii(col) - ascii('C')) AS ano, TRY_CAST(valor AS DOUBLE) AS valor
FROM longo WHERE valor IS NOT NULL ORDER BY i, ano
```

```
('População Residente', '(106 hab)', 2025, 213.816494)
('População Residente', '(106 hab)', 2026, 214.585832)
('População Residente', '(106 hab)', 2027, 215.3134975)
('População Residente', '(106 hab)', 2028, 216.0024875)
('População Residente', '(106 hab)', 2029, 216.655393)
```

---

## 6. Fonte 3 — `pde2035_transmissao.xlsx`: a expansão da transmissão obra a obra

**Arquivo** `data/raw/aneel_ons_epe_bndes/pde2035_transmissao.xlsx` (140 KB) · **1 aba**, `PDE 2035` ·
dimensão `A1:T759` · 20 colunas · **0 células mescladas** · **cabeçalho na linha 1** (ao contrário de todo o resto do
PDE) · dados **L2:L759** = **758 linhas** · **sem rodapé, sem nota, sem linha de total**.

É a planilha mais valiosa das quatro: cada linha é um empreendimento de transmissão com região, UF, extensão,
capacidade de transformação, investimento, código DMSE, data prevista no SIGET e **o ano de entrada em cada um dos
três cenários**.

### Tabela proposta: `epe_pde2035_transmissao_obras`

| Coluna na planilha | Coluna proposta | Tipo | Observação |
|---|---|---|---|
| `Estudo` | `estudo` | VARCHAR | nome do estudo de planejamento que originou a obra |
| `Tipo do Empreendimento` | `tipo_empreendimento` | VARCHAR | `LT`, `SE`, `SECC LT` ou NULL |
| `Região Geoelétrica` | `regiao_geoeletrica` | VARCHAR | |
| `UF Origem` | `uf_origem` | VARCHAR | nome do estado escrito por extenso, **não a sigla** |
| `UF Destino` | `uf_destino` | VARCHAR | idem |
| `UF Secc` | `uf_seccionamento` | VARCHAR | vazia em 662 das 758 linhas |
| `Característica` | `caracteristica` | VARCHAR | `Nova` (367) / `Expansão` (389) / NULL (2) |
| `Nome do Empreendimento` | `empreendimento` | VARCHAR | |
| `Itens de obra` | `itens_obra` | VARCHAR | **texto longo com `\n`**, a lista de módulos |
| `Status` | `status` | VARCHAR | `DMSE`, `Estudo/Consolidação`, `Outorga`… |
| `Data de Necessidade` | `data_necessidade` | DATE | texto `MM/AAAA` → `try_strptime(..., '%m/%Y')` |
| `km Total` | `extensao_km` | DOUBLE | |
| `Potência Total (TF / ATF )` | `capacidade_transformacao_mva` | DOUBLE | MVA; nome com espaço antes do `)` |
| `Contratação` | `forma_contratacao` | VARCHAR | `Leilão`, `Substituição`, `Autorização`… |
| `SIGET.codDMSE` | `codigo_dmse` | VARCHAR | vazia em 443 das 758 |
| `SIGET.datPrevista (19/08/2025)` | `data_prevista_siget` | DATE | data-base do extrato do SIGET **está no nome da coluna** |
| `Total Investimento ( 2025 ) R$/1000` | `investimento_brl` | DOUBLE | **ver a ressalva de unidade** |
| `Data de Tendendência - Cenário Pessimista` | `ano_pessimista` | INTEGER | `2099` → NULL |
| `Data de Tendendência - Cenário Referência` | `ano_referencia` | INTEGER | idem |
| `Data de Tendendência - Cenário Otimista` | `ano_otimista` | INTEGER | idem |

Já é longo (uma linha por obra). **758 linhas.** Não há o que despivotar; os três cenários ficam em três colunas
porque são atributos da mesma obra, não observações.

**Ressalvas — esta é a tabela com mais pegadinhas das quatro fontes**

1. **O nome da coluna de investimento mente sobre a unidade.** O cabeçalho diz `R$/1000`, o que sugere R$ mil, mas os
   valores estão em **reais**. Prova: somando `investimento_brl` com o corte `ano_otimista <= 2035` dá
   **R$ 147,83 bilhões**, exatamente o valor de 2035 do cenário otimista da `Figura 4-19`
   (`epe_pde2035_transmissao_investimento_cenario`); o mesmo vale para referência (116,90) e pessimista (98,83). Se a
   unidade fosse R$ mil, daria R$ 147 milhões. Daí o nome `investimento_brl` sem multiplicador. São **reais de 2025**
   (o `( 2025 )` do cabeçalho).
2. **`2099` é sentinela, não ano.** Significa "a obra não entra neste cenário". Converta para NULL — do contrário
   qualquer `max(ano)` ou média fica destruída. Depois do `nullif`, `max(ano_referencia) = 2038` e
   `max(ano_pessimista) = 2030`.
3. **O corte `<= 2035` é obrigatório para reproduzir o capítulo 4.** Sem ele o cenário de referência soma
   R$ 138,97 bi, porque inclui obras de 2036-2038 que estão na planilha mas fora do decênio do plano.
4. **As quantidades físicas NÃO reconciliam com o capítulo 4, e a diferença é grande.** Somando o cenário de
   referência com o corte `<= 2035`: 28.307 km contra os 28.780,87 km da `Figura 4-24`; 79.512 MVA contra os
   89.018,32 MVA da `Figura 4-27`. Sobre todas as 758 linhas sem corte: 33.360 km e 117.108 MVA. **Não afirme que a
   soma obra a obra é igual ao agregado publicado** — não é, e a diferença de MVA passa de 10 %. O investimento
   reconcilia; a física não.
5. **2 linhas sem `tipo_empreendimento`, `regiao_geoeletrica` nem `caracteristica`** são valores agregados:
   `Investimento Prospectivo 2032` (R$ 3.989.787.340) e `Investimento Prospectivo 2033` (R$ 4.872.559.530). Elas
   entram na soma de investimento mas não são obras identificadas — filtre-as em qualquer análise por obra.
6. Por tipo (todas as linhas): `SE` 410 linhas / R$ 47,61 bi / 117.108 MVA; `LT` 252 / R$ 86,01 bi / 32.092 km;
   `SECC LT` 94 / R$ 5,34 bi / 1.267 km. Somar LT + SECC LT (R$ 91,35 bi) **não** dá os R$ 77,97 bi de
   `epe_pde2035_transmissao_investimento_recorte` para LT — os recortes do capítulo 4 usam outra classificação.
7. **Células vazias vêm como `''`, não NULL** (é consequência de `empty_as_varchar=true`). 443 linhas com
   `codigo_dmse` vazio, 662 com `uf_seccionamento` vazia, 2 sem `data_prevista_siget`. Decida na implementação se
   `''` vira NULL (recomendo `nullif(x, '')` para as quatro colunas de texto opcionais).
8. **4 linhas com investimento igual a 0** — são obras reais com custo não estimado, não erro de leitura.
9. `regiao_geoeletrica` tem 5 valores com grafia própria da EPE, entre eles
   `'Centro-Oeste e Estados do Acre e Rondônia'`: Nordeste 201, Sul 196, Sudeste 176,
   Centro-Oeste e AC/RO 95, Norte 88, NULL 2. **Não é a região geográfica do IBGE** — não junte com `uf` de outras
   tabelas assumindo equivalência.
10. `uf_origem`/`uf_destino` são **nomes de estado** (`'Piauí'`, `'Mato Grosso do Sul'`), enquanto o resto do banco
    usa sigla de 2 letras. Um `JOIN` com `usinas.uf` ou `gd_mmgd.uf` exige tabela de conversão.
11. `data_necessidade` tem valores **no passado** (a primeira linha da amostra é 01/2018): é a data em que a obra
    passou a ser necessária, não a data de entrada. A data de entrada projetada é `ano_referencia`.

**No banco**: **complementa e é a melhor aquisição das quatro fontes.** `transmissao_empreendimentos` (16.262 linhas)
é o cadastro de empreendimentos outorgados da ANEEL e `rap_transmissao_modulos` (47.392) é a receita por módulo; não
há nada que diga **quais obras o planejador espera que entrem, quando e em que cenário**. A ponte natural é
`codigo_dmse`, que não existe no banco hoje, e em segundo lugar o nome do empreendimento (comparável por texto com
`transmissao_empreendimentos`, com a cautela habitual).

**Receita testada** (758 linhas, 20 colunas):

```sql
SELECT "Estudo" AS estudo, "Tipo do Empreendimento" AS tipo_empreendimento,
       "Região Geoelétrica" AS regiao_geoeletrica, "UF Origem" AS uf_origem, "UF Destino" AS uf_destino,
       "UF Secc" AS uf_seccionamento, "Característica" AS caracteristica,
       "Nome do Empreendimento" AS empreendimento, "Itens de obra" AS itens_obra, "Status" AS status,
       try_strptime("Data de Necessidade", '%m/%Y')::DATE AS data_necessidade,
       TRY_CAST("km Total" AS DOUBLE) AS extensao_km,
       TRY_CAST("Potência Total (TF / ATF )" AS DOUBLE) AS capacidade_transformacao_mva,
       "Contratação" AS forma_contratacao, "SIGET.codDMSE" AS codigo_dmse,
       try_strptime("SIGET.datPrevista (19/08/2025)", '%m/%Y')::DATE AS data_prevista_siget,
       TRY_CAST("Total Investimento ( 2025 ) R$/1000" AS DOUBLE) AS investimento_brl,
       nullif(CAST(TRY_CAST("Data de Tendendência - Cenário Pessimista" AS DOUBLE) AS INTEGER), 2099) AS ano_pessimista,
       nullif(CAST(TRY_CAST("Data de Tendendência - Cenário Referência" AS DOUBLE) AS INTEGER), 2099) AS ano_referencia,
       nullif(CAST(TRY_CAST("Data de Tendendência - Cenário Otimista" AS DOUBLE) AS INTEGER), 2099) AS ano_otimista
FROM read_xlsx('.../pde2035_transmissao.xlsx', sheet='PDE 2035', header=true,
               all_varchar=true, empty_as_varchar=true)
WHERE "Estudo" IS NOT NULL
```

Amostra real (primeira linha, com `itens_obra` truncado aqui por ser um bloco de várias linhas):

```
('Estudo de Atendimento Elétrico às Regiões Nordeste do Tocantins e Sul do Maranhão', 'LT', 'Nordeste',
 'Piauí', 'Maranhão', '', 'Nova', 'LT 230 kV Ribeiro Gonçalves - Balsas, C2',
 'Circuito Simples 230 kV, 1 x 795 MCM (Drake), 95 km\nEL (Entrada de Linha) 230 kV, Arranjo BD4 // SE Ribeiro
  Gonçalves\n...', 'DMSE', datetime.date(2018, 1, 1), 95.0, None, 'Leilão', 'T2024-205-B',
 datetime.date(2026, 1, 1), 119967150.0, 2026, 2026, 2026)
('Estudo de Suprimento à Região de Santana do Araguaia', 'LT', 'Norte', 'Pará', 'Pará', '', 'Nova',
 'LT 230 kV Integradora - Xinguara II, C3', '...', 'Estudo/Consolidação', datetime.date(2032, 1, 1), 79.0, None,
 'Leilão', '', datetime.date(2032, 1, 1), 96809190.0, None, 2032, 2029)
('Análise da Expansão da Interligação entre as Regiões Sul e Sudeste/Centro-Oeste', 'LT', 'Sul', 'Paraná',
 'Paraná', '', 'Expansão', 'LT 230 kV Londrina - Apucarana, C2', '...', 'Estudo/Consolidação',
 datetime.date(2037, 1, 1), 46.0, None, 'Substituição', '', datetime.date(2037, 1, 1), 25993650.0, None, 2037, 2034)
('Estudo de Atendimento Elétrico ao Estado do Mato Grosso do Sul', 'LT', 'Centro-Oeste e Estados do Acre e Rondônia',
 'Mato Grosso do Sul', 'Mato Grosso do Sul', '', 'Nova', 'LT 230 kV Campo Grande 2 - Paraíso 2, C3', '...',
 'Estudo/Consolidação', datetime.date(2037, 1, 1), 228.0, None, 'Leilão', '', datetime.date(2037, 1, 1),
 384848940.0, None, 2037, 2034)
('Estudo de Atendimento Elétrico ao Estado do Mato Grosso do Sul', 'LT', 'Centro-Oeste e Estados do Acre e Rondônia',
 'Mato Grosso do Sul', 'Mato Grosso do Sul', '', 'Nova', 'LT 230 kV Imbirussu - Campo Grande 2, C3', '...',
 'Estudo/Consolidação', datetime.date(2037, 1, 1), 50.0, None, 'Leilão', '', datetime.date(2037, 1, 1),
 103207340.0, None, 2037, 2034)
```

---

## 7. Fonte 4 — `deb_incentivadas.xls`: portarias autorizativas da Lei 12.431

**Arquivo** `data/raw/cvm/deb_incentivadas.xls` (116 KB) · **1 aba**, `ICVM 400 e 476` · 95 linhas × 16 colunas.

### 7.1 O arquivo não abre com DuckDB — os erros exatos

Este é um `.xls` **BIFF legado (OLE2)**, não um `.xlsx`. As duas tentativas com DuckDB 1.5.5 falharam assim:

```
read_xlsx(...)        -> IO Error: Failed to open zip for reading
st_read(...) (spatial)-> IO Error: Could not open GDAL dataset at: .../cvm/deb_incentivadas.xls
```

`file` confirma: `Composite Document File V2 Document ... OLE2 Compound Document`. Portanto **esta fonte exige uma
dependência nova, `xlrd` 2.0.2** (que só lê `.xls`), ou uma conversão prévia para `.xlsx`/CSV. É uma decisão de
arquitetura, não de leitura: `construir.py` hoje não importa `xlrd`. Se a preferência for não adicionar dependência,
converta o arquivo uma vez e versione a **conversão** (não o dado) no pipeline de ingestão. Toda a leitura abaixo foi
feita com `xlrd`, e as datas com `xlrd.xldate_as_tuple(v, livro.datemode)`.

### 7.2 Estrutura, linha a linha (índice 0 = primeira linha da aba)

| Linhas | Conteúdo |
|---|---|
| R0:R2 | título em três linhas |
| R3:R4 | vazias |
| **R5:R7** | **cabeçalho de três níveis** |
| **R8:R88** | dados — **81 registros** |
| R89 | `Total`: 13.342,075 e 11.438,878 (confere com a minha soma das duas colunas de volume) |
| R90 | `Fontes: ANBIMA e Ministérios` |
| R91 | **`Atualizado em 17/07/2015.`** |
| R92 | vazia |
| R93 | URL da ANBIMA |
| R94 | texto solto |

São **6 linhas de cabeçalho/título a pular e 6 linhas de rodapé a descartar**.

### 7.3 Tabela proposta: `debentures_incentivadas_portarias`

**O nome não pode ser `debentures_incentivadas`** — já existe uma tabela com esse nome no banco (777 linhas, ANBIMA).
Esta é a camada de **autorização ministerial**, não de emissão.

| Coluna na planilha (nível útil do cabeçalho) | Coluna proposta | Tipo | Observação |
|---|---|---|---|
| — | `ordem` | INTEGER | posição na planilha; **indispensável**, é o que permite o forward-fill |
| `Data` da portaria | `data_portaria` | DATE | serial do Excel via `xldate_as_tuple` |
| `Portaria` | `numero_portaria` | INTEGER | |
| `Ministério` | `ministerio` | VARCHAR | 4 valores |
| `Titular` | `titular` | VARCHAR | a SPE do projeto |
| `Holding/SPE` | `holding_spe` | VARCHAR | **texto multilinha** com os controladores |
| — | `serie_adicional` | BOOLEAN | linha que é série adicional da portaria anterior |
| `Data de Emissão` | `data_emissao` | DATE | NULL nas portarias sem emissão |
| `Início da Distribuição` | `inicio_distribuicao` | DATE | |
| `Regime` | `regime_distribuicao` | VARCHAR | `ICVM 400` (20) / `ICVM 476` (24) / NULL (37 antes do preenchimento) |
| `Código do Ativo` | `codigo_ativo` | VARCHAR | código CETIP, 55 preenchidos |
| `Série` | `serie_isenta` | INTEGER | número da série beneficiada |
| `Volume Total` | `volume_total_brl_milhoes` | DOUBLE | **R$ milhões** |
| `Volume 12.431` | `volume_12431_brl_milhoes` | DOUBLE | **R$ milhões**, parcela incentivada |
| `Vencimento` | `data_vencimento` | DATE | |
| `Remuneração` | `remuneracao` | VARCHAR | `IPCA` (53) / `Prefixado` (1) / NULL (27) |
| `Taxa` | `taxa_pct_aa` | DOUBLE | % ao ano; já é ponto decimal |

**81 linhas.** Já é longo.

**Ressalvas**

1. **O arquivo está congelado em 2015.** R91 diz literalmente `Atualizado em 17/07/2015.` **Esta tabela é um
   retrato histórico dos três primeiros anos da Lei 12.431 (2012-2015), não o estoque atual de debêntures
   incentivadas.** O `ressalvas` do catálogo precisa dizer isso na primeira frase, senão alguém vai comparar com a
   `debentures_snd` (10.008 linhas, atual) e concluir que o mercado encolheu.
2. **19 das 81 linhas são séries adicionais da portaria da linha anterior**, com `data_portaria`,
   `numero_portaria`, `ministerio` e `titular` **em branco** (a planilha usa o branco como "idem"). Sem preencher,
   qualquer `GROUP BY ministerio` perde um quarto dos dados. O preenchimento correto é por bloco:
   `count(data_portaria) OVER (ORDER BY ordem)` define o id do bloco, e dentro dele
   `first_value(... ) OVER (PARTITION BY bloco ORDER BY ordem)` replica os 4 campos. A coluna `serie_adicional`
   marca quais linhas foram preenchidas. Depois do preenchimento: **62 portarias distintas, 59 titulares**, e
   MME 50 linhas (R$ 3.656,3 MM), Transportes 21 (R$ 6.561,7 MM), Aviação Civil 9 (R$ 900,0 MM), Portos 1
   (R$ 320,9 MM).
3. **26 das 81 linhas são portarias autorizadas que nunca viraram emissão**: sem `codigo_ativo`, sem
   `data_emissao`, sem volume. Todas do MME — as dez `Eólica Geribatu I` a `X` (jan-fev/2013), as treze
   `Centrais Eólicas …` de 2013 (Seraíma, Tanque, dos Araçás, Morrão, Maron, Espigão, Borgo, Dourados, Serra do
   Espinhaço, Ventos do Nordeste, Pelourinho, Caetité, Pilões), `Tractebel Energia`, `Empresa de Transmissão de
   Várzea Grande - ETVG` e `Verde 08 Energia` / `Água Limpa Energia` (abr/2015). **É informação, não lixo**: é o
   funil autorização → emissão, e é exatamente o que uma tabela de debêntures emitidas não pode mostrar. Mantenha as
   26 linhas e documente-as.
4. **O arquivo NÃO tem CNPJ.** Não há coluna de CNPJ, nem de CNPJ do emissor, nem número de processo — só o nome do
   titular e o do controlador. Portanto **não há como aplicar `fmt_cnpj` diretamente nesta fonte**; a chave de
   ligação com o resto do banco tem de ser construída (item 5).
5. **A ponte com o banco é `codigo_ativo`, não o nome.** Medido:
   - `codigo_ativo` → `debentures_snd.codigo`: **55 de 55 casam** (100 % dos que têm código). Daí se obtém
     `debentures_snd.cnpj`, que **já vem formatado por `fmt_cnpj`** no `construir.py` — ou seja, o CNPJ entra por
     empréstimo, e **34 dos 59 titulares** ganham CNPJ por esse caminho.
   - Os mesmos 55 códigos casam com `debentures_incentivadas.codigo_cetip` (**55 de 55**).
   - Ligação por nome é fraca e **não deve ser usada**: de 60 titulares, só **7** casam com
     `agentes_aneel.razao_social` e **3** com `empresas.nome_social`, mesmo normalizando.
   - Portanto a coluna de ligação recomendada na tabela é `codigo_ativo`, e o CNPJ **não deve ser materializado
     aqui** — deve ser obtido por `JOIN` com `debentures_snd`, para não congelar um dado de outra fonte.
6. **A unidade R$ milhões está confirmada por igualdade exata**: `volume_12431_brl_milhoes * 1e6` é igual a
   `debentures_snd.volume_emitido_brl` nos 55 casos (ex.: `LTMC12` 25,0 → 25.000.000,00). Daí o sufixo
   `_brl_milhoes` no nome, e o aviso para **não** aplicar `num_br`: os números já vêm como `float` do `xlrd`.
7. **Cuidado com quem é o emissor.** `APAR16` tem como titular `'Empresa Litorânea de Transmissão de Energia
   S.A. - ELTE.'`, mas no SND a emissora é `'ALUPAR INVESTIMENTO S/A'` (08.364.948/0001-38): a portaria autoriza o
   **projeto** (a SPE), e a debênture é emitida pela **holding**. Ao juntar as duas tabelas, `titular` e
   `debentures_snd.emissora` podem ser empresas diferentes, e o CNPJ obtido é o da holding. Isso tem de estar no
   `ressalvas`.
8. **Só 34 das 81 linhas são de setor elétrico** (classificação de `debentures_snd`). As outras são rodovia,
   ferrovia, aeroporto e porto. Para uma análise do setor elétrico, filtre pelo `JOIN` com `debentures_snd` — o
   `ministerio = 'Ministério de Minas e Energia'` não é garantia (o MME também autorizou projetos de gás).
9. `taxa_pct_aa` sem `remuneracao` não significa nada: quando `remuneracao = 'IPCA'` a taxa é o **spread real**
   sobre o IPCA (8,75 % a.a. no `LTMC12`); quando é `Prefixado`, é a taxa nominal (10,1 % no `FERR18`). Nas 27
   linhas com `remuneracao` NULL não há emissão.

**No banco**: **complementa** `debentures_snd` (10.008 linhas, SND/ANBIMA, com CNPJ e volume em reais) e
`debentures_incentivadas` (777 linhas, ANBIMA). Nenhuma das duas tem a **portaria autorizativa** (número, data,
ministério) nem as autorizações sem emissão. O ganho é a camada de política pública: quem autorizou, quando, e quanto
foi efetivamente emitido do que foi autorizado. O custo é a data de corte de 2015 (ressalva 1).

**Receita testada** — o script é `04_deb_incentivadas.py` (Python + `xlrd`, não SQL, pelo motivo de §7.1). O miolo:

```python
import xlrd
livro = xlrd.open_workbook("/local/.../data/raw/cvm/deb_incentivadas.xls")
aba = livro.sheet_by_name("ICVM 400 e 476")          # 95 linhas x 16 colunas

def data(v):                                          # serial do Excel -> date
    if v in ("", None): return None
    a, m, d = xlrd.xldate_as_tuple(float(v), livro.datemode)[:3]
    return datetime.date(a, m, d)

registros = []
for i in range(8, 89):                                # R8:R88 = 81 registros
    c = [aba.cell_value(i, j) for j in range(16)]
    registros.append(dict(ordem=i - 7, data_portaria=data(c[0]), numero_portaria=inteiro(c[1]),
                          ministerio=txt(c[2]), titular=txt(c[3]), holding_spe=txt(c[4]),
                          data_emissao=data(c[5]), inicio_distribuicao=data(c[6]),
                          regime_distribuicao=txt(c[7]), codigo_ativo=txt(c[8]), serie_isenta=inteiro(c[9]),
                          volume_total_brl_milhoes=num(c[10]), volume_12431_brl_milhoes=num(c[11]),
                          data_vencimento=data(c[12]), remuneracao=txt(c[13]), taxa_pct_aa=num(c[14])))
```

e, já no DuckDB, o preenchimento das séries adicionais:

```sql
WITH b AS (SELECT *, count(data_portaria) OVER (ORDER BY ordem) AS bloco FROM registros)
SELECT ordem,
       first_value(data_portaria)   OVER (PARTITION BY bloco ORDER BY ordem) AS data_portaria,
       first_value(numero_portaria) OVER (PARTITION BY bloco ORDER BY ordem) AS numero_portaria,
       first_value(ministerio)      OVER (PARTITION BY bloco ORDER BY ordem) AS ministerio,
       first_value(titular)         OVER (PARTITION BY bloco ORDER BY ordem) AS titular,
       data_portaria IS NULL AS serie_adicional, * EXCLUDE (ordem, data_portaria, numero_portaria,
                                                            ministerio, titular, bloco)
FROM b ORDER BY ordem
```

Saída real (81 linhas; as 5 primeiras, já com o preenchimento):

```
(1, date(2012, 6, 26), 386, 'Ministério de Minas e Energia', 'Linhas de Transmissão de Montes Claros S.A.',
 'Cobra Instalaciones y Servicios S.A. \nLintran do Brasil Participações S.A.', False, date(2012, 8, 15),
 date(2012, 9, 27), 'ICVM 476', 'LTMC12', 1, 25.0, 25.0, date(2029, 4, 15), 'IPCA', 8.75)
(2, date(2012, 8, 24), 203, 'Ministério dos Transportes', 'ALL - América Latina Logística Malha Norte S.A.',
 'ALL - América Latina Logística S.A\n...', False, date(2012, 9, 25), date(2012, 10, 18), 'ICVM 476',
 'FERR18', 1, 160.0, 160.0, date(2020, 10, 18), 'Prefixado', 10.1)
(3, date(2012, 9, 13), 214, 'Ministério dos Transportes',
 'Concessionária do Sistema Anhanguera - Bandeirantes S.A.', '...', False, date(2012, 10, 15),
 date(2012, 10, 22), 'ICVM 400', 'ANHB24', 1, 1100.0, 135.0, date(2017, 10, 15), 'IPCA', 2.71)
(4, date(2012, 10, 3), 558, 'Ministério de Minas e Energia', 'Santo Antonio Energia S.A.',
 'Madeira Energia S.A.', False, date(2012, 12, 27), date(2013, 1, 24), 'ICVM 476', 'SAES12', 1, 420.0, 420.0,
 date(2022, 12, 27), 'IPCA', 6.2)
(5, date(2012, 10, 3), 558, 'Ministério de Minas e Energia', 'Santo Antonio Energia S.A.',
 'Madeira Energia S.A.', True, date(2014, 4, 15), date(2014, 5, 2), 'ICVM 400', 'STEN13', 2, 200.0, 200.0,
 date(2022, 4, 15), 'IPCA', 7.0537)
```

E a ligação com o banco, testada com `ATTACH '<db>' AS b (READ_ONLY)` (5 primeiros casos de setor elétrico):

```
('LTMC12', 'Linhas de Transmissão de Montes Claros S.A.', 386, 25.0, '11.620.646/0001-98',
 'LINHAS DE TRANSMISSAO DE MONTES CLAROS S/A', 25000000.0)
('SAES12', 'Santo Antonio Energia S.A.', 558, 420.0, '09.391.823/0001-60', 'SANTO ANTONIO ENERGIA S.A.', 420000000.0)
('STEN13', 'Santo Antonio Energia S.A.', 558, 200.0, '09.391.823/0001-60', 'SANTO ANTONIO ENERGIA S.A.', 200000000.0)
('STEN23', 'Santo Antonio Energia S.A.', 558, 500.0, '09.391.823/0001-60', 'SANTO ANTONIO ENERGIA S.A.', 500000000.0)
('FGEN13', 'Ferreira Gomes Energia S.A.', 559, 210.9, '12.489.315/0001-23', 'FERREIRA GOMES ENERGIA S.A.', 210900000.0)
```

---

## 8. Abas que eu NÃO recomendo

Li o título (L3) e o cabeçalho (L6) de **todas as 254 abas** do PDE — os despejos estão em `out_titulos.txt`,
`out_titulos_excl.txt` e `out_pde_inventario.txt`. Abaixo, o motivo de cada exclusão. Nenhuma outra aba foi
descartada sem leitura.

**Contagem**: 238 abas de dados − 39 recomendadas = **199 abas de dados excluídas**, mais **12 abas `Índice`** e
**4 abas ocultas**.

### 8.0 As 16 abas que não são dados

- **`Índice`** (1 por pasta, 12 no total): sumário com hiperlinks para as demais abas; nenhum dado.
- **`ESRI_MAPINFO_SHEET`** (nas pastas 03, 05, 07 e 08): aba **oculta** (`sheet_state = 'hidden'`) criada pelo
  plugin de mapas do ArcGIS; contém metadado de georreferenciamento das figuras de mapa, não dados da figura.

### 8.1 Pastas inteiras fora do recorte de eletricidade (84 abas)

**Pasta 01 — Economia e Demografia (11 abas):** é o cenário macroeconômico que **alimenta** as projeções elétricas,
mas não tem grandeza elétrica alguma. Os indicadores que interessam (população, PIB) já vêm consolidados em
`epe_pde2035_indicadores` (§5.8), com a mesma origem.
`Figura 1-1` população e habitantes por domicílio · `Figura 1-2` população por região (%) · `Figura 1-3` PIB e
comércio mundial · `Figura 1-4` taxa de investimento (% do PIB) · `Figura 1-5` produtividade total dos fatores ·
`Figura 1-6` balança comercial · `Figura 1-7` superávit primário e dívida líquida · `Figura 1-8` PIB e PIB per
capita · `Figura 1-9` valor adicionado por macrossetor · `Figura 1-10` valor adicionado industrial ·
`Figura 1-11` taxas médias dos cenários econômicos.

**Pasta 05 — Produção de Petróleo e Gás Natural (26 abas):** upstream de óleo e gás; só tocaria eletricidade via
oferta de gás para térmicas, e esse elo eu já trago pela pasta 07.
`Figura 5-2` a `Figura 5-9` previsões de produção de petróleo e de gás (por recurso, por camada, por contrato) ·
`Figura 5-10` a `Figura 5-15` produção onshore por bacia · `Tabela 5-1`, `Tabela 5-2` recursos e reservas por bacia ·
`Figura 5-16`, `Figura 5-17` sensibilidade de fator de recuperação · `Figura 5-18`, `Tabela 5-3`, `Tabela 5-4`
resultados de ciclos de oferta permanente · `Figura 5-19`, `Figura 5-20` reservas provadas e relação R/P ·
`Tabela 5-5` balanço de petróleo · `Figura 5-21` entrada de novas UEPs · `Figura 5-22` curva hipotética de emissões
de um campo.

**Pasta 06 — Abastecimento de Derivados de Petróleo (21 abas):** preço e balanço de derivados; nada de eletricidade.
`Figura 6-1` preço do Brent · `Figura 6-2` preços internacionais de derivados · `Figura 6-3` intensidade de emissões
das refinarias · `Figura 6-4` capacidade de refino · `Figura 6-5` perfil de produção das refinarias ·
`Figura 6-6` a `Figura 6-15` balanços nacionais por derivado (GLP, gasolina A, nafta, QAV, diesel A, óleo
combustível, outros secundários) · `Figura 6-16` saldo líquido por derivado · `Figura 6-17` a `Figura 6-21`
dependência externa por derivado.

**Pasta 08 — Oferta de Biocombustíveis (26 abas):** etanol, biodiesel, SAF e biometano.
`Figura 8-1` a `Figura 8-9` e `Figura 8-11` capacidade, processamento, oferta e demanda de etanol e açúcar ·
`Figura 8-14` a `Figura 8-16` potencial de biogás e biometano · `Figura 8-17` cooperativas e famílias da
agricultura familiar · `Figura 8-18` a `Figura 8-21` biodiesel · `Figura 8-24` a `Figura 8-29` SAF, metas de
emissão da aviação e biodiesel aquaviário.
Duas abas desta pasta **tocam** eletricidade e ainda assim ficaram de fora, com motivo próprio:
`Figura 8-12` energia contratada em leilões pelas usinas de bagaço (MWméd por tipo de leilão, série histórica) — é
resultado de leilão, e leilão deve entrar no banco pelo dado primário da CCEE/ANEEL, não por um recorte de
biocombustível; `Figura 8-13` potencial de exportação de eletricidade por bagaço (GWméd) — é **potencial técnico**,
não projeção do plano, e não é comparável com nenhuma série de oferta.

### 8.2 Pasta 02 — Demanda de Energia: 23 abas excluídas de 27

Todas as abas de consumo **em tep ou em %** ficaram de fora: o banco é de setor elétrico e o Anuário (fonte 1) já dá
o consumo elétrico realizado em MWh com muito mais detalhe.
`Figura 2-2` consumo final por setor (milhões tep) · `Figura 2-3` decomposição da variação do consumo industrial
(mil tep) · `Figura 2-4` consumo industrial por fonte (%) · `Figura 2-5` e `Figura 2-6` participação modal em carga e
passageiros · `Figura 2-7` consumo de transportes por fonte (milhões tep) · `Figura 2-8` edificações e serviços
públicos (%) · `Figura 2-9` fontes no consumo residencial (%) · `Figura 2-10` consumo elétrico residencial **por
equipamento** (TWh) — interessante, mas é eficiência de equipamento, já coberta conceitualmente pela pasta 09, e o
recorte por equipamento não se liga a nenhuma outra tabela do banco · `Figura 2-11` domicílios com água aquecida por
fonte (%) · `Figura 2-12` usos finais residenciais (%) · `Figura 2-13` consumo do setor serviços por fonte (%) ·
`Figura 2-14` distribuição do consumo de serviços em 2035 (%) · `Figura 2-15` e `Figura 2-16` consumo agropecuário
(mil tep e %) · `Figura 2-17` consumo final por fonte (%) · `Figura 2-18` etanol por tipo (milhões m³) ·
`Figura 2-19` biocombustíveis por fonte (milhões tep) · `Figura 2-20` derivados de petróleo (%) ·
`Figura 2-21` elasticidade-renda da demanda de eletricidade (histórico × projeção) — 16 linhas de **períodos**
(`1970-1980`), não de anos, e é indicador derivado · `Figura 2-24` cargas especiais em 2035 por cenário — 1 ano, 3
valores, e os cenários têm nomes que não batem com os das outras abas (`menos favorável`/`mais favorável`) ·
`Figura 2-27` carga diária × temperatura em 2019 (638 linhas) — insumo de modelagem climática de um ano histórico ·
`Figura 2-28` variabilidade da carga diária por mês (791 linhas) — razão adimensional de modelagem.

### 8.3 Pasta 03 — Geração Centralizada: 36 abas excluídas de 47

O grosso são **saídas intermediárias do NEWAVE** (métricas de risco por série sintética), que não são projeção
publicável e cuja interpretação exige o modelo:
`Figura 3-9a`, `Figura 3-9b`, `Figura 3-10`, `Figura 3-11a`, `Figura 3-11b`, `Figura 3-12`, `Figura 3-18`,
`Figura 3-32`, `Figura 3-33`, `Figura 3-34`, `Figura 3-35`, `Figura 3-38a`, `Figura 3-38b`, `Figura 3-39a`,
`Figura 3-39b` — critérios de suprimento (CVaR 10 % CMO, CVaR 1 % ENS, CVaR 5 % PNS, LOLP, risco de déficit), cada
uma com a série do indicador e a linha do limite regulatório.
`Figura 3-16` e `Figura 3-17` — distribuição da potência disponível nas hidrelétricas nas **2.000 séries** do NEWAVE
(1.007 e 206 linhas): histograma de simulação.
`Figura 3-40` a `Figura 3-44` e `Figura 3-49` — intercâmbio e geração térmica por patamar, **24.006 linhas** em
quatro delas: saída bruta de simulação por série e patamar, sem chave interpretável.
`Figura 3-36`, `Figura 3-37`, `Figura 3-30` — ENA sintética × histórico, permanência de ENA e taxa de conversão de
afluência em geração: hidrologia de modelagem.
`Figura 3-13` e `Figura 3-14` — **diferenças para o PDE 2034**: delta entre dois planos, sem valor absoluto.
`Figura 3-15` — requisito de potência por cenário de demanda (derivado das métricas de risco acima).
`Figura 3-5` — oferta termelétrica **retirada** da configuração por motivação (fim de contrato / vida útil): o
cabeçalho usa `|` dentro do nome da coluna (`FIM DE CONTRATO | Carvão Mineral`), o que quebra qualquer nomeação
automática, e é descontratação, não expansão.
`Figura 3-22` — faixas de CAPEX de bateria projetadas pelo NREL: faixa (mín/máx) de terceiro, não custo de
referência da EPE (esse está na `Figura 3-19`, que eu recomendo).
`Figura 3-25` — participação das fontes na matriz em 2025 e 2035 (%): derivada da `Figura 3-6`.
`Figura 3-26` — renovabilidade média (%): indicador derivado.
`Figura 3-27` — contribuição das fontes em energia e potência (%): derivada.
`Figura 3-45` — carga líquida horária média mensal em % diária: adimensional, e a curva horária absoluta já entra
pela `Figura 2-23`.
`Figura 3-46` — comparação de rampas horárias (1.455 linhas): insumo de estudo de flexibilidade.

### 8.4 Pasta 04 — Transmissão: 6 abas excluídas de 16

`Figura 4-20` — "Cenários de referência: Visão geral": 8 linhas de texto-resumo dos cenários, sem grandeza numérica
comparável.
`Figura 4-28` — investimentos potenciais em ativos em fim de vida útil regulatória: 8 linhas, e o conceito
("potencial") não é compromisso de expansão; misturaria com o investimento planejado.
`Figura 4-30` e `Figura 4-32` — TUST-Geração e TUST-Carga por barra em 2035 (**2.962 linhas cada**): a chave é o
**número da barra do modelo elétrico**, que não existe em nenhuma outra tabela do banco nem no arquivo; sem o mapa
barra → subestação os dados não são utilizáveis. É a exclusão que mais me incomoda (§9).
`Figura 4-31` e `Figura 4-33` — TUST média por submercado em 2035: 10 linhas, agregado das duas anteriores.

### 8.5 Pasta 07 — Gás Natural: 5 abas excluídas de 7

`Figura 7-4` preços de citygate (US$/MMBtu) · `Figura 7-7` produção líquida e oferta potencial de gás ·
`Figura 7-8` oferta potencial nacional e importada na malha integrada · `Figura 7-9` balanço de gás da malha
integrada · `Figura 7-10` oferta e demanda do Grupo de Trabalho "Gás para Empregar" (cenário alternativo de
política). Todas são **oferta e preço de gás**, não eletricidade; entram no banco só se ele passar a cobrir gás.

### 8.6 Pasta 09 — Eficiência Energética e RED: 27 abas excluídas de 33

Eficiência em **% de ganho** ou em tep, que não se liga a nenhuma série elétrica do banco:
`Figura 9-2` a `Figura 9-5` contribuição setorial aos ganhos de eficiência (energética e elétrica, % do ganho e % por
setor) · `Figura 9-6` consumo específico industrial (tep/mil t) · `Figura 9-7` ODEX industrial (índice) ·
`Figura 9-8` consumo médio por equipamento residencial (kWh/ano/equipamento) · `Figura 9-9` consumo elétrico
residencial com e sem eficiência (TWh) · `Figura 9-10` GLP e GN residencial · `Figura 9-11` a `Figura 9-15`
serviços, transportes e agropecuário com e sem ganhos de eficiência.
MMGD já coberta com mais precisão pelas 5 tabelas que recomendo, ou duplicada da base da ANEEL que já está no banco:
`Figura 9-16` potência por modalidade · `Figura 9-17` potência por classe de consumo · `Tabela 9-4` resumo da MMGD
**por região** de 2025 a 2035 (8 linhas; o corte geográfico melhor é a `Figura 9-19`, por UF) · `Figura 9-21`
capacidade por fonte em 2035 (10 linhas; 99 % é solar FV).
Simulações de bateria e de payback, que são estudo de viabilidade e não projeção:
`Figura 9-28` diferença tarifária ponta/fora-ponta por distribuidora (112 linhas) · `Figura 9-29` VPL de bateria por
distribuidora e fator de carga (**1.281 linhas**) · `Figura 9-30` VPL de bateria × gerador diesel (**1.536 linhas**) ·
`Figura 9-31` ganho potencial com bateria na tarifa B1 · `Figura 9-33` distribuição do payback do autoconsumo da
micro GD (**5.256 linhas**) · `Figura 9-34` mercado potencial da FV residencial diária em 2035 · `Figura 9-35`
potencial de investimento em baterias residenciais.
Aquecimento solar, que não é eletricidade: `Figura 9-40` domicílios com SAS × crescimento habitacional ·
`Figura 9-41` domicílios por fonte de aquecimento de água (%).

### 8.7 Pasta 10 — Análise Socioambiental: 5 abas excluídas de 7

`Figura 10-3` emissões por **combustível** (MtCO2eq) — recorte por energético, não por setor; não se liga a nenhuma
tabela do banco · `Figura 10-4` distribuição das emissões do Brasil por setor **em 2022**, incluindo uso da terra e
agropecuária: inventário nacional de outro escopo, um ano só · `Figura 10-5` emissões per capita (tCO2/hab) ·
`Figura 10-6` intensidade de carbono da economia (kgCO2eq/US$ppc 2015) · `Figura 10-7` intensidade de carbono da
energia (tCO2eq/tep) — as três são indicadores derivados de 7 linhas, recalculáveis a partir das emissões e dos
indicadores que eu já trago.

### 8.8 Pasta 11 — Transição Energética: 2 abas excluídas de 3

`Figura 11-2` evolução dos indicadores de continuidade (DEC/FEC) — **é setor elétrico e é relevante**, mas são 21
linhas de série histórica de qualidade de serviço que vêm da ANEEL, e o dado primário (por distribuidora) deve entrar
pela ANEEL, não por esta planilha agregada · `Figura 11-3` acesso ao cozimento limpo no meio urbano e rural: é GLP e
lenha, não eletricidade.

### 8.9 Pasta 12 — Consolidação dos Resultados: 11 abas excluídas de 14

`Figura 12-1` Oferta Interna de Energia per capita — comparação internacional com dados de **2023** de Mundo, China,
EUA, Europa OCDE e OCDE; não é série e não é eletricidade.
`Tabela 12-2` evolução da Oferta Interna de Energia no decênio e `Figura 12-2` OIE por fonte — em **tep**, matriz
energética e não elétrica.
`Figura 12-3` matriz energética brasileira — mesma coisa, em participação.
`Figura 12-4` geração total de eletricidade por fonte — **duplicata exata da `Tabela 12-3`** (conferi: hidráulica
centralizada 440,600 TWh em 2025 nas duas), com a desvantagem de ter os 13 valores em 13 colunas cujos nomes se
repetem (`Autoprodução & Geração Distribuída - …` cinco vezes truncado no cabeçalho) e de trazer só os 3 anos.
Recomendo a `Tabela 12-3`, que tem a hierarquia e os subtotais.
`Figura 12-5` evolução da geração por fonte em % — 2 anos (2025 e 2035), derivada da `Tabela 12-3`.
`Tabela 12-5` monitoramento de indicadores de renovabilidade — 3 anos de participações (%) derivadas.
`Tabela 12-6` oferta de petróleo e derivados e `Tabela 12-7` balanço de gás natural seco — fora do recorte elétrico.
`Tabela 12-9` "Síntese dos resultados" (61 linhas × 25 colunas) — é a tabela mais rica do capítulo **e a única com
18 blocos de células mescladas**, com cabeçalho de múltiplos níveis e blocos de energia em tep, eletricidade,
petróleo, gás e biocombustíveis empilhados na mesma grade. Cada bloco precisaria de uma tabela própria, e todos os
blocos elétricos que ela contém já vêm das abas que eu recomendo. Deixei fora **por custo de leitura, não por falta
de valor** (§9).
`Tabela 12-11` projeção da matriz energética de 2035 (37 × 28, com mescla em `B6:K6` e `L6:AA6`) — é a matriz
insumo-produto energética em tep: fonte × setor, escopo de balanço energético, não de setor elétrico.

---

## 9. Relação com o catálogo, decisões e o que ficou em aberto

### 9.1 O que o banco já tem e como as 34 tabelas se encaixam

Abri o banco em `/local/al.richard.viana/coppezip-platform/data/coppezip.duckdb` (o arquivo no disco local guarda o
nome antigo; no repositório ele é `data/energynexus.duckdb`, um link para lá) **sempre com
`ATTACH ... (READ_ONLY)`** e li a tabela `catalogo`: **65 tabelas, 18.625.032 linhas**. Fatos relevantes:

- **Não existe nenhuma tabela `epe_*`.** A EPE não é fonte do banco hoje.
- **Não existe nenhuma tabela de projeção.** Todas as 65 são realizado, cadastro ou outorga. As 33 tabelas da EPE
  seriam as primeiras com horizonte futuro — e é por isso que insisto em `ressalvas` dizendo "projeção" em todas.
- **Não existe nenhuma tabela de emissões.** `epe_pde2035_emissoes_setor` e
  `epe_pde2035_emissoes_eletricidade_recorte` são inéditas no banco.

Sobreposições que precisam ser tratadas no `ressalvas` de cada tabela nova:

| Tabela nova | Tabela existente | Relação |
|---|---|---|
| `epe_anuario_consumo_mensal` (423.751) | `mercado_distribuidoras_mensal` (85.343, 2020+) | **Sobrepõe-se em parte**: a nova começa em 2011 e abre por classe, tensão e faixa de consumo; a existente é por distribuidora. Perímetros diferentes (a nova inclui consumidor livre). Não somar as duas. |
| `epe_pde2035_carga_energia_cenario`, `..._demanda_maxima_sin_mes` | `ons_carga_diaria` (39.057) | Complementa: realizado diário × projeção mensal/anual por cenário. |
| `epe_pde2035_capacidade_instalada_fonte` | `usinas` (25.045 SIGA), `capacidade_por_grupo` (7.010) | **Não comparável**: a `Figura 3-6` inclui MMGD no total por fonte (solar 60,27 GW em 2025), o SIGA não. |
| `epe_pde2035_expansao_indicativa`, `..._expansao_termica` | `expansao_geracao` (2.246 RALIE) | Complementa: RALIE é obra declarada, a expansão indicativa é o que o modelo escolhe. |
| `epe_pde2035_cmo_projetado_mes` | `ons_cmo_mensal` (324), `ons_cmo_semihora` (464.256) | Complementa: CMO realizado × projetado (SE/CO). |
| `epe_pde2035_geracao_hidro_termica_mes`, `..._geracao_eletricidade_fonte` | `ons_geracao_fonte_mensal` (585) | Complementa; taxonomias de fonte diferentes. |
| `epe_pde2035_mmgd_*` (5 tabelas) | `gd_mmgd` (66.826) | **Sobrepõe-se no histórico** (2013-2025 idêntico nos três cenários); o valor está na projeção. |
| `epe_pde2035_transmissao_obras` e as 4 de transmissão | `transmissao_empreendimentos` (16.262), `transmissao_contratos` (413), `rap_transmissao_modulos` (47.392) | Complementa: o banco tem outorgado e receita; falta o planejado. Ponte: `codigo_dmse` (ausente hoje) e nome do empreendimento. |
| `debentures_incentivadas_portarias` (81) | `debentures_snd` (10.008), `debentures_incentivadas` (777) | Complementa com a camada de autorização; ponte `codigo_ativo` → `debentures_snd.codigo` (**55/55**). |

### 9.2 As três decisões mais discutíveis

**1. Três tabelas ficaram com coluna `valor` genérica, quebrando a regra de "unidade no nome".**
São `epe_pde2035_mmgd_expansao_fonte` (com `grandeza` ∈ {`potencia_mw`, `energia_mwmed`}),
`epe_pde2035_custos_referencia_fonte` (com `grandeza` ∈ {`capex_brl_kw`, `om_fixo_brl_kw_ano`,
`encargos_brl_kw_ano`}) e `epe_pde2035_indicadores` (13 unidades, chave `indicador` + `unidade`). A alternativa era
criar 2, 3 e 13 tabelas, ou uma coluna por unidade quase toda NULL. Escolhi empilhar e **pôr a unidade em uma coluna
de dimensão**, porque nesses três casos as abas de origem são o mesmo objeto conceitual medido de formas diferentes.
Preço: nenhuma soma é válida sem filtrar `grandeza`/`unidade`, e o nome da coluna deixou de dizer a unidade. Em
`epe_pde2035_transmissao_expansao_fisica` fiz o **oposto** (duas colunas de valor, `extensao_acumulada_km` e
`capacidade_acumulada_mva`, uma sempre NULL) porque km e MVA não são a mesma grandeza medida de dois jeitos. As duas
escolhas convivem no mesmo documento e isso é assumidamente inconsistente — se o projeto preferir uma regra única,
a que eu defenderia é a das colunas nomeadas, aceitando os NULLs.

**2. Descartei colunas de `Total` e de variação em vez de guardá-las com uma marca.**
Em `epe_pde2035_expansao_indicativa`, `epe_pde2035_emissoes_setor`, `epe_pde2035_mmgd_expansao_fonte`,
`epe_pde2035_transmissao_expansao_fisica` e `epe_pde2035_indicadores` joguei fora colunas de `Total` e as três de
`Variação média anual`. Justifiquei cada descarte **reproduzindo o valor descartado** (os totais fecham em todos os
anos; o CAGR de população confere na sexta casa). Mas na `Tabela 12-3` e na `Tabela 12-10` fiz o contrário: **mantive**
os subtotais e totais, com as colunas `tipo_linha` e `nivel`. O critério que usei: quando o total está em uma
**coluna**, descarto (o `UNPIVOT` o transformaria em uma categoria falsa); quando está em uma **linha** de uma
hierarquia que eu preciso preservar, mantenho com marca. É defensável, mas alguém pode legitimamente querer todas as
tabelas com a mesma política.

**3. Excluí as 4 abas de TUST (`Figura 4-30` a `4-33`) e a `Tabela 12-9`, que são dados de verdade.**
As duas abas de TUST por barra têm 2.962 linhas cada e são o único dado tarifário de transmissão projetado do plano;
deixei fora porque a chave é o número de barra do modelo elétrico e **não existe no arquivo nem no banco** o mapa
barra → subestação, o que tornaria a tabela impossível de juntar com qualquer coisa. A `Tabela 12-9` é a síntese mais
completa do plano e a única aba com 18 blocos mesclados: cada bloco dela é uma tabela diferente e o custo de leitura
é alto. Nos dois casos a exclusão é por **impossibilidade de ligação** e por **custo**, não por falta de valor — se
houver apetite, são as duas primeiras candidatas a uma segunda rodada.

### 9.3 O que ficou em aberto

1. **A premissa do enunciado sobre a fonte 4 não se sustenta.** O `deb_incentivadas.xls` **não tem coluna de CNPJ**,
   logo não há `fmt_cnpj` a aplicar sobre ele. A ligação com `debentures_snd` que eu testei (55/55 por
   `codigo_ativo`) resolve 34 dos 59 titulares; os outros 25 são portarias sem emissão ou sem código e **ficam sem
   CNPJ**. Decidir se isso é aceitável é uma decisão de produto, não minha.
2. **O `.xls` da fonte 4 exige dependência nova (`xlrd`) ou conversão prévia.** Não implementei nada; a escolha entre
   as duas é de quem é dono do `construir.py`.
3. **A divergência física da transmissão (28.307 km × 28.780,87 km; 79.512 MVA × 89.018,32 MVA) não tem explicação
   nos arquivos.** Testei o corte por ano, por cenário e por tipo de ativo; nenhuma combinação fecha. Pode ser
   diferença de escopo (obras fora do recorte de cenário, ou dupla contagem de seccionamento), mas **não afirmo**:
   só registro os dois números e a ressalva.
4. **Não sei se `Figura 3-6` inclui autoprodução além de MMGD.** Sei que inclui MMGD (solar 60,27 GW em 2025 contra
   ~40 GW de centralizada no SIGA), porque só isso explica a magnitude; mas a aba não tem nota e não há como provar
   a composição a partir dela.
5. **A abertura por UF da `Figura 4-3` não existe nos dados**, apesar do título prometê-la. Se o corte estadual da
   fila de data centers for necessário, a fonte é outra (o mapa do relatório ou o MME).
6. **Não verifiquei a origem do zip.** Trabalhei com `pde2035_dados.zip` extraído para a pasta temporária; as 12
   pastas de trabalho não têm dentro delas nenhum metadado de versão além dos títulos das figuras. Se a EPE
   republicar o zip, nada nas planilhas permite detectar a troca — recomendo guardar o hash do zip no
   `fonte`/`ressalvas` de cada tabela.
7. **As 34 tabelas não foram materializadas no banco**, por design: este documento é especificação de leitura. As 34
   receitas (33 em SQL no `05_receitas_finais.py`, mais a da fonte 4 em Python no `04_deb_incentivadas.py`) rodam
   sem erro e produzem exatamente as contagens aqui declaradas, mas quem as transformar em
   `tabela(...)` no `construir.py` ainda precisa decidir nomes finais, ordem de criação e o texto exato dos campos
   `descricao`, `fonte` e `ressalvas`.
