"""O painel fixo sobre o video: a barra de som e a frase que passa.

E discreto de proposito. Nao e informacao que alguem va ler com atencao: e a
textura de estar vendo uma camera ligada, e some da consciencia de quem assiste
em dois segundos. Por isso ocupa duas linhas finas no topo, na zona segura, e
nunca desce ate a legenda.

DUAS PECAS, E ELAS SE MEDEM DE JEITOS DIFERENTES:

- a **barra de som** e gerada pelo proprio ffmpeg a partir do audio, quadro a
  quadro. Nao passa pelo Pillow -- desenhar 1620 imagens de barra para um filme
  de 54 segundos custaria mais do que todo o resto da montagem junto.
- a **frase que passa** e UMA imagem do Pillow, deslizada por uma expressao de
  tempo do `overlay`. Tambem nao ha um quadro por posicao.
"""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from motor import config, estilos, probe

# --- onde as duas pecas ficam ------------------------------------------------
# Entre SEGURO_TOPO (acima disso o aplicativo desenha a propria interface) e a
# legenda, que comeca por volta de 1300. Nao ha o que negociar aqui: o resto do
# quadro e o rosto de quem fala.
VU_Y = 196
VU_X = 60
FRASE_Y = 226

# --- a barra de som ----------------------------------------------------------
VU_LARGURA = 400        # entre 80 e 8192, limite do proprio filtro
VU_ALTURA = 10
VU_PASSO = 2            # tamanho do segmento. 0 e barra continua, 5 e o maximo
VU_QUEDA = 0.25         # quanto o pico cai por quadro. Alto demais e a barra
                        # pisca; baixo demais ela nunca desce
VU_FUNDO = 0.14         # a canaleta apagada, atras da barra
VU_COR = "0xFFFFFFFF"   # AABBGGRR: branco solido. As duas pecas do painel usam
                        # a MESMA tinta -- com opacidades diferentes uma parece
                        # mais presente que a outra, e o painel deixa de ler
                        # como uma coisa so

# MEDIDO, e a medida mudou o desenho. Com o audio ja normalizado a -14 LUFS, a
# escala LOGARITMICA satura: as cinco amostras do filme real ficaram entre 85% e
# 95% da barra, e ela praticamente nao se mexia. Em RMS linear a barra andava,
# mas entre 10% e 28% -- fina demais para se ver. Em PICO linear foi de 35% a
# 55%, que e o unico dos tres em que da para ver o som subir e descer.
VU_MODO = "m=p:ds=lin"

# --- a frase que passa -------------------------------------------------------
FRASE_CORPO = 22
FRASE_CONTORNO = 0      # sem contorno, a pedido, e branca chapada como a barra.
                        # MEDIDO, porque o custo e real e tem numero: a variacao
                        # de brilho na faixa da frase cai de 71,7 para 0,0 sobre
                        # fundo BRANCO -- ela some inteira -- e de 62,8 para
                        # 13,1 sobre cinza claro. Sobre fundo escuro empata
                        # (90,1 contra 93,6), e na gravacao real, de parede
                        # bege, ela mede 69,7 e se le melhor SEM contorno do que
                        # com ele, porque a tinta subiu de 80% para 100%.
                        # Se um dia a frase sumir sobre uma parede branca, e
                        # este numero que volta a 2. `tests/test_hud.py` guarda
                        # os dois lados.
SEPARADOR = "   ·   "
VELOCIDADE = 90         # pixels por segundo. A 200 vira borrao; a 40 parece
                        # travada. 90 atravessa a tela em 12 segundos
FRASE_MAX = 90          # letras. Acima disso ninguem le uma frase que anda


def _fonte(corpo):
    """A monoespacada da legenda. O painel nao segue o estilo escolhido: ele e
    a moldura, e mudar de letra junto com a legenda o faria virar mais um
    elemento de design em vez de moldura."""
    return ImageFont.truetype(estilos.fonte_da_legenda("monoespaço"), corpo)


