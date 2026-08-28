"""Letreiro e moldura, desenhados com Pillow.

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


def _fatia(desenho, palavra, fonte_pil, largura_max):
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


def _quebra_forcando_largura(desenho, texto, fonte_pil, largura_max):
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
            pedacos = _fatia(desenho, palavra, fonte_pil, largura_max)
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


def letreiro(texto, estilo, destino, base=None, contorno=None):
    """PNG 1080x1920 transparente com o texto apoiado em `base`.

    O corpo encolhe ate caber na largura. No projeto de origem um letreiro de
    300pt vazou o quadro em 1075 de 1080 -- a busca evita isso.

    Se mesmo no corpo minimo uma palavra sozinha for mais larga que o quadro
    (por exemplo um token sem espaco de 40 caracteres), ela e fatiada em mais
    de uma linha em vez de vazar a margem -- ver `_quebra_forcando_largura`."""
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
        linhas = _quebra_forcando_largura(d_sonda, texto, f, largura_max)

    im = Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    altura_linha = corpo * ENTRELINHA
    y = base - altura_linha * len(linhas)
    for linha in linhas:
        largura = d.textlength(linha, font=f)
        d.text(((config.W - largura) / 2, y), linha, font=f,
               fill=estilos.rgb(ficha["texto"]) + (255,),
               stroke_width=contorno,
               stroke_fill=estilos.rgb(ficha["contorno"]) + (255,))
        y += altura_linha
    im.save(destino)
    return destino


def moldura(estilo, destino, janela=None):
    """Moldura de televendas: cor chapada com uma janela vazada no meio, por
    onde a imagem aparece. `janela` = (x, y, largura, altura)."""
    ficha = estilos.carregar(estilo)
    jx, jy, jw, jh = janela or (60, 429, 960, 1411)
    im = Image.new("RGBA", (config.W, config.H),
                   estilos.rgb(ficha["fundo"]) + (255,))
    d = ImageDraw.Draw(im)
    d.rectangle([jx, jy, jx + jw, jy + jh], fill=(0, 0, 0, 0))
    im.save(destino)
    return destino, (jx, jy, jw, jh)
