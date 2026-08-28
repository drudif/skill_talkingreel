"""Prova de ponta a ponta: roda o motor pela linha de comando, do jeito que um
agente ou uma pessoa vai rodar de verdade. Os testes aqui montam filme de
verdade com ffmpeg -- sao lentos de proposito, porque so assim pegam erro que
so aparece na cadeia inteira (corte de pausa + split + juncao + trilha)."""
import json
import subprocess
import sys

from motor import laudo, probe
from tests import fixtures

JARGAO = ("ffmpeg", "stream", "codec", "mux", "LUFS", "dB", "PTS", "crop",
          "overlay", "encode", "bitrate")


def _tom_audio(destino, freq, total):
    """Arquivo so de audio (sem video), tom continuo -- serve de trilha
    sonora sintetica. Frequencia diferente da fala (220 Hz, fixtures.py) para
    dar pra separar as duas por filtro depois."""
    r = subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-t", f"{total}", "-i", f"sine=frequency={freq}:sample_rate=48000",
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(destino)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:500])
    return destino


def _medir_banda(caminho, freq, ss, dur):
    """mean_volume (dB) numa banda estreita em torno de freq, num trecho do
    arquivo -- mesmo metodo de tests/test_trilha.py para isolar um tom de
    outro na mixagem final."""
    import re
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", str(ss), "-t", str(dur), "-i", str(caminho),
         "-af", f"bandpass=f={freq}:width_type=h:w=200,volumedetect",
         "-f", "null", "-"],
        capture_output=True, text=True)
    achado = re.search(r"mean_volume:\s*(-?\d+\.?\d*)\s*dB", r.stderr)
    return float(achado.group(1)) if achado else -99.0


def test_um_filme_com_tela_cheia_e_split(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    (tmp_path / "broll").mkdir(parents=True, exist_ok=True)
    for i in (1, 2, 3):
        fixtures.clipe_fala(tmp_path / "gravacoes" / f"take-{i:02d}.mov",
                            falas=[(0.4, 1.0), (2.0, 0.8)], total=3.5)
    fixtures.clipe_mudo(tmp_path / "broll" / "deitado.mp4", total=4.0, w=1920, h=1080)
    fixtures.clipe_mudo(tmp_path / "broll" / "vertical.mp4", total=4.0, w=1080, h=1920)

    (tmp_path / "cenas.json").write_text(json.dumps({
        "velocidade": 1.15, "legenda": False,
        "cenas": [
            {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"},
            {"n": 2, "trat": "split", "arquivo": "gravacoes/take-02.mov",
             "topo": {"arquivo": "broll/deitado.mp4"}},
            {"n": 3, "trat": "split", "arquivo": "gravacoes/take-03.mov",
             "topo": {"arquivo": "broll/vertical.mp4", "ancora": 0.0},
             "velocidade": 1.0},
        ]}), encoding="utf-8")

    saida = tmp_path / "filme.mp4"
    r = subprocess.run([sys.executable, "-m", "motor",
                        str(tmp_path / "cenas.json"), str(saida)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    assert probe.dimensao(saida) == (1080, 1920)
    resultado = laudo.rodar(saida, tmp_path / "cenas.json")
    assert resultado["ok"] is True, resultado["problemas"]
    assert resultado["cenas"] == 3

    # X: quem le a saida da linha de comando nao entende de montagem de video.
    for termo in JARGAO:
        assert termo not in r.stdout, f"'{termo}' vazou no stdout: {r.stdout!r}"


def test_erro_no_arquivo_de_cenas_explica_o_que_corrigir(tmp_path):
    (tmp_path / "cenas.json").write_text(json.dumps({
        "cenas": [{"n": 1, "trat": "split", "arquivo": "some.mov"}]}),
        encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "motor",
                        str(tmp_path / "cenas.json"), str(tmp_path / "f.mp4")],
                       capture_output=True, text=True)
    assert r.returncode == 1
    assert "topo" in r.stdout + r.stderr


# --- U: a trilha sonora sobrevive a cadeia inteira, via linha de comando ---

def test_trilha_sobrevive_a_cadeia_completa(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    for i in (1, 2):
        fixtures.clipe_fala(tmp_path / "gravacoes" / f"take-{i:02d}.mov",
                            falas=[(0.4, 1.0), (2.0, 0.8)], total=3.5)
    _tom_audio(tmp_path / "trilha.wav", freq=880, total=10.0)

    (tmp_path / "cenas.json").write_text(json.dumps({
        "velocidade": 1.15, "legenda": False,
        "trilha": "trilha.wav",
        "cenas": [
            {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"},
            {"n": 2, "trat": "cheia", "arquivo": "gravacoes/take-02.mov"},
        ]}), encoding="utf-8")

    saida = tmp_path / "filme.mp4"
    r = subprocess.run([sys.executable, "-m", "motor",
                        str(tmp_path / "cenas.json"), str(saida)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    assert probe.tem_audio(saida) is True
    resultado = laudo.rodar(saida, tmp_path / "cenas.json")
    assert resultado["ok"] is True, resultado["problemas"]

    # nao basta ter audio -- o take sozinho ja tem. Confere que o tom de
    # 880 Hz da trilha (fala e sempre 220 Hz, fixtures.py) esta de fato
    # misturado no filme final, em vez da trilha ter sido silenciosamente
    # ignorada pela cadeia.
    dur = probe.dur(saida)
    nivel_trilha = _medir_banda(saida, freq=880, ss=0, dur=dur)
    assert nivel_trilha > -80, (
        f"nao achei o tom de 880 Hz da trilha no filme final (nivel medido: "
        f"{nivel_trilha:.1f} dB) -- a trilha parece ter sido ignorada")


# --- V: arquivo de gravacao inexistente e relatado com clareza -------------

def test_arquivo_de_gravacao_inexistente_e_relatado_com_clareza(tmp_path):
    (tmp_path / "cenas.json").write_text(json.dumps({
        "cenas": [{"n": 1, "trat": "cheia",
                   "arquivo": "gravacoes/nao-existe.mov"}]}),
        encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "motor",
                        str(tmp_path / "cenas.json"), str(tmp_path / "f.mp4")],
                       capture_output=True, text=True)
    assert r.returncode == 1
    saida = r.stdout + r.stderr
    assert "nao-existe.mov" in saida, f"a mensagem nao nomeia o arquivo que falta: {saida!r}"


# --- W: numero errado de argumentos mostra o uso e sai com codigo 2 --------

def test_numero_errado_de_argumentos_mostra_o_uso():
    r = subprocess.run([sys.executable, "-m", "motor"],
                       capture_output=True, text=True)
    assert r.returncode == 2
    saida = r.stdout + r.stderr
    assert "Uso" in saida or "uso" in saida
    assert "motor" in saida
