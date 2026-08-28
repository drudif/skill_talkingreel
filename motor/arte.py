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
