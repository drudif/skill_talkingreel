"""A coordenada unica de tempo.

Cada teste aqui protege a conversao que decide ONDE o letreiro aparece. O modo
de falhar e silencioso: o filme renderiza, o texto entra, e entra na hora
errada. So se ve olhando.
"""
import pytest

from motor import config, tempo


def _mapa(**kw):
    base = dict(ini=0.0, fim=10.0, marcas=[(0.0, 10.0)], velocidade=1.0)
    base.update(kw)
    return tempo.Mapa(**base)


# --- as marcas: os pedacos que sobram depois de comprimir as pausas ---

def test_sem_pausa_a_cena_e_um_pedaco_so():
    assert tempo.marcas(2.0, 8.0, []) == [(0.0, 6.0)]


def test_a_pausa_vira_pausa_fica():
    """Uma pausa de 3,0s a 4,0s dentro de uma cena de 10s deixa PAUSA_FICA no
    lugar: o primeiro pedaco vai ate 3,0+PAUSA_FICA e o segundo comeca em 4,0."""
    m = tempo.marcas(0.0, 10.0, [(3.0, 4.0)])
    assert m == [(0.0, 3.0 + config.PAUSA_FICA), (4.0, 10.0)]


def test_pedaco_curto_demais_e_descartado():
    """Duas pausas quase coladas deixam um pedaco de 0,01s no meio. Ele nao
    vira arquivo -- o ffmpeg devolve um quadro so e o concat quebra."""
    m = tempo.marcas(0.0, 10.0, [(3.0, 4.0), (4.01, 5.0)])
    assert all(b - a >= tempo.PISO_PEDACO for a, b in m)
    assert (4.0, 4.01) not in m


def test_o_piso_do_pedaco_esta_provado_dos_dois_lados():
    """Se PISO_PEDACO subir demais come pedaco de fala legitimo; se descer
    demais deixa passar o pedaco que quebra o concat."""
    assert tempo.PISO_PEDACO < 0.10, (
        "piso acima de 0,10s descartaria a propria pausa que PAUSA_FICA deixa")
    assert tempo.PISO_PEDACO > 0.0, "piso zero deixa passar pedaco vazio"


# --- a conversao, no caminho de ida ---

def test_sem_pausa_e_sem_velocidade_a_conta_e_a_subtracao():
    m = _mapa(ini=2.0, fim=8.0, marcas=[(0.0, 6.0)])
    assert m.na_cena(5.0) == pytest.approx(3.0)


def test_a_velocidade_divide():
    m = _mapa(ini=0.0, fim=10.0, marcas=[(0.0, 10.0)], velocidade=2.0)
    assert m.na_cena(6.0) == pytest.approx(3.0)


def test_depois_da_pausa_o_instante_anda_para_tras():
    """O caso que motivou o modulo. Pausa de 3,0 a 4,0 comprimida para 0,10:
    quem falou em 6,0s da gravacao aparece em 5,1s da cena, nao em 6,0s."""
    m = _mapa(marcas=tempo.marcas(0.0, 10.0, [(3.0, 4.0)]))
    assert m.na_cena(6.0) == pytest.approx(3.0 + config.PAUSA_FICA + 2.0)


def test_o_erro_do_jeito_antigo_cresce_ao_longo_da_cena():
    """Somar o instante cru ao inicio da cena -- o jeito antigo -- erra pouco
    no comeco e muito no fim. E o que este modulo existe para impedir."""
    m = _mapa(marcas=tempo.marcas(0.0, 12.0, [(2.0, 3.0), (6.0, 7.5)]))
    erro_cedo = abs(1.0 - m.na_cena(1.0))
    erro_tarde = abs(11.0 - m.na_cena(11.0))
    assert erro_cedo < 0.01, "antes da primeira pausa nao ha erro nenhum"
    assert erro_tarde > 2.0, (
        f"depois de duas pausas o erro deveria passar de 2s, deu {erro_tarde:.2f}s")


def test_offset_poe_a_cena_no_lugar_do_filme():
    m = _mapa(ini=0.0, fim=5.0, marcas=[(0.0, 5.0)], offset=20.0)
    assert m.no_filme(2.0) == pytest.approx(22.0)


# --- os casos de borda ---

def test_instante_antes_da_fala_cai_no_comeco():
    m = _mapa(ini=3.0, fim=9.0, marcas=[(0.0, 6.0)])
    assert m.na_cena(1.0) == pytest.approx(0.0)


def test_instante_depois_da_fala_cai_no_fim():
    m = _mapa(ini=0.0, fim=6.0, marcas=[(0.0, 6.0)])
    assert m.na_cena(99.0) == pytest.approx(6.0)


