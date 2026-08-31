"""Quanto contraste tem a imagem, e quanto falta.

A REGRA, herdada de medidas.py: a referencia sai do PROPRIO material. Uma
gravacao de celular com luz de janela e uma gravacao com luz montada chegam com
faixas de brilho muito diferentes, e um numero absoluto de "contraste bom" nao
existe para as duas.

O QUE SE MEDE: a distancia entre o brilho do percentil 5 e o do percentil 95 --
a faixa que a imagem realmente ocupa na escala de 0 a 255. Percentil, e nao
minimo e maximo, porque um unico ponto de luz estourado ou um canto preto
esticariam a conta para 255 numa imagem que e toda cinza no meio.

NAO SE USA BRILHO MEDIO. Media cancela sinal: uma imagem meio preta e meio
branca e uma imagem toda cinza tem a mesma media e contrastes opostos.
"""
import subprocess

from motor import config, probe

LADO = 128        # o quadro e reduzido a este tamanho antes de medir: a
                  # distribuicao de brilho sobrevive, e a leitura fica barata
QUADROS = 6       # quantos quadros espalhados pelo video entram na conta


def _instantes(caminho, quantos):
    """Os instantes a amostrar, espalhados pelo video e longe das pontas.

    Longe das pontas de proposito: o primeiro e o ultimo segundo costumam ter a
    mao na camera, a tela preta do corte, ou a pessoa ainda se ajeitando."""
    d = probe.dur(caminho) or 1.0
    if d <= 1.0:
        return [d / 2]
    margem = min(1.0, d * 0.05)
    util = d - 2 * margem
    return [margem + util * (i + 0.5) / quantos for i in range(quantos)]


def _um_quadro(caminho, instante, filtro):
    """Um quadro so, buscado direto no instante pedido.

    O `-ss` vai ANTES do `-i`, e aqui a razao nao e a de sempre (nao escorregar
    o corte) e sim VELOCIDADE: assim o ffmpeg pula direto para perto do
    instante, em vez de decodificar tudo o que vem antes.

    MEDIDO num arquivo de celular de 4K com 4,7 minutos: pedir seis quadros
    espalhados com um filtro de taxa, que obriga a decodificar o video inteiro,
    passou de DOIS MINUTOS; buscando um quadro de cada vez, 6,9 segundos. O
    dossie e a primeira coisa que roda, antes de qualquer decisao -- travar ali
    trava tudo."""
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{instante:.3f}", "-i", str(caminho),
         "-frames:v", "1", "-vf", filtro, "-f", "rawvideo", "-"],
        capture_output=True)
    return r.stdout


def _quadros(caminho, quantos=QUADROS, lado=LADO):
    """Lista de quadros reduzidos, cada um como uma lista de brilho (0 a 255).

    Um video pode mudar muito de luz do comeco ao fim -- a pessoa se mexe, uma
    nuvem passa. Medir um quadro so daria um retrato de um instante."""
    n = lado * lado
    saida = []
    for t in _instantes(caminho, quantos):
        bruto = _um_quadro(caminho, t, f"scale={lado}:{lado},format=gray")
        if len(bruto) >= n:
            saida.append(list(bruto[:n]))
    return saida


def _percentil(ordenado, p):
    return ordenado[min(len(ordenado) - 1, int(len(ordenado) * p))]


def faixa_de_brilho(caminho):
    """(piso, teto) do brilho em 0 a 255, sobre quadros espalhados pelo video.

    Piso e o percentil 5; teto, o percentil 95."""
    quadros = _quadros(caminho)
    if not quadros:
        return 0.0, 0.0
    pisos, tetos = [], []
    for q in quadros:
        o = sorted(q)
        pisos.append(_percentil(o, 0.05))
        tetos.append(_percentil(o, 0.95))
    return sum(pisos) / len(pisos), sum(tetos) / len(tetos)


def contraste(caminho):
    """Quanto da escala de brilho a imagem ocupa, de 0 a 255. Numero baixo quer
    dizer imagem lavada -- tudo perto do mesmo cinza."""
    piso, teto = faixa_de_brilho(caminho)
    return teto - piso


def ganho(caminho, quando_lavado=None):
    """Quanto esticar o brilho desta gravacao, para o filtro de imagem.

    Devolve `config.CONTRASTE_BASE` -- o realce que todo material recebe -- para
    imagem que ja esta boa, e um numero maior para imagem lavada. Nunca passa de
    `config.CONTRASTE_MAX`.

    Medir no arquivo ORIGINAL, sempre. Depois do corte a cena pode ter poucos
    quadros, e a conta sai de uma amostra pequena demais para valer."""
    if quando_lavado is not None:
        return quando_lavado
    f = contraste(caminho)
    if f <= 0 or f >= config.CONTRASTE_LAVADO:
        return config.CONTRASTE_BASE
    return min(config.CONTRASTE_MAX,
               max(config.CONTRASTE_BASE, config.CONTRASTE_ALVO / f))


def estouro(caminho):
    """Fracao de pixels colados no preto ou no branco.

    E o dano de esticar demais: onde estourou, o desenho da imagem sumiu e nao
    volta. Serve para o laudo avisar quando a correcao passou do ponto."""
    quadros = _quadros(caminho)
    if not quadros:
        return 0.0
    presos = total = 0
    for q in quadros:
        total += len(q)
        presos += sum(1 for v in q if v <= 2 or v >= 253)
    return presos / max(1, total)


