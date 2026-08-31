"""Como o texto aparece: a fonte, a paleta e o efeito.

O QUE MUDOU, E POR QUE. Antes havia sete fichas fechadas -- cada uma com fonte,
cor e efeito amarrados, e a pessoa escolhia uma das sete. Fechado tem uma
vantagem real (nao sai combinacao feia) e um custo que apareceu no uso: a pessoa
gosta da letra de uma e da cor de outra, e nao tem como pedir isso.

Agora sao TRES escolhas independentes, e duas vezes -- uma para a legenda e
outra para o letreiro:

    fonte   +   paleta   +   efeito

A legenda escolhe entre tres fontes de leitura (serifa, sem serifa, monoespaco);
o letreiro, entre cinco fontes de display, que sao as de chamar atencao. As
cinco paletas e os dois efeitos valem para os dois.

POR QUE SO DOIS EFEITOS. Sao os dois que funcionam sobre imagem em movimento:
contorno escuro em volta da letra, como legenda de televisao, ou a letra dentro
de uma caixa cheia. Qualquer outra coisa -- sombra suave, brilho, gradiente --
some assim que o fundo muda de cor, e o fundo aqui e o rosto de alguem se
mexendo.

A FONTE NUNCA E EXIGIDA: cada entrada lista candidatas em ordem e devolve a
primeira que existir, terminando numa que existe em todo Mac. Sem isso a skill
quebraria na maquina de quem clonasse sem os arquivos.
"""
from pathlib import Path

FONTES_DA_SKILL = str(Path(__file__).resolve().parent.parent / "assets" / "fontes")
FONTES_DO_SISTEMA = "/System/Library/Fonts"
FONTES_DO_SISTEMA_SUPLEMENTAR = "/System/Library/Fonts/Supplemental"

# ultima linha de defesa: existe em todo Mac
RESERVA = f"{FONTES_DO_SISTEMA}/Helvetica.ttc"


class EstiloDesconhecido(Exception):
    """A fonte, a paleta ou o efeito pedido nao existe. A mensagem lista os
    que existem."""


def _p(nome):
    return f"{FONTES_DA_SKILL}/{nome}"


def _s(nome):
    return f"{FONTES_DO_SISTEMA}/{nome}"


def _sup(nome):
    """Fontes do sistema que ficam em Supplemental/ no macOS moderno."""
    return f"{FONTES_DO_SISTEMA_SUPLEMENTAR}/{nome}"


# --- as fontes da LEGENDA: tres jeitos de ler ---------------------------------
# Legenda e texto pequeno e corrido, lido de relance enquanto a pessoa fala.
# Fonte de display aqui cansa, e por isso as tres sao de leitura.
FONTES_LEGENDA = {
    "sem serifa": {
        "como e": "Letra limpa, sem os pezinhos. A mais neutra das tres.",
        "arquivos": [_p("Work-Sans-400.ttf"), _s("HelveticaNeue.ttc"), RESERVA],
    },
    "serifa": {
        "como e": "Letra com pezinhos, como livro. Fica mais calma e séria.",
        "arquivos": [_p("Newsreader-400.ttf"), _sup("Georgia.ttf"), RESERVA],
    },
    "monoespaço": {
        "como e": "Todas as letras ocupam a mesma largura, como máquina de "
                  "escrever. Puxa para o técnico.",
        "arquivos": [_p("IBM-Plex-Mono-400.ttf"), _s("Menlo.ttc"), RESERVA],
    },
}

# --- as fontes do LETREIRO: cinco jeitos de chamar atencao --------------------
FONTES_LETREIRO = {
    "estreita": {
        "como e": "Muito alta e apertada. Cabe frase grande sem diminuir a "
                  "letra.",
        "arquivos": [_p("Anton-400.ttf"), _sup("Impact.ttf"), RESERVA],
    },
    "estreita leve": {
        "como e": "Alta e apertada como a outra, mas com o traço mais fino.",
        "arquivos": [_p("Antonio-700.ttf"), _sup("Impact.ttf"), RESERVA],
    },
    "pesada": {
        "como e": "Grossa e larga, sem serifa. A que mais ocupa espaço.",
        "arquivos": [_p("Chivo-900.ttf"), _s("HelveticaNeue.ttc"), RESERVA],
    },
    "revista": {
        "como e": "Serifa moderna, com traço grosso e fino bem diferentes. "
                  "Ar de capa de revista.",
        "arquivos": [_p("Bodoni-Moda-900.ttf"), _sup("Didot.ttc"), RESERVA],
    },
    "editorial": {
        "como e": "Serifa mais macia, menos dura que a de revista.",
        "arquivos": [_p("Fraunces-700.ttf"), _sup("Georgia.ttf"), RESERVA],
    },
}

