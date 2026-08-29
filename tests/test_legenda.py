import os

import pytest

from motor import legenda


def _p(texto, t, f):
    return {"p": texto, "t": t, "f": f}


def test_quebra_em_fim_de_frase():
    palavras = [_p("muito", 0.0, 0.3), _p("agente.", 0.3, 0.6),
                _p("Voce", 0.7, 1.0), _p("que", 1.0, 1.2)]
    blocos = legenda.blocos(palavras)
    assert len(blocos) == 2
    assert blocos[0][-1]["p"] == "agente."


def test_quebra_no_respiro():
    palavras = [_p("uma", 0.0, 0.3), _p("frase", 0.3, 0.6),
                _p("outra", 1.5, 1.8)]      # 0.9s de silencio
    assert len(legenda.blocos(palavras)) == 2


def test_teto_de_palavras():
    palavras = [_p(f"w{i}", i * 0.2, i * 0.2 + 0.15) for i in range(9)]
    for b in legenda.blocos(palavras):
        assert len(b) <= legenda.MAX_PALAVRAS


def test_bloco_orfao_junta_com_o_vizinho():
    palavras = [_p("a", 0.0, 0.2), _p("b", 0.2, 0.4),
                _p("c", 0.4, 0.6), _p("d", 0.6, 0.8), _p("e", 0.85, 1.0)]
    blocos = legenda.blocos(palavras)
    assert all(len(b) > 1 for b in blocos), "sobrou bloco de uma palavra so"


def test_nome_proprio_e_corrigido():
    palavras = [_p("as", 0.0, 0.2), _p("facas", 0.2, 0.5), _p("guinco", 0.5, 0.9)]
    trocas = legenda.corrigir(palavras, ["Ginsu"])
    assert len(trocas) == 1
    assert palavras[2]["p"] == "Ginsu"


def test_palavra_curta_nao_e_trocada():
    """A regra larga destruia a fala: 'ter' virava 'te', 'quem' virava 'que'."""
    originais = ["ter", "quem", "no", "teu", "meus", "deles"]
    palavras = [_p(w, i * 0.3, i * 0.3 + 0.2) for i, w in enumerate(originais)]
    legenda.corrigir(palavras, ["Ginsu", "te", "que", "Nao"])
    assert [w["p"] for w in palavras] == originais


def test_pontuacao_colada_sobrevive_a_troca():
    palavras = [_p("guinco?", 0.0, 0.4)]
    legenda.corrigir(palavras, ["Ginsu"])
    assert palavras[0]["p"] == "Ginsu?"


def test_troca_pedida_pode_inserir_mais_de_uma_palavra():
    palavras = [_p("a", 0.0, 0.2), _p("generativa", 0.2, 0.8)]
    legenda.corrigir(palavras, [], pedidas={"generativa": "I.A. generativa"})
    assert palavras[1]["p"] == "I.A. generativa"


def test_rebalanceia_sem_estourar_o_teto():
    palavras = [_p(c, i * 0.2, i * 0.2 + 0.15)
                for i, c in enumerate("abcde")]
    bs = legenda.blocos(palavras)
    assert all(1 < len(b) <= legenda.MAX_PALAVRAS for b in bs)
    assert [w["p"] for b in bs for w in b] == list("abcde"), (
        "rebalancear nao pode reordenar nem perder palavra")


def test_orfao_isolado_por_silencio_fica_sozinho():
    """Nao inventa companhia: se a palavra esta separada por pausa longa,
    ela e um bloco de uma palavra mesmo."""
    palavras = [_p("a", 0.0, 0.2), _p("b", 0.2, 0.4), _p("c", 0.4, 0.6),
                _p("sozinha", 3.0, 3.4)]
    bs = legenda.blocos(palavras)
    assert bs[-1] == [palavras[-1]]


def test_nenhuma_palavra_se_perde_nem_se_duplica():
    palavras = [_p(f"w{i}", i * 0.25, i * 0.25 + 0.2) for i in range(23)]
    bs = legenda.blocos(palavras)
    assert [w["p"] for b in bs for w in b] == [f"w{i}" for i in range(23)]


