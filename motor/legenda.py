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

from PIL import Image, ImageDraw, ImageFont

from motor import config, estilos

MAX_PALAVRAS = 4
RESPIRO = 0.35            # silencio que separa dois blocos
LIMIAR_PROPRIO = 0.50     # sobre a forma sem acento
MIN_LETRAS = 4            # vale para os DOIS lados: palavra menor que isto
                          # nunca e corrigida, e nome proprio menor que isto
                          # nunca serve de alvo. Medido: toda troca errada do
                          # projeto de origem veio de um ALVO curto — "te",
                          # "que", "Nao". Filtrando o alvo, nenhuma palavra da
                          # fala passa de 0.29 de semelhanca; sem filtrar, tres
                          # passavam de 0.80. Subir este numero para 5 tambem
                          # resolveria, mas cegaria a correcao para nome proprio
                          # de quatro letras (Nike, Ford, Java).
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
            if len(normal(pr)) < MIN_LETRAS:
                continue          # alvo curto e a origem de toda troca errada
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


POSICOES = ("cheia", "esquerda", "direita", "centro")


def _linhas(desenho, texto, fonte_pil, largura_max):
    saida, atual = [], ""
    for palavra in texto.split():
        tentativa = (atual + " " + palavra).strip()
        if desenho.textlength(tentativa, font=fonte_pil) <= largura_max:
            atual = tentativa
        else:
            if atual:
                saida.append(atual)
            atual = palavra
    if atual:
        saida.append(atual)
    return saida


def png(texto, estilo, destino, posicao="cheia"):
    """Um PNG 1080x1920 transparente com a legenda na posicao pedida.

    As quatro posicoes foram medidas: em tela cheia a base e 1375 (a 1500 caia
    sob a interface do aplicativo); no split, esquerda e direita se apoiam em
    827, logo abaixo da divisoria, e a centralizada usa a mesma base da tela
    cheia — assim a legenda nao salta quando a cena vira."""
    if posicao not in POSICOES:
        raise ValueError(f"posicao '{posicao}' desconhecida. Use uma de: "
                         + ", ".join(POSICOES))
    ficha = estilos.carregar(estilo)
    f = ImageFont.truetype(estilos.fonte(estilo), config.LEG_CORPO)

    im = Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    util = config.LEG_LARGURA_MAX - config.LEG_PAD_X * 2
    linhas = _linhas(d, texto, f, util)
    alt_linha = config.LEG_CORPO * config.LEG_ENTRELINHA
    largura = max(d.textlength(l, font=f) for l in linhas) + config.LEG_PAD_X * 2
    altura = alt_linha * len(linhas) + config.LEG_PAD_Y * 2

    if posicao == "esquerda":
        x0, y0 = config.LEG_SPLIT_X, config.LEG_SPLIT_TOPO
    elif posicao == "direita":
        x0, y0 = config.W - config.LEG_SPLIT_X - largura, config.LEG_SPLIT_TOPO
    else:                                  # cheia e centro
        x0, y0 = (config.W - largura) / 2, config.LEG_BASE - altura

    d.rectangle([x0, y0, x0 + largura, y0 + altura],
                fill=estilos.rgb(ficha["legenda_caixa"]) + (255,))
    cor = estilos.rgb(ficha["legenda_texto"]) + (255,)
    for i, linha in enumerate(linhas):
        cx = d.textlength(linha, font=f)
        alinhado = (x0 + config.LEG_PAD_X if posicao == "esquerda"
                    else x0 + (largura - cx) / 2)
        d.text((alinhado, y0 + config.LEG_PAD_Y + i * alt_linha),
               linha, font=f, fill=cor)
    im.save(destino)
    return destino