# --- as cinco paletas ---------------------------------------------------------
# Cada uma diz quatro cores: a da letra e a do contorno (no efeito de contorno),
# e a da caixa e a da letra dentro dela (no efeito de caixa). As duas metades
# existem porque a mesma cor de letra nem sempre serve nos dois: amarelo com
# contorno preto se le bem sobre video, mas amarelo dentro de caixa amarela
# sumiria.
PALETAS = {
    "branco e preto": {
        "como e": "Letra branca com contorno preto, ou caixa branca com letra "
                  "preta. É o que quase todo vídeo usa, e funciona sobre "
                  "qualquer imagem.",
        "texto": "#FFFFFF", "contorno": "#000000",
        "caixa": "#FFFFFF", "caixa_texto": "#000000",
    },
    "amarelo": {
        "como e": "Amarelo forte com contorno preto. A que mais para o dedo de "
                  "quem rola a tela.",
        "texto": "#FFE800", "contorno": "#000000",
        "caixa": "#FFE800", "caixa_texto": "#000000",
    },
    "preto e branco": {
        "como e": "O contrário da primeira: letra preta com contorno branco, "
                  "ou caixa preta com letra branca. Mais sóbrio.",
        "texto": "#111111", "contorno": "#FFFFFF",
        "caixa": "#111111", "caixa_texto": "#FFFFFF",
    },
    "verde": {
        "como e": "Verde claro sobre contorno escuro. Puxa para tecnologia.",
        "texto": "#5BFF8F", "contorno": "#06120A",
        "caixa": "#06120A", "caixa_texto": "#5BFF8F",
    },
    "rosa": {
        "como e": "Rosa forte com contorno escuro. Criativo, com pegada de "
                  "arte impressa.",
        "texto": "#FF4F7B", "contorno": "#1B0A12",
        "caixa": "#FFF8E7", "caixa_texto": "#C31549",
    },
}

# --- os dois efeitos ----------------------------------------------------------
EFEITOS = {
    "contorno": "A letra com um traço escuro em volta, como legenda de "
                "televisão. A imagem aparece atrás do texto.",
    "caixa": "A letra dentro de um retângulo cheio. Tapa a imagem naquele "
             "pedaço, e é o que se lê melhor sobre fundo bagunçado.",
}

# o que sai quando ninguem escolhe nada
PADRAO_LEGENDA = {"fonte": "sem serifa", "paleta": "branco e preto",
                  "efeito": "caixa"}
PADRAO_LETREIRO = {"fonte": "estreita", "paleta": "amarelo",
                   "efeito": "contorno"}

CORPO_LEGENDA = 54       # o corpo da legenda; o do letreiro sai de config
CORPO_LETREIRO = 104


def _escolher(qual, chave, tabela, onde):
    if chave not in tabela:
        raise EstiloDesconhecido(
            f"nao conheco {qual} '{chave}' para {onde}. As que existem sao: "
            + ", ".join(sorted(tabela)))
    return tabela[chave]


def _primeira_que_existe(candidatas):
    for caminho in candidatas:
        if Path(caminho).exists():
            return caminho
    return RESERVA


def fonte_da_legenda(chave):
    return _primeira_que_existe(
        _escolher("a fonte", chave, FONTES_LEGENDA, "a legenda")["arquivos"])


def fonte_do_letreiro(chave):
    return _primeira_que_existe(
        _escolher("a fonte", chave, FONTES_LETREIRO, "o letreiro")["arquivos"])


def paleta(chave):
    return _escolher("a paleta", chave, PALETAS, "o texto")


def efeito(chave):
    if chave not in EFEITOS:
        raise EstiloDesconhecido(
            f"nao conheco o efeito '{chave}'. Os que existem sao: "
            + ", ".join(sorted(EFEITOS)))
    return chave


def compor(escolhas, para):
    """Junta fonte, paleta e efeito num so lugar, com o padrao no que faltar.

    `para` e "legenda" ou "letreiro" -- muda a lista de fontes e o padrao."""
    if para not in ("legenda", "letreiro"):
        raise ValueError("compor() e para 'legenda' ou 'letreiro'")
    padrao = PADRAO_LEGENDA if para == "legenda" else PADRAO_LETREIRO
    e = {**padrao, **(escolhas or {})}
    p = paleta(e["paleta"])
    efeito(e["efeito"])
    arquivo = (fonte_da_legenda(e["fonte"]) if para == "legenda"
               else fonte_do_letreiro(e["fonte"]))
    return {"fonte": e["fonte"], "arquivo": arquivo, "paleta": e["paleta"],
            "efeito": e["efeito"],
            "texto": p["caixa_texto"] if e["efeito"] == "caixa" else p["texto"],
            "contorno": p["contorno"], "caixa": p["caixa"],
            "corpo": CORPO_LEGENDA if para == "legenda" else CORPO_LETREIRO}


def rgb(cor):
    """'#RRGGBB' -> (r, g, b)."""
    cor = cor.lstrip("#")
    return tuple(int(cor[i:i + 2], 16) for i in (0, 2, 4))


def distancia_de_cor(a, b):
    """Distancia simples entre duas cores. Serve para provar contraste, nao
    para julgar estetica."""
    return sum(abs(x - y) for x, y in zip(rgb(a), rgb(b)))
