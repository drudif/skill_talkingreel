import pytest
from PIL import Image

from motor import arte, config, estilos


def _tinta(caminho):
    """(x0, x1, y0, y1) do que nao e transparente, ou None se estiver vazio."""
    im = Image.open(caminho).convert("RGBA")
    caixa = im.getchannel("A").getbbox()
    if caixa is None:
        return None
    x0, y0, x1, y1 = caixa
    return x0, x1, y0, y1


def test_o_letreiro_sai_no_formato_do_filme(tmp_path):
    p = arte.letreiro("QUERO", None, tmp_path / "l.png")
    im = Image.open(p)
    assert im.size == (config.W, config.H)
    assert im.mode == "RGBA"


def test_o_letreiro_tem_texto_desenhado(tmp_path):
    p = arte.letreiro("QUERO", None, tmp_path / "l.png")
    assert _tinta(p) is not None


def test_o_letreiro_respeita_a_base_pedida(tmp_path):
    """A base e o limite de baixo, e o que ela protege e a faixa onde o
    aplicativo desenha a propria interface. Entao a regra e assimetrica: a
    tinta NAO PODE passar da base, e nao pode ficar longe demais dela.

    A folga que sobra vem da metrica da fonte -- o espaco reservado para as
    letras que descem (g, p, q) fica vazio quando a frase nao tem nenhuma. As
    cinco fontes de display reservam de 15 a 42 pixels ali, em corpo 104."""
    for chave in estilos.FONTES_LETREIRO:
        p = arte.letreiro("TESTE", {"fonte": chave, "efeito": "contorno"},
                          tmp_path / f"b-{chave}.png", base=1200)
        _, _, _, y1 = _tinta(p)
        assert y1 <= 1200 + CONTORNO_FOLGA, (
            f"a fonte '{chave}' passou da base pedida: a tinta acaba em {y1}")
        assert y1 > 1200 - 60, (
            f"a fonte '{chave}' parou {1200 - y1}px acima da base, longe demais")


CONTORNO_FOLGA = 8   # o traco em volta da letra engrossa a mancha para fora



def test_texto_longo_quebra_em_linhas(tmp_path):
    curto = arte.letreiro("UM", None, tmp_path / "a.png")
    longo = arte.letreiro("UMA FRASE BEM MAIS COMPRIDA QUE A OUTRA",
                          None, tmp_path / "b.png")
    _, _, y0c, y1c = _tinta(curto)
    _, _, y0l, y1l = _tinta(longo)
    assert (y1l - y0l) > (y1c - y0c)


def test_o_letreiro_nao_vaza_a_margem(tmp_path):
    p = arte.letreiro("UMA FRASE MUITO LONGA QUE PRECISA CABER NO QUADRO",
                      None, tmp_path / "l.png")
    x0, x1, _, _ = _tinta(p)
    assert x0 >= arte.MARGEM - 12
    assert x1 <= config.W - arte.MARGEM + 12


def test_o_contorno_aparece(tmp_path):
    """Sem contorno o letreiro some sobre imagem clara."""
    com = arte.letreiro("A", None, tmp_path / "com.png")
    sem = arte.letreiro("A", None, tmp_path / "sem.png", contorno=0)

    def conta_opacos(caminho):
        im = Image.open(caminho).convert("RGBA")
        return sum(1 for p in im.getchannel("A").getdata() if p > 200)

    assert conta_opacos(com) > conta_opacos(sem)


def test_cada_fonte_de_letreiro_desenha(tmp_path):
    """As cinco fontes de display precisam produzir tinta. Uma que nao existisse
    no disco cairia na reserva sem avisar, e o letreiro sairia com a letra de
    outra."""
    for chave in estilos.FONTES_LETREIRO:
        p = arte.letreiro("TESTE", {"fonte": chave},
                          tmp_path / f"f-{chave}.png")
        assert _tinta(p) is not None, f"a fonte '{chave}' nao desenhou nada"


def test_cada_paleta_desenha(tmp_path):
    for chave in estilos.PALETAS:
        p = arte.letreiro("TESTE", {"paleta": chave},
                          tmp_path / f"p-{chave}.png")
        assert _tinta(p) is not None, f"a paleta '{chave}' nao desenhou nada"



def test_acento_e_desenhado_certo(tmp_path):
    """Modelo de imagem erra acento; texto vetorial nao. O til ocupa altura
    acima da letra, entao o topo da tinta sobe."""
    sem = arte.letreiro("NAO", None, tmp_path / "sem.png")
    com = arte.letreiro("NÃO", None, tmp_path / "com.png")
    _, _, y0s, _ = _tinta(sem)
    _, _, y0c, _ = _tinta(com)
    assert y0c < y0s, "o til nao foi desenhado"


