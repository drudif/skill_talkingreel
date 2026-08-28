import math
import struct
import subprocess

from tests import fixtures


def _dur(caminho):
    saida = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(caminho)],
        capture_output=True, text=True).stdout.strip()
    return float(saida)


def test_clipe_de_fala_tem_a_duracao_pedida(tmp_path):
    c = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.5, 1.0), (2.0, 1.0)], total=3.5)
    assert abs(_dur(c) - 3.5) < 0.05


def test_clipe_de_fala_e_vertical(tmp_path):
    c = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.2, 0.5)], total=1.5)
    w, h = fixtures.dimensao(c)
    assert (w, h) == (1080, 1920)


def test_clipe_deitado_para_material_complementar(tmp_path):
    c = fixtures.clipe_mudo(tmp_path / "c.mp4", total=2.0, w=1920, h=1080)
    assert fixtures.dimensao(c) == (1920, 1080)


def _energia_por_janela(caminho, sr=8000, janela_s=0.01):
    """Decodifica o audio para mono em `sr` Hz e devolve a energia RMS de cada
    janela de `janela_s` segundos, como lista de (tempo_inicial, rms)."""
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(caminho),
         "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
        capture_output=True)
    n_amostras = len(r.stdout) // 4
    amostras = struct.unpack(f"<{n_amostras}f", r.stdout[:n_amostras * 4])
    tam_janela = int(janela_s * sr)
    janelas = []
    for i in range(0, len(amostras) - tam_janela, tam_janela):
        bloco = amostras[i:i + tam_janela]
        rms = math.sqrt(sum(x * x for x in bloco) / len(bloco))
        janelas.append((i / sr, rms))
    return janelas


def test_o_tom_soa_exatamente_no_intervalo_pedido(tmp_path):
    """Prova que o volume='between(t,...)' com eval=frame de fato liga e
    desliga o tom nos instantes pedidos, e nao em outro lugar. Se isso
    falhar, todo teste futuro que confia num timestamp de fala silenciosamente
    nao testa nada."""
    c = fixtures.clipe_fala(tmp_path / "d.mov", falas=[(1.0, 1.0)], total=3.0)
    janelas = _energia_por_janela(c)

    rms_max = max(rms for _, rms in janelas)
    limiar = rms_max * 0.3
    altas = [t for t, rms in janelas if rms > limiar]

    assert altas, "nenhuma janela ficou acima do limiar de energia"
    assert abs(min(altas) - 1.0) < 0.1
    assert abs(max(altas) - 2.0) < 0.1

    # antes de 0.9s e depois de 2.1s tem que estar essencialmente mudo
    antes = [rms for t, rms in janelas if t < 0.9]
    depois = [rms for t, rms in janelas if t > 2.1]
    assert max(antes) < limiar
    assert max(depois) < limiar
