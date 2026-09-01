"""Produz o segmento de uma cena. E o unico modulo, junto com montar.py, que
chama ffmpeg para gerar video.

REGRAS QUE NAO PODEM SER QUEBRADAS:
  1. `-ss` vai ANTES do `-i`. Depois do `-i` ele vira opcao de saida e o corte
     escorrega para o arquivo seguinte. Custou meia hora de dessync.
  2. Audio dos segmentos em pcm_s16le. Comprimir aqui e comprimir de novo no
     final acumula atraso a cada emenda.
  3. -ar 48000 em toda etapa.
  4. Todo segmento sai EXATAMENTE 1080x1920. Alguma etapa devolve 1918 e o
     concat quebra.
"""
import subprocess
from pathlib import Path

from motor import config, fala, probe, tempo

def _sharp(contraste=None):
    """O realce que todo segmento recebe. `contraste` vem de
    `imagem.ganho()`, medido no arquivo ORIGINAL: imagem lavada e esticada ate
    a faixa que o material bem gravado ocupa, e imagem que ja esta boa recebe
    so o realce de sempre. Sem numero, e o de sempre."""
    c = config.CONTRASTE_BASE if contraste is None else contraste
    return f"unsharp=5:5:0.7:5:5:0,eq=contrast={c:.3f}:saturation=1.04"