def test_blocos_ficam_em_ordem_de_tempo():
    palavras = [_p(f"w{i}", i * 0.25, i * 0.25 + 0.2) for i in range(23)]
    bs = legenda.blocos(palavras)
    inicios = [b[0]["t"] for b in bs]
    assert inicios == sorted(inicios)


def test_correcao_nao_move_palavra_no_tempo():
    """A correcao mexe so no texto. Timestamp tem que sobreviver intacto,
    inclusive nas palavras trocadas."""
    palavras = [_p("as", 0.0, 0.2), _p("facas", 0.2, 0.5), _p("guinco", 0.5, 0.9)]
    originais = [(w["t"], w["f"]) for w in palavras]
    legenda.corrigir(palavras, ["Ginsu"])
    assert [(w["t"], w["f"]) for w in palavras] == originais


def test_nome_proprio_de_quatro_letras_ainda_e_corrigido():
    """A guarda protege a fala sem cegar a correcao. Subir MIN_LETRAS para 5
    faria este teste falhar: 'Nike' tem quatro letras."""
    palavras = [_p("comprei", 0.0, 0.4), _p("naique", 0.4, 0.9)]
    trocas = legenda.corrigir(palavras, ["Nike"])
    assert palavras[1]["p"] == "Nike"
    assert len(trocas) == 1


def test_alvo_curto_nunca_ganha():
    """A origem de toda troca errada: um alvo de duas ou tres letras bate alto
    contra qualquer palavra curta da fala."""
    palavras = [_p("quem", 0.0, 0.3), _p("deles", 0.3, 0.7)]
    trocas = legenda.corrigir(palavras, ["que", "te", "Nao", "ele"])
    assert trocas == []
    assert [w["p"] for w in palavras] == ["quem", "deles"]


def test_as_quatro_posicoes_existem():
    assert set(legenda.POSICOES) == {"cheia", "esquerda", "direita", "centro"}


def test_legenda_em_tela_cheia_e_centralizada(tmp_path):
    from PIL import Image
    p = legenda.png("uma frase", "brutalista", tmp_path / "a.png", posicao="cheia")
    caixa = Image.open(p).convert("RGBA").getchannel("A").getbbox()
    x0, y0, x1, y1 = caixa
    centro = (x0 + x1) / 2
    assert abs(centro - 540) < 20, "nao ficou centralizada"
    assert abs(y1 - 1375) < 30, "a base nao e 1375"


def test_legenda_a_esquerda_no_split(tmp_path):
    from PIL import Image
    p = legenda.png("uma frase", "brutalista", tmp_path / "b.png", posicao="esquerda")
    x0, y0, _, _ = Image.open(p).convert("RGBA").getchannel("A").getbbox()
    assert abs(x0 - 60) < 12
    assert abs(y0 - 827) < 12


def test_legenda_a_direita_no_split(tmp_path):
    from PIL import Image
    p = legenda.png("uma frase", "brutalista", tmp_path / "c.png", posicao="direita")
    _, y0, x1, _ = Image.open(p).convert("RGBA").getchannel("A").getbbox()
    assert abs(x1 - (1080 - 60)) < 12
    assert abs(y0 - 827) < 12


def test_centro_do_split_usa_a_mesma_base_da_tela_cheia(tmp_path):
    from PIL import Image
    a = legenda.png("frase", "brutalista", tmp_path / "d.png", posicao="cheia")
    b = legenda.png("frase", "brutalista", tmp_path / "e.png", posicao="centro")
    ba = Image.open(a).convert("RGBA").getchannel("A").getbbox()
    bb = Image.open(b).convert("RGBA").getchannel("A").getbbox()
    assert abs(ba[3] - bb[3]) < 4, "a legenda saltaria na virada de cena"