def test_instante_dentro_da_pausa_cortada_cai_onde_a_pausa_estava():
    """Nao existe lugar certo para um instante que foi removido do filme. A
    escolha e a borda de entrada da pausa, que e onde a fala parou."""
    m = _mapa(marcas=tempo.marcas(0.0, 10.0, [(3.0, 4.0)]))
    dentro = m.na_cena(3.5)
    assert dentro == pytest.approx(3.0 + config.PAUSA_FICA, abs=0.11)


# --- o caminho de volta ---

def test_ida_e_volta_bate_dentro_de_um_pedaco():
    m = _mapa(marcas=tempo.marcas(0.0, 12.0, [(2.0, 3.0), (6.0, 7.5)]),
              velocidade=1.15)
    for s in (0.5, 1.9, 4.0, 5.5, 8.0, 11.0):
        assert m.no_original(m.na_cena(s)) == pytest.approx(s, abs=0.01), (
            f"ida e volta nao fechou em {s}s")


def test_a_volta_de_um_instante_negativo_cai_no_inicio():
    m = _mapa(ini=4.0, fim=10.0, marcas=[(0.0, 6.0)])
    assert m.no_original(-1.0) == pytest.approx(4.0)


# --- o ajuste pela duracao medida ---

def test_sem_duracao_medida_nao_ha_ajuste():
    m = _mapa(dur=None)
    assert m.ajuste == 1.0


def test_a_duracao_medida_estica_a_conversao():
    """O segmento saiu 2% mais longo do que a conta previa. O instante do fim
    da cena tem de acompanhar, senao o letreiro do fim entra adiantado."""
    m = _mapa(marcas=[(0.0, 10.0)], velocidade=1.0, dur=10.2)
    assert m.ajuste == pytest.approx(1.02)
    assert m.na_cena(10.0) == pytest.approx(10.2)


def test_duracao_teorica_desconta_pausa_e_velocidade():
    m = _mapa(marcas=tempo.marcas(0.0, 10.0, [(3.0, 4.0)]), velocidade=2.0)
    assert m.dur_teorica == pytest.approx((10.0 - 0.9) / 2.0)


# --- o registro, para converter depois sem remontar ---

def test_o_registro_reconstroi_o_mesmo_mapa():
    m = _mapa(ini=1.0, fim=11.0,
              marcas=tempo.marcas(1.0, 11.0, [(3.0, 4.2)]), velocidade=1.15,
              offset=7.0, dur=8.5)
    reg = m.como_registro()
    reg.update({"ini": 7.0, "fim": 15.5})     # como montar.py grava: tempo do FILME
    volta = tempo.de_registro(reg)
    for s in (1.5, 3.0, 6.0, 10.0):
        assert volta.no_filme(s) == pytest.approx(m.no_filme(s), abs=0.01)


# --- os dois pares de ida e volta, que e facil trocar ---

def test_no_filme_e_do_filme_sao_o_par_certo():
    """`no_original` e o inverso de `na_cena`; `do_filme`, o de `no_filme`.
    Trocar um pelo outro nao levanta erro nenhum -- a conta continua valida, so
    nao e a que se queria. Aconteceu numa conferencia com filme de verdade: a
    volta devolveu 26,0s onde o certo era 20,0s, e o numero parecia plausivel."""
    m = _mapa(ini=16.0, fim=26.0,
              marcas=tempo.marcas(16.0, 26.0, [(2.0, 3.4), (6.0, 7.1)]),
              velocidade=1.15, offset=5.8, dur=4.7)
    for s in (16.5, 20.0, 23.5, 25.5):
        assert m.do_filme(m.no_filme(s)) == pytest.approx(s, abs=0.02), (
            f"do_filme nao desfez no_filme em {s}s")
        assert m.no_original(m.na_cena(s)) == pytest.approx(s, abs=0.02), (
            f"no_original nao desfez na_cena em {s}s")


def test_trocar_o_par_da_numero_errado_e_nao_avisa():
    """O teste que registra a armadilha. Se um dia os dois passarem a dar o
    mesmo resultado, ou este teste esta errado ou o offset sumiu."""
    m = _mapa(ini=16.0, fim=26.0, marcas=[(0.0, 10.0)], velocidade=1.0,
              offset=5.8, dur=10.0)
    certo = m.do_filme(m.no_filme(20.0))
    errado = m.no_original(m.no_filme(20.0))
    assert certo == pytest.approx(20.0, abs=0.02)
    assert abs(errado - 20.0) > 1.0, (
        "trocar o par deixou de dar numero errado -- confira se o offset "
        "ainda esta sendo aplicado")
