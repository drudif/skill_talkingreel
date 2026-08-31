"""Medicoes que o laudo junta. Cada uma responde uma pergunta so, devolve
numero, e nunca julga.

A REGRA: o nivel de referencia sai da PROPRIA gravacao. Comparar com um numero
absoluto nao funciona -- os takes chegam a -36 dB, e o mesmo -20 dB que e fala
alta num take e ruido de fundo em outro."""
import math

from motor import config, fala

JANELA_EMENDA = 0.04       # 40 ms de cada lado do ponto de corte
MARGEM_EMENDA = 15.0       # dB abaixo do nivel de FALA do proprio filme.
                           # MEDIDO: emenda limpa fica 41 dB abaixo da fala;
                           # emenda que corta palavra fica a 0 a 3 dB dela.
                           # A referencia e a FALA, nao o silencio: num talking
                           # head bem cortado quase nao sobra silencio, e ai o
                           # percentil de baixo do envelope JA E fala -- medido,
                           # um filme de duas cenas coladas deu "silencio" a
                           # -0,8 dB, e nenhuma emenda suja era detectada.

def _dB(x):
    return 20 * math.log10(x) if x > 1e-9 else -120.0


def _percentil(valores, p):
    if not valores:
        return 0.0
    ordenado = sorted(valores)
    return ordenado[min(len(ordenado) - 1, int(len(ordenado) * p))]


DINAMICA_MINIMA = 32.0     # dB entre a fala e o FUNDO ABSOLUTO do filme, abaixo
                           # do que a medicao de emenda deixa de valer.
                           # MEDIDO em tres filmes: fala do comeco ao fim, sem
                           # pausa nenhuma, da 44,2; corte real limpo da 50,8;
                           # o MESMO corte com musica por baixo cai para 20,2.
                           # O limiar fica no meio dessa distancia.
FUNDO = 0.02               # o percentil que representa o fundo. Tem de ser bem
                           # baixo: num talking head denso o percentil 10 JA E
                           # fala -- medido, a distancia ate ele deu 0,5 dB num
                           # filme perfeitamente medivel, e a guarda barrava o
                           # caso legitimo. O percentil 2 pega os micro-silencios
                           # que existem DENTRO das palavras (a oclusiva de
                           # `fala.py`), e esses so somem quando ha som continuo
                           # por baixo.


def da_para_ouvir_emenda(filme):
    """(da, distancia em dB) entre a fala e o fundo deste filme.

    A medicao de emenda procura som de fala onde deveria haver silencio. Num
    filme com musica por baixo NAO HA silencio em lugar nenhum, e a conta passa
    a acusar toda emenda -- inclusive as limpas. Medir assim e pior que nao
    medir: quem le o laudo devolve para o corte um filme que estava certo.

    Entao a pergunta vem antes da resposta: da para ouvir emenda aqui?

    O que se compara e a fala com o FUNDO ABSOLUTO, e nao com um percentil de
    baixo qualquer: um talking head bem cortado e quase todo fala, e ali o
    percentil 10 ja e voz. O que sempre existe, mesmo na fala mais corrida, sao
    os micro-silencios de dentro das palavras -- e sao justamente esses que a
    musica cobre."""
    env = fala.envelope(filme)
    if not env:
        return False, 0.0
    distancia = _dB(_percentil(env, 0.75)) - _dB(_percentil(env, FUNDO))
    return distancia >= DINAMICA_MINIMA, distancia


def emendas(filme, instantes, janela=JANELA_EMENDA, margem=MARGEM_EMENDA):
    """Onde o filme foi costurado, ainda ha som de fala?

    Se houver, a emenda cortou palavra pela metade -- a pessoa ouve como um
    engasgo. Devolve uma lista de achados; lista vazia quer dizer que todas as
    emendas estao limpas.

    A REFERENCIA E O NIVEL DA FALA DO PROPRIO FILME, nunca um numero absoluto
    nem o silencio. Absoluto nao serve porque os takes chegam a -36 dB. E o
    silencio nao serve porque num talking head bem cortado quase nao sobra
    silencio: medido, um filme de duas cenas coladas devolveu "silencio" a
    -0,8 dB, que era fala, e nenhuma emenda suja aparecia.

    SO RODE ISTO ONDE `da_para_ouvir_emenda` disser que sim. Num filme com
    musica por baixo o resultado nao vale nada: medido, as mesmas dez emendas
    passaram de zero acusadas para dez."""
    env = fala.envelope(filme)
    if not env:
        return []
    dur = len(env) * fala.PASSO
    nivel_fala = _dB(_percentil(env, 0.75))

    achados = []
    for t in instantes:
        if t <= janela or t >= dur - janela:
            continue
        i, j = int((t - janela) / fala.PASSO), int((t + janela) / fala.PASSO)
        pedaco = env[i:j]
        if not pedaco:
            continue
        nivel = _dB(max(pedaco))
        if nivel > nivel_fala - margem:
            achados.append({"instante": round(t, 3),
                            "dB": round(nivel, 1),
                            "fala_dB": round(nivel_fala, 1),
                            "abaixo_da_fala": round(nivel_fala - nivel, 1)})
    return achados


def dentro_da_faixa_segura(peca):
    """A tinta desta peca (legenda ou letreiro) cai onde o aplicativo desenha
    a propria interface?

    Instagram e TikTok escrevem nome de perfil, legenda do post e botoes por
    cima do video. Texto que cai ali fica ilegivel. A base da legenda foi de
    1500 para 1375 exatamente por causa disto."""
    from PIL import Image
    caixa = Image.open(peca).convert("RGBA").getchannel("A").getbbox()
    if caixa is None:
        return []
    _, y0, _, y1 = caixa
    achados = []
    if y0 < config.SEGURO_TOPO:
        achados.append({"onde": "em cima", "y": y0, "limite": config.SEGURO_TOPO})
    if y1 > config.SEGURO_BASE:
        achados.append({"onde": "embaixo", "y": y1, "limite": config.SEGURO_BASE})
    return achados


REPETICOES_DEMAIS = 4      # acima disto o material complementar vira padronagem


def repeticao_do_complementar(mapa, topos):
    """O material que entra na metade de cima repete quantas vezes?

    Medido com gravacao real: um b-roll de 2,4s debaixo de uma cena de 70,9s
    repete 30 vezes. O motor faz a coisa certa -- da loop em vez de congelar --
    mas o resultado e monotono. Nao e defeito de motor, e decisao de conteudo:
    material curto demais debaixo de cena longa demais."""
    from motor import probe
    achados = []
    for c in mapa or []:
        arquivo = topos.get(c["n"])
        if not arquivo:
            continue
        d_topo = probe.dur(arquivo)
        d_cena = c["fim"] - c["ini"]
        if d_topo <= 0 or d_cena <= 0:
            continue
        vezes = d_cena / d_topo
        if vezes > REPETICOES_DEMAIS:
            achados.append({"n": c["n"], "vezes": round(vezes, 1),
                            "material_s": round(d_topo, 1),
                            "cena_s": round(d_cena, 1)})
    return achados
