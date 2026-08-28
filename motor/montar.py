"""Orquestra: le o arquivo de cenas, produz um segmento por cena, junta tudo.

A ARMADILHA CENTRAL: juntar por lista (concat demuxer) descartava trechos de
audio e o filme dessincronizava progressivamente. Juntar por FILTRO decodifica
e re-sincroniza. E antes de juntar, todo segmento tem de ter exatamente o mesmo
tamanho — alguma etapa devolve um pixel a menos."""
import json
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

from motor import cenas as mod_cenas
from motor import config, fala, probe, tratamentos, trilha


def _bordas(cena):
    return fala.bordas_com_teto(cena.arquivo, cena.teto)


def duracoes(caminho):
    """(duracao do video, duracao do audio). Se diferirem muito, ha problema."""
    def _d(fluxo):
        saida = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", fluxo,
             "-show_entries", "stream=duration", "-of", "csv=p=0", str(caminho)],
            capture_output=True, text=True).stdout.strip()
        return float(saida.split(",")[0]) if saida else 0.0
    return _d("v:0"), _d("a:0")


def _segmento(cena, destino, ja_cortado=False):
    if cena.trat == "cheia":
        return tratamentos.tela_cheia(cena, destino, ja_cortado)
    if cena.trat == "split":
        return tratamentos.split(cena, destino, ja_cortado)
    raise ValueError(f"tratamento sem implementacao: {cena.trat}")


def montar(caminho_cenas, destino, tmp=None):
    prod = mod_cenas.carregar(caminho_cenas)
    destino = Path(destino)
    tmp = Path(tmp or tempfile.mkdtemp(prefix="talkingreel-"))
    tmp.mkdir(parents=True, exist_ok=True)

    segmentos, mapa, t = [], [], 0.0
    for cena in prod.cenas:
        ini, fim = _bordas(cena)
        apertado, n_pausas = tratamentos.aperta(
            cena.arquivo, tmp / f"a{cena.n:03d}.mov", ini, fim)
        cena_apertada = replace(cena, arquivo=Path(apertado))
        seg = _segmento(cena_apertada, tmp / f"s{cena.n:03d}.mov", ja_cortado=True)
        d = probe.dur(seg)
        mapa.append({"n": cena.n, "trat": cena.trat, "pausas": n_pausas,
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

    if prod.trilha:
        com_trilha = tmp / "com-trilha.mov"
        trilha.aplicar(destino, prod.trilha, com_trilha)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(com_trilha),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-ar", str(config.SR), "-movflags", "+faststart",
                        str(destino)], check=True)

    (Path(caminho_cenas).parent / "cenas-mapa.json").write_text(
        json.dumps(mapa, indent=1, ensure_ascii=False), encoding="utf-8")
    return destino
