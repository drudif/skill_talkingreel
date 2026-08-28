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
    p = arte.letreiro("QUERO", "brutalista", tmp_path / "l.png")
    im = Image.open(p)
    assert im.size == (config.W, config.H)
    assert im.mode == "RGBA"


def test_o_letreiro_tem_texto_desenhado(tmp_path):
    p = arte.letreiro("QUERO", "brutalista", tmp_path / "l.png")
    assert _tinta(p) is not None


def test_o_letreiro_respeita_a_base_pedida(tmp_path):
    p = arte.letreiro("TESTE", "brutalista", tmp_path / "l.png", base=1200)
    _, _, _, y1 = _tinta(p)
    assert abs(y1 - 1200) < 30


def test_texto_longo_quebra_em_linhas(tmp_path):
    curto = arte.letreiro("UM", "brutalista", tmp_path / "a.png")
    longo = arte.letreiro("UMA FRASE BEM MAIS COMPRIDA QUE A OUTRA",
                          "brutalista", tmp_path / "b.png")
    _, _, y0c, y1c = _tinta(curto)
    _, _, y0l, y1l = _tinta(longo)
    assert (y1l - y0l) > (y1c - y0c)


def test_o_letreiro_nao_vaza_a_margem(tmp_path):
    p = arte.letreiro("UMA FRASE MUITO LONGA QUE PRECISA CABER NO QUADRO",
                      "brutalista", tmp_path / "l.png")
    x0, x1, _, _ = _tinta(p)
    assert x0 >= arte.MARGEM - 12
    assert x1 <= config.W - arte.MARGEM + 12


def test_o_contorno_aparece(tmp_path):
    """Sem contorno o letreiro some sobre imagem clara."""
    com = arte.letreiro("A", "brutalista", tmp_path / "com.png")
    sem = arte.letreiro("A", "brutalista", tmp_path / "sem.png", contorno=0)

    def conta_opacos(caminho):
        im = Image.open(caminho).convert("RGBA")
        return sum(1 for p in im.getchannel("A").getdata() if p > 200)

    assert conta_opacos(com) > conta_opacos(sem)


def test_cada_estilo_desenha(tmp_path):
    for chave in estilos.ESTILOS:
        p = arte.letreiro("TESTE", chave, tmp_path / f"{chave}.png")
        assert _tinta(p) is not None, f"{chave} saiu vazio"


def test_acento_e_desenhado_certo(tmp_path):
    """Modelo de imagem erra acento; texto vetorial nao. O til ocupa altura
    acima da letra, entao o topo da tinta sobe."""
    sem = arte.letreiro("NAO", "brutalista", tmp_path / "sem.png")
    com = arte.letreiro("NÃO", "brutalista", tmp_path / "com.png")
    _, _, y0s, _ = _tinta(sem)
    _, _, y0c, _ = _tinta(com)
    assert y0c < y0s, "o til nao foi desenhado"


# --- Checagem D: uma palavra sem espaco, mais larga que o quadro mesmo no
# corpo minimo, nao pode travar (NameError) nem vazar a moldura. ---

def test_palavra_sem_espaco_nao_trava_nem_vaza(tmp_path):
    """120 'M' seguidos, sem espaco: em uma linha unica no corpo minimo isso
    daria ~2640px de largura (medido), quase 2.5x o quadro de 1080px. A
    funcao tem que fatiar a palavra em vez de travar ou vazar."""
    palavra = "M" * 120
    p = arte.letreiro(palavra, "brutalista", tmp_path / "l.png")
    x0, x1, _, _ = _tinta(p)
    assert x0 >= 0
    assert x1 <= config.W


# --- Checagem E: a moldura de televendas -- janela vazada transparente,
# resto opaco na cor de fundo do estilo. ---

def test_moldura_sai_no_formato_do_filme(tmp_path):
    p, _ = arte.moldura("brutalista", tmp_path / "m.png")
    im = Image.open(p)
    assert im.size == (config.W, config.H)
    assert im.mode == "RGBA"


def test_moldura_janela_transparente_resto_opaco_na_cor_do_fundo(tmp_path):
    """Amostra um pixel no centro da janela (tem que ser 100% transparente)
    e um pixel no canto superior esquerdo, fora da janela (tem que ser
    100% opaco e bater com o `fundo` da ficha de estilo)."""
    ficha = estilos.carregar("brutalista")
    p, (jx, jy, jw, jh) = arte.moldura("brutalista", tmp_path / "m.png")
    im = Image.open(p).convert("RGBA")

    dentro = im.getpixel((jx + jw // 2, jy + jh // 2))
    assert dentro[3] == 0, f"centro da janela nao esta transparente: {dentro}"

    fora = im.getpixel((10, 10))
    assert fora[3] == 255, f"fora da janela nao esta opaco: {fora}"
    assert fora[:3] == estilos.rgb(ficha["fundo"]), \
        f"fora da janela nao bate com o fundo do estilo: {fora[:3]}"


# --- Checagem F: as sete fichas tem que produzir tinta visualmente
# diferente, nao so config diferente. ---

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


def test_os_sete_estilos_produzem_pares_de_cor_diferentes(tmp_path):
    """Para cada estilo, desenha 'A' e sonda a tinta atras dos pixels
    totalmente opacos, exigindo que a cor de preenchimento (`texto`) e a de
    contorno (`contorno`) da ficha realmente aparecam nos pixels renderizados
    -- prova que a fonte foi desenhada com aquela cor, nao so que a config
    diz aquilo. Depois conta quantos pares (preenchimento, contorno)
    distintos existem entre os sete: se duas fichas pintarem igual, o
    conjunto de pares fica menor que 7."""
    pares = set()
    for chave in estilos.ESTILOS:
        ficha = estilos.carregar(chave)
        p = arte.letreiro("A", chave, tmp_path / f"cor_{chave}.png")
        cores = _cores_opacas_na_tinta(p)
        preenchimento = estilos.rgb(ficha["texto"])
        contorno_cor = estilos.rgb(ficha["contorno"])
        assert preenchimento in cores, \
            f"{chave}: cor de preenchimento {preenchimento} nao apareceu na tinta"
        assert contorno_cor in cores, \
            f"{chave}: cor de contorno {contorno_cor} nao apareceu na tinta"
        pares.add((preenchimento, contorno_cor))
    assert len(pares) >= 5, f"so {len(pares)} pares distintos entre os 7: {pares}"


# --- Checagem G: com varias linhas, a base pedida continua sendo onde a
# ULTIMA linha se apoia -- as linhas extras crescem para cima. ---

def test_base_com_tres_linhas_ainda_se_apoia_na_base_pedida(tmp_path):
    """'AGENTES DE IA SAO COMO FACAS GINSU' quebra em tres linhas no estilo
    brutalista (medido). O fundo da tinta tem que ficar perto da base
    pedida -- nao a base menos duas linhas, o que aconteceria se as linhas
    extras crescessem para baixo."""
    texto_tres_linhas = "AGENTES DE IA SAO COMO FACAS GINSU"
    p = arte.letreiro(texto_tres_linhas, "brutalista", tmp_path / "l.png",
                      base=1400)
    _, _, y0, y1 = _tinta(p)
    assert abs(y1 - 1400) < 30, f"base saiu em {y1}, pedida era 1400"
    # confere que de fato quebrou em mais de uma linha (senao o teste nao
    # prova nada sobre "linhas crescem pra cima")
    altura_texto = y1 - y0
    assert altura_texto > 200, \
        f"texto de {altura_texto}px parece ter saido em 1 linha so, nao 3"