# --- Checagem D: uma palavra sem espaco, mais larga que o quadro mesmo no
# corpo minimo, nao pode travar (NameError) nem vazar o quadro. ---

def test_palavra_sem_espaco_nao_trava_nem_vaza(tmp_path):
    """120 'M' seguidos, sem espaco: em uma linha unica no corpo minimo isso
    daria ~2640px de largura (medido), quase 2.5x o quadro de 1080px. A
    funcao tem que fatiar a palavra em vez de travar ou vazar."""
    palavra = "M" * 120
    p = arte.letreiro(palavra, None, tmp_path / "l.png")
    x0, x1, _, _ = _tinta(p)
    assert x0 >= 0
    assert x1 <= config.W


# --- Checagem E (escopo corrigido): sem moldura de cena -- so um box atras
# do proprio letreiro, para sustentacao sobre imagem clara. ---

def test_a_caixa_pinta_em_volta_do_texto_e_o_contorno_deixa_ver(tmp_path):
    """Um ponto logo fora da mancha de texto, mas dentro da folga da caixa
    (28px): opaco e na cor da caixa quando o efeito e `caixa`, e transparente
    na mesma posicao quando e `contorno` -- ali a imagem do video aparece."""
    sem = arte.letreiro("TESTE", {"efeito": "contorno"}, tmp_path / "sem.png")
    com = arte.letreiro("TESTE", {"efeito": "caixa"}, tmp_path / "com.png")
    cor_da_caixa = estilos.rgb(
        estilos.compor({"efeito": "caixa"}, "letreiro")["caixa"])

    x0, x1, y0, _ = _tinta(sem)
    px, py = (x0 + x1) // 2, max(0, y0 - 10)

    im_sem = Image.open(sem).convert("RGBA")
    im_com = Image.open(com).convert("RGBA")
    assert im_sem.getpixel((px, py))[3] == 0, (
        "no efeito de contorno esse ponto deveria deixar a imagem aparecer")
    r, g, b, a = im_com.getpixel((px, py))
    assert a == 255, "no efeito de caixa esse ponto deveria estar pintado"
    assert (r, g, b) == cor_da_caixa, (
        f"a caixa saiu em {(r, g, b)} e a paleta pede {cor_da_caixa}")



def test_box_acompanha_o_tamanho_do_texto(tmp_path):
    """Texto de tres linhas produz um box mais alto que um de uma linha,
    mesmo estilo e mesma base."""
    def altura_do_box(caminho):
        im = Image.open(caminho).convert("RGBA")
        _, y0, _, y1 = im.getchannel("A").getbbox()
        return y1 - y0

    uma_linha = arte.letreiro("OI", {"efeito": "caixa"}, tmp_path / "uma.png")
    tres_linhas = arte.letreiro("AGENTES DE IA SAO COMO FACAS GINSU", {"efeito": "caixa"}, tmp_path / "tres.png")
    assert altura_do_box(tres_linhas) > altura_do_box(uma_linha)


def test_box_nao_vaza_a_margem_lateral_do_quadro(tmp_path):
    p = arte.letreiro("UMA FRASE MUITO LONGA QUE PRECISA CABER NO QUADRO", {"efeito": "caixa"}, tmp_path / "l.png")
    im = Image.open(p).convert("RGBA")
    x0, _, x1, _ = im.getchannel("A").getbbox()
    assert x0 >= 0
    assert x1 <= config.W


def test_a_letra_dentro_da_caixa_usa_a_cor_de_dentro(tmp_path):
    """A paleta tem duas metades de proposito: amarelo com contorno preto se le
    bem sobre video, mas amarelo dentro de caixa amarela sumiria. Quando o
    efeito e caixa, a letra usa a cor de dentro."""
    peca = estilos.compor({"paleta": "amarelo", "efeito": "caixa"}, "letreiro")
    assert peca["texto"] == estilos.PALETAS["amarelo"]["caixa_texto"]
    fora = estilos.compor({"paleta": "amarelo", "efeito": "contorno"},
                          "letreiro")
    assert fora["texto"] == estilos.PALETAS["amarelo"]["texto"]
    assert peca["texto"] != fora["texto"], (
        "a cor dentro e fora da caixa ficou igual, e a caixa some")

def _cores_opacas_na_tinta(caminho):
    """Recorta a bbox da tinta e devolve o conjunto de cores RGB de pixels
    100% opacos (sem blending de antialiasing) -- ou seja, pixels que caem
    bem dentro de um traco (preenchimento ou contorno), nao na borda."""
    im = Image.open(caminho).convert("RGBA")
    caixa = im.getchannel("A").getbbox()
    recorte = im.crop(caixa)
    cores = set()
    for x in range(recorte.width):
        for y in range(recorte.height):
            r, g, b, a = recorte.getpixel((x, y))
            if a == 255:
                cores.add((r, g, b))
    return cores


