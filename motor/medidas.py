"""Medicoes que o laudo junta. Cada uma responde uma pergunta so, devolve
numero, e nunca julga.

A REGRA: o nivel de referencia sai da PROPRIA gravacao. Comparar com um numero
absoluto nao funciona -- os takes chegam a -36 dB, e o mesmo -20 dB que e fala
alta num take e ruido de fundo em outro."""
import math

from motor import config, fala

JANELA_EMENDA = 0.04       # 40 ms de cada lado do ponto de corte
FOLGA_EMENDA = 10.0        # dB acima do silencio da propria gravacao


def _dB(x):
    return 20 * math.log10(x) if x > 1e-9 else -120.0


def _percentil(valores, p):
    if not valores:
        return 0.0
    ordenado = sorted(valores)
    return ordenado[min(len(ordenado) - 1, int(len(ordenado) * p))]


def emendas(filme, instantes, janela=JANELA_EMENDA, folga=FOLGA_EMENDA):
    """Onde o filme foi costurado, o som deveria estar no nivel do silencio.

    Se estiver perto do nivel da fala, a emenda cortou palavra pela metade --
    a pessoa ouve como um engasgo. Devolve uma lista de achados; lista vazia
    quer dizer que todas as emendas estao limpas."""
    env = fala.envelope(filme)
    if not env:
        return []
    dur = len(env) * fala.PASSO
    silencio = _dB(_percentil(env, 0.10))

    achados = []
    for t in instantes:
        if t <= janela or t >= dur - janela:
            continue
        i, j = int((t - janela) / fala.PASSO), int((t + janela) / fala.PASSO)
        pedaco = env[i:j]
        if not pedaco:
            continue
        nivel = _dB(max(pedaco))
        if nivel > silencio + folga:
            achados.append({"instante": round(t, 3),
                            "dB": round(nivel, 1),
                            "silencio_dB": round(silencio, 1)})
    return achados
