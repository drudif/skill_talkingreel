"""Como o video vai ficar, antes de montar o video.

DUAS PERGUNTAS DIFERENTES, DOIS ARTEFATOS.

1. "Qual destes sete estilos eu quero?" -- `amostra()` responde com um quadro da
   PROPRIA gravacao da pessoa, com a legenda e o letreiro daquele estilo por
   cima. Sete amostras, uma por estilo, e a escolha deixa de ser feita por
   descricao escrita.

2. "O corte ficou bom?" -- `em_baixa()` responde com o filme inteiro, pequeno e
   leve, para a pessoa assistir e aprovar antes da versao final.

POR QUE O QUADRO E DA GRAVACAO DELA. Um catalogo com foto de outra pessoa
mostra o estilo, nao mostra o resultado. Cor de fundo e contorno de letra se
comportam de um jeito sobre um rosto claro e de outro sobre um rosto escuro, e
a decisao muda.
"""
import re
import subprocess
from pathlib import Path

from PIL import Image

from motor import arte, config, legenda as mod_legenda, probe

LARGURA_BAIXA = 540      # metade da largura final: da para ver o corte, o
                         # letreiro e a legenda, e o arquivo fica leve o
                         # bastante para mandar por mensagem
CRF_BAIXA = 30           # qualidade da previa. Nao e o arquivo de publicar


def _quadro(gravacao, instante, destino):
    """Um quadro da gravacao, ja enquadrado em pe, como o filme vai sair."""
    area = probe.area_util(gravacao) or ""
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{instante:.3f}",
         "-i", str(gravacao), "-frames:v", "1",
         "-vf", (f"{area}scale={config.W}:{config.H}"
                 f":force_original_aspect_ratio=increase,"
                 f"crop={config.W}:{config.H}"),
         str(destino)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg falhou ao tirar o quadro: "
                           + r.stderr.strip()[:300])
    return destino


def amostra(gravacao, instante, escolhas, destino, letreiro=None,
            legenda=None, base=None, para=None):
    """Um quadro da gravacao com a cara que aquelas escolhas dariam ao video.

    `escolhas` e `{"fonte": ..., "paleta": ..., "efeito": ...}`. `letreiro` e
    `legenda` sao os textos de exemplo -- passe frases que a pessoa realmente
    falou, porque o ponto da amostra e mostrar o resultado, nao o catalogo.

    `para` limita a amostra a uma das duas pecas: "legenda" desenha so a
    legenda, "letreiro" so o letreiro. Sem ele, desenha as duas -- que e o que
    serve para ver o conjunto, e nao para escolher uma coisa de cada vez."""
    destino = Path(destino)
    tmp = destino.parent
    fundo = Image.open(_quadro(gravacao, instante,
                               tmp / f".q-{destino.stem}.png")).convert("RGBA")

    if letreiro and para in (None, "letreiro"):
        peca = arte.letreiro(letreiro, escolhas, tmp / f".l-{destino.stem}.png",
                             base=base)
        fundo = Image.alpha_composite(fundo, Image.open(peca).convert("RGBA"))
    if legenda and para in (None, "legenda"):
        peca = mod_legenda.png(legenda, escolhas, tmp / f".g-{destino.stem}.png")
        fundo = Image.alpha_composite(fundo, Image.open(peca).convert("RGBA"))

    fundo.convert("RGB").save(destino)
    for lixo in (f".q-{destino.stem}.png", f".l-{destino.stem}.png",
                 f".g-{destino.stem}.png"):
        (tmp / lixo).unlink(missing_ok=True)
    return destino


def _nome_de_arquivo(texto):
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")


def catalogo(gravacao, instante, pasta, para, texto, fixas=None):
    """Uma amostra por opcao de UM eixo, com os outros dois parados.

    E o que torna a escolha possivel: comparar trinta combinacoes de uma vez
    nao e escolher, e adivinhar. Aqui a pessoa ve as tres fontes com a mesma
    cor e o mesmo efeito, depois as cinco cores com a mesma fonte, e assim por
    diante -- cada tela muda uma coisa so.

    Devolve `{eixo: {opcao: caminho}}` para os tres eixos."""
    from motor import estilos
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    fontes = (estilos.FONTES_LEGENDA if para == "legenda"
              else estilos.FONTES_LETREIRO)
    padrao = (estilos.PADRAO_LEGENDA if para == "legenda"
              else estilos.PADRAO_LETREIRO)
    base = {**padrao, **(fixas or {})}
    texto_letreiro = texto if para == "letreiro" else None
    texto_legenda = texto if para == "legenda" else None

    saida = {}
    for eixo, opcoes in (("fonte", fontes), ("paleta", estilos.PALETAS),
                         ("efeito", estilos.EFEITOS)):
        saida[eixo] = {}
        for opcao in opcoes:
            escolhas = {**base, eixo: opcao}
            arq = pasta / f"{para}-{eixo}-{_nome_de_arquivo(opcao)}.jpg"
            saida[eixo][opcao] = amostra(gravacao, instante, escolhas, arq,
                                         letreiro=texto_letreiro,
                                         legenda=texto_legenda, para=para)
    return saida


def em_baixa(filme, destino, largura=LARGURA_BAIXA, crf=CRF_BAIXA):
    """O filme inteiro, pequeno e leve, para a pessoa assistir e aprovar.

    Serve para a aprovacao intermediaria: gastar a exportacao boa num corte que
    ainda vai mudar e tempo perdido, e um arquivo grande demais nem chega do
    outro lado.

    A altura sai do proprio video (`-2` deixa o ffmpeg calcular, sempre par,
    que e o que o formato exige), entao isto funciona igual num vertical ja
    montado e numa gravacao crua."""
    destino = Path(destino)
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(filme),
         "-vf", f"scale={largura}:-2",
         "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast",
         "-c:a", "aac", "-b:a", "96k", "-ar", str(config.SR),
         "-movflags", "+faststart", str(destino)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg falhou ao gerar a previa: "
                           + r.stderr.strip()[:300])
    return destino