def test_a_cor_da_paleta_chega_ao_pixel(tmp_path):
    """Prova que a fonte foi desenhada com aquela cor, e nao so que a paleta
    diz aquilo. Sem isto, trocar a paleta poderia nao mudar nada na tela."""
    for chave, cores in estilos.PALETAS.items():
        p = arte.letreiro("A", {"paleta": chave, "efeito": "contorno"},
                          tmp_path / f"cor_{chave}.png")
        na_tinta = _cores_opacas_na_tinta(p)
        assert estilos.rgb(cores["texto"]) in na_tinta, (
            f"{chave}: a cor da letra nao apareceu na tinta")
        assert estilos.rgb(cores["contorno"]) in na_tinta, (
            f"{chave}: a cor do contorno nao apareceu na tinta")

def test_base_com_tres_linhas_ainda_se_apoia_na_base_pedida(tmp_path):
    """'AGENTES DE IA SAO COMO FACAS GINSU' quebra em tres linhas no estilo
    brutalista (medido). O fundo da tinta tem que ficar perto da base
    pedida -- nao a base menos duas linhas, o que aconteceria se as linhas
    extras crescessem para baixo."""
    texto_tres_linhas = "AGENTES DE IA SAO COMO FACAS GINSU"
    p = arte.letreiro(texto_tres_linhas, None, tmp_path / "l.png",
                      base=1400)
    _, _, y0, y1 = _tinta(p)
    assert abs(y1 - 1400) < 30, f"base saiu em {y1}, pedida era 1400"
    # confere que de fato quebrou em mais de uma linha (senao o teste nao
    # prova nada sobre "linhas crescem pra cima")
    altura_texto = y1 - y0
    assert altura_texto > 200, \
        f"texto de {altura_texto}px parece ter saido em 1 linha so, nao 3"


# ---------------------------------------------------------------------------
# O letreiro entrando
#
# A animacao transforma o desenho pronto; ela nao redesenha o texto. O que
# estes testes protegem: que a peca guarde transparencia (sem isso o letreiro
# entra dentro de um retangulo preto), que ela chegue na posicao certa, e que
# cada entrada faca o movimento que o nome dela promete.
# ---------------------------------------------------------------------------

def _quadro(peca, t):
    """Um quadro da peca animada, como imagem com transparencia."""
    import subprocess
    from PIL import Image
    saida = str(peca) + f".{t:.2f}.png"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(peca),
         "-frames:v", "1", "-c:v", "png", "-pix_fmt", "rgba", saida],
        check=True)
    return Image.open(saida).convert("RGBA")


@pytest.mark.parametrize("animacao", arte.ANIMACOES)
def test_cada_entrada_produz_peca_com_transparencia(tmp_path, animacao):
    """Sem transparencia o letreiro entraria dentro de um retangulo preto,
    tapando a imagem inteira."""
    peca = arte.letreiro_animado("OLA MUNDO", None,
                                 tmp_path / f"{animacao}.mov",
                                 animacao=animacao, dur=1.2)
    im = _quadro(peca, 1.0)
    alfa = im.getchannel("A")
    assert alfa.getextrema()[0] == 0, (
        "nao ha nenhum ponto transparente: a peca taparia o video inteiro")
    assert alfa.getbbox() is not None, "a peca saiu vazia"


@pytest.mark.parametrize("animacao", arte.ANIMACOES)
def test_a_peca_dura_o_que_foi_pedido(tmp_path, animacao):
    from motor import probe
    peca = arte.letreiro_animado("TESTE", None,
                                 tmp_path / f"d{animacao}.mov",
                                 animacao=animacao, dur=2.0)
    assert abs(probe.dur(peca) - 2.0) < 0.12, (
        f"pedi 2,0s e a peca saiu com {probe.dur(peca):.2f}s")


@pytest.mark.parametrize("animacao", arte.ANIMACOES)
def test_o_letreiro_chega_na_mesma_posicao_do_letreiro_parado(tmp_path, animacao):
    """A animacao muda como o texto entra, nunca onde ele para. Se parasse em
    outro lugar, a conferencia de faixa segura -- que roda sobre o letreiro
    parado -- estaria medindo uma peca diferente da que vai ao ar."""
    from PIL import Image
    parado = arte.letreiro("FIM", None, tmp_path / f"p{animacao}.png",
                           base=1300)
    peca = arte.letreiro_animado("FIM", None,
                                 tmp_path / f"a{animacao}.mov",
                                 animacao=animacao, dur=1.5, base=1300)
    esperado = Image.open(parado).convert("RGBA").getchannel("A").getbbox()
    medido = _quadro(peca, 1.2).getchannel("A").getbbox()
    for i, (e, m) in enumerate(zip(esperado, medido)):
        assert abs(e - m) <= 6, (
            f"a entrada '{animacao}' parou fora do lugar: o letreiro parado "
            f"ocupa {esperado} e o animado terminou em {medido}")


