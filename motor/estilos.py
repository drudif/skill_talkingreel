"""As sete fichas de estilo, reduzidas da skill de carrossel ao que atravessa
para video: cor, fonte e como o texto se apoia no quadro.

DUAS FONTES POR FICHA, e nao uma: a do letreiro e a da legenda. Sao as mesmas
que a skill de carrossel usa para titulo e corpo, e sao a metade do que separa
um estilo do outro. Antes desta separacao os sete usavam a MESMA fonte na
pratica -- todas as fichas listavam a mesma primeira candidata, e como ela
existia na maquina do autor, ganhava sempre. Os sete estilos diferiam so por
cor, e "fonte" era um eixo que existia so no papel.

AS FONTES VEM COM A SKILL, em `assets/fontes/`, com as licencas ao lado. Mas
NUNCA sao exigidas: cada ficha lista candidatas em ordem e `fonte()` devolve a
primeira que existir, terminando numa que existe em todo Mac. Sem isso a skill
quebraria na maquina de quem clonasse sem os arquivos."""
from pathlib import Path

FONTES_DA_SKILL = str(Path(__file__).resolve().parent.parent / "assets" / "fontes")
FONTES_DO_SISTEMA = "/System/Library/Fonts"
FONTES_DO_SISTEMA_SUPLEMENTAR = "/System/Library/Fonts/Supplemental"
FONTES_DO_USUARIO = str(Path.home() / "Library" / "Fonts")

# ultima linha de defesa: existe em todo Mac
RESERVA = f"{FONTES_DO_SISTEMA}/Helvetica.ttc"


class EstiloDesconhecido(Exception):
    """O estilo pedido nao existe. A mensagem lista os que existem."""


def _p(nome):
    """Fonte que vem dentro da propria skill."""
    return f"{FONTES_DA_SKILL}/{nome}"


def _u(nome):
    return f"{FONTES_DO_USUARIO}/{nome}"


def _s(nome):
    return f"{FONTES_DO_SISTEMA}/{nome}"


def _sup(nome):
    """Fontes do sistema que ficam em Supplemental/ no macOS moderno
    (Impact, Georgia e varias outras nao estao mais na raiz de Fonts)."""
    return f"{FONTES_DO_SISTEMA_SUPLEMENTAR}/{nome}"


