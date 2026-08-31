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







def _larguras(peca, instantes):
    saida = []
    for t in instantes:
        caixa = _quadro(peca, t).getchannel("A").getbbox()
        saida.append(caixa[2] - caixa[0] if caixa else 0)
    return saida






# ---------------------------------------------------------------------------
# A entrada do letreiro: a frase se monta palavra a palavra
#
# E uma so. Houve sete por um tempo, e a escolha entre elas nao mudava nada que
# importasse -- so punha mais uma decisao no caminho de quem quer publicar.
# ---------------------------------------------------------------------------

def _quadro(peca, t):
    """Um quadro da peca animada, como imagem com transparencia."""
    import subprocess
    saida = str(peca) + f".{t:.2f}.png"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(peca),
         "-frames:v", "1", "-c:v", "png", "-pix_fmt", "rgba", saida],
        check=True)
    return Image.open(saida).convert("RGBA")


def test_a_peca_guarda_transparencia(tmp_path):
    """Sem isso o letreiro entraria dentro de um retangulo preto, tapando a
    imagem inteira."""
    peca = arte.letreiro_animado("OLA MUNDO", None, tmp_path / "a.mov", dur=1.2)
    alfa = _quadro(peca, 1.0).getchannel("A")
    assert alfa.getextrema()[0] == 0, "nao ha nenhum ponto transparente"
    assert alfa.getbbox() is not None, "a peca saiu vazia"


def test_a_peca_dura_o_que_foi_pedido(tmp_path):
    from motor import probe
    peca = arte.letreiro_animado("TESTE", None, tmp_path / "d.mov", dur=2.0)
    assert abs(probe.dur(peca) - 2.0) < 0.12


def test_a_frase_vai_se_montando_palavra_a_palavra(tmp_path):
    """O que a entrada promete. A largura da tinta tem de CRESCER ao longo da
    entrada -- se ja comecasse inteira, nao haveria entrada nenhuma."""
    peca = arte.letreiro_animado("UMA DUAS TRES QUATRO", None,
                                 tmp_path / "p.mov", dur=1.5, base=1300)
    larguras = []
    for t in (0.02, 0.14, 0.26, 0.40, 1.0):
        caixa = _quadro(peca, t).getchannel("A").getbbox()
        larguras.append(caixa[2] - caixa[0] if caixa else 0)
    assert larguras == sorted(larguras), (
        f"a frase nao cresceu do comeco ao fim: {larguras}")
    assert larguras[-1] > larguras[0] * 1.8, (
        f"a primeira imagem ja estava quase completa: {larguras}")


def test_o_texto_nao_pula_de_lugar_enquanto_monta(tmp_path):
    """Cada pedaco se apoia no x da frase INTEIRA. Centralizar cada um faria o
    texto saltar para os lados a cada palavra que entra, que e pior de ler do
    que nao ter animacao nenhuma."""
    peca = arte.letreiro_animado("UMA DUAS TRES QUATRO", None,
                                 tmp_path / "q.mov", dur=1.5, base=1300)
    esquerdas = []
    for t in (0.02, 0.14, 0.26, 0.40, 1.0):
        caixa = _quadro(peca, t).getchannel("A").getbbox()
        if caixa:
            esquerdas.append(caixa[0])
    assert max(esquerdas) - min(esquerdas) <= 4, (
        f"a borda esquerda do texto andou durante a entrada: {esquerdas}")


def test_a_frase_termina_igual_ao_letreiro_parado(tmp_path):
    """A entrada muda como o texto chega, nunca onde ele para. Se parasse em
    outro lugar, a conferencia de faixa segura -- que roda sobre o letreiro
    parado -- estaria medindo uma peca diferente da que vai ao ar."""
    parado = arte.letreiro("FIM DA FRASE", None, tmp_path / "p.png", base=1300)
    peca = arte.letreiro_animado("FIM DA FRASE", None, tmp_path / "f.mov",
                                 dur=1.5, base=1300)
    esperado = Image.open(parado).convert("RGBA").getchannel("A").getbbox()
    medido = _quadro(peca, 1.2).getchannel("A").getbbox()
    for e, m in zip(esperado, medido):
        assert abs(e - m) <= 6, (
            f"o letreiro parou fora do lugar: parado {esperado}, animado {medido}")


def test_uma_palavra_so_tambem_funciona(tmp_path):
    """Frase de uma palavra nao tem o que montar, e nao pode quebrar."""
    peca = arte.letreiro_animado("AGORA", None, tmp_path / "u.mov", dur=1.0)
    assert _quadro(peca, 0.8).getchannel("A").getbbox() is not None
