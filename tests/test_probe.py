import subprocess

from motor import probe
from tests import fixtures


def test_duracao(tmp_path):
    c = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.5, 1.0)], total=3.0)
    assert abs(probe.dur(c) - 3.0) < 0.05


def test_dimensao(tmp_path):
    c = fixtures.clipe_mudo(tmp_path / "b.mp4", total=1.0, w=1920, h=1080)
    assert probe.dimensao(c) == (1920, 1080)


def test_vertical_nao_tem_area_util_para_cortar(tmp_path):
    c = fixtures.clipe_mudo(tmp_path / "c.mp4", total=1.0, w=1080, h=1920)
    assert probe.area_util(c) is None


def test_tem_audio(tmp_path):
    com = fixtures.clipe_fala(tmp_path / "d.mov", falas=[(0.2, 0.5)], total=1.5)
    sem = fixtures.clipe_mudo(tmp_path / "e.mp4", total=1.5)
    assert probe.tem_audio(com) is True
    assert probe.tem_audio(sem) is False


def test_area_util_encontra_o_crop_de_gravacao_pillarbox(tmp_path):
    """Simula uma gravacao exportada de app de edicao: 1920x1080 deitado, com o
    conteudo vertical (608x1080) centralizado e barra preta dos dois lados.
    area_util tem que achar e devolver o crop dessa area, e nao None."""
    vertical = fixtures.clipe_mudo(tmp_path / "vertical.mp4", total=2.5, w=608, h=1080, cor="teal")
    pillarbox = tmp_path / "pillarbox.mp4"
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(vertical),
         "-vf", "scale=608:1080,pad=1920:1080:(ow-iw)/2:0:black",
         "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         "-an", str(pillarbox)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    crop = probe.area_util(pillarbox)
    assert crop is not None, "esperava um crop para gravacao pillarbox, veio None"

    numeros = [int(x) for x in crop.replace("crop=", "").rstrip(",").split(":")]
    cw, ch = numeros[0], numeros[1]
    assert abs(cw - 608) <= 10
    assert abs(ch - 1080) <= 10
