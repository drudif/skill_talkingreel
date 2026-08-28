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
    """Filtro de video para mudar a velocidade sem mudar o tom. O filtro de
    audio equivalente (atempo) e montado por quem chama, junto do loudnorm."""
    if abs(vel - 1.0) < 0.001:
        return ""
    return f",setpts=PTS/{vel}"


def enquadrar(caminho):
    """Preenche 1080x1920 cortando o excesso, nunca deformando."""
    pb = probe.area_util(caminho) or ""
    return (f"{pb}scale={config.W}:{config.H}"
            f":force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={config.W}:{config.H},{_SHARP},setsar=1")


def tela_cheia(cena, destino):
    ini, fim = fala.bordas_com_teto(cena.arquivo, cena.teto)
    vf_vel = _velocidade(cena.velocidade)
    muda_vel = abs(cena.velocidade - 1.0) > 0.001
    af = ["-af", (f"atempo={cena.velocidade}," if muda_vel else "")
          + f"loudnorm=I={config.LUFS}:TP={config.TETO_DB}"]
    _roda(["ffmpeg", "-y", "-v", "error",
           "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(cena.arquivo),
           "-vf", f"{enquadrar(cena.arquivo)}{vf_vel},fps={config.FPS},format=yuv420p",
           *af] + _saida_padrao(destino))
    return destino


def recorte_topo(largura, altura, ancora):
    """Filtro que encaixa um material de `largura`x`altura` na janela de cima do
    split (1080x807), cortando o que sobra.

    A janela e deitada. Material vertical perde altura: 9:16 sobra 42%, 1:1
    sobra 75%. Por isso a ancora existe -- cortar pelo centro decepa cabeca.
    ancora 0.0 = topo, 0.5 = centro, 1.0 = base. Na largura o corte e sempre
    centralizado, porque ali sobra pouco."""
    jan_w, jan_h = config.W, config.DIVISORIA
    escala = max(jan_w / largura, jan_h / altura)
    esc_w, esc_h = round(largura * escala), round(altura * escala)
    y = int(round((esc_h - jan_h) * ancora))
    x = int(round((esc_w - jan_w) / 2))
    return (f"scale={esc_w}:{esc_h}:flags=lanczos,"
            f"crop={jan_w}:{jan_h}:{x}:{y}")


def split(cena, destino):
    """Cena 3-em-1: material complementar na janela de cima, o take embaixo.
    O audio e sempre o do take; o material de cima entra mudo."""
    baixo = config.H - config.DIVISORIA
    ini, fim = fala.bordas_com_teto(cena.arquivo, cena.teto)
    d = fim - ini
    tw, th = probe.dimensao(cena.topo.arquivo)
    vf_vel = _velocidade(cena.velocidade)
    pb = probe.area_util(cena.arquivo) or ""

    _roda([
        "ffmpeg", "-y", "-v", "error",
        "-stream_loop", "-1", "-i", str(cena.topo.arquivo),
        "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(cena.arquivo),
        "-filter_complex",
        # janela de cima: o complementar, recortado pela ancora
        f"[0:v]{recorte_topo(tw, th, cena.topo.ancora)},"
        f"trim=0:{d:.3f},setpts=PTS-STARTPTS,fps={config.FPS},setsar=1[cima];"
        # janela de baixo: o take, com o teto cortado para o rosto caber
        f"[1:v]{pb}scale={config.W}:{config.H}"
        f":force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={config.W}:{baixo}:0:{config.SPLIT_TETO},{_SHARP},"
        f"fps={config.FPS},setsar=1[baixo];"
        # empilha e fixa o tamanho: sem isto sai 1918 e o concat quebra
        f"[cima][baixo]vstack=inputs=2,scale={config.W}:{config.H},"
        f"setsar=1{vf_vel},format=yuv420p[v]",
        "-map", "[v]", "-map", "1:a",
        "-af", (f"atempo={cena.velocidade}," if abs(cena.velocidade - 1.0) > 0.001 else "")
                + f"loudnorm=I={config.LUFS}:TP={config.TETO_DB}",
    ] + _saida_padrao(destino))
    return destino
