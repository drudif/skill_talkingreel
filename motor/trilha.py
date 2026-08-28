"""Musica por baixo da voz.

A ORDEM IMPORTA: comprimir a MUSICA tendo a VOZ como chave, e so depois
misturar. Inverter as entradas do sidechaincompress comprime a voz usando a
musica como chave — o contrario do que se quer, e o erro passa despercebido
porque o arquivo sai sem erro."""
import subprocess

from motor import config, probe


def aplicar(filme, musica, destino, volume=None):
    volume = config.VOL_TRILHA if volume is None else volume
    total = probe.dur(filme)
    r = subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(filme),
        "-stream_loop", "-1", "-i", str(musica),
        "-filter_complex",
        f"[1:a]volume={volume},atrim=0:{total:.3f},asetpts=PTS-STARTPTS[m];"
        # a voz e a chave; quem abaixa e a musica
        f"[m][0:a]sidechaincompress=threshold=0.06:ratio=6:attack=20:release=350[duck];"
        f"[0:a][duck]amix=inputs=2:duration=first:normalize=0,"
        f"alimiter=limit={10 ** (config.TETO_DB / 20):.4f}[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "pcm_s16le", "-ar", str(config.SR), "-ac", "2",
        "-t", f"{total:.3f}", str(destino)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg falhou na trilha: " + r.stderr.strip()[:500])
    return destino
