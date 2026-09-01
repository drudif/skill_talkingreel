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
import subprocess
import tempfile
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from motor import arte, config, estilos

MAX_PALAVRAS = 4
RESPIRO = 0.35            # silencio que separa dois blocos
CONTORNO_LEGENDA = 4      # espessura do traco em volta da letra da legenda, no
                          # efeito de contorno. Menor que o do letreiro (7), que
                          # tem corpo quase o dobro: contorno grosso demais em
                          # letra pequena fecha o buraco do "a" e do "o".

LIMIAR_PROPRIO = 0.73     # semelhanca minima, sobre a forma sem acento, para
                          # trocar uma palavra da fala pelo nome proprio certo.
                          # MEDIDO dos dois lados com material real. Abaixo de
                          # 0,59 a troca pega palavra comum: "bastante" bate
                          # 0,588 contra "ByteDance", e a 0,50 -- o valor que
                          # este numero tinha -- "sabe" (0,500), "semanas"
                          # (0,533) e "verdade" (0,533) viravam "Seedance" na
                          # legenda queimada. Acima de 0,88 a correcao para de
                          # servir: "Seedence" bate 0,875 contra "Seedance" e
                          # deixaria de ser corrigido. 0,73 e o meio da janela.
                          #
                          # O QUE ISTO NAO PEGA, e NAO HA LIMIAR QUE PEGUE:
                          # erro de SOM. A transcricao ouviu "Sidense" onde a
                          # pessoa disse "Seedance" -- as duas grafias batem
                          # 0,267. E os casos mais faceis tambem nao dao: pegar
                          # "guinco" para "Ginsu" (0,545) exigiria um limiar que
                          # tambem troca "verdade" por "Seedance" (0,533), e
                          # pegar "naique" para "Nike" (0,600) fica a 0,012 de
                          # trocar "bastante" por "ByteDance" (0,588). As duas
                          # faixas se sobrepoem: nao e questao de achar o numero
                          # certo, e de a comparacao de LETRAS nao saber nada
                          # sobre SOM. Erro de som se conserta com `pedidas`.
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


def _fundir(palavras, pedidas, trocas):
    """Aplica as trocas cuja chave tem mais de uma palavra, fundindo-as numa so.

    POR QUE ISTO EXISTE. A transcricao parte numero decimal: "Seedance 2.5" sai
    como tres palavras, `Sidense`, `2` e `.5.` -- e nenhuma troca palavra a
    palavra conserta isso, porque nao ha palavra nenhuma que devesse virar
    "2.5". A peca que sobra, `.5.`, nao tem letra, entao `normal` a esvazia e o
    laco de baixo a pula: a legenda sairia "Seedance 2 .5." sem ninguem ver.

    A palavra fundida guarda o comeco da primeira e o fim da ultima, que e o
    que mantem a legenda em cima da fala."""
    chaves = {k: v for k, v in pedidas.items() if " " in k.strip()}
    if not chaves:
        return list(palavras)
    # a chave mais longa primeiro: "2 .5" nao pode ser comida por "2"
    ordem = sorted(chaves, key=lambda k: -len(k.split()))
    saida, i = [], 0
    while i < len(palavras):
        for chave in ordem:
            partes = chave.split()
            trecho = palavras[i:i + len(partes)]
            if len(trecho) < len(partes):
                continue
            if [normal(w["p"]) or w["p"].strip() for w in trecho] == \
                    [normal(x) or x for x in partes]:
                antes = " ".join(w["p"] for w in trecho)
                # so a pontuacao DEPOIS do ultimo caractere de palavra: em
                # ".5." o primeiro ponto e do numero e o segundo fecha a frase
                sufixo = re.sub(r"^.*[\wÀ-ſ]", "", trecho[-1]["p"])
                novo = chaves[chave] + sufixo
                trocas.append((antes, novo, round(trecho[0]["t"], 2)))
                saida.append({**trecho[0], "p": novo, "f": trecho[-1]["f"]})
                i += len(partes)
                break
        else:
            saida.append(palavras[i])
            i += 1
    return saida


def corrigir(palavras, proprios, pedidas=None):
    """Conserta SO nome proprio mal reconhecido, e as trocas explicitamente
    pedidas. Mantem o timestamp e a pontuacao colada.

    Devolve a lista de (antes, depois, instante) para auditoria."""
    pedidas = pedidas or {}
    trocas = []
    palavras[:] = _fundir(palavras, pedidas, trocas)
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
    """Quebra o texto em linhas que cabem na largura.

    Usa a mesma quebra do letreiro, que fatia caractere a caractere a palavra
    que sozinha nao cabe. Sem isso um token sem espaco — um link, uma hashtag
    colada — monta uma caixa mais larga que o quadro, e o Pillow corta a tinta
    em silencio nas duas bordas: medido, uma palavra de 40 letras gerava caixa
    de 1248px num quadro de 1080 e ninguem percebia, porque o bbox de um PNG
    nunca pode ser maior que o proprio PNG."""
    return arte.quebra_forcando_largura(desenho, texto, fonte_pil, largura_max)