def tira(texto, destino, corpo=FRASE_CORPO, largura_tela=None):
    """A imagem da frase, repetida, pronta para deslizar em laco perfeito.

    Devolve `(caminho, passo)`: `passo` e a largura de UMA repeticao, e e por
    ela que a expressao de tempo faz a volta. A imagem tem DUAS repeticoes
    lado a lado, e e isso que fecha o laco sem emenda visivel: quando a
    primeira sai pela direita, a segunda ja esta desenhada atras dela.
    """
    largura_tela = largura_tela or config.W
    texto = " ".join((texto or "").split()).upper()[:FRASE_MAX]
    if not texto:
        raise ValueError("a frase do painel esta vazia")

    f = _fonte(corpo)
    bloco = texto + SEPARADOR
    medida = Image.new("RGBA", (1, 1))
    d0 = ImageDraw.Draw(medida)
    w_bloco = int(d0.textlength(bloco, font=f))

    # UMA repeticao tem de ser mais larga que a tela. Se a frase for curta, ela
    # entra varias vezes: sem isso, o ponto de volta cairia dentro da tela e a
    # frase sumiria por um instante antes de voltar.
    vezes = max(1, -(-largura_tela // max(1, w_bloco)))
    passo = w_bloco * vezes
    sobe, desce = f.getmetrics()
    alto = sobe + desce + FRASE_CONTORNO * 2

    im = Image.new("RGBA", (passo * 2, alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(vezes * 2):
        d.text((i * w_bloco, FRASE_CONTORNO), bloco, font=f,
               fill=(255, 255, 255, 255),
               stroke_width=FRASE_CONTORNO, stroke_fill=(0, 0, 0, 150))
    destino = Path(destino)
    im.save(destino)
    return destino, passo


def aplicar(filme, destino, texto=None, voz=None, vu=True, velocidade=None):
    """Poe o painel sobre o filme inteiro e devolve `destino`.

    `voz` e o filme ANTES da trilha. A barra tem de responder a quem fala, e
    nao a musica: alimentada pelo audio final, ela sobe e desce com a batida,
    que e o contrario do que o painel diz. Sem `voz`, usa o audio do proprio
    filme.

    NADA DE `-shortest`. Como em toda composicao deste motor, ele comeria
    quadros de video e deixaria o audio inteiro; quem fixa a duracao e o `-t`.
    """
    filme, destino = Path(filme), Path(destino)
    dur = probe.dur(filme)
    vel = VELOCIDADE if velocidade is None else velocidade
    entradas = ["-i", str(filme)]
    cadeia, atual, prox = [], "0:v", 1

    if vu:
        # o audio da voz entra como arquivo proprio quando existe; senao, sai
        # do proprio filme, que ja tem musica por baixo
        if voz is not None:
            entradas += ["-i", str(voz)]
            fonte_audio = f"{prox}:a"
            prox += 1
        else:
            fonte_audio = "0:a"
        cadeia.append(
            f"[{fonte_audio}]pan=mono|c0=0.5*c0+0.5*c1,"
            f"showvolume=rate={config.FPS}:b=0:w={VU_LARGURA}:h={VU_ALTURA}:"
            f"f={VU_QUEDA}:s={VU_PASSO}:p={VU_FUNDO}:t=0:v=0:o=h:{VU_MODO}:"
            f"c={VU_COR}[vu]")
        cadeia.append(f"[{atual}][vu]overlay={VU_X}:{VU_Y}:"
                      f"eof_action=pass[cv]")
        atual = "cv"

    if texto:
        arq, passo = tira(texto, destino.parent / f".tira-{destino.stem}.png")
        entradas += ["-loop", "1", "-i", str(arq)]
        # a imagem tem duas repeticoes; x anda de -passo ate 0 e recomeca. O
        # sinal e o que faz a frase ir para a DIREITA: em t=0 ela esta um passo
        # atras, e vai chegando.
        cadeia.append(
            f"[{atual}][{prox}:v]overlay="
            f"x='-{passo}+mod(t*{vel}\\,{passo})':y={FRASE_Y}:"
            f"eof_action=pass[fv]")
        atual = "fv"
        prox += 1

    if not cadeia:
        raise ValueError("o painel foi pedido sem barra e sem frase")

    cadeia.append(f"[{atual}]format=yuv420p[v]")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", *entradas,
         "-filter_complex", ";".join(cadeia),
         "-map", "[v]", "-map", "0:a?",
         "-t", f"{dur:.3f}",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-c:a", "copy", "-movflags", "+faststart", str(destino)],
        check=True, capture_output=True)
    return destino
