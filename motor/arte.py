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


def letreiro(texto, escolhas, destino, base=None, contorno=None):
    """PNG 1080x1920 transparente com o texto apoiado em `base`.

    `escolhas` e o que a pessoa escolheu -- `{"fonte": ..., "paleta": ...,
    "efeito": ...}` -- ou None para o padrao. O antigo `box=True` virou
    `efeito: "caixa"`: era a mesma decisao dita duas vezes, uma como parametro
    solto e outra dentro da ficha de estilo.

    O corpo encolhe ate caber na largura. No projeto de origem um letreiro de
    300pt vazou o quadro em 1075 de 1080 -- a busca evita isso.

    Se mesmo no corpo minimo uma palavra sozinha for mais larga que o quadro
    (por exemplo um token sem espaco de 40 caracteres), ela e fatiada em mais
    de uma linha em vez de vazar a margem -- ver `quebra_forcando_largura`.

    No efeito `caixa` sai um retangulo cheio atras do texto, com folga de
    `FOLGA_BOX` em volta da mancha de tinta (nao do quadro inteiro) --
    sustentacao para quando o letreiro cai sobre imagem clara e o contorno
    sozinho nao basta. A paleta ja traz a cor da caixa e a da letra dentro
    dela, que sao diferentes das de fora: amarelo com contorno preto se le bem
    sobre video, mas amarelo dentro de caixa amarela sumiria.

    Sem grafismo alem disso: nao ha moldura de cena, so o que sustenta o
    proprio letreiro."""
    peca = estilos.compor(escolhas, "letreiro")
    caminho_fonte = peca["arquivo"]
    box = peca["efeito"] == "caixa"
    base = BASE_PADRAO if base is None else base
    contorno = CONTORNO if contorno is None else contorno
    largura_max = config.W - MARGEM * 2

    linhas, f, maior = None, None, None
    corpo = peca["corpo"]
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

    # Onde a ultima linha se apoia sai da METRICA DA FONTE, e nao de
    # `corpo * ENTRELINHA`. As duas coisas nao sao a mesma: a entrelinha e o
    # espaco ENTRE linhas, e a metrica e quanto a letra ocupa de fato.
    #
    # MEDIDO em corpo 104: a conta antiga reservava 114px para toda fonte,
    # enquanto as cinco de display ocupam de 124 a 159. Com a mais alta o texto
    # descia 46px abaixo da base pedida -- e a base existe justamente para o
    # letreiro nao cair onde o aplicativo desenha a propria interface.
    subida, descida = f.getmetrics()
    altura_linha = corpo * ENTRELINHA
    y = base - descida - subida - altura_linha * (len(linhas) - 1)
    cor_texto = estilos.rgb(peca["texto"]) + (255,)
    # dentro da caixa o contorno some: a caixa ja separa a letra da imagem, e
    # contorno por cima de fundo cheio so engrossa o traco.
    cor_contorno = (estilos.rgb(peca["caixa"]) if box
                    else estilos.rgb(peca["contorno"])) + (255,)

    im = Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    if box:
        # sonda a mancha real de tinta numa camada a
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
            d.rectangle([bx0, by0, bx1, by1],
                        fill=estilos.rgb(peca["caixa"]) + (255,))

    _desenha_linhas(d, linhas, f, y, altura_linha, cor_texto, contorno,
                    cor_contorno)
    im.save(destino)
    return destino


# --- o letreiro entrando ---
#
# UMA ENTRADA SO: a frase se monta palavra a palavra. Houve sete por um tempo --
# surgir de leve, subir, vir da esquerda, pular, varrer, digitar letra a letra --
# e a escolha entre elas nao mudava nada que importasse. Uma entrada so tambem
# tira uma decisao do caminho de quem esta tentando publicar um video.
#
# O texto continua sendo desenhado pelo Pillow, com a busca de corpo e a quebra
# de linha que ja existiam. Depois da entrada o letreiro fica parado, e o quadro
# parado e repetido pelo proprio ffmpeg (`tpad`), sem gerar imagem a mais.

ENTRADA = 0.45       # quanto dura a entrada inteira, do vazio a frase completa.
                     # ESTIMATIVA, nao medicao: e o tempo em que o olho
                     # acompanha as palavras entrando sem que isso atrase a
                     # leitura. Mais curto vira estalo; mais longo rouba tempo
                     # de quem esta lendo.


def letreiro_animado(texto, escolhas, destino, dur=None, base=None,
                     contorno=None, fps=None, entrada=None):
    """O letreiro como peca de video com fundo transparente, montando-se
    palavra a palavra.

    `dur` e quanto a peca dura no total; sem ela, a peca acaba quando a entrada
    acaba.

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

    fps = config.FPS if fps is None else fps
    entrada = ENTRADA if entrada is None else entrada
    pasta = Path(tempfile.mkdtemp(prefix="letreiro-"))
    try:
        # a frase inteira, primeiro: e dela que sai a posicao em que todos os
        # pedacos se apoiam. Centralizar cada pedaco faria o texto pular de
        # lugar a cada palavra que entra.
        png_caminho = letreiro(texto, escolhas, pasta / "base.png", base=base,
                               contorno=contorno)
        inteira = Image.open(png_caminho).convert("RGBA")
        mancha = inteira.getchannel("A").getbbox()
        if mancha is None:                      # texto vazio: nada a animar
            mancha = (0, 0, inteira.width, inteira.height)

        palavras = texto.split()
        pedacos = [" ".join(palavras[:i + 1]) for i in range(len(palavras))] \
            or [texto]

        prontos = []
        for i, pedaco in enumerate(pedacos):
            parcial = letreiro(pedaco, escolhas, pasta / f"p{i:04d}.png",
                               base=base, contorno=contorno)
            im = Image.open(parcial).convert("RGBA")
            caixa = im.getchannel("A").getbbox()
            encaixado = Image.new("RGBA", im.size, (0, 0, 0, 0))
            if caixa:
                encaixado.paste(im.crop(caixa), (mancha[0], caixa[1]))
            prontos.append(encaixado)
            (pasta / f"p{i:04d}.png").unlink(missing_ok=True)

        # Cada pedaco e desenhado UMA vez e repetido pelos quadros que couberem.
        # Sem isso a entrada dura um quadro por palavra: numa frase de tres
        # palavras isso da um decimo de segundo, e a frase inteira aparece antes
        # de dar para ver a primeira.
        n = max(len(prontos), int(round(entrada * fps)))
        for i in range(n):
            prontos[min(len(prontos) - 1,
                        i * len(prontos) // n)].save(pasta / f"q{i:04d}.png")

        parada = ""
        if dur is not None and dur > entrada:
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