def _roda(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg falhou: " + r.stderr.strip()[:500])


def _saida_padrao(destino, vf=None):
    filtro = ["-vf", vf] if vf else []
    return filtro + ["-c:v", "libx264", "-crf", "18", "-preset", "medium",
                     "-c:a", "pcm_s16le", "-ar", str(config.SR), "-ac", "2",
                     str(destino)]


def _velocidade(vel):
    """Filtro de video para mudar a velocidade sem mudar o tom. O filtro de
    audio equivalente (atempo) e montado por quem chama, junto do loudnorm."""
    if abs(vel - 1.0) < 0.001:
        return ""
    return f",setpts=PTS/{vel}"


def enquadrar(caminho, area=None, contraste=None):
    """Preenche 1080x1920 cortando o excesso, nunca deformando.

    `area` e o filtro de crop da area util ja detectado (string, possivelmente
    vazia) por quem chama. Se vier None, detecta sozinho a partir de `caminho`
    -- e o que preserva o uso direto desta funcao e das chamadas de teste."""
    pb = area if area is not None else (probe.area_util(caminho) or "")
    return (f"{pb}scale={config.W}:{config.H}"
            f":force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={config.W}:{config.H},{_sharp(contraste)},setsar=1")


def tela_cheia(cena, destino, ja_cortado=False, area=None, contraste=None):
    if ja_cortado:
        ini, fim = 0.0, probe.dur(cena.arquivo)
    else:
        ini, fim = fala.bordas_com_teto(cena.arquivo, cena.teto)
    vf_vel = _velocidade(cena.velocidade)
    muda_vel = abs(cena.velocidade - 1.0) > 0.001
    af = ["-af", (f"atempo={cena.velocidade}," if muda_vel else "")
          + f"loudnorm=I={config.LUFS}:TP={config.TETO_DB}"]
    _roda(["ffmpeg", "-y", "-v", "error",
           "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(cena.arquivo),
           "-vf", f"{enquadrar(cena.arquivo, area, contraste)}{vf_vel},fps={config.FPS},format=yuv420p",
           *af] + _saida_padrao(destino))
    return destino


def recorte_topo(largura, altura, ancora):
    """Filtro que encaixa um material de `largura`x`altura` na janela de cima do
    split (1080x807), cortando o que sobra.

    A janela e deitada. Material vertical perde altura: 9:16 sobra 42%, 1:1
    sobra 75%. Por isso a ancora existe -- cortar pelo centro decepa cabeca.
    ancora 0.0 = topo, 0.5 = centro, 1.0 = base. Na largura o corte e sempre
    centralizado, porque ali sobra pouco."""
    return recorte(largura, altura, ancora, config.W, config.DIVISORIA)


def recorte(largura, altura, ancora, jan_w, jan_h):
    """O mesmo encaixe, para uma janela qualquer. Na tela inteira (1080x1920)
    quem perde e o material DEITADO, e perde LARGURA: de um 16:9 sobram 32%,
    cortados pelo centro. Ali a ancora so muda alguma coisa se o material for
    mais alto que 9:16 -- e por isso ela nao resolve material deitado em tela
    cheia, que e o caso comum."""
    escala = max(jan_w / largura, jan_h / altura)
    esc_w, esc_h = round(largura * escala), round(altura * escala)
    y = int(round((esc_h - jan_h) * ancora))
    x = int(round((esc_w - jan_w) / 2))
    return (f"scale={esc_w}:{esc_h}:flags=lanczos,"
            f"crop={jan_w}:{jan_h}:{x}:{y}")


def material_cheio(cena, destino, ja_cortado=False, area=None, contraste=None):
    """O material complementar ocupando a tela inteira, com a voz da pessoa.

    A imagem da pessoa some por esses segundos; o som dela continua, e e ele
    que manda na duracao. Serve para mostrar aquilo de que ela esta falando --
    no split o material fica pela metade da tela e detalhe pequeno se perde.

    `-stream_loop -1` REPETE o material ate cobrir a fala. Sem isso um material
    de 4 segundos numa fala de 9 deixa cinco segundos de tela preta com voz --
    e ninguem ve isso ate assistir. `contraste` e ignorado de proposito: e a
    correcao medida na gravacao da PESSOA, e o material dela entra como veio."""
    if ja_cortado:
        ini, fim = 0.0, probe.dur(cena.arquivo)
    else:
        ini, fim = fala.bordas_com_teto(cena.arquivo, cena.teto)
    d = fim - ini
    mw, mh = probe.dimensao(cena.topo.arquivo)
    vf_vel = _velocidade(cena.velocidade)
    muda_vel = abs(cena.velocidade - 1.0) > 0.001
    _roda([
        "ffmpeg", "-y", "-v", "error",
        "-stream_loop", "-1", "-i", str(cena.topo.arquivo),
        "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(cena.arquivo),
        "-filter_complex",
        f"[0:v]{recorte(mw, mh, cena.topo.ancora, config.W, config.H)},"
        f"trim=0:{d:.3f},setpts=PTS-STARTPTS,fps={config.FPS},setsar=1"
        f"{vf_vel},fps={config.FPS},format=yuv420p[v]",
        "-map", "[v]", "-map", "1:a",
        "-af", (f"atempo={cena.velocidade}," if muda_vel else "")
                + f"loudnorm=I={config.LUFS}:TP={config.TETO_DB}",
    ] + _saida_padrao(destino))
    return destino


def split(cena, destino, ja_cortado=False, area=None, contraste=None):
    """Cena 3-em-1: material complementar na janela de cima, o take embaixo.
    O audio e sempre o do take; o material de cima entra mudo.

    `area` funciona como em enquadrar(): filtro de crop ja detectado por quem
    chama, ou None para detectar sozinho a partir de `cena.arquivo`."""
    alto, baixo = config.DIVISORIA, config.H - config.DIVISORIA
    if ja_cortado:
        ini, fim = 0.0, probe.dur(cena.arquivo)
    else:
        ini, fim = fala.bordas_com_teto(cena.arquivo, cena.teto)
    d = fim - ini
    tw, th = probe.dimensao(cena.topo.arquivo)
    vf_vel = _velocidade(cena.velocidade)
    pb = area if area is not None else (probe.area_util(cena.arquivo) or "")

    _roda([
        "ffmpeg", "-y", "-v", "error",
        "-stream_loop", "-1", "-i", str(cena.topo.arquivo),
        "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(cena.arquivo),
        "-filter_complex",
        # janela de cima: o complementar, recortado pela ancora
        f"[0:v]{recorte_topo(tw, th, cena.topo.ancora)},"
        f"trim=0:{d:.3f},setpts=PTS-STARTPTS,fps={config.FPS},setsar=1[cima];"
        # janela de baixo: o take, com o teto cortado para o rosto caber
        f"[1:v]{pb}scale={config.W}:{config.H}"
        f":force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={config.W}:{baixo}:(iw-{config.W})/2:{config.SPLIT_TETO},"
        f"{_sharp(contraste)},"
        f"fps={config.FPS},setsar=1[baixo];"
        # empilha e fixa o tamanho: sem isto sai 1918 e o concat quebra
        # fps DEPOIS do setpts da velocidade (vf_vel), igual em tela_cheia():
        # sem isto o encoder arredonda os quadros por conta propria e o
        # video sai mais longo que o audio.
        f"[cima][baixo]vstack=inputs=2,scale={config.W}:{config.H},"
        f"setsar=1{vf_vel},fps={config.FPS},format=yuv420p[v]",
        "-map", "[v]", "-map", "1:a",
        "-af", (f"atempo={cena.velocidade}," if abs(cena.velocidade - 1.0) > 0.001 else "")
                + f"loudnorm=I={config.LUFS}:TP={config.TETO_DB}",
    ] + _saida_padrao(destino))
    return destino


def trocar_fundo(caminho, destino, fundo, cor=None, tolerancia=None):
    """Troca o pano verde de tras da pessoa por outra imagem, ou por uma cor.

    SO FUNCIONA COM PANO VERDE DE VERDADE. Quem verifica antes e
    `imagem.tem_fundo_verde`; chamar isto sem verificar apaga pedacos da pessoa.

    `fundo` e um arquivo de imagem ou video, ou uma cor escrita como `#111111`.
    `cor` e a cor do pano, que sai de `imagem.cor_do_fundo_verde` -- panos
    verdes nao sao todos iguais e a luz muda o tom, entao cortar por uma cor
    fixa deixaria uma borda verde no contorno da pessoa.

    NADA DE `-shortest`, pela mesma razao de com_overlay(): ele come quadros de
    video e deixa o audio inteiro. Quem fixa a duracao aqui e o `-t` na saida.
    """
    d = probe.dur(caminho)
    w, h = probe.dimensao(caminho)
    cor = cor or "0x00b140"
    tol = config.VERDE_TOLERANCIA if tolerancia is None else tolerancia
    fundo = str(fundo)
    if fundo.startswith("#"):
        entrada_fundo = ["-f", "lavfi", "-t", f"{d + 0.05:.3f}",
                         "-i", f"color=c={fundo}:s={w}x{h}:r={config.FPS}"]
    elif probe.dur(fundo) > 0:
        # fundo em VIDEO. `-loop 1`, que serve para imagem parada, aqui
        # congelaria o primeiro quadro: o video de tras ficaria imovel e nada
        # acusaria. Quem repete video e `-stream_loop`, e ele precisa vir antes
        # do `-i` do proprio video.
        entrada_fundo = ["-stream_loop", "-1", "-i", fundo]
    else:
        entrada_fundo = ["-loop", "1", "-framerate", str(config.FPS),
                         "-t", f"{d + 0.05:.3f}", "-i", fundo]
    _roda([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(caminho), *entrada_fundo,
        "-filter_complex",
        # despill tira o verde que reflete na pele e no cabelo. Sem ele o
        # contorno da pessoa fica esverdeado sobre o fundo novo.
        f"[0:v]chromakey=color={cor}:similarity={tol:.3f}:blend={config.VERDE_BORDA:.3f},"
        f"despill=type=green[fg];"
        f"[1:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},setsar=1[bg];"
        f"[bg][fg]overlay=0:0:eof_action=pass,format=yuv420p[v]",
        "-map", "[v]", "-map", "0:a?", "-t", f"{d:.3f}"] + _saida_padrao(destino))
    return destino


def abertura(filme, destino, forca=None):
    """O estalo do comeco: a imagem desaba de um zoom violento enquanto se
    desmonta em canais fora de registro, croma deslocado e grao.

    Nos primeiros instantes o dedo de quem rola a tela ainda esta decidindo, e
    movimento forte segura. Passado um terco de segundo o mesmo efeito
    atrapalha a leitura, e por isso ele acaba ali.

    COMO CADA PARTE E FEITA, e por que assim:

    - O CRASH ZOOM e continuo: `scale` com `eval=frame` aceita expressao de
      tempo. A curva ao cubo poe quase toda a viagem nos tres primeiros
      quadros -- e o que separa um crash de um movimento de camera.
    - OS CANAIS, O CROMA E O GRAO vao em DEGRAUS, e nao por escolha: nenhum
      dos tres filtros aceita expressao de tempo, so numero fixo. O que eles
      aceitam e `enable`, entao sao varias copias de cada um, cada uma valendo
      numa faixa, com o valor caindo. Cada faixa dura de dois a tres quadros.

    NAO HA CLARAO BRANCO. Ele existiu numa versao e foi tirado: somar luz por
    cima de uma imagem que ja esta se desmontando lava tudo, e o pouco que ha
    para ver some.

    `forca` de 0 a 1 multiplica tudo. Em 0 nao ha efeito nenhum."""
    f = config.ABERTURA_FORCA if forca is None else forca
    if f <= 0:
        _roda(["ffmpeg", "-y", "-v", "error", "-i", str(filme),
               "-c", "copy", str(destino)])
        return destino
    d = config.ABERTURA_DUR
    zoom = config.ABERTURA_ZOOM * f

    canais = ",".join(
        f"rgbashift=rh={int(round(h * f))}:bh={-int(round(h * f))}"
        + (f":rv={-int(round(v * f))}:bv={int(round(v * f))}" if v else "")
        + f":enable='between(t,{a:.3f},{b:.3f})'"
        for h, v, a, b in config.ABERTURA_CANAIS)
    croma = ",".join(
        f"chromashift=cbh={int(round(px * f))}:crh={-int(round(px * f))}"
        f":enable='between(t,{a:.3f},{b:.3f})'"
        for px, a, b in config.ABERTURA_CROMA)
    grao = ",".join(
        f"noise=alls={int(round(px * f))}:allf=t+u"
        f":enable='between(t,{a:.3f},{b:.3f})'"
        for px, a, b in config.ABERTURA_GRAO)

    _roda([
        "ffmpeg", "-y", "-v", "error", "-i", str(filme),
        "-vf",
        f"scale=w='iw*(1+{zoom:.3f}*max(0,1-t/{d})^3)'"
        f":h='ih*(1+{zoom:.3f}*max(0,1-t/{d})^3)':eval=frame,"
        f"crop={config.W}:{config.H},{canais},{croma},{grao},format=yuv420p",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "copy", "-movflags", "+faststart", str(destino)])
    return destino


def emendas_do_glitch(emendas, minimo=None, maximo=None):
    """Quais emendas recebem o estalo: uma a cada 6 a 8 segundos, na que cair
    mais perto.

    A primeira NUNCA entra -- ali ja esta o estalo de abertura, e os dois juntos
    viram uma borra so. Por isso quem chama passa `mapa[1:]`.

    Por tempo, e nao por contagem: contando emendas o resultado fica irregular,
    porque as cenas nao tem o mesmo tamanho. Quatro cenas curtas seguidas
    juntavam dois estalos quase colados, e uma cena longa deixava meio minuto
    sem nenhum."""
    minimo = config.GLITCH_MIN if minimo is None else minimo
    maximo = config.GLITCH_MAX if maximo is None else maximo
    escolhidas, ultima = [], None
    for t in sorted(emendas):
        if ultima is None:
            # a primeira so entra depois do intervalo minimo desde o comeco do
            # filme: colada na abertura ela desaparece dentro dela
            if t >= minimo:
                escolhidas.append(t)
                ultima = t
            continue
        if t - ultima >= minimo:
            escolhidas.append(t)
            ultima = t
    return escolhidas


def glitch(filme, destino, instantes, forca=None):
    """Um estalo curto e fraco em cada instante da lista.

    E a versao de emenda do efeito de abertura, e existe para marcar uma virada
    de assunto. Ali o efeito abre o video e pode ser violento; aqui ele acontece
    no meio da fala e nao pode roubar a atencao dela -- dura um terco do tempo e
    o zoom e um tranco, nao um crash.

    `instantes` sao os segundos do filme em que cada estalo comeca; quem escolhe
    quais e `emendas_do_glitch`.

    Como na abertura, os filtros de canal, croma e grao NAO aceitam expressao de
    tempo -- entao cada instante vira mais um punhado de copias com `enable`. O
    zoom, esse aceita, e a expressao soma os trancos de todos os instantes."""
    instantes = [t for t in (instantes or []) if t is not None and t >= 0]
    if not instantes or (forca if forca is not None else config.GLITCH_FORCA) <= 0:
        _roda(["ffmpeg", "-y", "-v", "error", "-i", str(filme),
               "-c", "copy", str(destino)])
        return destino
    f = config.GLITCH_FORCA if forca is None else forca
    d = config.GLITCH_DUR

    # o tranco de escala de todos os instantes somados numa expressao so
    trancos = "+".join(
        f"max(0,1-max(0,t-{t:.3f})/{d})^2*between(t,{t:.3f},{t + d:.3f})"
        for t in instantes)
    escala = f"1+{config.GLITCH_ZOOM * f:.3f}*({trancos})"

    partes = []
    for t in instantes:
        for h, v, a, b in config.GLITCH_CANAIS:
            partes.append(
                f"rgbashift=rh={int(round(h * f))}:bh={-int(round(h * f))}"
                + (f":rv={-int(round(v * f))}:bv={int(round(v * f))}" if v else "")
                + f":enable='between(t,{t + a:.3f},{t + b:.3f})'")
        for px, a, b in config.GLITCH_CROMA:
            partes.append(
                f"chromashift=cbh={int(round(px * f))}:crh={-int(round(px * f))}"
                f":enable='between(t,{t + a:.3f},{t + b:.3f})'")
        for px, a, b in config.GLITCH_GRAO:
            partes.append(
                f"noise=alls={int(round(px * f))}:allf=t+u"
                f":enable='between(t,{t + a:.3f},{t + b:.3f})'")

    _roda([
        "ffmpeg", "-y", "-v", "error", "-i", str(filme),
        "-vf",
        f"scale=w='iw*({escala})':h='ih*({escala})':eval=frame,"
        f"crop={config.W}:{config.H}," + ",".join(partes) + ",format=yuv420p",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "copy", "-movflags", "+faststart", str(destino)])
    return destino


def com_peca_animada(base, peca, destino, entra=0.0):
    """Poe uma peca de video com fundo transparente por cima do video, a partir
    de `entra` segundos.

    E a irma de com_overlay() para o letreiro que entra em movimento. A peca ja
    traz a propria duracao, entao aqui nao ha `dura`: quando ela acaba, o
    letreiro sai.

    As MESMAS duas regras de com_overlay valem, e pela mesma razao medida:
    nada de `-shortest`, que come quadros de video e deixa o audio inteiro; e
    `eof_action=pass`, para que os quadros da base sigam passando depois que a
    peca terminar."""
    d_peca = probe.dur(peca)
    saida = (f",fade=t=out:st={max(0.0, d_peca - 0.3):.3f}:d=0.3:alpha=1"
             if d_peca > 0.35 else "")
    _roda([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(base), "-i", str(peca),
        "-filter_complex",
        # o esmaecer da saida conta no relogio da PROPRIA peca, entao vem antes
        # do setpts. Depois dele, `st` estaria medindo a partir do inicio do
        # video de baixo e a saida cairia na hora errada.
        f"[1:v]format=rgba{saida},setpts=PTS-STARTPTS+{entra:.3f}/TB[p];"
        f"[0:v][p]overlay=0:0:eof_action=pass,format=yuv420p[v]",
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "copy", str(destino)])
    return destino


def aperta(caminho, destino, ini, fim, pausas=None, area=None):
    """Corta as pontas E comprime as pausas internas. Devolve (arquivo, quantas
    pausas foram comprimidas).

    So cortar as pontas deixa buraco no meio da fala. Pausa acima de PAUSA_MAX
    vira PAUSA_FICA, e e isso que da o ritmo sem pausa entre falas.

    `pausas` existe para quem ja as detectou nao pagar de novo pela deteccao,
    que e uma passada inteira do ffmpeg pelo audio. Quem chama assim tambem
    garante que o mapa de tempo e o corte olham EXATAMENTE a mesma lista -- se
    as duas divergirem, o letreiro entra na hora errada e nada acusa.

    `area` PODE E DEVE ser passado: com ele, o enquadramento vertical acontece
    JA AQUI, e os pedacos saem no tamanho final em vez de na resolucao da
    camera. MEDIDO num arquivo de celular de 4K: cortar tres segundos mantendo
    o tamanho da camera custou 6,7 segundos e 8,6 MB; cortando ja enquadrado,
    2,4 segundos e 2,8 MB. Como cada cena passa por aqui, e como o destino e
    1080x1920 de qualquer jeito, guardar 4K no meio do caminho e so custo.
    Quem passa `area` deve passar "" adiante, para o enquadramento nao ser
    refeito -- refazer nao estraga a imagem, mas paga de novo."""
    if pausas is None:
        pausas = fala.pausas_internas(caminho, ini, fim)
    vf = None if area is None else (
        f"{area}scale={config.W}:{config.H}"
        f":force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={config.W}:{config.H},setsar=1")
    if not pausas:
        _roda(["ffmpeg", "-y", "-v", "error",
               "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(caminho)]
              + _saida_padrao(destino, vf))
        return destino, 0

    partes = []
    for k, (a, b) in enumerate(tempo.marcas(ini, fim, pausas)):
        pedaco = f"{destino}.p{k}.mov"
        _roda(["ffmpeg", "-y", "-v", "error",
               "-ss", f"{ini + a:.3f}", "-to", f"{ini + b:.3f}", "-i", str(caminho)]
              + _saida_padrao(pedaco, vf))
        partes.append(pedaco)

    args = ["ffmpeg", "-y", "-v", "error"]
    for p in partes:
        args += ["-i", p]
    cadeia = "".join(f"[{i}:v][{i}:a]" for i in range(len(partes)))
    args += ["-filter_complex", f"{cadeia}concat=n={len(partes)}:v=1:a=1[v][a]",
             "-map", "[v]", "-map", "[a]"] + _saida_padrao(destino)
    _roda(args)
    for p in partes:
        Path(p).unlink(missing_ok=True)
    return destino, len(pausas)


def com_overlay(base, peca, destino, entra=0.0, dura=None):
    """Poe um PNG por cima do video, entrando em `entra` e saindo depois de
    `dura` segundos. `dura=None` deixa ate o fim.

    Este ffmpeg nao tem drawtext nem subtitles -- todo texto sobre imagem
    entra por aqui, como PNG desenhado pelo Pillow.

    NADA DE `-shortest` AQUI. Medido: com `-shortest` a saida perdia quadros de
    video enquanto o audio ficava inteiro -- 135 quadros viravam 133, e o filme
    dessincronizava 0,06s a 0,16s por cena, sem relacao com o tamanho da cena.
    Quem segura a duracao e `eof_action=pass` no overlay: quando a imagem acaba,
    os quadros da base seguem passando sem alteracao. Com isso a saida bate
    quadro a quadro com a base, mesmo se a imagem acabar antes.

    A imagem parada (segunda entrada) roda em loop, entra na mesma taxa de
    quadros do video e e cortada com `-t d_png` -- a duracao da base MAIS uma
    folga de 50ms, para o letreiro nao sumir um quadro antes do fim por erro de
    arredondamento (fps, decimais de ffprobe)."""
    d = probe.dur(base)
    d_png = d + 0.05
    saida_fade = (f",fade=t=out:st={entra + dura:.2f}:d=0.3:alpha=1"
                  if dura else "")
    _roda([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(base),
        "-loop", "1", "-framerate", str(config.FPS),
        "-t", f"{d_png:.3f}", "-i", str(peca),
        "-filter_complex",
        f"[1:v]format=rgba,fade=t=in:st={entra:.2f}:d=0.25:alpha=1{saida_fade}[p];"
        f"[0:v][p]overlay=0:0:eof_action=pass,format=yuv420p[v]",
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "copy", str(destino)])
    return destino
