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


def test_area_util_funciona_em_arquivo_com_menos_de_1s(tmp_path):
    """FIX 2a: o ponto de amostra do cropdetect era fixo em -ss 1. Num arquivo
    com menos de 1s (cena com pouca fala, depois de aperta() cortar as
    pontas) o -ss pulava direto para o fim, cropdetect nao lia nada e a
    funcao devolvia None -- lido por quem chama como 'ja esta vertical, nao
    mexe'. Mesma gravacao pillarbox do teste acima, so que cortada para
    0.9s."""
    vertical = fixtures.clipe_mudo(tmp_path / "vertical_curto.mp4", total=0.9,
                                   w=608, h=1080, cor="teal")
    pillarbox = tmp_path / "pillarbox_curto.mp4"
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(vertical),
         "-vf", "scale=608:1080,pad=1920:1080:(ow-iw)/2:0:black",
         "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         "-an", str(pillarbox)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert abs(probe.dur(pillarbox) - 0.9) < 0.2

    crop = probe.area_util(pillarbox)
    assert crop is not None, (
        "esperava um crop mesmo com o arquivo tendo menos de 1s, veio None "
        "(o -ss fixo em 1s pulou o arquivo inteiro)")

    numeros = [int(x) for x in crop.replace("crop=", "").rstrip(",").split(":")]
    cw, ch = numeros[0], numeros[1]
    assert abs(cw - 608) <= 10
    assert abs(ch - 1080) <= 10


def test_duracao_de_arquivo_que_nao_e_video_e_zero(tmp_path):
    """O ffprobe devolve a palavra 'N/A', nao um erro. Sem tratar, isso vira
    uma parada do programa com mensagem em ingles no meio do trabalho da
    pessoa. Achado rodando o caminho inteiro, nao em teste de unidade."""
    ruim = tmp_path / "nao-e-video.mp4"
    ruim.write_bytes(b"nada disso e video")
    assert probe.dur(ruim) == 0.0


def test_area_util_de_arquivo_que_nao_abre_nao_quebra(tmp_path):
    """Quem chama le None como 'ja esta vertical, nao mexe' -- que e a resposta
    segura para um arquivo que nao da para ler."""
    ruim = tmp_path / "vazio.mp4"
    ruim.write_bytes(b"")
    assert probe.area_util(ruim) is None
