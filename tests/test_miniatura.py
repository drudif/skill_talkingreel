import base64
import subprocess
from pathlib import Path

from motor import miniatura
from tests import fixtures


def _clipe_imagem_variavel(destino, total=3.0, w=320, h=240):
    """Um clipe cujo QUADRO muda ao longo do tempo -- diferente de
    `fixtures.clipe_fala`, que usa `color=c=gray` (cor solida) e so varia o
    audio. Medido: dois quadros extraidos de um `clipe_fala` em instantes
    diferentes saem byte a byte identicos (675 bytes, iguais), porque a
    imagem nunca muda. O teste abaixo precisa de dois quadros DIFERENTES
    para fazer sentido, entao usa `testsrc` (padrao de teste do ffmpeg, que
    se move) so aqui, sem tocar em `tests/fixtures.py` -- esse arquivo e
    usado por quase todo o resto da suite, inclusive por testes fora deste
    escopo de trabalho."""
    destino = Path(destino)
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", f"{total}",
         "-i", f"testsrc=s={w}x{h}:r=30", "-c:v", "libx264", "-crf", "28",
         "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-an", str(destino)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:400])
    return destino


def test_devolve_um_data_uri_de_jpeg(tmp_path):
    filme = fixtures.clipe_fala(tmp_path / "f.mov", falas=[(0.3, 2.0)], total=3.0)
    uri = miniatura.de(filme, 1.0)
    assert uri.startswith("data:image/jpeg;base64,")
    bruto = base64.b64decode(uri.split(",", 1)[1])
    assert bruto[:2] == b"\xff\xd8", "nao e um JPEG"


def test_cabe_no_teto_de_tamanho(tmp_path):
    filme = fixtures.clipe_fala(tmp_path / "f.mov", falas=[(0.3, 2.0)], total=3.0)
    uri = miniatura.de(filme, 1.0)
    assert len(uri) <= miniatura.TETO_BYTES, (
        f"a miniatura ficou com {len(uri)} bytes, teto {miniatura.TETO_BYTES}")


def test_largura_pedida_e_respeitada(tmp_path):
    import io
    from PIL import Image
    filme = fixtures.clipe_fala(tmp_path / "f.mov", falas=[(0.3, 2.0)], total=3.0)
    uri = miniatura.de(filme, 1.0, largura=120)
    im = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1])))
    assert im.width == 120


def test_instante_fora_do_filme_devolve_nada(tmp_path):
    filme = fixtures.clipe_fala(tmp_path / "f.mov", falas=[(0.3, 2.0)], total=3.0)
    assert miniatura.de(filme, 99.0) is None


def test_arquivo_que_nao_existe_devolve_nada(tmp_path):
    assert miniatura.de(tmp_path / "nada.mov", 1.0) is None


def test_dois_instantes_diferentes_dao_miniaturas_diferentes(tmp_path):
    # fixtures.clipe_fala nao serve aqui: o video e cor solida (so o audio
    # varia com `falas`), entao dois instantes dariam o mesmo quadro sempre.
    # Ver _clipe_imagem_variavel acima.
    filme = _clipe_imagem_variavel(tmp_path / "f.mp4", total=3.0)
    assert miniatura.de(filme, 0.5) != miniatura.de(filme, 2.5)
