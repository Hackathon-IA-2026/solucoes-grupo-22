# Índice local dos PDFs (`data/indexar_dados_local.py`)

Índice de busca de todos os PDFs de `data/raw`, com os embeddings calculados na GPU da própria máquina (nada de API
paga). Gera `documentos`, `paginas`, `trechos` (com o vetor), `blocos` (os parágrafos que a aba Timeline lê) e o índice
de palavras BM25, num único DuckDB trocado de forma atômica no fim.

É a versão e5 do índice: mesmo esquema do `data/docs_titan.duckdb`, **outro espaço de vetores** (ver
[Quem lê o índice](#quem-lê-o-índice)).

## Onde ficam as coisas

O repositório está no NFS (`/impa/home/...`), visível de todos os nós; os dados ficam no disco local de cada nó, e
`data/raw`, `data/modelos`, `data/parquet` e `data/coppezip.duckdb` são links para lá. Por isso os caminhos absolutos
são os mesmos em todas as máquinas: `/local/<usuário>/coppezip-platform/...`.

O DuckDB **nunca** é gravado no NFS: o lock de arquivo do DuckDB não funciona bem em disco de rede e a indexação trava
no meio. O `--saida` é obrigatório e o script recusa qualquer destino cujo ponto de montagem seja `nfs`, `cifs` ou
`sshfs`, com o nome do arquivo na mensagem. Depois da rodada, o banco vai para o disco local do nó que serve o chat e
`data/docs.duckdb` passa a ser um link para ele.

## O modelo

`intfloat/multilingual-e5-large` (1024 dimensões, janela de 512 tokens), em duas cópias com nomes parecidos:

| Pasta em `data/modelos/` | O que é | Serve para |
|---|---|---|
| `multilingual-e5-large` | exportação ONNX da Qdrant (`model.onnx` + `model.onnx_data`, sem `safetensors`) | `fastembed` (CPU), o antigo `indexar_docs.py` |
| `multilingual-e5-large-torch` | pesos PyTorch (`model.safetensors`, 2,24 GB) | **este script** |

`AutoModel.from_pretrained` na pasta ONNX falha com *"no file named model.safetensors"*. Se a pasta `-torch` não
existir no nó:

```bash
.runtime/venv/bin/python -c "
from huggingface_hub import snapshot_download
snapshot_download('intfloat/multilingual-e5-large',
                  local_dir='/local/$USER/coppezip-platform/modelos/multilingual-e5-large-torch')"
```

O e5 só funciona com os prefixos com que foi treinado: **`passage: `** em tudo o que é indexado (o script põe) e
**`query: `** na pergunta (quem busca põe). Sem isso a semelhança cai. Cada trecho vai para o modelo precedido de
empresa, ano e título, senão um trecho solto de tabela não tem contexto nenhum.

## Rodar

Na kolyma, que é a dona dos dados, mas cuja GPU é dividida com o vLLM do chat:

```bash
cd /impa/home/$USER/projects/clean-hack/coppezip
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv   # o lote 256 pede ~5,5 GiB livres
setsid nohup .runtime/venv/bin/python data/indexar_dados_local.py \
  --gpu 0 --saida /local/$USER/coppezip-platform/data/docs_local.duckdb \
  > /local/$USER/indexar.log 2>&1 < /dev/null &
tail -f /local/$USER/indexar.log
```

Num nó com a GPU livre (amazonas e as outras RTX 5090 do cluster). O repositório já se vê pelo NFS; o que falta é
espelhar o venv, os modelos e os PDFs **nos mesmos caminhos absolutos**, senão os links de `data/` não resolvem:

```bash
# ida, da kolyma (1× por nó; ~17 GB, ~15 min)
for p in coppezip-runtime/venv coppezip-platform/modelos coppezip-platform/data/raw; do
  ssh amazonas mkdir -p /local/$USER/$(dirname $p)
  rsync -a /local/$USER/$p/ amazonas:/local/$USER/$p/
done

# a rodada (setsid porque a sessão ssh pode cair antes do fim)
ssh amazonas "setsid nohup /local/$USER/coppezip-runtime/venv/bin/python \
  /impa/home/$USER/projects/clean-hack/coppezip/data/indexar_dados_local.py \
  --gpu 0 --saida /local/$USER/coppezip-platform/data/docs_local.duckdb --lote 256 --leitores 32 \
  > /local/$USER/indexar.log 2>&1 < /dev/null &"
ssh amazonas 'tail -f /local/'$USER'/indexar.log'

# volta: o banco pronto para o disco local da kolyma, e o link que o chat usa
rsync -a amazonas:/local/$USER/coppezip-platform/data/docs_local.duckdb /local/$USER/coppezip-platform/data/
ln -sfn /local/$USER/coppezip-platform/data/docs_local.duckdb data/docs.duckdb
```

Parâmetros:

| Parâmetro | Padrão | Para que serve |
|---|---|---|
| `--saida` | obrigatório | caminho do DuckDB, sempre no disco local do nó |
| `--gpu` | obrigatório | índice da GPU (o do `nvidia-smi`). Não há escolha automática nem caminho em CPU |
| `--lote` | 256 | trechos por lote na GPU |
| `--leitores` | núcleos da máquina | processos lendo PDFs |
| `--limite` | todos | indexa só os N primeiros documentos (teste) |
| `--tudo` | não | recalcula todos os vetores, ignorando o índice anterior |

Nada é adivinhado: sem CUDA, com uma `--gpu` que não existe, sem memória livre para o lote pedido ou sem o modelo, o
script para na primeira linha dizendo o que falta.

## Números medidos (RTX 5090 32 GiB, 32 núcleos)

- **Extração**: 2474 PDFs, 75.906 páginas em ~80 s com 32 processos (≈950 páginas/s). O gargalo é aqui, não na GPU —
  o `pymupdf` não solta o GIL, então são processos, não threads (com threads o ganho era zero).
- **GPU**, com trechos enchendo a janela de 512 tokens: lote 128 → 190 trechos/s e 2,6 GiB; **lote 256 → 195 trechos/s
  e 4,1 GiB**; lote 512 → 197 trechos/s e 7,1 GiB; lote 1024 → 13,1 GiB; lote 2048 estoura. O ganho acima de 256 é de
  1%, então o padrão é 256: a placa é compartilhada e não vale reservar memória para nada. Com os trechos reais
  (ordenados por tamanho, menos preenchimento) a mesma placa faz ~530 trechos/s.
- **Rodada completa**: ~10 min, ~1 GB de banco.
- A memória exigida na GPU é calculada do `--lote` (`GPU_FIXA`, `GPU_POR_TRECHO` no script, medidos nesta placa) com
  30% de folga; abaixo disso a rodada não começa.

## O que entra

Todo PDF de `data/raw`, e não só o que está no `documentos.csv`:

- `financeiro/<empresa>/pdfs/<ano>/` e `sustentabilidade/<empresa>/<ano>/` (mais `sustentabilidade/referencias/`), as
  pastas do `organizar.py`;
- `pdfs_esg/`, onde ficam os PDFs que o `organizar.py` ainda não moveu;
- os 6 dicionários de dados da ANEEL em `aneel/<base>/`, que descrevem as colunas das bases do `coppezip.duckdb`.

Metadados: a linha do `documentos.csv` casada pelo caminho ou, quando o CSV aponta para a pasta organizada e o PDF só
existe solto em `pdfs_esg`, pelo nome do arquivo. Os dicionários da ANEEL não estão no CSV: vêm da lista `DICIONARIOS`
e do próprio PDF (título do conjunto de dados e ano da versão), com `area = "dados"`,
`tipo = "dicionario_de_dados"`, `empresa = "ANEEL (dicionário de dados)"` e `cnpj` vazio — `empresa` preenchida porque
`linha_do_tempo.py` agrupa por ela e quebra com nome vazio, no mesmo estilo dos "CVM (regulação)" e
"EPE (referência setorial)" que já existem no CSV.

PDF sem metadados nenhum **interrompe** a indexação com o nome do arquivo: é sinal de que falta uma linha no
`documentos.csv`. O mesmo PDF sob dois caminhos (md5 igual) entra uma vez só, pelo caminho organizado — repetido,
ocuparia as duas primeiras posições de toda busca. Os `.txt` de `pdfs_esg/txt/` são extrações de PDFs já indexados e
ficam de fora (um `.txt` não tem página para citar). Tudo isso sai como `aviso:` no fim do log, com o total de PDFs em
disco, de cópias descartadas e de documentos indexados.

PDF que não abre não derruba a rodada: o índice é publicado e o script termina com erro listando os arquivos
ilegíveis, para ir atrás deles. PDF que abre mas não tem texto (só imagem) entra sem trechos e aparece na lista de
avisos.

## Reaproveitar vetores

Calcular 186 mil vetores leva minutos, mas não faz sentido refazê-los quando só chegaram PDFs novos. O script copia do
índice anterior o vetor de todo trecho com o mesmo arquivo, a mesma página e o mesmo texto. O que decide se um vetor
antigo vale é a chave `embedding` da tabela `meta`: modelo, prefixo, pooling, janela e corte dos trechos. Mudou
qualquer um deles, a chave muda, nada é reaproveitado e a busca não mistura dois espaços de vetores.

## Esquema gerado

| Tabela | Colunas |
|---|---|
| `documentos` | `arquivo` (caminho a partir de `data/raw`, chave), `area`, `empresa`, `cnpj`, `ano`, `tipo`, `titulo`, `url`, `paginas`, `bytes` |
| `paginas` | `arquivo`, `pagina`, `texto` |
| `trechos` | `id`, `arquivo`, `pagina`, `texto`, `embedding FLOAT[1024]` |
| `blocos` | `id`, `arquivo`, `pagina`, `texto` (um parágrafo do PDF, na ordem da página) |
| `meta` | `chave`, `valor`: `modelo`, `embedding`, `dimensoes`, `prefixo_trecho`, `prefixo_pergunta`, `gerado_em` e as contagens |

Mais os índices BM25 `fts_main_trechos` e `fts_main_blocos` (stemmer português, sem acento, mantendo números como
"escopo 1" e "tCO2e").

## Quem lê o índice

- `data/linha_do_tempo.py` lê `data/docs.duckdb`: precisa de `blocos`, `fts_main_blocos` e de `documentos.empresa` e
  `documentos.ano` preenchidos. É o consumidor direto deste índice.
- `proper_mcps/docs/server.py` e `proper_mcps/docs/busca.py` leem `data/docs_titan.duckdb` e transformam a pergunta em
  vetor com o **Amazon Titan** pelo Bedrock. O esquema é o mesmo (1024 dimensões, coluna `area`), mas o espaço de
  vetores não: pergunta em Titan contra trechos em e5 devolve lixo. Para usar este índice ali é preciso trocar o
  `_embed` do `server.py` pelo e5 com `query: ` (e ter o modelo onde o servidor roda); enquanto isso não acontecer, os
  dois índices convivem, e o `docs_titan.duckdb` continua sendo o do chat. O BM25 e a tabela `blocos`, que não
  dependem de embedding, funcionam nos dois.

## Depois de indexar

```bash
.runtime/venv/bin/python -m pytest proper_mcps data -q
.runtime/venv/bin/python data/linha_do_tempo.py      # refaz a aba Timeline a partir de blocos
```
