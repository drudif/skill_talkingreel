"""Orquestra: le o arquivo de cenas, produz um segmento por cena, junta tudo.

A ARMADILHA CENTRAL: juntar por lista (concat demuxer) descartava trechos de
audio e o filme dessincronizava progressivamente. Juntar por FILTRO decodifica
e re-sincroniza. E antes de juntar, todo segmento tem de ter exatamente o mesmo
tamanho — alguma etapa devolve um pixel a menos."""
import json
import shutil
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

from motor import arte
from motor import cenas as mod_cenas
from motor import config, fala, legenda as mod_legenda, probe, tratamentos, trilha


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


def _segmento(cena, destino, ja_cortado=False, area=None):
    if cena.trat == "cheia":
        return tratamentos.tela_cheia(cena, destino, ja_cortado, area)
    if cena.trat == "split":
        return tratamentos.split(cena, destino, ja_cortado, area)
    raise ValueError(f"tratamento sem implementacao: {cena.trat}")


def montar(caminho_cenas, destino, tmp=None, transcrever=None):
    """Monta o filme. `transcrever` existe para o teste poder exercitar a
    fiacao da legenda sem baixar o modelo de 3GB nem depender de fala real:
    e uma funcao que recebe o caminho do filme e devolve
    [{"p": palavra, "t": inicio, "f": fim}, ...]."""
    prod = mod_cenas.carregar(caminho_cenas)
    destino = Path(destino)
    tmp = Path(tmp or tempfile.mkdtemp(prefix="talkingreel-"))
    tmp.mkdir(parents=True, exist_ok=True)

    segmentos, mapa, t = [], [], 0.0
    for cena in prod.cenas:
        # a area util (crop de pillarbox) e uma propriedade de ENQUADRAMENTO,
        # nao de tempo: tem de vir do arquivo ORIGINAL. aperta() corta pelo
        # span da fala e pode devolver um arquivo com menos de 1s -- rodar a
        # deteccao nele deixa a funcao cega (ver motor/probe.py:area_util).
        area = probe.area_util(cena.arquivo) or ""
        ini, fim = _bordas(cena)
        apertado, n_pausas = tratamentos.aperta(
            cena.arquivo, tmp / f"a{cena.n:03d}.mov", ini, fim)
        cena_apertada = replace(cena, arquivo=Path(apertado))
        seg = _segmento(cena_apertada, tmp / f"s{cena.n:03d}.mov",
                        ja_cortado=True, area=area)
        if cena.letreiro:
            peca = tmp / f"l{cena.n:03d}.png"
            arte.letreiro(cena.letreiro.texto, prod.estilo, peca,
                          base=cena.letreiro.base, box=cena.letreiro.box)
            com_arte = tmp / f"la{cena.n:03d}.mov"
            tratamentos.com_overlay(seg, peca, com_arte,
                                    entra=cena.letreiro.entra,
                                    dura=cena.letreiro.dura)
            seg = com_arte
        d = probe.dur(seg)
        registro = {"n": cena.n, "trat": cena.trat, "pausas": n_pausas,
                    "ini": round(t, 3), "fim": round(t + d, 3)}
        if cena.letreiro:
            # em tempo de FILME, para a legenda saber onde sumir. `entra` e
            # `dura` sao contados na cena ja pronta -- depois do corte de
            # silencio e da velocidade -- entao basta somar o inicio da cena.
            fim_letreiro = (cena.letreiro.entra + cena.letreiro.dura
                            if cena.letreiro.dura else d)
            registro["letreiro"] = [round(t + cena.letreiro.entra, 3),
                                    round(t + min(fim_letreiro, d), 3)]
        mapa.append(registro)
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

    if prod.legenda:
        # transcreve o filme JA MONTADO: os tempos ja saem na escala final,
        # depois do corte de silencio e da velocidade. E antes da trilha nao
        # adianta -- a musica entra depois, mas a duracao nao muda.
        ler = transcrever or mod_legenda.transcrever
        palavras = ler(destino)
        mod_legenda.corrigir(palavras, prod.proprios)
        com_leg = tmp / "legendado.mp4"
        mod_legenda.queimar(destino, mod_legenda.blocos(palavras), prod.estilo,
                            com_leg, mapa=mapa,
                            posicao_split=prod.legenda_split)
        shutil.copyfile(com_leg, destino)

    (Path(caminho_cenas).parent / "cenas-mapa.json").write_text(
        json.dumps(mapa, indent=1, ensure_ascii=False), encoding="utf-8")
    return destino