def test_a_entrada_comeca_fora_da_posicao_final(tmp_path):
    """Se o primeiro quadro ja estivesse no lugar e opaco, nao haveria
    animacao nenhuma -- e o teste acima passaria do mesmo jeito."""
    from PIL import Image
    peca = arte.letreiro_animado("SOBE", None, tmp_path / "s.mov",
                                 animacao="sobe", dur=1.5, base=1300)
    cedo = _quadro(peca, 0.03).getchannel("A")
    tarde = _quadro(peca, 1.2).getchannel("A")
    assert cedo.getbbox() != tarde.getbbox() or \
        max(cedo.getextrema()) < max(tarde.getextrema()), (
        "o primeiro quadro ja esta igual ao ultimo: nada se moveu")


def test_sobe_move_na_vertical_e_esquerda_move_na_horizontal(tmp_path):
    def desloc(animacao):
        peca = arte.letreiro_animado("MOVE", None,
                                     tmp_path / f"m{animacao}.mov",
                                     animacao=animacao, dur=1.5, base=1300)
        a = _quadro(peca, 0.06).getchannel("A").getbbox()
        b = _quadro(peca, 1.2).getchannel("A").getbbox()
        if a is None or b is None:
            return 0, 0
        return abs(a[0] - b[0]), abs(a[1] - b[1])

    dx_sobe, dy_sobe = desloc("sobe")
    dx_esq, dy_esq = desloc("esquerda")
    assert dy_sobe > dx_sobe, (
        f"'sobe' deveria mover mais na vertical (moveu {dx_sobe} na "
        f"horizontal e {dy_sobe} na vertical)")
    assert dx_esq > dy_esq, (
        f"'esquerda' deveria mover mais na horizontal (moveu {dx_esq} na "
        f"horizontal e {dy_esq} na vertical)")


def _larguras(peca, instantes):
    saida = []
    for t in instantes:
        caixa = _quadro(peca, t).getchannel("A").getbbox()
        saida.append(caixa[2] - caixa[0] if caixa else 0)
    return saida


def test_pulo_muda_o_tamanho_do_texto_e_aparece_nao(tmp_path):
    """O que separa o 'pulo' das outras entradas e a escala mudando. Medir so
    o pulo nao provaria nada -- e o par que prova, porque 'aparece' passa pelo
    mesmo caminho de codigo e tem de sair com tamanho constante."""
    instantes = [0.0, 0.05, 0.10, 0.20, 0.30, 0.44, 1.2]
    pulo = _larguras(
        arte.letreiro_animado("PULO", None, tmp_path / "pu.mov",
                              animacao="pulo", dur=1.5, base=1300), instantes)
    aparece = _larguras(
        arte.letreiro_animado("PULO", None, tmp_path / "ap.mov",
                              animacao="aparece", dur=1.5, base=1300), instantes)

    variacao_pulo = max(pulo) - min(pulo)
    variacao_aparece = max(aparece) - min(aparece)
    assert variacao_pulo > 20, (
        f"o 'pulo' quase nao mudou de tamanho ao longo da entrada: "
        f"larguras {pulo}")
    assert variacao_aparece <= 2, (
        f"o 'aparece' mudou de tamanho, e nao deveria: larguras {aparece}")


def test_o_pulo_passa_do_tamanho_final_e_volta(tmp_path):
    """O repuxo e o que faz o movimento parecer vivo em vez de so crescer.
    Sem ele o 'pulo' seria um 'cresce'."""
    instantes = [0.0, 0.06, 0.12, 0.18, 0.24, 0.30, 0.36, 0.42, 1.2]
    larguras = _larguras(
        arte.letreiro_animado("PULO", None, tmp_path / "ov.mov",
                              animacao="pulo", dur=1.5, base=1300), instantes)
    final = larguras[-1]
    assert max(larguras[:-1]) > final, (
        f"o texto nunca passou do tamanho final ({final}px) durante a "
        f"entrada: {larguras[:-1]}")


def test_entrada_desconhecida_e_erro(tmp_path):
    with pytest.raises(ValueError, match="aparece"):
        arte.letreiro_animado("X", None, tmp_path / "x.mov",
                              animacao="explode")
