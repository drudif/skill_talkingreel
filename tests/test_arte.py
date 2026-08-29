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
# corpo minimo, nao pode travar (NameError) nem vazar o quadro. ---

def test_palavra_sem_espaco_nao_trava_nem_vaza(tmp_path):
    """120 'M' seguidos, sem espaco: em uma linha unica no corpo minimo isso
    daria ~2640px de largura (medido), quase 2.5x o quadro de 1080px. A
    funcao tem que fatiar a palavra em vez de travar ou vazar."""
    palavra = "M" * 120
    p = arte.letreiro(palavra, "brutalista", tmp_path / "l.png")
    x0, x1, _, _ = _tinta(p)
    assert x0 >= 0
    assert x1 <= config.W


# --- Checagem E (escopo corrigido): sem moldura de cena -- so um box atras
# do proprio letreiro, para sustentacao sobre imagem clara. ---

def test_box_pinta_ao_redor_do_texto_e_sem_box_fica_transparente(tmp_path):
    """Um pixel logo fora da mancha de texto, mas dentro da folga do box
    (28px), tem que estar opaco e na cor de fundo da ficha quando box=True --
    e transparente na mesma posicao quando box=False."""
    sem_box = arte.letreiro("TESTE", "neubrutal", tmp_path / "sem.png")
    com_box = arte.letreiro("TESTE", "neubrutal", tmp_path / "com.png", box=True)
    ficha = estilos.carregar("neubrutal")

    x0, x1, y0, _ = _tinta(sem_box)
    px, py = (x0 + x1) // 2, max(0, y0 - 10)

    im_sem = Image.open(sem_box).convert("RGBA")
    assert im_sem.getpixel((px, py))[3] == 0, \
        "sem box, o pixel ao redor do texto deveria ser transparente"

    im_com = Image.open(com_box).convert("RGBA")
    pixel = im_com.getpixel((px, py))
    assert pixel[3] == 255, f"com box, o pixel deveria ser opaco: {pixel}"
    assert pixel[:3] == estilos.rgb(ficha["fundo"]), \
        f"com box, a cor deveria ser o fundo da ficha: {pixel[:3]}"


def test_box_acompanha_o_tamanho_do_texto(tmp_path):
    """Texto de tres linhas produz um box mais alto que um de uma linha,
    mesmo estilo e mesma base."""
    def altura_do_box(caminho):
        im = Image.open(caminho).convert("RGBA")
        _, y0, _, y1 = im.getchannel("A").getbbox()
        return y1 - y0

    uma_linha = arte.letreiro("OI", "neubrutal", tmp_path / "uma.png", box=True)
    tres_linhas = arte.letreiro("AGENTES DE IA SAO COMO FACAS GINSU",
                                "neubrutal", tmp_path / "tres.png", box=True)
    assert altura_do_box(tres_linhas) > altura_do_box(uma_linha)


def test_box_nao_vaza_a_margem_lateral_do_quadro(tmp_path):
    p = arte.letreiro("UMA FRASE MUITO LONGA QUE PRECISA CABER NO QUADRO",
                      "neubrutal", tmp_path / "l.png", box=True)
    im = Image.open(p).convert("RGBA")
    x0, _, x1, _ = im.getchannel("A").getbbox()
    assert x0 >= 0
    assert x1 <= config.W


def test_box_usa_contorno_quando_texto_e_fundo_sao_iguais(tmp_path):
    """No brutalista, `texto` e `fundo` sao os dois #FFE800 (amarelo): se o
    box usasse o fundo, o texto sumiria em cima dele. Confere que so o
    brutalista cai nesse caso entre os sete estilos, e que o box dele de
    fato usa a cor de `contorno`, nao a de `fundo`."""
    fichas_com_texto_igual_ao_fundo = sorted(
        chave for chave, e in estilos.ESTILOS.items() if e["fundo"] == e["texto"])
    assert fichas_com_texto_igual_ao_fundo == ["brutalista"], \
        f"esperava so o brutalista, achei: {fichas_com_texto_igual_ao_fundo}"

    ficha = estilos.carregar("brutalista")
    sem_box = arte.letreiro("TESTE", "brutalista", tmp_path / "sem.png")
    com_box = arte.letreiro("TESTE", "brutalista", tmp_path / "com.png", box=True)

    x0, x1, y0, _ = _tinta(sem_box)
    px, py = (x0 + x1) // 2, max(0, y0 - 10)
    im_com = Image.open(com_box).convert("RGBA")
    pixel = im_com.getpixel((px, py))
    assert pixel[3] == 255
    assert pixel[:3] == estilos.rgb(ficha["contorno"]), \
        f"o box do brutalista deveria usar o contorno, saiu {pixel[:3]}"
    assert pixel[:3] != estilos.rgb(ficha["fundo"])


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
