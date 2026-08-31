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


def amostra(gravacao, instante, estilo, destino, letreiro=None, legenda=None,
            base=None, box=False):
    """Um quadro da gravacao com a cara que aquele estilo daria ao video.

    `letreiro` e `legenda` sao os textos de exemplo. Sem eles a amostra sai so
    com o quadro, o que nao ajuda ninguem a escolher -- passe frases que a
    pessoa realmente falou."""
    destino = Path(destino)
    tmp = destino.parent
    fundo = Image.open(_quadro(gravacao, instante,
                               tmp / f".q-{destino.stem}.png")).convert("RGBA")

    if letreiro:
        peca = arte.letreiro(letreiro, estilo, tmp / f".l-{destino.stem}.png",
                             base=base, box=box)
        fundo = Image.alpha_composite(fundo, Image.open(peca).convert("RGBA"))
    if legenda:
        peca = mod_legenda.png(legenda, estilo, tmp / f".g-{destino.stem}.png")
        fundo = Image.alpha_composite(fundo, Image.open(peca).convert("RGBA"))

    fundo.convert("RGB").save(destino)
    for lixo in (f".q-{destino.stem}.png", f".l-{destino.stem}.png",
                 f".g-{destino.stem}.png"):
        (tmp / lixo).unlink(missing_ok=True)
    return destino


def das_sete(gravacao, instante, pasta, letreiro=None, legenda=None):
    """Uma amostra por estilo, na ordem das fichas. Devolve {estilo: caminho}.

    E o catalogo que vai para a folha de aprovacao: a pessoa ve os sete
    aplicados no proprio video, lado a lado, e escolhe um."""
    from motor import estilos
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    saida = {}
    for chave in estilos.ESTILOS:
        saida[chave] = amostra(gravacao, instante, chave,
                               pasta / f"estilo-{chave}.jpg",
                               letreiro=letreiro, legenda=legenda)
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