def test_texto_longo_quebra_e_nao_vaza(tmp_path):
    from PIL import Image
    from motor import config
    p = legenda.png("uma frase bastante longa que precisa quebrar em duas linhas",
                    "brutalista", tmp_path / "f.png", posicao="cheia")
    x0, y0, x1, y1 = Image.open(p).convert("RGBA").getchannel("A").getbbox()
    assert (x1 - x0) <= config.LEG_LARGURA_MAX + 8
    assert (y1 - y0) > config.LEG_CORPO      # mais de uma linha


def _bbox(caminho):
    from PIL import Image
    return Image.open(caminho).convert("RGBA").getchannel("A").getbbox()


def test_palavra_sem_espaco_nao_vaza_o_quadro(tmp_path):
    """Um link ou hashtag colada e uma palavra so. Sem fatiar, a caixa fica
    mais larga que o quadro e o Pillow corta a tinta em silencio — e o bbox
    do PNG nunca denuncia, porque nao pode ser maior que o proprio PNG.
    Por isso o teste olha a MARGEM, nao o tamanho."""
    from motor import config
    palavra = "a" * 40
    for posicao in legenda.POSICOES:
        p = legenda.png(palavra, "brutalista", tmp_path / f"{posicao}.png",
                        posicao=posicao)
        x0, y0, x1, y1 = _bbox(p)
        assert x0 > 4, f"{posicao}: a tinta encosta na borda esquerda (x0={x0})"
        assert x1 < config.W - 4, (
            f"{posicao}: a tinta encosta na borda direita (x1={x1})")
        assert (x1 - x0) <= config.LEG_LARGURA_MAX + 8, (
            f"{posicao}: a caixa passou da largura maxima ({x1 - x0}px)")


def test_palavra_sem_espaco_vira_mais_de_uma_linha(tmp_path):
    from motor import config
    p = legenda.png("a" * 40, "brutalista", tmp_path / "fatiada.png")
    _, y0, _, y1 = _bbox(p)
    assert (y1 - y0) > config.LEG_CORPO * config.LEG_ENTRELINHA * 1.5, (
        "a palavra longa nao foi fatiada em mais de uma linha")


def test_frase_normal_continua_em_uma_linha(tmp_path):
    """A quebra forcada nao pode fatiar quem cabe."""
    from motor import config
    p = legenda.png("uma frase", "brutalista", tmp_path / "curta.png")
    _, y0, _, y1 = _bbox(p)
    assert (y1 - y0) < config.LEG_CORPO * config.LEG_ENTRELINHA * 1.5


LENTO = pytest.mark.skipif(
    os.environ.get("TESTE_LENTO") != "1",
    reason="baixa e roda o modelo de transcricao; ligue com TESTE_LENTO=1")


def test_transcrever_devolve_o_formato_que_os_blocos_esperam():
    """Sem rodar o modelo: prova o contrato de dados que o resto consome."""
    palavras = [{"p": "ola", "t": 0.0, "f": 0.4}]
    assert legenda.blocos(palavras)[0][0]["p"] == "ola"


@LENTO
def test_transcrever_acha_as_palavras(tmp_path):
    import subprocess
    fala = tmp_path / "fala.wav"
    # voz sintetica do proprio macOS: fala de verdade, sem depender de gravacao
    subprocess.run(["say", "-v", "Luciana", "-o", str(fala),
                    "--data-format=LEF32@22050", "as facas ginsu cortam tudo"],
                   check=True)
    palavras = legenda.transcrever(fala, modelo="medium")
    texto = " ".join(w["p"] for w in palavras).lower()
    assert "facas" in texto
    assert all(w["f"] >= w["t"] for w in palavras)
    assert palavras == sorted(palavras, key=lambda w: w["t"])


def test_sob_letreiro_reconhece_a_janela():
    mapa = [{"n": 1, "ini": 0.0, "fim": 3.0, "letreiro": [0.0, 3.0]},
            {"n": 2, "ini": 3.0, "fim": 6.0}]
    assert legenda.sob_letreiro(0.5, 1.5, mapa) is True
    assert legenda.sob_letreiro(4.0, 5.0, mapa) is False


