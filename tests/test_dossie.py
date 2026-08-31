"""O dossie: o que o Bingo mede enquanto o Bandit ouve.

A propriedade que estes testes protegem e a que torna o paralelismo seguro:
NADA aqui depende de decisao. As mesmas contas, sobre os mesmos arquivos, dao o
mesmo resultado antes ou depois do Bandit escolher o que fica. No dia em que
alguem puser aqui uma etapa que corta ou acelera, o paralelismo passa a jogar
fora material que o roteiro ainda pode pedir.
"""
import json

from motor import dossie
from tests import fixtures


def test_a_ficha_traz_o_tempo_e_o_tamanho(tmp_path):
    g = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.3, 1.5)], total=3.0)
    f = dossie.de_um(g)
    assert abs(f["duracao"] - 3.0) < 0.15
    assert (f["largura"], f["altura"]) == (1080, 1920)
    assert f["em_pe"] is True
    assert f["tem_som"] is True


def test_a_ficha_diz_onde_a_fala_esta(tmp_path):
    """E o que permite ao Bluey dizer 'sua gravacao tem 3 minutos, 2 de fala'
    antes de qualquer corte."""
    g = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(1.0, 2.0)], total=5.0)
    f = dossie.de_um(g)
    assert 0.8 < f["fala_de"] < 1.2, f"a fala comeca em 1,0s, achou {f['fala_de']}"
    assert 2.9 < f["fala_ate"] < 3.5, f"a fala acaba em 3,0s, achou {f['fala_ate']}"
    assert 1.7 < f["fala_dura"] < 2.6


def test_a_ficha_conta_o_silencio_de_dentro_da_fala(tmp_path):
    """O numero que responde 'quanto o corte vai encurtar o video'."""
    g = fixtures.clipe_fala(tmp_path / "c.mov",
                            falas=[(0.3, 1.2), (3.5, 1.5)], total=6.0)
    f = dossie.de_um(g)
    assert f["pausas"], "nao achou a pausa de 2s no meio da fala"
    assert f["silencio_a_cortar"] > 1.0


def test_video_sem_som_nao_ganha_campo_de_fala(tmp_path):
    """Material complementar entra mudo. Procurar fala nele devolveria numero
    inventado."""
    m = fixtures.clipe_mudo(tmp_path / "m.mov", total=2.0)
    f = dossie.de_um(m)
    assert f["tem_som"] is False
    assert "fala_de" not in f


def test_a_ficha_avisa_de_gravacao_deitada(tmp_path):
    g = fixtures.clipe_fala(tmp_path / "d.mov", falas=[(0.2, 1.0)], total=2.0,
                            w=1920, h=1080)
    assert dossie.de_um(g)["em_pe"] is False


def test_a_ficha_avisa_de_pano_verde(tmp_path):
    com = fixtures.clipe_croma(tmp_path / "v.mov", falas=[(0.2, 1.0)])
    sem = fixtures.clipe_fala(tmp_path / "s.mov", falas=[(0.2, 1.0)], total=2.0)
    assert dossie.de_um(com)["pano_verde"] is True
    assert dossie.de_um(sem)["pano_verde"] is False


def test_o_dossie_grava_o_que_mediu(tmp_path):
    """O Bandit e o Bluey leem este arquivo. Se ele nao existir, os dois teriam
    de medir de novo, cada um por sua conta."""
    g = fixtures.clipe_fala(tmp_path / "e.mov", falas=[(0.3, 1.0)], total=2.0)
    destino = tmp_path / "dossie.json"
    dossie.de([g], destino)
    lido = json.loads(destino.read_text(encoding="utf-8"))
    assert len(lido) == 1 and lido[0]["arquivo"] == str(g)


def test_medir_duas_vezes_da_o_mesmo_resultado(tmp_path):
    """A propriedade que torna o paralelismo seguro. Se o dossie dependesse de
    alguma decisao, ou de alguma etapa que muda o arquivo, duas passadas
    discordariam -- e o Bingo estaria trabalhando sobre material que o Bandit
    ainda vai mudar."""
    g = fixtures.clipe_fala(tmp_path / "f.mov",
                            falas=[(0.3, 1.0), (2.5, 1.0)], total=4.0)
    assert dossie.de_um(g) == dossie.de_um(g)


def test_o_dossie_em_portugues_nao_usa_termo_tecnico(tmp_path):
    """O texto vai direto para a folha, que a pessoa le."""
    g = fixtures.clipe_fala(tmp_path / "g.mov", falas=[(0.3, 1.5)], total=3.0)
    texto = dossie.em_portugues(dossie.de([g])).lower()
    for termo in ("codec", "bitrate", "luma", "lufs", "crop", "pillarbox",
                  "envelope", "percentil", "rgb"):
        assert termo not in texto, f"o texto da folha usa '{termo}'"
    assert "segundos" in texto


def test_o_dossie_em_portugues_avisa_do_que_muda_o_video(tmp_path):
    deitado = fixtures.clipe_fala(tmp_path / "h.mov", falas=[(0.2, 1.0)],
                                  total=2.0, w=1920, h=1080)
    texto = dossie.em_portugues(dossie.de([deitado]))
    assert "deitado" in texto, (
        "a pessoa precisa saber que a gravacao vai ser cortada para caber em pe")


def test_arquivo_estragado_vira_aviso_e_nao_derruba_o_programa(tmp_path):
    """Achado rodando o caminho inteiro com material de verdade: um arquivo
    truncado fazia o ffprobe devolver a palavra 'N/A' onde deveria vir um
    numero, e o programa parava com erro em ingles e um monte de linha de
    codigo na tela. Quem usa esta skill nao tem o que fazer com isso."""
    ruim = tmp_path / "estragado.mp4"
    ruim.write_bytes(b"isto nao e um video")
    f = dossie.de_um(ruim)
    assert f["ilegivel"] is True
    assert "fala_de" not in f, "nao da para medir fala num arquivo que nao abre"

    texto = dossie.em_portugues([f]).lower()
    assert "nao deu para abrir" in texto
    assert "mande de novo" in texto, "o aviso nao diz o que a pessoa deve fazer"


def test_arquivo_bom_nao_e_marcado_como_estragado(tmp_path):
    g = fixtures.clipe_fala(tmp_path / "ok.mov", falas=[(0.3, 1.0)], total=2.0)
    assert dossie.de_um(g)["ilegivel"] is False
