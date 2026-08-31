"""Leitura de arquivo. Nada aqui produz video."""
import re
import subprocess


def _ffprobe(args):
    return subprocess.run(["ffprobe", "-v", "error"] + args,
                          capture_output=True, text=True).stdout.strip()


def dur(caminho):
    """Duracao em segundos, ou 0.0 quando o arquivo nao diz.

    O ffprobe devolve a palavra `N/A` para arquivo truncado, vazio ou que nao e
    video -- e nao um erro. Sem tratar isso aqui, um arquivo estragado que a
    pessoa mandou por engano derrubava o programa inteiro com uma mensagem em
    ingles e um monte de linha de codigo na tela. Devolver 0.0 faz o problema
    virar aviso em portugues, que e o que ela consegue entender."""
    saida = _ffprobe(["-show_entries", "format=duration", "-of", "csv=p=0",
                      str(caminho)])
    try:
        return float(saida)
    except (TypeError, ValueError):
        return 0.0


def rotacao(caminho):
    """Quantos graus o arquivo pede para girar a imagem, ou 0.

    Celular grava com o sensor sempre na mesma posicao e anota a rotacao num
    campo a parte, em vez de girar os pixels. Um video gravado em pe chega
    guardado deitado, com esta marca em -90."""
    saida = _ffprobe(["-select_streams", "v:0",
                      "-show_entries", "stream_side_data=rotation",
                      "-of", "default=nw=1:nk=1", str(caminho)])
    for linha in saida.splitlines():
        try:
            return int(round(float(linha.strip())))
        except ValueError:
            continue
    return 0


def dimensao(caminho):
    """Largura e altura COMO O FFMPEG ENTREGA aos filtros, ja com a rotacao
    do arquivo aplicada.

    O ffprobe devolve o tamanho GUARDADO, que num video de celular gravado em
    pe vem deitado -- 3840x2160 com uma marca de -90 grau. Todo calculo deste
    motor acontece depois dos filtros, onde a imagem ja esta girada: usar o
    numero guardado faz a conta do encaixe do material complementar sair
    trocada, e o video sai com o enquadramento errado sem nada acusar.

    MEDIDO num arquivo de iPhone: guardado 3840x2160, marca -90, entregue aos
    filtros 2160x3840. Sem esta correcao o dossie dizia "gravado deitado" para
    um video que esta em pe."""
    saida = _ffprobe(["-select_streams", "v:0", "-show_entries", "stream=width,height",
                      "-of", "csv=p=0", str(caminho)])
    nums = [int(x) for x in saida.split(",") if x.strip()]
    if len(nums) < 2:
        return (0, 0)
    largura, altura = nums[0], nums[1]
    if abs(rotacao(caminho)) % 180 == 90:
        return (altura, largura)
    return (largura, altura)


def tem_audio(caminho):
    saida = _ffprobe(["-select_streams", "a:0", "-show_entries", "stream=index",
                      "-of", "csv=p=0", str(caminho)])
    return bool(saida)


def area_util(caminho):
    """Gravacao exportada de app de edicao chega deitada com o vertical no meio e
    barra preta nos lados. Devolve o filtro de crop da area util, ou None se o
    arquivo ja for vertical.

    O ponto de amostra do cropdetect nao pode ser fixo em 1s: um arquivo com
    menos de 1s (cena com pouca fala, por exemplo) faz o -ss pular direto
    para o fim, o cropdetect nao le nenhum quadro e a funcao devolve None --
    que quem chama le como "ja esta vertical, nao mexe"."""
    duracao = dur(caminho)
    if duracao <= 0:
        return None
    ss = min(1.0, duracao / 3)
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", f"{ss:.3f}", "-i", str(caminho),
         "-vf", "cropdetect=24:2:0", "-frames:v", "12", "-f", "null", "-"],
        capture_output=True, text=True)
    achados = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", r.stderr)
    if not achados:
        return None
    cw, ch, cx, cy = map(int, achados[-1])
    if ch == 0 or cw / ch > 0.6:      # ja e vertical ou quase: nao mexe
        return None
    sw, sh = dimensao(caminho)
    if sw and sh and sw <= sh:        # o ffmpeg ja entregou vertical aos filtros
        return None                   # (bruto de iPhone tem rotacao nos metadados)
    return f"crop={cw}:{ch}:{cx}:{cy},"
