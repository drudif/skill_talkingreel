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


def _com_rotacao(origem, destino, graus):
    """Copia o arquivo marcando a rotacao, sem girar os pixels -- que e como o
    celular grava.

    `-display_rotation` vai ANTES do `-i`: e opcao de entrada, e o que ela faz e
    dizer como aquela entrada deve ser exibida. O jeito antigo
    (`-metadata:s:v:0 rotate=`) e ignorado em silencio por este ffmpeg, e o
    teste passava a pular sozinho sem exercitar nada."""
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-display_rotation", str(graus),
         "-i", str(origem), "-c", "copy", str(destino)], check=True)
    return destino


def test_a_dimensao_respeita_a_rotacao_do_arquivo(tmp_path):
    """Achado com um video de iPhone de verdade: gravado em pe, guardado
    deitado (3840x2160) com uma marca de -90 grau. O ffprobe devolve o tamanho
    GUARDADO; os filtros do ffmpeg trabalham com o girado.

    Quem usa o numero guardado erra a conta do encaixe do material complementar
    e o video sai com o enquadramento errado, sem nada acusar."""
    deitado = fixtures.clipe_fala(tmp_path / "d.mov", falas=[(0.2, 0.8)],
                                  total=1.5, w=640, h=360)
    assert probe.dimensao(deitado) == (640, 360)

    girado = _com_rotacao(deitado, tmp_path / "g.mov", 90)
    if probe.rotacao(girado) == 0:
        import pytest
        pytest.skip("este ffmpeg nao gravou a marca de rotacao no arquivo")
    assert probe.dimensao(girado) == (360, 640), (
        "a dimensao ignorou a marca de rotacao: um video gravado em pe seria "
        "tratado como deitado")


def test_sem_marca_de_rotacao_nada_muda(tmp_path):
    c = fixtures.clipe_fala(tmp_path / "n.mov", falas=[(0.2, 0.8)], total=1.5,
                            w=640, h=360)
    assert probe.rotacao(c) == 0
    assert probe.dimensao(c) == (640, 360)


def test_area_util_nao_cropa_video_que_a_rotacao_ja_poe_em_pe(tmp_path):
    """O crop existe para tirar a barra preta dos lados de um video deitado.
    Num video que so PARECE deitado, por causa da marca de rotacao, ele
    recortaria a imagem inteira a toa."""
    deitado = fixtures.clipe_fala(tmp_path / "r.mov", falas=[(0.2, 0.8)],
                                  total=1.5, w=640, h=360)
    girado = _com_rotacao(deitado, tmp_path / "rg.mov", 90)
    if probe.rotacao(girado) == 0:
        import pytest
        pytest.skip("este ffmpeg nao gravou a marca de rotacao no arquivo")
    assert probe.area_util(girado) is None
