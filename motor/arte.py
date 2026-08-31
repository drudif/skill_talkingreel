"""Letreiro, desenhado com Pillow. No maximo um box atras dele para
sustentacao -- sem grafismo decorativo, sem moldura de cena. Essa e uma
decisao de escopo do dono do projeto: a skill nao faz enfeite.

POR QUE NAO MODELO DE IMAGEM: modelo erra acento em portugues -- escreve "nao"
no lugar de "não" com til, "voce" sem o circunflexo. Letreiro e legenda sao
texto vetorial, sempre.

O CONTORNO IMPORTA: no projeto de origem o letreiro de abertura ficou ilegivel
sobre o rosto ate ganhar contorno preto de 7px, como legenda de televisao."""
from PIL import Image, ImageDraw, ImageFont

from motor import config, estilos

MARGEM = 60          # folga lateral minima
BASE_PADRAO = 1560   # onde o letreiro se apoia, quando ninguem diz
CONTORNO = 7          # espessura do contorno, em pixels
ENTRELINHA = 1.10
CORPO_MINIMO = 24    # corpo menor que este nao encolhe mais -- quebra a palavra
FOLGA_BOX = 28       # folga do box em volta da mancha de texto, quando box=True


def _quebra(desenho, texto, fonte_pil, largura_max):
    linhas, atual = [], ""
    for palavra in texto.split():
        tentativa = (atual + " " + palavra).strip()
        if desenho.textlength(tentativa, font=fonte_pil) <= largura_max:
            atual = tentativa
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def fatia(desenho, palavra, fonte_pil, largura_max):
    """Quebra uma palavra unica que sozinha nao cabe na largura maxima,
    caractere a caractere. So acontece com corpo ja no minimo e uma palavra
    mais larga que o quadro -- por exemplo um token de 40 letras sem espaco."""
    partes, atual = [], ""
    for c in palavra:
        tentativa = atual + c
        if desenho.textlength(tentativa, font=fonte_pil) <= largura_max or not atual:
            atual = tentativa
        else:
            partes.append(atual)
            atual = c
    if atual:
        partes.append(atual)
    return partes


def quebra_forcando_largura(desenho, texto, fonte_pil, largura_max):
    """Como `_quebra`, mas se uma palavra sozinha estourar a largura maxima
    ela e fatiada em pedacos que cabem, em vez de vazar o quadro."""
    linhas, atual = [], ""
    for palavra in texto.split():
        tentativa = (atual + " " + palavra).strip()
        if desenho.textlength(tentativa, font=fonte_pil) <= largura_max:
            atual = tentativa
            continue
        if atual:
            linhas.append(atual)
            atual = ""
        if desenho.textlength(palavra, font=fonte_pil) <= largura_max:
            atual = palavra
        else:
            # a palavra sozinha nao cabe nem em uma linha vazia: fatia
            pedacos = fatia(desenho, palavra, fonte_pil, largura_max)
            linhas.extend(pedacos[:-1])
            atual = pedacos[-1] if pedacos else ""
    if atual:
        linhas.append(atual)
    return linhas


def _cabe(texto, caminho_fonte, corpo, largura_max):
    im = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(caminho_fonte, corpo)
    linhas = _quebra(d, texto, f, largura_max)
    maior = max(d.textlength(l, font=f) for l in linhas) if linhas else 0
    return linhas, f, maior


def _desenha_linhas(d, linhas, f, y_inicial, altura_linha, cor_texto,
                    contorno, cor_contorno):
    """Desenha as linhas centralizadas, empilhando de cima para baixo a
    partir de `y_inicial`. Usado tanto pra sondar a mancha real de tinta
    quanto pro desenho final -- as duas passadas tem que ser identicas,
    senao a mancha sondada nao bate com o que sai no PNG."""
    y = y_inicial
    for linha in linhas:
        largura = d.textlength(linha, font=f)
        d.text(((config.W - largura) / 2, y), linha, font=f,
               fill=cor_texto, stroke_width=contorno, stroke_fill=cor_contorno)
        y += altura_linha


