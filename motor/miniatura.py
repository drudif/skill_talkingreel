"""Um quadro do filme, pequeno, embutido na folha como texto.

A folha nao carrega arquivo de fora -- a pagina publicada roda isolada. Entao
a miniatura vira `data:` URI. Vale o teto: video embutido levou a folha do
projeto de origem a 5 MB, e o custo de token de uma pagina grande e real."""
import base64
import subprocess
from pathlib import Path

LARGURA = 160
TETO_BYTES = 12_000        # do data: URI ja codificado
QUALIDADES = (4, 7, 12)    # -q:v do ffmpeg: menor e melhor


def de(filme, instante, largura=LARGURA, teto=TETO_BYTES):
    """O quadro em `instante`, como data: URI. None se nao der para extrair.

    Tenta qualidades cada vez menores ate caber no teto. Devolver uma imagem
    grande demais e pior que devolver uma feia: a pagina inteira e o custo."""
    filme = Path(filme)
    if not filme.exists():
        return None
    for q in QUALIDADES:
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{instante:.3f}", "-i", str(filme),
             "-frames:v", "1", "-vf", f"scale={largura}:-2",
             "-q:v", str(q), "-f", "mjpeg", "-"],
            capture_output=True)
        if r.returncode != 0 or not r.stdout:
            return None
        uri = "data:image/jpeg;base64," + base64.b64encode(r.stdout).decode()
        if len(uri) <= teto:
            return uri
    return uri     # a ultima tentativa, mesmo estourando: melhor que nada


def de_imagem(caminho, largura=LARGURA, teto=TETO_BYTES):
    """O mesmo que `de()`, mas a partir de uma imagem em vez de um filme.

    E o que leva as amostras de estilo para a folha: elas ja sao imagem, e
    passar por um arquivo de video so para tirar um quadro seria caminho longo
    para o mesmo lugar."""
    caminho = Path(caminho)
    if not caminho.exists():
        return None
    for q in QUALIDADES:
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(caminho),
             "-frames:v", "1", "-vf", f"scale={largura}:-2",
             "-q:v", str(q), "-f", "mjpeg", "-"],
            capture_output=True)
        if r.returncode != 0 or not r.stdout:
            return None
        uri = "data:image/jpeg;base64," + base64.b64encode(r.stdout).decode()
        if len(uri) <= teto:
            return uri
    return uri


# --- trecho de audio, para a pessoa ouvir a trilha antes de escolher ---

SEGUNDOS_DE_AMOSTRA = 12       # o bastante para reconhecer a musica
TETO_AUDIO_BYTES = 180_000     # do data: URI ja codificado, por faixa
_TAXAS = (64, 48, 32)          # kbps: a primeira que couber no teto


def audio_de(caminho, segundos=SEGUNDOS_DE_AMOSTRA, teto=TETO_AUDIO_BYTES,
             comeco=None):
    """Um trecho da faixa como data: URI, para tocar dentro da folha.

    A folha nao carrega arquivo de fora -- a pagina publicada roda isolada -- e
    a faixa inteira nao cabe: um MP3 de 1 MB vira 1,4 MB em texto, e quatro
    deles inflariam a pagina em quase 6 MB. Um trecho basta: quem escolhe
    musica reconhece a faixa nos primeiros segundos.

    O trecho comeca depois do inicio, e nao no zero: muita faixa abre com dois
    ou tres segundos de quase nada, e a amostra sairia muda."""
    caminho = Path(caminho)
    if not caminho.exists():
        return None
    if comeco is None:
        from motor import probe
        dur = probe.dur(caminho)
        comeco = min(8.0, dur * 0.15) if dur > segundos * 1.5 else 0.0
    for kbps in _TAXAS:
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{comeco:.2f}",
             "-t", str(segundos), "-i", str(caminho),
             "-vn", "-ac", "1", "-b:a", f"{kbps}k", "-f", "mp3", "-"],
            capture_output=True)
        if r.returncode != 0 or not r.stdout:
            return None
        uri = "data:audio/mpeg;base64," + base64.b64encode(r.stdout).decode()
        if len(uri) <= teto:
            return uri
    return uri