ESTILOS = {
    "terminal": {
        "nome": "Terminal — vazio, tipografia seca, sem enfeite",
        "fundo": "#0A0A0A", "texto": "#F2F2F2", "contorno": "#0A0A0A",
        "legenda_caixa": "#0A0A0A", "legenda_texto": "#F2F2F2",
        "fontes": [_p("Cascadia-Mono-300.ttf"), _s("Menlo.ttc"), RESERVA],
        "fontes_legenda": [_p("Cascadia-Mono-400.ttf"), _s("Menlo.ttc"), RESERVA],
        "peso_letreiro": 96,
    },
    "brutalista": {
        "nome": "Brutalista — amarelo puro, contorno preto grosso",
        "fundo": "#FFE800", "texto": "#FFE800", "contorno": "#000000",
        "legenda_caixa": "#FFFFFF", "legenda_texto": "#000000",
        "fontes": [_p("Anton-400.ttf"), _sup("Impact.ttf"), RESERVA],
        "fontes_legenda": [_p("IBM-Plex-Mono-400.ttf"), _s("Menlo.ttc"), RESERVA],
        "peso_letreiro": 104,
    },
    "neubrutal": {
        "nome": "Neubrutal — cor chapada, contorno duro, sombra deslocada",
        "fundo": "#3D5AFE", "texto": "#FFFFFF", "contorno": "#0A0A0A",
        "legenda_caixa": "#3D5AFE", "legenda_texto": "#FFFFFF",
        "fontes": [_p("Chivo-900.ttf"), _s("Avenir Next.ttc"), RESERVA],
        "fontes_legenda": [_p("Chivo-Mono-400.ttf"), _s("Menlo.ttc"), RESERVA],
        "peso_letreiro": 96,
    },
    "editorial": {
        "nome": "Editorial — creme e tinta, uma imagem grande",
        "fundo": "#F4F1EA", "texto": "#1A1A1A", "contorno": "#F4F1EA",
        "legenda_caixa": "#F4F1EA", "legenda_texto": "#1A1A1A",
        "fontes": [_p("Fraunces-700.ttf"), _sup("Georgia.ttf"), RESERVA],
        "fontes_legenda": [_p("Work-Sans-400.ttf"), _s("HelveticaNeue.ttc"), RESERVA],
        "peso_letreiro": 88,
    },
    "riso": {
        "nome": "Risografia — duas tintas, rosa e azul",
        "fundo": "#FF4F7B", "texto": "#FFF8E7", "contorno": "#1B2A88",
        "legenda_caixa": "#FFF8E7", "legenda_texto": "#1B2A88",
        "fontes": [_p("Antonio-700.ttf"), _s("Avenir Next.ttc"), RESERVA],
        "fontes_legenda": [_p("Newsreader-400.ttf"), _sup("Georgia.ttf"), RESERVA],
        "peso_letreiro": 96,
    },
    "colagem": {
        "nome": "Colagem — recorte de papel, tipografia cortada",
        "fundo": "#E8E2D0", "texto": "#111111", "contorno": "#E8E2D0",
        "legenda_caixa": "#111111", "legenda_texto": "#E8E2D0",
        "fontes": [_p("Bodoni-Moda-900.ttf"), _sup("Didot.ttc"), RESERVA],
        "fontes_legenda": [_p("Karla-400.ttf"), _s("Helvetica.ttc"), RESERVA],
        "peso_letreiro": 92,
    },
    "superminimal": {
        "nome": "Superminimal — branco, uma cor de acento",
        "fundo": "#FFFFFF", "texto": "#111111", "contorno": "#FFFFFF",
        "legenda_caixa": "#FFFFFF", "legenda_texto": "#111111",
        "fontes": [_p("Plus-Jakarta-Sans-500.ttf"), _s("HelveticaNeue.ttc"), RESERVA],
        "fontes_legenda": [_p("Plus-Jakarta-Sans-400.ttf"), _s("HelveticaNeue.ttc"), RESERVA],
        "peso_letreiro": 84,
    },
}

PADRAO = "brutalista"


def carregar(chave):
    if chave not in ESTILOS:
        raise EstiloDesconhecido(
            f"nao conheco o estilo '{chave}'. Os que existem sao: "
            + ", ".join(sorted(ESTILOS)))
    return ESTILOS[chave]


def _primeira_que_existe(candidatas):
    for caminho in candidatas:
        if Path(caminho).exists():
            return caminho
    return RESERVA


def fonte(chave):
    """A fonte do LETREIRO: primeira da lista que existir no disco."""
    return _primeira_que_existe(carregar(chave)["fontes"])


def fonte_legenda(chave):
    """A fonte da LEGENDA. E outra que a do letreiro de proposito: no carrossel
    de onde estas fichas vieram, cada estilo tem uma para titulo e outra para
    corpo, e usar a de titulo num texto pequeno e corrido deixa a leitura
    pesada. Ficha sem esta lista cai na do letreiro."""
    ficha = carregar(chave)
    return _primeira_que_existe(ficha.get("fontes_legenda") or ficha["fontes"])


def rgb(cor):
    """'#RRGGBB' -> (r, g, b)."""
    cor = cor.lstrip("#")
    return tuple(int(cor[i:i + 2], 16) for i in (0, 2, 4))


def distancia_de_cor(a, b):
    """Distancia simples entre duas cores. Serve para provar contraste, nao
    para julgar estetica."""
    ra, rb = rgb(a), rgb(b)
    return sum(abs(x - y) for x, y in zip(ra, rb))
