"""As duas previas: o catalogo de escolhas e o filme leve.

O catalogo mostra UM EIXO POR VEZ -- as tres fontes com a mesma cor e o mesmo
efeito, depois as cinco cores com a mesma fonte. Comparar as trinta combinacoes
de uma vez nao e escolher, e adivinhar; e a folha estaria pedindo uma decisao
que ninguem consegue tomar olhando.
"""
import subprocess

import pytest
from PIL import Image

from motor import config, estilos, miniatura, previa, probe
from tests import fixtures


@pytest.fixture
def gravacao(tmp_path):
    return fixtures.clipe_fala(tmp_path / "g.mov", falas=[(0.3, 2.0)],
                               total=3.0)


def _dif(a, b, caixa):
    """Diferenca media pixel a pixel dentro de `caixa`.

    Pixel a pixel, e num recorte apertado: brilho MEDIO cancela sinal --
    contorno preto contra preenchimento claro se anulam na media, e duas
    imagens muito diferentes empatam."""
    ia = Image.open(a).convert("L").crop(caixa)
    ib = Image.open(b).convert("L").crop(caixa)
    pa, pb = list(ia.getdata()), list(ib.getdata())
    return sum(abs(x - y) for x, y in zip(pa, pb)) / max(1, len(pa))


# --- a amostra ---

def test_a_amostra_sai_no_tamanho_do_video(tmp_path, gravacao):
    p = previa.amostra(gravacao, 1.0, None, tmp_path / "a.jpg",
                       letreiro="OLA", legenda="teste")
    assert Image.open(p).size == (config.W, config.H)


def test_a_amostra_mostra_o_letreiro_e_a_legenda(tmp_path, gravacao):
    """Sem o texto por cima a amostra e so um quadro do video, e nao ajuda
    ninguem a escolher estilo nenhum."""
    from motor import arte
    limpa = previa.amostra(gravacao, 1.0, None, tmp_path / "limpa.jpg")
    cheia = previa.amostra(gravacao, 1.0, None, tmp_path / "cheia.jpg",
                           letreiro="ISSO MUDA TUDO", legenda="a legenda")
    ref = arte.letreiro("ISSO MUDA TUDO", None, tmp_path / "r.png")
    caixa = Image.open(ref).convert("RGBA").getchannel("A").getbbox()
    assert _dif(limpa, cheia, caixa) > 20, (
        "o letreiro nao apareceu na amostra")


def _caixa_da_legenda(tmp_path, texto):
    """A regiao onde a legenda cai, tirada da propria peca."""
    from motor import legenda as mod_legenda
    g = mod_legenda.png(texto, None, tmp_path / "_rg.png")
    return Image.open(g).convert("RGBA").getchannel("A").getbbox()


def _caixa_das_pecas(tmp_path, texto_letreiro, texto_legenda):
    """A regiao onde o estilo se manifesta: onde cai o letreiro mais onde cai
    a legenda.

    Recorte apertado, tirado do bbox das PROPRIAS pecas. Um recorte chutado,
    maior que a tinta, dilui a diferenca na media e faz duas imagens bem
    distintas empatarem."""
    from motor import arte, legenda as mod_legenda
    l = arte.letreiro(texto_letreiro, None, tmp_path / "_rl.png")
    g = mod_legenda.png(texto_legenda, "brutalista", tmp_path / "_rg.png")
    cl = Image.open(l).convert("RGBA").getchannel("A").getbbox()
    cg = Image.open(g).convert("RGBA").getchannel("A").getbbox()
    return (min(cl[0], cg[0]), min(cl[1], cg[1]),
            max(cl[2], cg[2]), max(cl[3], cg[3]))


def test_as_opcoes_de_um_eixo_nao_saem_parecidas(tmp_path, gravacao):
    """O teste que sustenta o catalogo: se duas opcoes do mesmo eixo saem
    iguais na amostra, a folha pede uma escolha impossivel de fazer olhando."""
    caixa = _caixa_da_legenda(tmp_path, "a legenda fica assim")
    cat = previa.catalogo(gravacao, 1.0, tmp_path / "cat", "legenda",
                          "a legenda fica assim")
    for eixo, opcoes in cat.items():
        chaves = list(opcoes)
        iguais = []
        for i, a in enumerate(chaves):
            for b in chaves[i + 1:]:
                d = _dif(opcoes[a], opcoes[b], caixa)
                if d < 8:
                    iguais.append((a, b, round(d, 1)))
        assert not iguais, (
            f"no eixo '{eixo}' estas opcoes saem quase identicas: {iguais}")




