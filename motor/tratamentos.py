"""Produz o segmento de uma cena. E o unico modulo, junto com montar.py, que
chama ffmpeg para gerar video.

REGRAS QUE NAO PODEM SER QUEBRADAS:
  1. `-ss` vai ANTES do `-i`. Depois do `-i` ele vira opcao de saida e o corte
     escorrega para o arquivo seguinte. Custou meia hora de dessync.
  2. Audio dos segmentos em pcm_s16le. Comprimir aqui e comprimir de novo no
     final acumula atraso a cada emenda.
  3. -ar 48000 em toda etapa.
  4. Todo segmento sai EXATAMENTE 1080x1920. Alguma etapa devolve 1918 e o
     concat quebra.
"""
import subprocess

from motor import config, fala, probe

_SHARP = "unsharp=5:5:0.7:5:5:0,eq=contrast=1.08:saturation=1.04"


def _roda(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg falhou: " + r.stderr.strip()[:500])


def _saida_padrao(destino):
    return ["-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-c:a", "pcm_s16le", "-ar", str(config.SR), "-ac", "2", str(destino)]


def _velocidade(vel):
    """Filtros de video e audio para mudar a velocidade sem mudar o tom."""
    if abs(vel - 1.0) < 0.001:
        return "", []
    return f",setpts=PTS/{vel}", ["-af", f"atempo={vel}"]


def enquadrar(caminho):
    """Preenche 1080x1920 cortando o excesso, nunca deformando."""
    pb = probe.area_util(caminho) or ""
    return (f"{pb}scale={config.W}:{config.H}"
            f":force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={config.W}:{config.H},{_SHARP},setsar=1")


def tela_cheia(cena, destino):
    ini, fim = fala.bordas_com_teto(cena.arquivo, cena.teto)
    vf_vel, _ = _velocidade(cena.velocidade)
    muda_vel = abs(cena.velocidade - 1.0) > 0.001
    af = ["-af", (f"atempo={cena.velocidade}," if muda_vel else "")
          + f"loudnorm=I={config.LUFS}:TP={config.TETO_DB}"]
    _roda(["ffmpeg", "-y", "-v", "error",
           "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(cena.arquivo),
           "-vf", f"{enquadrar(cena.arquivo)}{vf_vel},fps={config.FPS},format=yuv420p",
           *af] + _saida_padrao(destino))
    return destino