def letreiro(texto, estilo, destino, base=None, contorno=None, box=False):
    """PNG 1080x1920 transparente com o texto apoiado em `base`.

    O corpo encolhe ate caber na largura. No projeto de origem um letreiro de
    300pt vazou o quadro em 1075 de 1080 -- a busca evita isso.

    Se mesmo no corpo minimo uma palavra sozinha for mais larga que o quadro
    (por exemplo um token sem espaco de 40 caracteres), ela e fatiada em mais
    de uma linha em vez de vazar a margem -- ver `quebra_forcando_largura`.

    `box=True` desenha um retangulo cheio na cor de fundo da ficha, atras do
    texto, com folga de `FOLGA_BOX` em volta da mancha de tinta (nao do
    quadro inteiro) -- sustentacao para quando o letreiro cai sobre imagem
    clara e o contorno sozinho nao basta. Sem grafismo alem disso: nao ha
    moldura de cena, so o que sustenta o proprio letreiro. Quando a cor de
    texto da ficha e igual a de fundo (caso do `brutalista`, amarelo nos
    dois -- o texto sumiria sobre o proprio box), o box usa a cor de
    `contorno` da ficha no lugar."""
    ficha = estilos.carregar(estilo)
    caminho_fonte = estilos.fonte(estilo)
    base = BASE_PADRAO if base is None else base
    contorno = CONTORNO if contorno is None else contorno
    largura_max = config.W - MARGEM * 2

    linhas, f, maior = None, None, None
    corpo = ficha["peso_letreiro"]
    while True:
        linhas, f, maior = _cabe(texto, caminho_fonte, corpo, largura_max)
        if maior <= largura_max or corpo <= CORPO_MINIMO:
            break
        corpo -= 4

    if maior > largura_max:
        # corpo ja no minimo e ainda vaza: alguma palavra e mais larga que o
        # quadro sozinha. Fatia em vez de deixar a tinta vazar a margem.
        im_sonda = Image.new("RGBA", (10, 10))
        d_sonda = ImageDraw.Draw(im_sonda)
        linhas = quebra_forcando_largura(d_sonda, texto, f, largura_max)

    altura_linha = corpo * ENTRELINHA
    y = base - altura_linha * len(linhas)
    cor_texto = estilos.rgb(ficha["texto"]) + (255,)
    cor_contorno = estilos.rgb(ficha["contorno"]) + (255,)

    im = Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    if box:
        # sonda a mancha real de tinta (contorno incluso) numa camada a
        # parte, pra apoiar o box nela -- a metrica nominal da fonte nao
        # bate com o pixel de tinta de verdade.
        sonda = Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0))
        _desenha_linhas(ImageDraw.Draw(sonda), linhas, f, y, altura_linha,
                        cor_texto, contorno, cor_contorno)
        mancha = sonda.getchannel("A").getbbox()
        if mancha is not None:
            x0, y0, x1, y1 = mancha
            bx0 = max(0, x0 - FOLGA_BOX)
            by0 = max(0, y0 - FOLGA_BOX)
            bx1 = min(config.W, x1 + FOLGA_BOX)
            by1 = min(config.H, y1 + FOLGA_BOX)
            cor_box = (ficha["contorno"] if ficha["fundo"] == ficha["texto"]
                      else ficha["fundo"])
            d.rectangle([bx0, by0, bx1, by1], fill=estilos.rgb(cor_box) + (255,))

    _desenha_linhas(d, linhas, f, y, altura_linha, cor_texto, contorno,
                    cor_contorno)
    im.save(destino)
    return destino


# --- o letreiro entrando ---
#
# O texto continua sendo desenhado UMA vez pelo Pillow, com a busca de corpo e
# a quebra de linha que ja existiam. A animacao so TRANSFORMA esse desenho
# quadro a quadro -- deslocar, redimensionar, clarear. Redesenhar o texto a
# cada quadro custaria a busca de corpo inteira trinta vezes por segundo, e o
# resultado seria o mesmo.
#
# A peca sai como um video com fundo transparente. Depois da entrada o letreiro
# fica parado, e o quadro parado e repetido pelo proprio ffmpeg (`tpad`), sem
# gerar imagem nenhuma a mais.

ENTRADA = 0.45       # quanto dura a entrada. ESTIMATIVA, nao medicao: e o
                     # tempo em que o olho acompanha o movimento sem que ele
                     # atrase a leitura. Mais curto vira estalo, mais longo
                     # rouba tempo de quem esta lendo.
DESLOCA = 90         # de quantos pixels o texto vem, nas entradas que deslizam
ANIMACOES = ("aparece", "sobe", "esquerda", "pulo")


