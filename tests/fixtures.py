"""Clipes sinteticos para teste. Um tom de 220 Hz marca onde ha fala; o resto e
silencio digital. Assim o valor esperado de cada teste e conhecido, e nenhum
video pessoal entra no repositorio."""
import subprocess
from pathlib import Path

W, H, FPS, SR = 1080, 1920, 30, 48000


def _roda(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:400])


def dimensao(caminho):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(caminho)],
        capture_output=True, text=True)
    nums = [int(x) for x in r.stdout.strip().split(",") if x.strip()]
    return nums[0], nums[1]


def clipe_fala(destino, falas, total, w=W, h=H, ruido_dB=None):
    """falas: lista de (inicio, duracao) em segundos, onde ha tom audivel.

    `ruido_dB` poe um piso de ruido debaixo de tudo, como numa gravacao de
    verdade. SEM ele o silencio e zero DIGITAL, e isso mente para qualquer
    teste que meca nivel: o piso vira -120 dB e a distancia entre fala e
    silencio fica em 120 dB, distancia que nao existe em gravacao nenhuma.
    Uma sala silenciosa fica por volta de -50 dB abaixo da fala."""
    destino = Path(destino)
    volume = "+".join(
        f"between(t,{ini},{ini + dur})" for ini, dur in falas) or "0"
    if ruido_dB is None:
        cadeia = f"[1:a]volume='{volume}':eval=frame[a]"
        entradas = []
    else:
        ganho = 10 ** (ruido_dB / 20)
        cadeia = (f"[1:a]volume='{volume}':eval=frame[s];"
                  f"[2:a]volume={ganho:.6f}[r];"
                  f"[s][r]amix=inputs=2:duration=first:normalize=0[a]")
        entradas = ["-f", "lavfi", "-t", f"{total}",
                    "-i", f"anoisesrc=color=pink:sample_rate={SR}:seed=7"]
    _roda([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-t", f"{total}", "-i", f"color=c=gray:s={w}x{h}:r={FPS}",
        "-f", "lavfi", "-t", f"{total}", "-i", f"sine=frequency=220:sample_rate={SR}",
        *entradas,
        "-filter_complex", cadeia,
        "-map", "0:v", "-map", "[a]",
        "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "pcm_s16le", "-ar", str(SR), "-ac", "2",
        str(destino)])
    return destino


def clipe_mudo(destino, total, w=W, h=H, cor="teal"):
    destino = Path(destino)
    _roda([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-t", f"{total}", "-i", f"testsrc=s={w}x{h}:r={FPS}",
        "-vf", f"drawbox=c={cor}@0.3:t=fill",
        "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-an", str(destino)])
    return destino
