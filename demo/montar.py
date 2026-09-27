#!/usr/bin/env python3
"""Monta o vídeo executivo do EnergyNexus a partir dos frames gravados e da arte renderizada.

Estrutura: cartela de texto -> cena de tela limpa -> cartela -> cena... Cada afirmação é dita numa
cartela e provada na tela seguinte, então NENHUMA legenda cobre a interface (era o defeito da versão
anterior: caixas negras em cima justamente dos números).

Três passos:
  1. cada segmento vira um clipe 1920x1080@25 com os mesmos parâmetros de codec;
  2. os clipes são costurados com xfade (dissolve), sem cortes secos;
  3. um passe final põe a barra de progresso e os fades de entrada e saída.

Parâmetros por cena:
  vel   -> >1 acelera (geração e rolagens longas no ritmo certo)
  de/ate-> recorta o intervalo de quadros da cena (o pedido do PDF, por exemplo, só usa o começo)
  y     -> aproximação de 1,33x na coluna da conversa (crop 1440x810 em x=480), para o texto ficar
           confortável de ler em projetor; `y` é onde o recorte começa na vertical
  caixas-> retângulos (x,y,l,a) pintados com a cor do fundo, antes do recorte, para apagar o ponto
           do ponteiro falso que ficou parado numa cena (o fundo ali é chapado, então não deixa marca)

Rodar: python3 montar.py
"""
import json
import os
import subprocess
import sys

T = os.environ.get('DEMO_DIR', os.path.dirname(os.path.abspath(__file__)))
FRAMES = f'{T}/frames'
ARTE = f'{T}/arte'
SEG = f'{T}/seg'
SAIDA = f'{T}/demo_executiva.mp4'
FPS = 25
W, H = 1920, 1080
ACENTO = '0x8b5cf6'  # roxo da marca (violet-500)

# ---------------------------------------------------------------- roteiro
ROTEIRO = [
    {'tipo': 'cartela', 'arte': 'c00_abertura',   'dur': 4.4, 'zoom': 0.030},
    {'tipo': 'cartela', 'arte': 'c10_pergunta',   'dur': 2.6, 'zoom': 0.022},
    # 01_abertura sai: a tela inicial gravada ficou com o perfil padrão, e não com o do Claude —
    # 02_pergunta já abre na mesma tela, com o cabeçalho certo e a pergunta sendo digitada
    {'tipo': 'cena',    'cena': '02_pergunta',    'vel': 1.0, 'y': 0},
    {'tipo': 'cartela', 'arte': 'c20_apuracao',   'dur': 2.6, 'zoom': 0.022},
    # o ponteiro falso ficou parado sobre o botão de enviar durante toda a geração: apaga o ponto
    {'tipo': 'cena',    'cena': '03_ferramentas', 'vel': 2.2, 'ate': 150,
     'caixas': [(1708, 697, 90, 88)], 'cor_fundo': '0x221535'},
    # e então as sete consultas nomeadas, uma por linha: é a prova do que a cartela afirmou
    {'tipo': 'cena',    'cena': '03b_ferramentas', 'vel': 1.0, 'ate': 70, 'y': 180},
    {'tipo': 'cartela', 'arte': 'c30_veredito',   'dur': 2.6, 'zoom': 0.022},
    {'tipo': 'cena',    'cena': '04_conclusao',   'vel': 1.0, 'y': 40},
    {'tipo': 'cena',    'cena': '05_tabela',      'vel': 1.25, 'y': 135},
    {'tipo': 'cartela', 'arte': 'c40_prova',      'dur': 2.4, 'zoom': 0.022},
    {'tipo': 'cena',    'cena': '06_fonte',       'vel': 1.0, 'y': 100},
    {'tipo': 'cartela', 'arte': 'c50_entregavel', 'dur': 2.6, 'zoom': 0.022},
    # do pedido só interessa o clique no botão do produto; a espera da geração sai fora
    {'tipo': 'cena',    'cena': '07_relatorio',   'vel': 1.0, 'de': 1, 'ate': 58},
    {'tipo': 'cena',    'cena': '07b_pdf',        'vel': 1.0},
    {'tipo': 'cena',    'cena': '07c_folhas',     'vel': 1.25},
    {'tipo': 'cartela', 'arte': 'c60_plataforma', 'dur': 2.4, 'zoom': 0.022},
    {'tipo': 'cena',    'cena': '08_grafo',       'vel': 1.3},
    # os primeiros quadros do painel mostram a nota metodológica: entra já na rolagem dos cartões
    {'tipo': 'cena',    'cena': '09_painel',      'vel': 1.1, 'de': 40, 'y': 270},
    {'tipo': 'cena',    'cena': '10_timeline',    'vel': 1.15, 'y': 150},
    {'tipo': 'cena',    'cena': '11_busca',       'vel': 1.3, 'y': 100},
    {'tipo': 'cartela', 'arte': 'c99_final',      'dur': 4.6, 'zoom': 0.026},
]
TRANSICAO = 0.34  # segundos de dissolve entre segmentos

# recorte da coluna da conversa: 1440x810 é 16:9 exato, então amplia 1,33x sem distorcer
CORTE_L, CORTE_A, CORTE_X = 1440, 810, 480


def rodar(cmd, desc):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print(f'FALHOU: {desc}')
        print(r.stderr[-2500:])
        sys.exit(1)
    return r.stdout


def duracao(arq):
    s = subprocess.run(
        f'ffprobe -v quiet -show_entries format=duration -of csv=p=0 "{arq}"',
        shell=True, capture_output=True, text=True).stdout.strip()
    return float(s)


CODEC = '-c:v libx264 -preset medium -crf 17 -pix_fmt yuv420p -r 25 -g 50'


