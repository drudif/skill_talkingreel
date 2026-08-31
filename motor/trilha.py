"""Musica por baixo da voz.

A ORDEM IMPORTA: comprimir a MUSICA tendo a VOZ como chave, e so depois
misturar. Inverter as entradas do sidechaincompress comprime a voz usando a
musica como chave — o contrario do que se quer, e o erro passa despercebido
porque o arquivo sai sem erro.

SEGUNDA ARMADILHA: o `alimiter` tem `level=true` por padrao, e essa opcao
normaliza o audio de volta para 0 dB DEPOIS de limitar — desfazendo o
trabalho. Sem `level=disabled` o pico final sai em 0 dB em vez do teto.
Medido: -0.0 dB com a opcao padrao, -1.5 dB com ela desligada."""
import re
import subprocess
from pathlib import Path

from motor import config, probe

# As faixas que vem com a skill. NAO ha lista de nomes fixos: quem instala poe
# os arquivos que quiser, com os nomes que eles ja tem. Exigir nome canonico
# obrigaria a renomear musica baixada, e o unico ganho seria um rotulo que o
# proprio nome do arquivo ja costuma dar.
#
# O que substitui o rotulo e MEDIDA: duracao, energia e quantos picos a faixa
# tem por minuto. Com isso a Chili escolhe comparando as faixas entre si, em vez
# de acreditar num rotulo que ninguem conferiu.
FORMATOS = (".mp3", ".m4a", ".wav", ".aac", ".flac")

MIN_SEGUNDOS = 5.0     # abaixo disto nao e trilha, e efeito ou arquivo quebrado


def pasta():
    """Onde as trilhas moram, dentro da propria skill."""
    return Path(__file__).resolve().parent.parent / "assets" / "trilhas"


def _nome_limpo(stem):
    """O nome da faixa sem o carimbo de data que os exportadores grudam.

    `Amor_e_Ritmo_2026-08-31T172951` vira `Amor e Ritmo`. Quem le a folha nao
    tem o que fazer com a hora em que o arquivo foi baixado, e o carimbo empurra
    o nome de verdade para fora da linha."""
    limpo = re.sub(r"[_-]?\d{4}-\d{2}-\d{2}[T_]?\d{0,6}$", "", stem)
    return (limpo or stem).replace("_", " ").strip()


def medir(caminho):
    """O que da para saber de uma faixa sem ouvir.

    `picos_por_minuto` nao e batida por minuto de verdade -- e a contagem de
    vezes que a energia sobe acima da media. Serve para ordenar as faixas da
    mais parada para a mais agitada, que e a comparacao que interessa; nao serve
    como andamento musical, e nao deve ser chamado assim em lugar nenhum."""
    import math
    from motor import fala
    caminho = Path(caminho)
    env = fala.envelope(caminho)
    dur = probe.dur(caminho)
    if not env or dur <= 0:
        return {"arquivo": str(caminho), "nome": _nome_limpo(caminho.stem),
                "duracao": round(dur, 1), "ilegivel": True}
    media = sum(env) / len(env)
    desvio = math.sqrt(sum((x - media) ** 2 for x in env) / len(env))
    picos, acima = 0, False
    for v in env:
        if v > media * 1.35 and not acima:
            picos += 1
            acima = True
        elif v < media:
            acima = False
    return {"arquivo": str(caminho), "nome": _nome_limpo(caminho.stem),
            "duracao": round(dur, 1),
            "energia": round(media, 3),
            "variacao": round(desvio, 3),
            "picos_por_minuto": round(picos / (dur / 60)),
            "ilegivel": False}


def disponiveis(onde=None):
    """Toda faixa da pasta, medida, da mais parada para a mais agitada.

    Devolve so o que existe e abre. Prometer uma faixa que nao existe faria a
    montagem falhar la na frente, com o trabalho ja feito."""
    onde = Path(onde) if onde else pasta()
    if not onde.is_dir():
        return []
    achadas = []
    for caminho in sorted(onde.iterdir()):
        if caminho.suffix.lower() not in FORMATOS:
            continue
        ficha = medir(caminho)
        if ficha.get("ilegivel") or ficha["duracao"] < MIN_SEGUNDOS:
            continue
        achadas.append(ficha)
    return sorted(achadas, key=lambda f: f["picos_por_minuto"])


def em_portugues(fichas, duracao_do_filme=None):
    """As faixas descritas em frases, para a folha de aprovacao.

    A descricao e COMPARATIVA -- mais parada, mais agitada -- porque um numero
    de energia sozinho nao diz nada para quem esta escolhendo musica."""
    if not fichas:
        return ("Nao ha nenhuma trilha guardada com a skill. A pessoa pode "
                "mandar a musica dela, ou o video sai sem musica.")
    linhas = []
    for i, f in enumerate(fichas):
        nome = f["nome"]
        if len(fichas) == 1:
            ritmo = ""
        elif i == 0:
            ritmo = ", a mais parada das que ha"
        elif i == len(fichas) - 1:
            ritmo = ", a mais agitada das que ha"
        else:
            ritmo = ""
        partes = [f"{nome}: {f['duracao']:.0f} segundos{ritmo}"]
        if duracao_do_filme and f["duracao"] < duracao_do_filme:
            vezes = duracao_do_filme / f["duracao"]
            if vezes > 1.5:
                partes.append(
                    f"vai repetir cerca de {vezes:.0f} vezes no video")
        linhas.append(", ".join(partes) + ".")
    return "\n".join(linhas)


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
        f"alimiter=limit={10 ** (config.TETO_DB / 20):.4f}:level=disabled[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "pcm_s16le", "-ar", str(config.SR), "-ac", "2",
        "-t", f"{total:.3f}", str(destino)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg falhou na trilha: " + r.stderr.strip()[:500])
    return destino