def png(texto, estilo, destino, posicao="cheia"):
    """Um PNG 1080x1920 transparente com a legenda na posicao pedida.

    As quatro posicoes foram medidas: em tela cheia a base e 1375 (a 1500 caia
    sob a interface do aplicativo); no split, esquerda e direita se apoiam em
    827, logo abaixo da divisoria, e a centralizada usa a mesma base da tela
    cheia — assim a legenda nao salta quando a cena vira."""
    if posicao not in POSICOES:
        raise ValueError(f"posicao '{posicao}' desconhecida. Use uma de: "
                         + ", ".join(POSICOES))
    peca = estilos.compor(estilo, "legenda")
    caixa = peca["efeito"] == "caixa"
    f = ImageFont.truetype(peca["arquivo"], config.LEG_CORPO)

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

    if caixa:
        d.rectangle([x0, y0, x0 + largura, y0 + altura],
                    fill=estilos.rgb(peca["caixa"]) + (255,))
    cor = estilos.rgb(peca["texto"]) + (255,)
    # no efeito de contorno a imagem aparece atras da letra, e o que separa uma
    # da outra e o traco em volta. Sem ele a legenda some assim que o fundo
    # ficar da cor do texto -- e o fundo aqui e um rosto se mexendo.
    traco = 0 if caixa else CONTORNO_LEGENDA
    cor_traco = estilos.rgb(peca["contorno"]) + (255,)
    for i, linha in enumerate(linhas):
        cx = d.textlength(linha, font=f)
        alinhado = (x0 + config.LEG_PAD_X if posicao == "esquerda"
                    else x0 + (largura - cx) / 2)
        d.text((alinhado, y0 + config.LEG_PAD_Y + i * alt_linha),
               linha, font=f, fill=cor,
               stroke_width=traco, stroke_fill=cor_traco)
    im.save(destino)
    return destino


def sob_letreiro(ini, fim, mapa):
    """O bloco cai onde um letreiro grande ja ocupa a faixa da legenda?

    Nessas cenas o letreiro escreve a mesma frase em corpo grande; legendar por
    baixo duplica o texto e briga com a arte."""
    for c in mapa or []:
        janela = c.get("letreiro")
        if janela and ini < janela[1] and fim > janela[0]:
            return True
    return False


def posicao_do_bloco(ini, fim, mapa, posicao_split="esquerda"):
    """Onde este bloco cai na tela.

    Bloco numa cena de tela dividida usa a posicao escolhida na producao —
    esquerda, direita ou centro, conforme onde a pessoa aparece. Bloco em tela
    cheia e sempre centralizado. O criterio e o MEIO do bloco: um bloco que
    atravessa a virada de cena escolhe um lado so, senao a legenda saltaria no
    meio da propria frase."""
    meio = (ini + fim) / 2
    for c in mapa or []:
        if c["ini"] <= meio < c["fim"]:
            return posicao_split if c.get("trat") == "split" else "cheia"
    return "cheia"


def faixa(blocos_, estilo, destino, total, mapa=None,
          posicao_split="esquerda"):
    """Uma faixa RGBA com todos os blocos, para entrar num overlay so.

    ARMADILHA: no concat de imagens a ULTIMA entrada duplicada herda a duracao
    da anterior. Sem `-t` na duracao total a faixa infla — no projeto de origem
    passou de 48s para 90s e o video saiu curto."""
    tmp = Path(tempfile.mkdtemp(prefix="legenda-"))
    vazio = tmp / "vazio.png"
    Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0)).save(vazio)

    partes, t, omitidos = [], 0.0, 0
    for k, b in enumerate(blocos_):
        ini, fim = b[0]["t"], b[-1]["f"]
        if sob_letreiro(ini, fim, mapa):
            omitidos += 1
            continue
        if ini > t + 0.02:
            partes.append((vazio, ini - t))
        p = tmp / f"b{k:04d}.png"
        posicao = posicao_do_bloco(ini, fim, mapa, posicao_split)
        png(" ".join(w["p"] for w in b), estilo, p, posicao=posicao)
        partes.append((p, max(0.08, fim - ini)))
        t = fim
    if total > t:
        partes.append((vazio, total - t))
    if not partes:
        partes.append((vazio, total))

    lista = tmp / "faixa.txt"
    with open(lista, "w", encoding="utf-8") as fh:
        for p, d in partes:
            fh.write(f"file '{Path(p).resolve()}'\nduration {d:.3f}\n")
        fh.write(f"file '{Path(partes[-1][0]).resolve()}'\n")

    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(lista), "-vf", f"fps={config.FPS},format=rgba",
         "-t", f"{total:.3f}", "-c:v", "qtrle", str(destino)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("nao consegui montar a faixa de legenda: "
                           + r.stderr.strip()[:400])
    return destino, omitidos


def queimar(filme, blocos_, estilo, destino, mapa=None,
            posicao_split="esquerda"):
    """Queima a legenda no filme, com um overlay so."""
    from motor import probe
    total = probe.dur(filme)
    tmp = Path(tempfile.mkdtemp(prefix="queimar-"))
    trilha_leg, _ = faixa(blocos_, estilo, tmp / "faixa.mov", total,
                          mapa, posicao_split)
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(filme), "-i", str(trilha_leg),
         "-filter_complex",
         "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]",
         "-map", "[v]", "-map", "0:a?", "-t", f"{total:.3f}",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-c:a", "copy", str(destino)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("nao consegui queimar a legenda: "
                           + r.stderr.strip()[:400])
    return destino


MODELO = "large-v3"


def transcrever(caminho, modelo=MODELO):
    """Transcreve com timestamp por palavra. Devolve
    [{"p": palavra, "t": inicio, "f": fim}, ...].

    O modelo baixa no primeiro uso. Isto e lento e nao entra na suite normal."""
    import mlx_whisper
    r = mlx_whisper.transcribe(
        str(caminho),
        path_or_hf_repo=f"mlx-community/whisper-{modelo}-mlx",
        language="pt", word_timestamps=True, verbose=False)
    palavras = []
    for seg in r["segments"]:
        for w in seg.get("words", []):
            palavras.append({"p": w["word"].strip(),
                             "t": float(w["start"]), "f": float(w["end"])})
    return palavras