def _suave(a):
    """Desacelerando no fim. Movimento com velocidade constante parece
    mecanico; o olho espera que a coisa chegue e assente."""
    return 1 - (1 - a) ** 3


def _com_repuxo(a):
    """Como `_suave`, mas passa um pouco do lugar e volta. E o que da o
    caracter de pulo."""
    s = 1.70158
    return 1 + (s + 1) * (a - 1) ** 3 + s * (a - 1) ** 2


def _quadro_da_entrada(png, animacao, avanco, mancha):
    """Um quadro da entrada. `avanco` vai de 0, no comeco, a 1, na posicao
    final. Devolve uma imagem do tamanho do quadro inteiro."""
    from PIL import Image
    if avanco >= 1.0 and animacao != "pulo":
        return png
    vazio = Image.new("RGBA", png.size, (0, 0, 0, 0))

    if animacao == "pulo":
        # a escala tem de girar em torno do centro da MANCHA de tinta, nao do
        # centro do quadro: o letreiro se apoia embaixo, e escalar pelo centro
        # do quadro faria ele subir e descer junto.
        e = 0.82 + 0.18 * _com_repuxo(avanco)
        x0, y0, x1, y1 = mancha
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        recorte = png.crop(mancha)
        nw = max(1, int(round(recorte.width * e)))
        nh = max(1, int(round(recorte.height * e)))
        vazio.paste(recorte.resize((nw, nh), Image.LANCZOS),
                    (int(round(cx - nw / 2)), int(round(cy - nh / 2))))
    else:
        dx = dy = 0
        if animacao == "sobe":
            dy = int(round(DESLOCA * (1 - _suave(avanco))))
        elif animacao == "esquerda":
            dx = -int(round(DESLOCA * (1 - _suave(avanco))))
        vazio.paste(png, (dx, dy))

    if avanco < 1.0:
        alfa = vazio.getchannel("A").point(lambda v: int(v * avanco))
        vazio.putalpha(alfa)
    return vazio


def letreiro_animado(texto, estilo, destino, animacao="aparece", dur=None,
                     base=None, contorno=None, box=False, fps=None,
                     entrada=None):
    """O letreiro como peca de video com fundo transparente, entrando.

    `animacao` e uma de ANIMACOES. `dur` e quanto a peca dura no total; sem
    ela, a peca acaba quando a entrada acaba.

    Sai em qtrle, que e o formato de video deste ffmpeg que guarda
    transparencia -- ou seja, que sabe dizer que parte do quadro nao tem tinta
    nenhuma e deixa o video de baixo aparecer. Comprimir em h264 aqui perderia
    isso e o letreiro entraria dentro de um retangulo preto.
    """
    import shutil
    import subprocess
    import tempfile
    from pathlib import Path
    from PIL import Image

    if animacao not in ANIMACOES:
        raise ValueError(
            f"nao conheco a animacao '{animacao}'. As que existem sao: "
            + ", ".join(ANIMACOES))
    fps = config.FPS if fps is None else fps
    entrada = ENTRADA if entrada is None else entrada
    pasta = Path(tempfile.mkdtemp(prefix="letreiro-"))
    try:
        png_caminho = letreiro(texto, estilo, pasta / "base.png", base=base,
                               contorno=contorno, box=box)
        png = Image.open(png_caminho).convert("RGBA")
        mancha = png.getchannel("A").getbbox()
        if mancha is None:                      # texto vazio: nada a animar
            mancha = (0, 0, png.width, png.height)

        n = max(1, int(round(entrada * fps)))
        for i in range(n):
            avanco = (i + 1) / n
            _quadro_da_entrada(png, animacao, avanco, mancha).save(
                pasta / f"q{i:04d}.png")

        parada = ""
        if dur is not None and dur > entrada:
            # o ffmpeg repete o ultimo quadro pelo resto do tempo. Gerar esses
            # quadros com o Pillow seria desenhar a mesma imagem dezenas de
            # vezes para nada.
            parada = f",tpad=stop_mode=clone:stop_duration={dur - entrada:.3f}"
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-framerate", str(fps),
             "-i", str(pasta / "q%04d.png"),
             "-vf", f"format=rgba{parada}",
             "-c:v", "qtrle", str(destino)], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("ffmpeg falhou ao montar o letreiro: "
                               + r.stderr.strip()[:400])
        return destino
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
