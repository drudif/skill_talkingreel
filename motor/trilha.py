"""Musica por baixo da voz.

A ORDEM IMPORTA: comprimir a MUSICA tendo a VOZ como chave, e so depois
misturar. Inverter as entradas do sidechaincompress comprime a voz usando a
musica como chave — o contrario do que se quer, e o erro passa despercebido
porque o arquivo sai sem erro.

SEGUNDA ARMADILHA: o `alimiter` tem `level=true` por padrao, e essa opcao
normaliza o audio de volta para 0 dB DEPOIS de limitar — desfazendo o
trabalho. Sem `level=disabled` o pico final sai em 0 dB em vez do teto.
Medido: -0.0 dB com a opcao padrao, -1.5 dB com ela desligada."""
import subprocess
from pathlib import Path

from motor import config, probe

# As faixas que vem com a skill, e para que serve cada uma. A Chili escolhe
# uma quando a pessoa nao mandou musica propria; o texto ao lado e o que ela
# tem para decidir, e e o que vai para a folha.
PRONTAS = {
    "calma": "conversa, opiniao, relato -- a musica fica atras e nao disputa",
    "tensao": "quando o assunto tem virada, problema ou alerta",
    "animada": "humor, novidade, convite -- ritmo para a frente",
    "neutra": "conteudo tecnico ou institucional, onde a musica e so base",
}
FORMATOS = (".mp3", ".m4a", ".wav")


def pasta():
    """Onde as trilhas prontas moram, dentro da propria skill."""
    return Path(__file__).resolve().parent.parent / "assets" / "trilhas"


def disponiveis(onde=None):
    """As trilhas prontas que existem no disco: {nome: caminho}.

    Devolve so o que esta la de verdade. As quatro faixas nao entram no
    repositorio -- quem instala a skill poe as suas -- e prometer uma faixa que
    nao existe faria a montagem falhar la na frente, com o trabalho ja feito."""
    onde = Path(onde) if onde else pasta()
    achadas = {}
    if not onde.is_dir():
        return achadas
    for nome in PRONTAS:
        for ext in FORMATOS:
            caminho = onde / f"{nome}{ext}"
            if caminho.exists():
                achadas[nome] = caminho
                break
    return achadas


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
