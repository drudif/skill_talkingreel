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


def clipe_fala(destino, falas, total, w=W, h=H):
    """falas: lista de (inicio, duracao) em segundos, onde ha tom audivel."""
    destino = Path(destino)
    volume = "+".join(
        f"between(t,{ini},{ini + dur})" for ini, dur in falas) or "0"
    _roda([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-t", f"{total}", "-i", f"color=c=gray:s={w}x{h}:r={FPS}",
        "-f", "lavfi", "-t", f"{total}", "-i", f"sine=frequency=220:sample_rate={SR}",
        "-filter_complex", f"[1:a]volume='{volume}':eval=frame[a]",
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
