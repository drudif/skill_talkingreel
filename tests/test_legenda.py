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
