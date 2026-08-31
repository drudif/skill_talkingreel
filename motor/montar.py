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
from motor import (config, fala, imagem, legenda as mod_legenda, probe, tempo,
                   tratamentos, trilha)


def _bordas(cena):
    """As bordas da fala DENTRO do trecho que a cena pediu. `de` e `ate`
    recortam o take antes de procurar onde a voz comeca -- e o que faz duas
    cenas do mesmo arquivo nao encontrarem a mesma fala."""
    return fala.bordas_com_teto(cena.arquivo, cena.teto,
                                de=cena.de, ate=cena.ate)


def duracoes(caminho):
    """(duracao do video, duracao do audio). Se diferirem muito, ha problema."""
    def _d(fluxo):
        saida = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", fluxo,
             "-show_entries", "stream=duration", "-of", "csv=p=0", str(caminho)],
            capture_output=True, text=True).stdout.strip()
        return float(saida.split(",")[0]) if saida else 0.0
    return _d("v:0"), _d("a:0")


def _segmento(cena, destino, ja_cortado=False, area=None, contraste=None):
    if cena.trat == "cheia":
        return tratamentos.tela_cheia(cena, destino, ja_cortado, area, contraste)
    if cena.trat == "split":
        return tratamentos.split(cena, destino, ja_cortado, area, contraste)
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

    # Antes de renderizar qualquer coisa: se alguem pediu para trocar o fundo,
    # a gravacao precisa ter sido feita na frente de um pano verde. Recusar aqui
    # custa segundos; descobrir depois custa a montagem inteira -- e o resultado
    # seria um video com pedacos da pessoa apagados.
    for cena in prod.cenas:
        if cena.fundo and not imagem.tem_fundo_verde(cena.arquivo):
            raise mod_cenas.CenasInvalidas(
                f"cena {cena.n}: voce pediu para trocar o fundo, mas esta "
                "gravacao nao foi feita na frente de um pano ou parede verde. "
                "Trocar o fundo so funciona com pano verde: e o verde que diz "
                "ao programa o que e cenario e o que e pessoa. Numa sala comum "
                "o programa apagaria pedacos de voce junto com o fundo.")

    segmentos, mapa, t = [], [], 0.0
    for cena in prod.cenas:
        # a area util (crop de pillarbox) e uma propriedade de ENQUADRAMENTO,
        # nao de tempo: tem de vir do arquivo ORIGINAL. aperta() corta pelo
        # span da fala e pode devolver um arquivo com menos de 1s -- rodar a
        # deteccao nele deixa a funcao cega (ver motor/probe.py:area_util).
        area = probe.area_util(cena.arquivo) or ""
        # como a area util, o contraste e propriedade da IMAGEM e sai do arquivo
        # ORIGINAL: depois do corte a cena pode ter poucos quadros, e a conta
        # sairia de uma amostra pequena demais.
        contraste = (imagem.ganho(cena.arquivo) if prod.contraste is True
                     else (None if prod.contraste is False else prod.contraste))
        ini, fim = _bordas(cena)
        # detectadas UMA vez e passadas adiante: o corte e o mapa de tempo tem
        # de olhar a mesma lista de pausas. Detectar duas vezes abriria a porta
        # para as duas discordarem, e o sintoma seria o letreiro fora de hora.
        pausas = fala.pausas_internas(cena.arquivo, ini, fim)
        apertado, n_pausas = tratamentos.aperta(
            cena.arquivo, tmp / f"a{cena.n:03d}.mov", ini, fim, pausas=pausas)
        cena_apertada = replace(cena, arquivo=Path(apertado))
        if cena.fundo:
            # a cor do pano sai do arquivo ORIGINAL, que tem o pano inteiro e
            # muitos quadros; o trecho cortado pode ter poucos.
            trocado = tmp / f"v{cena.n:03d}.mov"
            tratamentos.trocar_fundo(
                cena_apertada.arquivo, trocado, cena.fundo,
                cor=imagem.cor_do_fundo_verde(cena.arquivo))
            cena_apertada = replace(cena_apertada, arquivo=trocado)
        seg = _segmento(cena_apertada, tmp / f"s{cena.n:03d}.mov",
                        ja_cortado=True, area=area, contraste=contraste)
        # medido ANTES do letreiro: o overlay nao muda a duracao (e para isso
        # que serve o eof_action=pass), e o mapa precisa da duracao real para
        # corrigir o arredondamento acumulado.
        d = probe.dur(seg)
        m = tempo.Mapa(n=cena.n, ini=ini, fim=fim, marcas=tempo.marcas(ini, fim, pausas),
                       velocidade=cena.velocidade, offset=t, dur=d)
        if cena.letreiro:
            # AQUI mora a coordenada unica: o agente escreveu o segundo da
            # GRAVACAO, e so este ponto converte para o tempo da cena pronta.
            entra = m.na_cena(cena.letreiro.de)
            if cena.letreiro.ate is not None:
                dura = max(config.LEG_MIN_LETREIRO,
                           m.na_cena(cena.letreiro.ate) - entra)
            else:
                dura = max(config.LEG_MIN_LETREIRO, d - entra)
            peca = tmp / f"l{cena.n:03d}.mov"
            arte.letreiro_animado(cena.letreiro.texto, prod.estilo, peca,
                                  animacao=cena.letreiro.animacao, dur=dura,
                                  base=cena.letreiro.base,
                                  box=cena.letreiro.box)
            com_arte = tmp / f"la{cena.n:03d}.mov"
            tratamentos.com_peca_animada(seg, peca, com_arte, entra=entra)
            seg = com_arte
        registro = {"n": cena.n, "trat": cena.trat, "pausas": n_pausas,
                    "ini": round(t, 3), "fim": round(t + d, 3),
                    "contraste": round(contraste or config.CONTRASTE_BASE, 3),
                    **m.como_registro()}
        if cena.topo:
            # o laudo precisa saber que material entrou na metade de cima
            # para medir quantas vezes ele repete dentro da cena.
            registro["topo"] = str(cena.topo.arquivo)
        if cena.letreiro:
            # em tempo de FILME, para a legenda saber onde sumir.
            fim_letreiro = entra + dura
            registro["letreiro"] = [round(t + entra, 3),
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
        # guarda o filme SEM legenda antes de queimar: e um dos
        # entregaveis, para quando o aplicativo legenda sozinho. Sem isto ele
        # so existiria na pasta temporaria, que e descartada.
        sem_legenda = destino.with_name(destino.stem + "-sem-legenda"
                                        + destino.suffix)
        shutil.copyfile(destino, sem_legenda)
        com_leg = tmp / "legendado.mp4"
        mod_legenda.queimar(destino, mod_legenda.blocos(palavras), prod.estilo,
                            com_leg, mapa=mapa,
                            posicao_split=prod.legenda_split)
        shutil.copyfile(com_leg, destino)

    (Path(caminho_cenas).parent / "cenas-mapa.json").write_text(
        json.dumps(mapa, indent=1, ensure_ascii=False), encoding="utf-8")
    return destino