def test_sob_letreiro_pega_sobreposicao_parcial():
    mapa = [{"n": 1, "ini": 0.0, "fim": 3.0, "letreiro": [1.0, 2.0]}]
    assert legenda.sob_letreiro(1.8, 2.5, mapa) is True


def _crop_da_legenda(tmp_path, texto, posicao="cheia"):
    """O recorte exato onde a legenda tem tinta. Chutar coordenada dilui o
    sinal — medido antes, um recorte quatro vezes maior que a tinta baixou a
    diferenca de 72 para 15."""
    from PIL import Image
    ref = legenda.png(texto, "brutalista", tmp_path / "_ref.png", posicao=posicao)
    x0, y0, x1, y1 = Image.open(ref).convert("RGBA").getchannel("A").getbbox()
    return f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}"


def _regiao(caminho, t, crop):
    import subprocess
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(caminho),
         "-frames:v", "1", "-vf", f"{crop},scale=48:16",
         "-pix_fmt", "gray", "-f", "rawvideo", "-"], capture_output=True)
    return list(r.stdout[:768])


def _quanto_mudou(caminho, t1, t2, crop):
    a, b = _regiao(caminho, t1, crop), _regiao(caminho, t2, crop)
    assert a and b, "nao consegui ler o quadro"
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def test_a_faixa_tem_a_duracao_do_filme(tmp_path):
    from motor import probe
    from tests import fixtures
    filme = fixtures.clipe_fala(tmp_path / "f.mov", falas=[(0.3, 2.0)], total=4.0)
    palavras = [{"p": "uma", "t": 0.5, "f": 0.8},
                {"p": "frase", "t": 0.8, "f": 1.2}]
    faixa, omitidos = legenda.faixa(legenda.blocos(palavras), "brutalista",
                                    tmp_path / "faixa.mov", total=probe.dur(filme),
                                    mapa=[])
    assert abs(probe.dur(faixa) - 4.0) < 0.15, (
        "a faixa inflou — a ultima entrada duplicada herdou a duracao anterior")
    assert omitidos == 0


def test_queimar_nao_muda_duracao_nem_audio(tmp_path):
    from motor import probe
    from tests import fixtures
    filme = fixtures.clipe_fala(tmp_path / "g.mov", falas=[(0.3, 2.0)], total=4.0)
    palavras = [{"p": "teste", "t": 0.5, "f": 1.0}]
    saida = legenda.queimar(filme, legenda.blocos(palavras), "brutalista",
                            tmp_path / "leg.mp4", mapa=[])
    assert abs(probe.dur(saida) - probe.dur(filme)) < 0.15
    assert probe.tem_audio(saida) is True
    assert probe.dimensao(saida) == (1080, 1920)


def test_a_legenda_aparece_no_quadro(tmp_path):
    from tests import fixtures
    filme = fixtures.clipe_fala(tmp_path / "h.mov", falas=[(0.3, 2.0)], total=4.0)
    palavras = [{"p": "teste", "t": 1.0, "f": 1.8}]
    saida = legenda.queimar(filme, legenda.blocos(palavras), "brutalista",
                            tmp_path / "leg2.mp4", mapa=[])
    crop = _crop_da_legenda(tmp_path, "teste")
    assert _quanto_mudou(saida, 1.4, 3.5, crop) > 20, "a legenda nao apareceu"


def test_bloco_sob_letreiro_e_omitido(tmp_path):
    from tests import fixtures
    filme = fixtures.clipe_fala(tmp_path / "i.mov", falas=[(0.3, 3.0)], total=4.0)
    palavras = [{"p": "escondido", "t": 1.0, "f": 1.8}]
    mapa = [{"n": 1, "ini": 0.0, "fim": 4.0, "letreiro": [0.0, 4.0]}]
    saida = legenda.queimar(filme, legenda.blocos(palavras), "brutalista",
                            tmp_path / "leg3.mp4", mapa=mapa)
    crop = _crop_da_legenda(tmp_path, "escondido")
    assert _quanto_mudou(saida, 1.4, 3.5, crop) < 6, (
        "a legenda apareceu mesmo sob o letreiro")