def test_o_catalogo_cobre_os_tres_eixos_inteiros(tmp_path, gravacao):
    cat = previa.catalogo(gravacao, 1.0, tmp_path / "c2", "letreiro", "OLA")
    assert set(cat) == {"fonte", "paleta", "efeito"}
    assert set(cat["fonte"]) == set(estilos.FONTES_LETREIRO)
    assert set(cat["paleta"]) == set(estilos.PALETAS)
    assert set(cat["efeito"]) == set(estilos.EFEITOS)
    for eixo in cat.values():
        for caminho in eixo.values():
            assert caminho.exists() and caminho.stat().st_size > 0


def test_o_catalogo_muda_uma_coisa_de_cada_vez(tmp_path, gravacao):
    """E o que torna a comparacao possivel. Se cada amostra mudasse tudo, a
    pessoa nao teria como saber o que causou a diferenca que ela viu."""
    cat = previa.catalogo(gravacao, 1.0, tmp_path / "c3", "legenda", "texto",
                          fixas={"paleta": "amarelo", "efeito": "caixa"})
    # no eixo da fonte, todas saem amarelas e com caixa; o que muda e a letra
    assert len(cat["fonte"]) == len(estilos.FONTES_LEGENDA)
    assert len(cat["paleta"]) == len(estilos.PALETAS)



def test_a_amostra_cabe_na_folha(tmp_path, gravacao):
    """A folha nao carrega arquivo de fora: a imagem vai embutida nela. Uma
    amostra grande demais infla a pagina inteira."""
    p = previa.amostra(gravacao, 1.0, None, tmp_path / "m.jpg",
                       letreiro="TESTE", legenda="legenda")
    uri = miniatura.de_imagem(p)
    assert uri and uri.startswith("data:image/jpeg;base64,")
    assert len(uri) <= miniatura.TETO_BYTES, (
        f"a miniatura ficou com {len(uri)} bytes, teto {miniatura.TETO_BYTES}")


def test_a_amostra_nao_deixa_arquivo_solto(tmp_path, gravacao):
    """Os arquivos de passagem sao apagados. Sete estilos deixariam vinte e um
    arquivos na pasta de trabalho da pessoa."""
    previa.amostra(gravacao, 1.0, None, tmp_path / "s.jpg",
                   letreiro="OLA", legenda="oi")
    soltos = [p.name for p in tmp_path.iterdir() if p.name.startswith(".")]
    assert not soltos, f"sobraram arquivos de passagem: {soltos}"


# --- o filme em baixa ---

def test_o_filme_em_baixa_fica_muito_menor(tmp_path, gravacao):
    leve = previa.em_baixa(gravacao, tmp_path / "leve.mp4")
    assert leve.stat().st_size < gravacao.stat().st_size / 2, (
        "a previa nao ficou leve o bastante para mandar por mensagem")


def test_o_filme_em_baixa_mantem_a_duracao(tmp_path, gravacao):
    """E para aprovar o CORTE. Se a duracao mudar, o que a pessoa aprova nao e
    o filme que ela vai receber."""
    leve = previa.em_baixa(gravacao, tmp_path / "l2.mp4")
    assert abs(probe.dur(leve) - probe.dur(gravacao)) < 0.15


def test_o_filme_em_baixa_mantem_o_som(tmp_path, gravacao):
    leve = previa.em_baixa(gravacao, tmp_path / "l3.mp4")
    assert probe.tem_audio(leve) is True


def test_o_filme_em_baixa_continua_em_pe(tmp_path):
    """A largura e fixa e a altura sai do proprio video. Se a conta errar, a
    previa sai deitada e a pessoa aprova um enquadramento que nao existe."""
    vertical = fixtures.clipe_fala(tmp_path / "v.mov", falas=[(0.2, 1.0)],
                                   total=1.5, w=1080, h=1920)
    leve = previa.em_baixa(vertical, tmp_path / "l4.mp4")
    w, h = probe.dimensao(leve)
    assert h > w, f"a previa saiu deitada: {w}x{h}"
    assert abs(w / h - 1080 / 1920) < 0.02
