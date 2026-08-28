"""Medicao do resultado, para o Bluey rodar antes de publicar qualquer folha.

E medicao, nao julgamento. No projeto de origem quase todo erro apareceu aqui e
nao no olho: 0,475s de dessync, um pedaco de palavra que sobrou, uma cena que
encurtou 0,19s."""
import json
from pathlib import Path

from motor import limites, montar, probe

TOLERANCIA_SYNC = 0.10      # segundos entre o fim do video e o fim do audio


def rodar(filme, caminho_cenas=None):
    d_v, d_a = montar.duracoes(filme)
    problemas = []

    if d_a <= 0:
        problemas.append("o filme esta sem audio")
    if d_v <= 0:
        problemas.append("o filme esta sem imagem")
    if d_v > 0 and d_a > 0 and abs(d_v - d_a) > TOLERANCIA_SYNC:
        problemas.append(
            f"a imagem e o som terminam em momentos diferentes: "
            f"{abs(d_v - d_a):.2f} segundo de diferenca")

    w, h = probe.dimensao(filme)
    if (w, h) != (1080, 1920):
        problemas.append(f"o filme saiu {w}x{h} em vez de 1080x1920")

    cenas_mapa = []
    if caminho_cenas:
        mapa = Path(caminho_cenas).parent / "cenas-mapa.json"
        if mapa.exists():
            cenas_mapa = json.loads(mapa.read_text(encoding="utf-8"))
            # "ini" e "fim" no mapa vem do mesmo total corrente (montar.py
            # soma "d" nos dois ao mesmo tempo) -- comparar um com o outro e
            # tautologia, sempre bate, mesmo que "d" esteja errado. O que
            # prova algo de verdade e comparar o mapa contra uma medida
            # INDEPENDENTE: a duracao real do filme ja montado.
            if cenas_mapa:
                fim_mapa = cenas_mapa[-1]["fim"]
                dur_real = max(d_v, d_a)
                if abs(fim_mapa - dur_real) > TOLERANCIA_SYNC:
                    problemas.append(
                        f"o mapa de cenas (cena {cenas_mapa[0]['n']} a cena "
                        f"{cenas_mapa[-1]['n']}) diz que o filme termina em "
                        f"{fim_mapa:.2f} segundos, mas o filme dura "
                        f"{dur_real:.2f} segundos")

    estado_limites, recado = limites.verificar()
    if estado_limites != limites.INTACTO:
        problemas.append(recado)

    return {"ok": not problemas,
            "limites": estado_limites,
            "duracao": round(max(d_v, d_a), 3),
            "dif_video_audio": round(d_v - d_a, 3),
            "dimensao": [w, h],
            "cenas": len(cenas_mapa),
            "problemas": problemas}


def em_portugues(resultado):
    """O texto que vai para a pessoa. Sem termo tecnico -- quem le nao entende de
    montagem nem de audio."""
    linhas = [f"O video tem {resultado['duracao']:.1f} segundos"]
    if resultado["cenas"]:
        linhas[0] += f", em {resultado['cenas']} cenas"
    linhas[0] += "."
    if resultado["ok"]:
        linhas.append("Imagem e som terminam juntos, e o tamanho esta certo "
                      "para Instagram e TikTok.")
    else:
        linhas.append("Encontrei isto:")
        linhas += [f"- {p}" for p in resultado["problemas"]]
    return "\n".join(linhas)