def clipe_cartela(arte, dur, zoom, saida):
    """Cartela 3840x2160 com um empurrão de câmera lento; a redução para 1080p mantém tudo nítido."""
    n = max(2, int(round(dur * FPS)))
    vf = (f"zoompan=z='1+{zoom}*on/{n}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":s={W}x{H}:fps={FPS},format=yuv420p")
    rodar(f'ffmpeg -y -loop 1 -i "{ARTE}/{arte}.png" -frames:v {n} -vf "{vf}" {CODEC} "{saida}"',
          f'cartela {arte}')


def clipe_cena(s, quadros, saida):
    d = f'{FRAMES}/{s["cena"]}'
    de = s.get('de', 1)
    ate = min(s.get('ate', quadros), quadros)
    filtros = []
    for (cx, cy, cl, ca) in s.get('caixas', []):
        filtros.append(f'drawbox=x={cx}:y={cy}:w={cl}:h={ca}:'
                       f'color={s.get("cor_fundo", "black")}:t=fill')
    if 'y' in s:
        filtros.append(f'crop={CORTE_L}:{CORTE_A}:{CORTE_X}:{s["y"]}')
        filtros.append(f'scale={W}:{H}:flags=lanczos')
    vel = s.get('vel', 1.0)
    if abs(vel - 1.0) > 1e-3:
        filtros.append(f'setpts=PTS/{vel}')
    filtros.append(f'fps={FPS}')
    if 'y' not in s:
        filtros.append(f'scale={W}:{H}')
    filtros.append('format=yuv420p')
    rodar(f'ffmpeg -y -framerate {FPS} -start_number {de} -i "{d}/%06d.png" '
          f'-frames:v {ate - de + 1} -vf "{",".join(filtros)}" {CODEC} "{saida}"',
          f'cena {s["cena"]}')


def main():
    # o relato do pickup manda nas cenas que foram regravadas
    cenas = {}
    for arq in ('relato.json', 'relato_pickup.json', 'relato_pickup2.json',
                'relato_pickup4.json', 'relato_pickup5.json',
                'relato_pickup6.json'):
        p = f'{T}/{arq}'
        if not os.path.exists(p):
            continue
        r = json.load(open(p))
        for c in r['cenas']:
            if c['frames'] >= 3:
                cenas[c['nome']] = dict(c, origem=arq)
    base = json.load(open(f'{T}/relato.json'))
    print(f"modelo gravado: {base['textos'].get('modelo')}")
    for nome in sorted(cenas):
        c = cenas[nome]
        print(f"  {nome:<16} {c['frames']:>5} frames  {c['segundos']:>6.2f}s  {c['origem']}  marcas={c['marcas']}")

    os.makedirs(SEG, exist_ok=True)
    clipes = []
    for i, s in enumerate(ROTEIRO):
        saida = f'{SEG}/{i:02d}.mp4'
        if s['tipo'] == 'cartela':
            clipe_cartela(s['arte'], s['dur'], s.get('zoom', 0.0), saida)
            rotulo = s['arte']
        else:
            if s['cena'] not in cenas:
                print(f"  -- pula {s['cena']}: não foi gravada")
                continue
            clipe_cena(s, cenas[s['cena']]['frames'], saida)
            rotulo = s['cena']
        clipes.append({'arq': saida, 'rotulo': rotulo, 'dur': duracao(saida)})
        print(f"  clipe {i:02d} {rotulo:<16} {clipes[-1]['dur']:.2f}s")

    # ---- costura com dissolve
    entradas = ' '.join(f'-i "{c["arq"]}"' for c in clipes)
    partes, atual, acumulado = [], '[0:v]', clipes[0]['dur']
    for i in range(1, len(clipes)):
        deslocamento = acumulado - TRANSICAO
        rotulo = f'[v{i}]'
        partes.append(f'{atual}[{i}:v]xfade=transition=fade:duration={TRANSICAO}:'
                      f'offset={deslocamento:.3f}{rotulo}')
        atual = rotulo
        acumulado = acumulado + clipes[i]['dur'] - TRANSICAO
    fg = ';'.join(partes) if partes else ''
    bruto = f'{T}/bruto.mp4'
    if fg:
        rodar(f'ffmpeg -y {entradas} -filter_complex "{fg}" -map "{atual}" {CODEC} "{bruto}"',
              'costurar segmentos')
    else:
        rodar(f'ffmpeg -y -i "{clipes[0]["arq"]}" {CODEC} "{bruto}"', 'copiar único segmento')

    total = duracao(bruto)
    # ---- passe final: barra de progresso discreta + fades
    barra = (f"drawbox=x=0:y={H-5}:w=iw:h=5:color=black@0.42:t=fill,"
             f"drawbox=x=0:y={H-5}:w='iw*t/{total:.3f}':h=5:color={ACENTO}@0.95:t=fill")
    fades = f'fade=t=in:st=0:d=0.6,fade=t=out:st={total-0.8:.3f}:d=0.8'
    rodar(f'ffmpeg -y -i "{bruto}" -vf "{barra},{fades}" '
          f'-c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -movflags +faststart "{SAIDA}"',
          'barra de progresso e fades')

    print('\nlinha do tempo:')
    t = 0.0
    for i, c in enumerate(clipes):
        fim = t + c['dur'] - (TRANSICAO if i > 0 else 0)
        print(f'  {t:6.2f} -> {fim:6.2f}  {c["rotulo"]}')
        t = fim
    print(f'\n✓ {SAIDA}')
    print(f'  {duracao(SAIDA):.1f}s · {os.path.getsize(SAIDA)/1024/1024:.1f} MB · {W}x{H}@{FPS}')


if __name__ == '__main__':
    main()