# --- fundo verde ---
#
# Trocar o fundo de um video so funciona quando a pessoa gravou na frente de um
# pano ou parede verde de verdade. Nao existe, neste motor, jeito de recortar
# alguem de uma sala comum: isso exigiria um modelo treinado para separar
# pessoa de cenario, que este projeto nao carrega. Entao a unica coisa honesta
# a fazer e VERIFICAR antes e avisar quando nao der.

VERDE_MIN = 60      # abaixo deste brilho de verde a cor e sombra, nao pano
MOLDURA = 0.18      # que parte de cada lado do quadro conta como borda


def _quadros_rgb(caminho, quantos=QUADROS, lado=64):
    """Como `_quadros`, mas com a cor. Mesma busca direta pelo instante."""
    n = lado * lado * 3
    saida = []
    for t in _instantes(caminho, quantos):
        bruto = _um_quadro(caminho, t, f"scale={lado}:{lado},format=rgb24")
        if len(bruto) >= n:
            saida.append(bruto[:n])
    return saida


def quanto_tem_de_verde(caminho):
    """Que parte do quadro e verde de croma -- o verde forte e uniforme de um
    pano de fundo -- de 0 a 1.

    Verde de croma nao e so "puxa para o verde": e verde que domina os outros
    dois canais com folga. Uma planta, uma camiseta ou uma parede esverdeada
    ficam muito abaixo de um pano de fundo, que ocupa quase todo o quadro."""
    quadros = _quadros_rgb(caminho)
    if not quadros:
        return 0.0
    fracoes = []
    for q in quadros:
        verdes = total = 0
        for i in range(0, len(q) - 2, 3):
            r, g, b = q[i], q[i + 1], q[i + 2]
            total += 1
            if g > VERDE_MIN and g > r * 1.25 and g > b * 1.25:
                verdes += 1
        fracoes.append(verdes / max(1, total))
    return sum(fracoes) / len(fracoes)


def _e_verde(r, g, b):
    """Verde de croma nao e so "puxa para o verde": e verde que domina os
    outros dois canais com folga."""
    return g > VERDE_MIN and g > r * 1.25 and g > b * 1.25


def verde_na_moldura(caminho):
    """Que parte da BORDA do quadro e verde de croma, de 0 a 1.

    A borda, e nao o quadro inteiro, porque e ela que separa pano de fundo de
    roupa verde. A pessoa fica no meio; o pano aparece em volta dela.

    MEDIDO. Pano de fundo verde: 85% com a pessoa no meio, 58% com a pessoa
    ocupando quase todo o quadro. Camiseta verde: 13%. Planta num canto: 13%.
    Imagem colorida qualquer: 12%. Gravacao de sala comum: 0%. Pela fracao do
    quadro inteiro os dois grupos quase se encostavam -- 33% do croma apertado
    contra 20% da camiseta -- e a borda os separou por um fator de quatro."""
    quadros = _quadros_rgb(caminho, lado=64)
    if not quadros:
        return 0.0
    lado = 64
    m = max(1, int(lado * MOLDURA))
    fracoes = []
    for q in quadros:
        verdes = total = 0
        for y in range(lado):
            for x in range(lado):
                if not (x < m or x >= lado - m or y < m or y >= lado - m):
                    continue
                i = (y * lado + x) * 3
                total += 1
                if _e_verde(q[i], q[i + 1], q[i + 2]):
                    verdes += 1
        fracoes.append(verdes / max(1, total))
    return sum(fracoes) / len(fracoes)


def tem_fundo_verde(caminho):
    """A pessoa gravou na frente de um pano ou parede verde?

    Esta e a unica pergunta que decide se da para trocar o fundo. Trocar o
    fundo de uma gravacao feita numa sala comum exigiria um modelo treinado
    para separar pessoa de cenario, que este motor nao tem. Responder errado
    para o lado do sim produz um video com pedacos da pessoa apagados."""
    return verde_na_moldura(caminho) >= config.VERDE_DA_MOLDURA


def cor_do_fundo_verde(caminho):
    """A cor media do pano, em 0xRRGGBB, para o corte usar a cor certa.

    Panos verdes nao sao todos iguais, e a iluminacao muda o tom. Cortar por
    uma cor fixa deixa borda no contorno da pessoa."""
    quadros = _quadros_rgb(caminho, lado=64)
    if not quadros:
        return None
    lado = 64
    m = max(1, int(lado * MOLDURA))
    somas, n = [0, 0, 0], 0
    for q in quadros:
        for y in range(lado):
            for x in range(lado):
                if not (x < m or x >= lado - m or y < m or y >= lado - m):
                    continue
                i = (y * lado + x) * 3
                r, g, b = q[i], q[i + 1], q[i + 2]
                if _e_verde(r, g, b):
                    somas[0] += r
                    somas[1] += g
                    somas[2] += b
                    n += 1
    if not n:
        return None
    r, g, b = (v // n for v in somas)
    return f"0x{r:02x}{g:02x}{b:02x}"
