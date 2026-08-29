"""As sete fichas de estilo, reduzidas da skill de carrossel ao que atravessa
para video: cor, fonte e como o texto se apoia no quadro.

A FONTE E UM PROBLEMA REAL: a do projeto de origem e licenciada e mora na
maquina do autor. Cada ficha lista candidatas em ordem, e `fonte()` devolve a
primeira que existir. Sem isso a skill quebra na maquina de outra pessoa."""
from pathlib import Path

FONTES_DO_SISTEMA = "/System/Library/Fonts"
FONTES_DO_SISTEMA_SUPLEMENTAR = "/System/Library/Fonts/Supplemental"
FONTES_DO_USUARIO = str(Path.home() / "Library" / "Fonts")

# ultima linha de defesa: existe em todo Mac
RESERVA = f"{FONTES_DO_SISTEMA}/Helvetica.ttc"


class EstiloDesconhecido(Exception):
    """O estilo pedido nao existe. A mensagem lista os que existem."""


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
        "fontes": [_u("Satoshi-Black.otf"), _s("Menlo.ttc"), RESERVA],
        "peso_letreiro": 96,
    },
    "brutalista": {
        "nome": "Brutalista — amarelo puro, contorno preto grosso",
        "fundo": "#FFE800", "texto": "#FFE800", "contorno": "#000000",
        "legenda_caixa": "#FFFFFF", "legenda_texto": "#000000",
        "fontes": [_u("Satoshi-Black.otf"), _sup("Impact.ttf"), RESERVA],
        "peso_letreiro": 104,
    },
    "neubrutal": {
        "nome": "Neubrutal — cor chapada, contorno duro, sombra deslocada",
        "fundo": "#3D5AFE", "texto": "#FFFFFF", "contorno": "#0A0A0A",
        "legenda_caixa": "#3D5AFE", "legenda_texto": "#FFFFFF",
        "fontes": [_u("Satoshi-Black.otf"), _s("Avenir Next.ttc"), RESERVA],
        "peso_letreiro": 96,
    },
    "editorial": {
        "nome": "Editorial — creme e tinta, uma imagem grande",
        "fundo": "#F4F1EA", "texto": "#1A1A1A", "contorno": "#F4F1EA",
        "legenda_caixa": "#F4F1EA", "legenda_texto": "#1A1A1A",
        "fontes": [_u("Satoshi-Bold.otf"), _sup("Georgia.ttf"), RESERVA],
        "peso_letreiro": 88,
    },
    "riso": {
        "nome": "Risografia — duas tintas, rosa e azul",
        "fundo": "#FF4F7B", "texto": "#FFF8E7", "contorno": "#1B2A88",
        "legenda_caixa": "#FFF8E7", "legenda_texto": "#1B2A88",
        "fontes": [_u("Satoshi-Black.otf"), _s("Avenir Next.ttc"), RESERVA],
        "peso_letreiro": 96,
    },
    "colagem": {
        "nome": "Colagem — recorte de papel, tipografia cortada",
        "fundo": "#E8E2D0", "texto": "#111111", "contorno": "#E8E2D0",
        "legenda_caixa": "#111111", "legenda_texto": "#E8E2D0",
        "fontes": [_u("Satoshi-Black.otf"), _s("Helvetica.ttc"), RESERVA],
        "peso_letreiro": 92,
    },
    "superminimal": {
        "nome": "Superminimal — branco, uma cor de acento",
        "fundo": "#FFFFFF", "texto": "#111111", "contorno": "#FFFFFF",
        "legenda_caixa": "#FFFFFF", "legenda_texto": "#111111",
        "fontes": [_u("Satoshi-Bold.otf"), _s("HelveticaNeue.ttc"), RESERVA],
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


def fonte(chave):
    """Primeira fonte da lista que existir no disco."""
    for caminho in carregar(chave)["fontes"]:
        if Path(caminho).exists():
            return caminho
    return RESERVA


def rgb(cor):
    """'#RRGGBB' -> (r, g, b)."""
    cor = cor.lstrip("#")
    return tuple(int(cor[i:i + 2], 16) for i in (0, 2, 4))


def distancia_de_cor(a, b):
    """Distancia simples entre duas cores. Serve para provar contraste, nao
    para julgar estetica."""
    ra, rb = rgb(a), rgb(b)
    return sum(abs(x - y) for x, y in zip(ra, rb))
