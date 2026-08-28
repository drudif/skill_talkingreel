"""Cobre o codigo de saida da linha de comando (motor/__main__.py). Os agentes
que rodam este motor decidem se precisam refazer o trabalho pelo codigo de
saida -- se ele voltar 0 mesmo com o laudo reprovado, ninguem refaz nada."""
import subprocess

from motor import __main__ as cli
from motor import montar


def _filme_dessincronizado(destino, dur_video=3, dur_audio=5):
    """Muxa um video de dur_video segundos com um audio de dur_audio segundos,
    sem -shortest, para que os dois fluxos fiquem com duracao diferente --
    o mesmo helper de tests/test_laudo.py."""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-t", str(dur_video), "-i", "color=c=gray:s=1080x1920:r=30",
        "-f", "lavfi", "-t", str(dur_audio), "-i", "sine=frequency=220:sample_rate=48000",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000",
        str(destino)], check=True, capture_output=True)
    return destino


def test_cli_retorna_codigo_diferente_de_zero_quando_o_laudo_reprova(tmp_path, monkeypatch, capsys):
    """Constroi um filme de verdade com video e audio de duracoes bem
    diferentes (o caso mais facil de reprovar: laudo.rodar mede isso
    diretamente, sem precisar montar um arquivo de cenas valido) e substitui
    motor.montar.montar por uma funcao que devolve esse filme quebrado --
    assim o main() real (inclusive o laudo.rodar real, sobre o arquivo
    quebrado de verdade) roda por inteiro, sem precisar da cadeia completa
    de montagem so para testar o branch do codigo de saida."""
    quebrado = _filme_dessincronizado(tmp_path / "quebrado.mp4")
    monkeypatch.setattr(montar, "montar", lambda *a, **k: quebrado)

    cenas_json = tmp_path / "cenas.json"
    cenas_json.write_text("{}", encoding="utf-8")

    codigo = cli.main(["motor", str(cenas_json), str(tmp_path / "saida.mp4")])
    saida = capsys.readouterr().out

    assert codigo != 0, "o filme esta quebrado (video e audio com duracoes bem diferentes) mas o codigo de saida veio 0"
    assert "diferentes" in saida, f"o problema nao apareceu impresso: {saida!r}"
