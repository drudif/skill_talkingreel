"""Orquestra: le o arquivo de cenas, produz um segmento por cena, junta tudo.

A ARMADILHA CENTRAL: juntar por lista (concat demuxer) descartava trechos de
audio e o filme dessincronizava progressivamente. Juntar por FILTRO decodifica
e re-sincroniza. E antes de juntar, todo segmento tem de ter exatamente o mesmo
tamanho — alguma etapa devolve um pixel a menos."""
import json
import subprocess
import tempfile
from pathlib import Path

from motor import cenas as mod_cenas
from motor import config, probe, tratamentos


def duracoes(caminho):
    """(duracao do video, duracao do audio). Se diferirem muito, ha problema."""
    def _d(fluxo):
        saida = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", fluxo,
             "-show_entries", "stream=duration", "-of", "csv=p=0", str(caminho)],
            capture_output=True, text=True).stdout.strip()
        return float(saida.split(",")[0]) if saida else 0.0
    return _d("v:0"), _d("a:0")


def _segmento(cena, destino):
    if cena.trat == "cheia":
        return tratamentos.tela_cheia(cena, destino)
    if cena.trat == "split":
        return tratamentos.split(cena, destino)
    raise ValueError(f"tratamento sem implementacao: {cena.trat}")


def montar(caminho_cenas, destino, tmp=None):
    prod = mod_cenas.carregar(caminho_cenas)
    destino = Path(destino)
    tmp = Path(tmp or tempfile.mkdtemp(prefix="talkingreel-"))
    tmp.mkdir(parents=True, exist_ok=True)

    segmentos, mapa, t = [], [], 0.0
    for cena in prod.cenas:
        seg = _segmento(cena, tmp / f"s{cena.n:03d}.mov")
        d = probe.dur(seg)
        mapa.append({"n": cena.n, "trat": cena.trat,
                     "ini": round(t, 3), "fim": round(t + d, 3)})
        t += d
        segmentos.append(seg)

    args = ["ffmpeg", "-y", "-v", "error"]
    for seg in segmentos:
        args += ["-i", str(seg)]
    cadeia = "".join(f"[{i}:v][{i}:a]" for i in range(len(segmentos)))
    args += ["-filter_complex",
             f"{cadeia}concat=n={len(segmentos)}:v=1:a=1[v][a]",
             "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-crf", "18", "-preset", "medium",
             "-c:a", "aac", "-b:a", "192k", "-ar", str(config.SR),
             "-movflags", "+faststart", str(destino)]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg falhou ao juntar: " + r.stderr.strip()[:500])

    (Path(caminho_cenas).parent / "cenas-mapa.json").write_text(
        json.dumps(mapa, indent=1, ensure_ascii=False), encoding="utf-8")
    return destino
