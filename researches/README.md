# research/ — base de pesquisa consolidada (CoppeZIP)

Reúne, na `main`, os documentos de pesquisa produzidos em paralelo por cada agente/branch, **sem alterar o conteúdo original** (exceto onde marcado em "Errata"). Pergunta-guia comum a todos:

> Como transformar os relatórios financeiros e socioambientais que as empresas do setor elétrico são obrigadas a divulgar em inteligência comparativa, capaz de revelar, de forma rápida e rastreável, como cada companhia investe, se posiciona e avança na transição energética?

## Índice

| Arquivo | Branch de origem (commit) | O que tem de melhor |
|---|---|---|
| [`FINDINGS-muse-spark-1.2.md`](FINDINGS-muse-spark-1.2.md) | `muse-spark-1.2-contributor-free` (`fe211b7`) | Maior cobertura de fontes (>100): ANEEL (19 datasets), CVM (18), ONS/CCEE/EPE, socioambientais, complementares; matriz de processabilidade; crons de coleta |
| [`FINDINGS-big-pickle.md`](FINDINGS-big-pickle.md) | `big-pickle` (`233f475`) | Mais cauteloso: corrige premissas (GRI 11, XBRL, CVM 244); links diretos de relatórios ESG por empresa; ferramentas de extração (Docling/MinerU/Marker/Arelle/RAGFlow) |
| [`FRAMEWORKS-big-pickle.md`](FRAMEWORKS-big-pickle.md) | `big-pickle` (`233f475`) | Frameworks/regulação em profundidade: ISSB S1/S2, CVM 193→244, GRI, SASB IF-EU (códigos), CSRD/ESRS, EU Taxonomy, TSB, taxonomias XBRL |
| [`FINDINGS-gemini-3.7-flash.md`](FINDINGS-gemini-3.7-flash.md) | `gemini-3.7-flash` (`3527ef7`) | Esqueleto de código (Pydantic/Instructor com conversão de unidades), 9 métricas híbridas com fórmulas, desenho do agente com tools |
| [`FINDINGS-claude-sonnet-5.md`](FINDINGS-claude-sonnet-5.md) | `claude-sonnet-5` (`0cff4e5`) | Conteúdo **baixado e lido de verdade**: colunas reais de CSVs, números de emissões/CAPEX extraídos de 10 PDFs com página, API não documentada da B3, BNDES por CNPJ, bloqueio WAF da CCEE |
| [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) | (novo, nesta consolidação) | Formato e variáveis/indicadores de cada fonte, com marcação do que foi conferido no arquivo real |

`nemotron-3-ultra-free` não produziu nada: a branch é idêntica à `main` original (`9293e7f`).

Os históricos individuais continuam nas branches; aqui há uma cópia de cada arquivo. Dados brutos (CSVs, PDFs) **não** foram versionados.

## Errata entre branches (conferido em 23/09/2026)

1. **CVM 193 "obrigatória a partir de 2026, em XBRL"** — afirmado em `FINDINGS-gemini-3.7-flash.md` (§1.1). Desatualizado: a Resolução CVM 244/2026 (29/05/2026) revogou a obrigatoriedade; o reporte é voluntário e, a partir de 01/01/2027, vale "pratique ou explique". O relatório em si não tem XBRL confirmado. Ver `FRAMEWORKS-big-pickle.md` §2 e as fontes lá citadas (confirmado também por busca web em escritórios/Migalhas/Mattos Filho).
2. **"Eletrobras não aparece na DFP 2024"** — afirmado em `FINDINGS-big-pickle.md` (§1, §2.5, §9). Aparece sim, como **AXIA ENERGIA S.A.** (CNPJ `00.001.180/0001-26`, CD_CVM `002437`) em `dfp_cia_aberta_DRE_con_2024.csv`; é a mesma companhia após a renomeação (também há AXIA ENERGIA NORTE e SUL).
3. **Conta de CAPEX no DFC** — `gemini`, `muse-spark` e `big-pickle` usam `6.02.01` como proxy. O subagente do `claude-sonnet-5`, olhando CEMIG e CPFL, encontrou imobilizado em `6.02.02`, intangível em `6.02.03` e "ativos de contrato/concessão" em `6.02.04` (rótulo varia por empresa). **Não reconciliado**: ninguém abriu `6.02.01` para dizer o que é. Num teste com `6.02.02+6.02.03`, Equatorial, Copel e Engie deram 0 (provavelmente registram em `6.02.04`). Decidir por `DS_CONTA` empresa a empresa antes de calcular qualquer KPI de CAPEX.
4. **`Global-Data-Finance`** — o `FINDINGS-claude-sonnet-5.md` publicado originalmente na branch (`0cff4e5`) dizia que o repositório não existe. Errado: `jordanestralioto/Global-Data-Finance` responde 200 na API do GitHub. Corrigido na branch `claude-sonnet-5` (`f8f3342`) e nesta cópia.
5. **SIGET `VlrHisRct` = RAP** — `FINDINGS-claude-sonnet-5.md` (§2.1, linha do SIGET) trata essa coluna como a receita regulada da transmissora. Não confirmado: o valor se repete por módulo e a soma é implausível (ver `DATA_DICTIONARY.md`). O join Agente × Obra/Módulo por `IdeCcd` funciona; o significado da coluna não está resolvido.

## Verificação independente feita nesta sessão

Conferido por download/consulta: `dfp_cia_aberta_2024.zip` e `fre_cia_aberta_2025.zip` (CVM), `cad_cia_aberta.csv`, SIGA diário (ANEEL, 23 colunas, cabeçalho lido), `package_show` do ONS (`restricao_coff_eolica_detail`), PDFs Cemig RAS 2025 e Taesa RS 2025 (URLs vindas de `big-pickle`, ambos HTTP 200 e ~35 MB), Resolução CVM 244/2026 (busca web). **Não** foi refeita a checagem individual das >100 URLs do `muse-spark`; o "todas verificadas" do documento é alegação do autor.
