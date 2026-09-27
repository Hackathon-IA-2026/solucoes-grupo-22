# Vídeo de demonstração do EnergyNexus

Resultado: `../img/demo_energynexus.mp4` — 71 s · 1920x1080 · 25 fps · sem áudio (a capa usada no README,
`../img/demo_capa.jpg`, é um quadro dele).

Feito para apresentação executiva: cada afirmação aparece numa cartela de texto em tela cheia e é
provada na tela seguinte, com a interface limpa. Nenhuma legenda cobre a interface.

## Como é produzido

Três etapas, nesta ordem:

1. **Gravação** (`gravar3.js` e os passes `pickupN.js`) — Playwright abre o Chromium em 1440x810 CSS
   com `deviceScaleFactor` 4/3, de modo que cada quadro sai em 1920x1080 com a interface 33% maior
   do que o normal (é o que deixa o texto legível em projetor). Não usa `recordVideo`: grava uma
   sequência de PNGs por cena, em `frames/<NN_nome>/%06d.png`, e escreve um `relato*.json` com o
   número de quadros e as marcas de cada cena.
2. **Arte** (`arte.js`) — as cartelas e os selos são HTML/CSS renderizados pelo próprio Chromium em
   3840x2160, com a fonte Inter do produto embutida. O texto delas está em `copia.json`.
3. **Montagem** (`montar.py`) — ffmpeg. Cada segmento vira um clipe com o mesmo codec, os clipes são
   costurados com dissolve (`xfade`) e um passe final põe a barra de progresso e os fades.

Os passes de pickup regravam apenas as cenas que precisavam de correção; quando duas gravações têm a
mesma cena, vale a mais recente na lista de `relato*.json` dentro de `montar.py`.

## Parâmetros por cena (no `ROTEIRO` de `montar.py`)

| parâmetro | efeito |
|---|---|
| `vel` | acelera a cena (>1); usado nas gerações e nas rolagens longas |
| `de` / `ate` | recorta o intervalo de quadros |
| `y` | aproximação de 1,33x (`crop=1440:810:480:y`), para leitura confortável em projetor |
| `caixas` | retângulos pintados com a cor do fundo, antes do recorte (apagam o ponteiro falso que ficou parado numa cena) |

## O que precisa estar de pé

- LibreChat em `http://127.0.0.1:3090` (`./iniciar.sh`), com o usuário do demo.
- Node do projeto: `PATH=.runtime/bin:$PATH` (v24).
- Chromium do Playwright e ffmpeg/ffprobe.
- A conversa da comparação já gravada no histórico (os passes de pickup a reabrem e param qualquer
  geração pendente antes de gravar, para não filmar tela em movimento).

O perfil usado no vídeo é o **EnergyNexus Analista (Claude)** — `bedrock` /
`us.anthropic.claude-sonnet-5`. Os scripts trocam o perfil pelo seletor de modelo da interface
(`?spec=` na URL não funciona) e abortam se o `endpoint` não ficar em `bedrock`.

Os quadros (~500 MB) e a arte renderizada não ficam versionados: são regerados pelos scripts.

Todos os scripts trabalham dentro de `$DEMO_DIR` (quadros, arte, segmentos e saída). Sem essa
variável, usam a própria pasta deles. Para não encher o repositório, aponte para um diretório de
trabalho:

```bash
export DEMO_DIR=/caminho/para/um/diretorio/de/trabalho
export PATH=$PWD/../.runtime/bin:$PATH
export DEMO_EMAIL=... DEMO_SENHA=...   # usuário do LibreChat que aparece na gravação
cp demo/copia.json "$DEMO_DIR"/
node demo/gravar3.js && node demo/arte.js && python3 demo/montar.py
```
