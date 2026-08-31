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
