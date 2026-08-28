"""Legenda queimada: transcricao, correcao, blocos, desenho e composicao.

A TRANSCRICAO MANDA. O roteiro so conserta NOME PROPRIO. Qualquer regra mais
larga destroi a fala: os takes se afastam do roteiro, e palavra curta bate 0,8
de similaridade com qualquer vizinha. Numa rodada do projeto de origem sairam
19 correcoes e as 19 estavam erradas — "ter" virou "te", "quem" virou "que",
"no" virou "Nao", "contar" virou "continuar".

QUEBRA DE BLOCO: so teto de palavras e respiro emenda frases. Tem de quebrar
tambem em fim de frase."""
import difflib
import re
import unicodedata

MAX_PALAVRAS = 4
RESPIRO = 0.35            # silencio que separa dois blocos
LIMIAR_PROPRIO = 0.50     # sobre a forma sem acento
MIN_LETRAS = 5            # palavra menor que isto nunca e corrigida
FIM_DE_FRASE = re.compile(r"[.!?…]$")


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")


def normal(s):
    return re.sub(r"[^\wÀ-ſ]", "", s.lower())


def corrigir(palavras, proprios, pedidas=None):
    """Conserta SO nome proprio mal reconhecido, e as trocas explicitamente
    pedidas. Mantem o timestamp e a pontuacao colada.

    Devolve a lista de (antes, depois, instante) para auditoria."""
    pedidas = pedidas or {}
    trocas = []
    for w in palavras:
        n = normal(w["p"])
        sufixo = re.sub(r"^[\wÀ-ſ]+", "", w["p"])

        if n in pedidas:
            novo = pedidas[n] + sufixo
            trocas.append((w["p"], novo, round(w["t"], 2)))
            w["p"] = novo
            continue

        if not n or len(n) < MIN_LETRAS:
            continue

        melhor, semelhanca = None, 0.0
        for pr in proprios:
            s = difflib.SequenceMatcher(None, sem_acento(n), sem_acento(pr)).ratio()
            if s > semelhanca:
                melhor, semelhanca = pr, s
        if (melhor and semelhanca >= LIMIAR_PROPRIO
                and sem_acento(melhor) != sem_acento(n)):
            novo = melhor + sufixo
            trocas.append((w["p"], novo, round(w["t"], 2)))
            w["p"] = novo
    return trocas


def _corta_entre(a, b):
    """True se nao pode haver bloco atravessando de a pra b: fim de frase
    em a, ou pausa maior que RESPIRO entre os dois."""
    return bool(FIM_DE_FRASE.search(a["p"])) or (b["t"] - a["f"] > RESPIRO)


def blocos(palavras):
    """Agrupa em blocos curtos. Quebra em fim de frase, em respiro, e no teto
    de palavras — nesta ordem."""
    saida, atual = [], []
    for w in palavras:
        if atual:
            corta = (FIM_DE_FRASE.search(atual[-1]["p"])
                     or w["t"] - atual[-1]["f"] > RESPIRO
                     or len(atual) >= MAX_PALAVRAS)
            if corta:
                saida.append(atual)
                atual = []
        atual.append(w)
    if atual:
        saida.append(atual)

    junto = []
    for b in saida:
        anterior = junto[-1] if junto else None
        pode_juntar = (anterior is not None and len(b) == 1
                       and not _corta_entre(anterior[-1], b[0]))

        if pode_juntar and len(anterior) < MAX_PALAVRAS:
            # ha espaco: emenda o orfao direto no bloco anterior.
            anterior.extend(b)
        elif pode_juntar and len(anterior) >= 3:
            # bloco anterior ja esta no teto: rebalanceia em vez de
            # estourar. Move a ULTIMA palavra do anterior para o orfao,
            # preservando os dois invariantes (nunca 1, nunca > MAX).
            realocada = anterior.pop()
            junto.append([realocada] + b)
        else:
            junto.append(b)
    return junto
