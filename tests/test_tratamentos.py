from motor import arte, cenas, config, fala, probe, tratamentos
from tests import fixtures


def _cena(tmp_path, nome="a.mov", falas=((0.5, 1.0),), total=3.0):
    arq = fixtures.clipe_fala(tmp_path / nome, falas=list(falas), total=total)
    return cenas.Cena(n=1, trat="cheia", arquivo=arq, velocidade=1.0)


def test_tela_cheia_sai_no_formato_do_filme(tmp_path):
    c = _cena(tmp_path)
    saida = tratamentos.tela_cheia(c, tmp_path / "s1.mov")
    assert probe.dimensao(saida) == (1080, 1920)


def test_tela_cheia_corta_o_silencio_das_pontas(tmp_path):
    # fala de 1.0s no meio de um clipe de 4s: o segmento tem de ficar bem menor
    c = _cena(tmp_path, falas=((1.5, 1.0),), total=4.0)
    saida = tratamentos.tela_cheia(c, tmp_path / "s2.mov")
    assert probe.dur(saida) < 2.2


def test_tela_cheia_mantem_audio(tmp_path):
    c = _cena(tmp_path)
    saida = tratamentos.tela_cheia(c, tmp_path / "s3.mov")
    assert probe.tem_audio(saida) is True


def test_teto_encurta_a_cena(tmp_path):
    arq = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.5, 2.5)], total=4.0)
    sem = cenas.Cena(n=1, trat="cheia", arquivo=arq, velocidade=1.0)
    com = cenas.Cena(n=2, trat="cheia", arquivo=arq, velocidade=1.0, teto=1.0)
    d_sem = probe.dur(tratamentos.tela_cheia(sem, tmp_path / "s4.mov"))
    d_com = probe.dur(tratamentos.tela_cheia(com, tmp_path / "s5.mov"))
    assert d_com < d_sem
    assert abs(d_com - 1.0) < 0.15


def test_velocidade_encurta_na_proporcao(tmp_path):
    arq = fixtures.clipe_fala(tmp_path / "c.mov", falas=[(0.3, 2.0)], total=3.0)
    normal = cenas.Cena(n=1, trat="cheia", arquivo=arq, velocidade=1.0)
    rapida = cenas.Cena(n=2, trat="cheia", arquivo=arq, velocidade=1.15)
    d1 = probe.dur(tratamentos.tela_cheia(normal, tmp_path / "s6.mov"))
    d2 = probe.dur(tratamentos.tela_cheia(rapida, tmp_path / "s7.mov"))
    assert abs(d2 - d1 / 1.15) < 0.15


def test_segmento_audio_e_pcm_48k(tmp_path):
    """Regra 2 e 3 do docstring: audio dos segmentos fica sem compressao, em
    pcm_s16le, e a taxa de amostragem e sempre 48000 Hz."""
    c = _cena(tmp_path)
    saida = tratamentos.tela_cheia(c, tmp_path / "s8.mov")
    import subprocess
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_name,sample_rate", "-of", "csv=p=0", str(saida)],
        capture_output=True, text=True)
    codec, taxa = r.stdout.strip().split(",")
    assert codec == "pcm_s16le"
    assert int(taxa) == 48000


def test_segmento_preenche_o_quadro_sem_deformar(tmp_path):
    """Regra 3 do docstring: todo segmento sai EXATAMENTE 1080x1920, mesmo
    quando a fonte tem outra proporcao. Sem barra preta, sem distorcao."""
    paisagem = fixtures.clipe_fala(tmp_path / "paisagem.mov", falas=[(0.5, 1.0)],
                                    total=3.0, w=1920, h=1080)
    quatro_por_cinco = fixtures.clipe_fala(tmp_path / "4x5.mov", falas=[(0.5, 1.0)],
                                            total=3.0, w=1080, h=1350)

    c_paisagem = cenas.Cena(n=1, trat="cheia", arquivo=paisagem, velocidade=1.0)
    c_4x5 = cenas.Cena(n=2, trat="cheia", arquivo=quatro_por_cinco, velocidade=1.0)

    saida_paisagem = tratamentos.tela_cheia(c_paisagem, tmp_path / "s9.mov")
    saida_4x5 = tratamentos.tela_cheia(c_4x5, tmp_path / "s10.mov")

    assert probe.dimensao(saida_paisagem) == (1080, 1920)
    assert probe.dimensao(saida_4x5) == (1080, 1920)


def test_corte_cai_onde_fala_bordas_diz(tmp_path):
    """Pega o trap do -ss: se ele for parar depois do -i, o corte escorrega
    para o arquivo seguinte (ou nao corta nada) e o tom aparece la pelo meio
    do segmento de saida, nao no comeco. Mede a energia da SAIDA em janelas
    de 10ms, do jeito que motor/fala.py faz, e confere que o tom comeca perto
    do inicio do segmento (± RESPIRO_IN de folga), nao 2s adentro."""
    import array
    import subprocess

    arq = fixtures.clipe_fala(tmp_path / "tom.mov", falas=[(2.0, 1.0)], total=5.0)
    c = cenas.Cena(n=1, trat="cheia", arquivo=arq, velocidade=1.0)
    saida = tratamentos.tela_cheia(c, tmp_path / "s11.mov")

    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(saida), "-ac", "1", "-ar", "8000",
         "-f", "f32le", "-"],
        capture_output=True)
    amostras = array.array("f")
    amostras.frombytes(r.stdout[:len(r.stdout) - len(r.stdout) % 4])

    passo = 0.010
    n = int(8000 * passo)
    blocos = len(amostras) // n
    energias = []
    for i in range(blocos):
        fatia = amostras[i * n:(i + 1) * n]
        soma = sum(x * x for x in fatia)
        energias.append((soma / n) ** 0.5)

    topo = max(energias) if energias else 0.0
    limiar = topo * 0.3
    acesos = [i for i, v in enumerate(energias) if v > limiar]
    assert acesos, "nenhuma energia detectada na saida"
    inicio_tom = acesos[0] * passo
    assert inicio_tom < 0.3, (
        f"o tom comecou em {inicio_tom:.3f}s da saida, esperado perto do "
        f"inicio (o -ss pode ter escorregado para depois do -i)")


def _cena_split(tmp_path, topo_w, topo_h, ancora=0.0):
    take = fixtures.clipe_fala(tmp_path / f"t{topo_w}x{topo_h}.mov",
                               falas=[(0.4, 1.2)], total=3.0)
    broll = fixtures.clipe_mudo(tmp_path / f"b{topo_w}x{topo_h}.mp4",
                                total=3.0, w=topo_w, h=topo_h)
    return cenas.Cena(n=3, trat="split", arquivo=take, velocidade=1.0,
                      topo=cenas.Topo(arquivo=broll, ancora=ancora))


def test_split_sai_no_formato_do_filme(tmp_path):
    c = _cena_split(tmp_path, 1920, 1080)
    saida = tratamentos.split(c, tmp_path / "sp1.mov")
    assert probe.dimensao(saida) == (1080, 1920)


def test_split_mantem_o_audio_do_take(tmp_path):
    c = _cena_split(tmp_path, 1920, 1080)
    saida = tratamentos.split(c, tmp_path / "sp2.mov")
    assert probe.tem_audio(saida) is True


def test_material_deitado_nao_precisa_de_ancora():
    # 1920x1080 na janela 1080x807: a altura sobra inteira, o corte e na largura
    assert tratamentos.recorte_topo(1920, 1080, ancora=0.0) == \
           tratamentos.recorte_topo(1920, 1080, ancora=1.0)


def test_ancora_muda_o_corte_de_material_vertical():
    do_topo = tratamentos.recorte_topo(1080, 1920, ancora=0.0)
    do_meio = tratamentos.recorte_topo(1080, 1920, ancora=0.5)
    da_base = tratamentos.recorte_topo(1080, 1920, ancora=1.0)
    assert do_topo != do_meio != da_base


def test_ancora_zero_pega_o_topo_da_imagem():
    filtro = tratamentos.recorte_topo(1080, 1920, ancora=0.0)
    assert filtro.endswith(":0:0")


def test_ancora_um_pega_a_base_da_imagem():
    # 1080x1920 escalado para largura 1080 continua 1920 de altura;
    # a janela pede 807, entao o corte comeca em 1920-807 = 1113
    filtro = tratamentos.recorte_topo(1080, 1920, ancora=1.0)
    assert filtro.endswith(":0:1113")


def _pixel(caminho, x, y):
    """Le 1 pixel da SAIDA (o video ja montado) em (x, y), via crop + rawvideo.
    Prova que o filtro chegou de fato no quadro final, nao so na string do
    filtro. O crop pede 2x2 (nao 1x1): a saida e yuv420p, e o filtro de crop
    arredonda dimensao impar para baixo em formato com chroma subsampled --
    1x1 vira 0x0 e a leitura falha em silencio. So o primeiro pixel do 2x2
    interessa."""
    import subprocess
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(caminho), "-vf", f"crop=2:2:{x}:{y}",
         "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True)
    dado = r.stdout[:3]
    return tuple(dado) if len(dado) == 3 else (0, 0, 0)


def test_ancora_muda_o_pixel_de_verdade(tmp_path):
    """As comparacoes de string acima nao provam que o filtro chega inteiro
    no comando do ffmpeg. Aqui o material do topo e metade vermelha, metade
    azul (1080x1920, dividido ao meio); a ancora 0.0 tem de pegar o vermelho
    (topo da imagem), a ancora 1.0 tem de pegar o azul (base da imagem).
    Amostra o pixel em x=540, y=400 -- bem dentro da janela de cima, acima
    da divisoria em y=807."""
    import subprocess

    vert = tmp_path / "vert_vermelho_azul.mp4"
    r = subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-t", "3", "-i", "color=c=red:s=1080x960:r=30",
        "-f", "lavfi", "-t", "3", "-i", "color=c=blue:s=1080x960:r=30",
        "-filter_complex", "[0][1]vstack=inputs=2",
        "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", str(vert)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    take = fixtures.clipe_fala(tmp_path / "take_pixel.mov", falas=[(0.4, 1.2)], total=3.0)

    c_topo = cenas.Cena(n=3, trat="split", arquivo=take, velocidade=1.0,
                        topo=cenas.Topo(arquivo=vert, ancora=0.0))
    c_base = cenas.Cena(n=3, trat="split", arquivo=take, velocidade=1.0,
                        topo=cenas.Topo(arquivo=vert, ancora=1.0))

    saida_topo = tratamentos.split(c_topo, tmp_path / "sp_ancora_topo.mov")
    saida_base = tratamentos.split(c_base, tmp_path / "sp_ancora_base.mov")

    rt, gt, bt = _pixel(saida_topo, 540, 400)
    rb, gb, bb = _pixel(saida_base, 540, 400)

    assert rt > 150 and bt < 100, (
        f"ancora 0.0 devia sair avermelhada (topo da imagem), veio rgb=({rt},{gt},{bt})")
    assert bb > 150 and rb < 100, (
        f"ancora 1.0 devia sair azulada (base da imagem), veio rgb=({rb},{gb},{bb})")


def test_split_janela_de_baixo_sem_barra_preta(tmp_path):
    """A janela de baixo (o take) tem de preencher 1080 de largura por corte,
    nunca por padding -- senao sobra barra preta nas laterais. Amostra um
    pixel perto da borda esquerda (x=5) e outro perto da direita (x=1075),
    na metade da altura da janela de baixo (y = 807 + (1920-807)/2 = 1363),
    e confere que nenhum e preto puro."""
    c = _cena_split(tmp_path, 1920, 1080)
    saida = tratamentos.split(c, tmp_path / "sp3.mov")
    assert probe.dimensao(saida) == (1080, 1920)

    y_meio_baixo = config.DIVISORIA + (config.H - config.DIVISORIA) // 2
    esquerda = _pixel(saida, 5, y_meio_baixo)
    direita = _pixel(saida, 1075, y_meio_baixo)
    assert esquerda != (0, 0, 0), f"pixel esquerdo da janela de baixo saiu preto: {esquerda}"
    assert direita != (0, 0, 0), f"pixel direito da janela de baixo saiu preto: {direita}"


def _clipe_bandas_verticais(destino, cores, w=1920, h=1080, falas=((0.4, 1.2),), total=3.0):
    """Video 16:9 dividido em faixas verticais coloridas iguais (uma ao lado
    da outra), com audio de fala sintetica -- para provar de onde um crop
    horizontal pega o pixel."""
    import subprocess
    n = len(cores)
    faixa = w // n
    entradas = []
    for cor in cores:
        entradas += ["-f", "lavfi", "-t", f"{total}",
                     "-i", f"color=c={cor}:s={faixa}x{h}:r={config.FPS}"]
    hstack = "".join(f"[{i}:v]" for i in range(n)) + f"hstack=inputs={n}[v]"
    volume = "+".join(f"between(t,{ini},{ini + dur})" for ini, dur in falas) or "0"
    args = ["ffmpeg", "-y", "-v", "error"] + entradas + [
        "-f", "lavfi", "-t", f"{total}", "-i", f"sine=frequency=220:sample_rate={config.SR}",
        "-filter_complex", f"{hstack};[{n}:a]volume='{volume}':eval=frame[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "pcm_s16le", "-ar", str(config.SR), "-ac", "2",
        str(destino)]
    r = subprocess.run(args, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return destino


def test_split_recorta_o_centro_como_tela_cheia(tmp_path):
    """FIX 1: o crop da janela de baixo do split estava fixo em x=0 (canto
    esquerdo), enquanto tela_cheia (via enquadrar) deixa o ffmpeg centralizar
    por padrao -- os dois tratamentos enquadravam a mesma fonte de jeitos
    diferentes. Fonte 16:9 dividida em tres faixas verticais (vermelho|verde|
    azul); depois do scale (force_original_aspect_ratio=increase) o quadro
    fica mais largo que 1080, entao um crop centralizado tem de pegar a
    faixa do meio (verde) nos dois tratamentos -- um crop pela esquerda
    pegaria a faixa vermelha."""
    banda = _clipe_bandas_verticais(tmp_path / "bandas.mov", ["red", "green", "blue"])

    c_cheia = cenas.Cena(n=1, trat="cheia", arquivo=banda, velocidade=1.0)
    saida_cheia = tratamentos.tela_cheia(c_cheia, tmp_path / "cheia_bandas.mov")

    topo = fixtures.clipe_mudo(tmp_path / "topo_bandas.mp4", total=3.0, w=1920, h=1080)
    c_split = cenas.Cena(n=2, trat="split", arquivo=banda, velocidade=1.0,
                         topo=cenas.Topo(arquivo=topo, ancora=0.0))
    saida_split = tratamentos.split(c_split, tmp_path / "split_bandas.mov")

    r_c, g_c, b_c = _pixel(saida_cheia, config.W // 2, config.H // 2)
    assert g_c > 100 and r_c < 60 and b_c < 60, (
        f"tela_cheia: centro do quadro deveria sair verde (faixa do meio), "
        f"veio rgb=({r_c},{g_c},{b_c})")

    y_meio_baixo = config.DIVISORIA + (config.H - config.DIVISORIA) // 2
    r_s, g_s, b_s = _pixel(saida_split, config.W // 2, y_meio_baixo)
    assert g_s > 100 and r_s < 60 and b_s < 60, (
        f"split: centro da janela de baixo deveria sair verde (faixa do "
        f"meio), veio rgb=({r_s},{g_s},{b_s})")


def _clipe_bandas_horizontais(destino, cores, w=1080, h=1920, falas=((0.4, 1.2),), total=3.0):
    """Video vertical (9:16 exato, sem folga de escala) dividido em faixas
    HORIZONTAIS coloridas iguais (uma em cima da outra), com audio de fala
    sintetica -- para provar que o deslocamento vertical do crop
    (SPLIT_TETO) muda qual faixa cai na janela de baixo."""
    import subprocess
    n = len(cores)
    faixa = h // n
    entradas = []
    for cor in cores:
        entradas += ["-f", "lavfi", "-t", f"{total}",
                     "-i", f"color=c={cor}:s={w}x{faixa}:r={config.FPS}"]
    vstack = "".join(f"[{i}:v]" for i in range(n)) + f"vstack=inputs={n}[v]"
    volume = "+".join(f"between(t,{ini},{ini + dur})" for ini, dur in falas) or "0"
    args = ["ffmpeg", "-y", "-v", "error"] + entradas + [
        "-f", "lavfi", "-t", f"{total}", "-i", f"sine=frequency=220:sample_rate={config.SR}",
        "-filter_complex", f"{vstack};[{n}:a]volume='{volume}':eval=frame[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "pcm_s16le", "-ar", str(config.SR), "-ac", "2",
        str(destino)]
    r = subprocess.run(args, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return destino


def test_split_teto_seleciona_a_faixa_certa_na_janela_de_baixo(tmp_path):
    """FIX 3: SPLIT_TETO nao tinha nenhum teste que dependesse do seu valor --
    mudar de 380 para 0 fazia os 77 testes originais passarem do mesmo jeito.
    Fonte vertical 1080x1920 exata (sem folga de escala: scale com
    force_original_aspect_ratio=increase nao mexe em nada aqui) dividida em
    tres faixas horizontais iguais de 640px (vermelho|verde|azul, de cima
    para baixo). O pixel amostrado no meio da janela de baixo corresponde a
    linha 936 da fonte (556 do offset de amostragem + 380 do SPLIT_TETO
    calibrado) -- dentro da faixa do meio (verde, linhas 640-1280). Com
    SPLIT_TETO=0 cairia na linha 556, dentro da faixa de cima (vermelha)."""
    banda = _clipe_bandas_horizontais(tmp_path / "bandas_h.mov", ["red", "green", "blue"])
    topo = fixtures.clipe_mudo(tmp_path / "topo_h.mp4", total=3.0, w=1920, h=1080)
    c = cenas.Cena(n=4, trat="split", arquivo=banda, velocidade=1.0,
                   topo=cenas.Topo(arquivo=topo, ancora=0.0))
    saida = tratamentos.split(c, tmp_path / "split_bandas_h.mov")

    y_meio_baixo = config.DIVISORIA + (config.H - config.DIVISORIA) // 2
    r, g, b = _pixel(saida, config.W // 2, y_meio_baixo)
    assert g > 100 and r < 60 and b < 60, (
        f"janela de baixo deveria mostrar a faixa do meio (verde) com "
        f"SPLIT_TETO={config.SPLIT_TETO}, veio rgb=({r},{g},{b})")


def _crop_da_peca(peca):
    """O recorte exato onde a peca tem tinta.

    Chutar coordenada dilui o sinal: medido, um recorte 4x maior que a tinta
    baixou a diferenca de 72 para 15. O teste pergunta ao PNG onde ele
    desenhou, em vez de adivinhar."""
    from PIL import Image
    caixa = Image.open(peca).convert("RGBA").getchannel("A").getbbox()
    x0, y0, x1, y1 = caixa
    return f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}"


def _regiao(caminho, t, crop="crop=600:200:240:1050"):
    """Os pixels de uma regiao do quadro, em cinza, sem reduzir a uma media."""
    import subprocess
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(caminho),
         "-frames:v", "1", "-vf", f"{crop},scale=60:20",
         "-pix_fmt", "gray", "-f", "rawvideo", "-"], capture_output=True)
    return list(r.stdout[:1200])


def _quanto_mudou(caminho, t1, t2, crop="crop=600:200:240:1050"):
    """Diferenca media pixel a pixel entre dois instantes da mesma regiao.

    NAO usar brilho medio aqui. O letreiro tem contorno preto e preenchimento
    claro em area parecida, e a media cancela os dois: medido, o amarelo soma
    +82 de luz e o contorno subtrai 123, e a diferenca de brilho medio fica em
    5 de 255 — indistinguivel de ruido. Pixel a pixel o mesmo letreiro da 60."""
    a, b = _regiao(caminho, t1, crop), _regiao(caminho, t2, crop)
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def _brilho(caminho, t, crop="crop=600:200:240:1050"):
    """Brilho medio de uma regiao. Serve para comparar com um controle, nao
    para detectar letreiro — veja `_quanto_mudou`."""
    import subprocess
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(caminho),
         "-frames:v", "1", "-vf", f"{crop},scale=1:1",
         "-pix_fmt", "gray", "-f", "rawvideo", "-"], capture_output=True)
    return int(r.stdout[0]) if r.stdout else 0


def test_overlay_entra_no_instante_pedido(tmp_path):
    from motor import arte
    base = fixtures.clipe_fala(tmp_path / "base.mov", falas=[(0.2, 2.0)], total=3.0)
    peca = arte.letreiro("TESTE", None, tmp_path / "p.png", base=1200)
    saida = tratamentos.com_overlay(base, peca, tmp_path / "o.mov",
                                    entra=1.5, dura=None)
    assert _quanto_mudou(saida, 0.5, 2.5, _crop_da_peca(peca)) > 20, (
        "o letreiro nao mudou o quadro depois de entrar")


def test_overlay_nao_muda_formato_nem_audio(tmp_path):
    from motor import arte
    base = fixtures.clipe_fala(tmp_path / "b2.mov", falas=[(0.2, 1.0)], total=2.0)
    peca = arte.letreiro("X", None, tmp_path / "p2.png")
    saida = tratamentos.com_overlay(base, peca, tmp_path / "o2.mov", entra=0.0)
    assert probe.dimensao(saida) == (1080, 1920)
    assert probe.tem_audio(saida) is True
    assert abs(probe.dur(saida) - probe.dur(base)) < 0.10


def test_overlay_com_duracao_sai_do_quadro(tmp_path):
    from motor import arte
    base = fixtures.clipe_fala(tmp_path / "b3.mov", falas=[(0.2, 3.0)], total=4.0)
    peca = arte.letreiro("SOME", None, tmp_path / "p3.png", base=1200)
    saida = tratamentos.com_overlay(base, peca, tmp_path / "o3.mov",
                                    entra=0.5, dura=1.0)
    # mesmo limiar medido de test_overlay_entra_no_instante_pedido, mesma razao.
    assert _quanto_mudou(saida, 3.5, 1.0, _crop_da_peca(peca)) > 20, (
        "o letreiro nao saiu do quadro")


def test_overlay_duracao_nao_round_bate_com_a_base(tmp_path):
    """Trap H: a segunda entrada (PNG parado, -loop 1 -t d) e limitada por uma
    duracao `d` calculada a partir da base. Se `d` sair igual ou menor que a
    base por arredondamento, o -shortest corta a SAIDA inteira pela imagem, nao
    pela base. Base com duracao nao redonda (2.37s) para forcar o caso."""
    from motor import arte
    base = fixtures.clipe_fala(tmp_path / "hnr.mov", falas=[(0.2, 1.5)], total=2.37)
    peca = arte.letreiro("H", None, tmp_path / "ph.png")
    saida = tratamentos.com_overlay(base, peca, tmp_path / "oh.mov",
                                    entra=0.1, dura=None)
    d_base, d_saida = probe.dur(base), probe.dur(saida)
    assert abs(d_saida - d_base) < 0.05, (
        f"base={d_base:.3f}s saida={d_saida:.3f}s -- o -shortest cortou pela "
        f"imagem parada, nao pela base")


def _ffprobe_audio(caminho):
    import subprocess
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_name,sample_rate", "-of", "csv=p=0",
         str(caminho)], capture_output=True, text=True)
    codec, taxa = r.stdout.strip().split(",")
    return codec, int(taxa)


def test_overlay_audio_copiado_bit_a_bit(tmp_path):
    """Trap I: audio dos segmentos fica sem compressao ate a montagem final --
    com_overlay nao pode reencodar. Codec e taxa de amostragem da saida tem de
    bater exatamente com os da entrada (pcm_s16le, 48000 Hz)."""
    from motor import arte
    base = fixtures.clipe_fala(tmp_path / "bi.mov", falas=[(0.2, 1.0)], total=2.0)
    peca = arte.letreiro("I", None, tmp_path / "pi.png")
    saida = tratamentos.com_overlay(base, peca, tmp_path / "oi.mov", entra=0.0)

    codec_in, taxa_in = _ffprobe_audio(base)
    codec_out, taxa_out = _ffprobe_audio(saida)
    assert codec_in == "pcm_s16le" and taxa_in == 48000
    assert codec_out == codec_in, f"codec mudou: entrada={codec_in} saida={codec_out}"
    assert taxa_out == taxa_in, f"taxa mudou: entrada={taxa_in} saida={taxa_out}"


def test_overlay_duas_vezes_seguidas_sobrevive(tmp_path):
    """Trap J: uma cena pode levar um letreiro e depois uma legenda. Aplica
    com_overlay duas vezes no mesmo clipe, com PNGs em linhas diferentes
    (base=900 e base=1650, que nao se sobrepoem -- ver bbox medido), e confere
    que as DUAS regioes mudaram em relacao ao clipe original. Se a segunda
    chamada apagar a primeira, a funcao esta errada para o pipeline que a usa."""
    from motor import arte
    base = fixtures.clipe_fala(tmp_path / "bj.mov", falas=[(0.3, 2.0)], total=3.0)

    peca1 = arte.letreiro("UM", None, tmp_path / "pj1.png", base=900)
    passo1 = tratamentos.com_overlay(base, peca1, tmp_path / "oj1.mov", entra=0.0)

    peca2 = arte.letreiro("DOIS", None, tmp_path / "pj2.png", base=1650)
    passo2 = tratamentos.com_overlay(passo1, peca2, tmp_path / "oj2.mov", entra=0.0)

    # As janelas saem do bbox da PROPRIA peca, nao de coordenada anotada a
    # mao. Coordenada fixa envelhece: quando cada ficha de estilo ganhou fonte
    # propria, a mancha de tinta mudou de tamanho, a janela antiga passou a
    # pegar mais fundo que letra, e o sinal caiu de 5 para exatamente 3 --
    # reprovando um teste que media a coisa certa com a regua errada. E a mesma
    # armadilha ja anotada no limiar de _brilho: janela larga demais dilui.
    from PIL import Image

    def janela(caminho_png):
        x0, y0, x1, y1 = Image.open(caminho_png).convert("RGBA") \
            .getchannel("A").getbbox()
        return f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}"

    regiao_um = janela(peca1)
    regiao_dois = janela(peca2)
    t = 1.5

    diff_um = abs(_brilho(passo2, t, crop=regiao_um) - _brilho(base, t, crop=regiao_um))
    diff_dois = abs(_brilho(passo2, t, crop=regiao_dois) - _brilho(base, t, crop=regiao_dois))

    assert diff_um > 3, f"a primeira sobreposicao (UM) sumiu, diff={diff_um}"
    assert diff_dois > 3, f"a segunda sobreposicao (DOIS) nao apareceu, diff={diff_dois}"


def _media_rgb(caminho, t, cx, cy, tam=40):
    """Media de cor RGB de um quadrado tam x tam centrado em (cx, cy)."""
    import subprocess
    meio = tam // 2
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(caminho),
         "-frames:v", "1", "-vf",
         f"crop={tam}:{tam}:{cx - meio}:{cy - meio},scale=1:1",
         "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], capture_output=True)
    dado = r.stdout[:3]
    return tuple(dado) if len(dado) == 3 else (0, 0, 0)


def test_overlay_transparente_nao_muda_a_imagem(tmp_path):
    """Trap K: um PNG 1080x1920 totalmente transparente (alpha 0 em todo
    pixel) nao pode mudar a imagem nem de leve -- prova que o overlay nao
    desloca cor nem aplica blend por conta propria. Base em quatro quadrantes
    de cor bem diferentes, pra pegar qualquer desvio em qualquer regiao."""
    import subprocess
    from PIL import Image

    base = tmp_path / "bk.mov"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-t", "2", "-i", "color=c=red:s=540x960",
        "-f", "lavfi", "-t", "2", "-i", "color=c=green:s=540x960",
        "-f", "lavfi", "-t", "2", "-i", "color=c=blue:s=540x960",
        "-f", "lavfi", "-t", "2", "-i", "color=c=yellow:s=540x960",
        "-filter_complex",
        "[0][1]hstack=inputs=2[cima];[2][3]hstack=inputs=2[baixo];"
        "[cima][baixo]vstack=inputs=2,format=yuv420p[v]",
        "-map", "[v]",
        "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast",
        str(base)], capture_output=True, text=True, check=True)

    transparente = tmp_path / "vazio.png"
    Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)).save(transparente)

    saida = tratamentos.com_overlay(base, transparente, tmp_path / "ok.mov",
                                    entra=0.0, dura=None)

    pontos = [(270, 480), (810, 480), (270, 1440), (810, 1440), (540, 960)]
    for cx, cy in pontos:
        antes = _media_rgb(base, 0.5, cx, cy)
        depois = _media_rgb(saida, 0.5, cx, cy)
        for canal_antes, canal_depois in zip(antes, depois):
            assert abs(canal_antes - canal_depois) < 3, (
                f"ponto ({cx},{cy}) mudou: antes={antes} depois={depois}")


def _streams(caminho):
    """(duracao do video, n de quadros, duracao do audio)."""
    import subprocess
    def _q(fluxo, campos):
        return subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", fluxo,
             "-show_entries", f"stream={campos}", "-of", "csv=p=0",
             str(caminho)], capture_output=True, text=True).stdout.strip()
    dv, nf = (_q("v:0", "duration,nb_frames") + ",0").split(",")[:2]
    da = (_q("a:0", "duration") or "0").split(",")[0]
    return float(dv), int(nf or 0), float(da or 0)


def test_overlay_nao_perde_quadro_em_nenhuma_duracao(tmp_path):
    """O DEFEITO QUE ISTO GUARDA: com `-shortest`, o overlay devolvia menos
    quadros de video que a base enquanto o audio ficava inteiro. Medido: 135
    quadros viravam 133, e a folga variava de 0,057s a 0,157s sem relacao com
    o tamanho da cena — a cena mais LONGA era a pior. Um filme de dez cenas com
    letreiro acumulava mais de um segundo de descompasso entre boca e som."""
    peca = arte.letreiro("TESTE", None, tmp_path / "p.png", base=1400)
    for total in (1.3, 2.4, 4.5):
        base = fixtures.clipe_fala(tmp_path / f"b{total}.mov",
                                   falas=[(0.15, total - 0.15)], total=total)
        dv_b, nf_b, da_b = _streams(base)
        for rot, dura in (("com fim", 0.8), ("ate o fim", None)):
            saida = tratamentos.com_overlay(
                base, peca, tmp_path / f"s{total}-{dura}.mov",
                entra=0.2, dura=dura)
            dv_s, nf_s, da_s = _streams(saida)
            assert nf_s == nf_b, (
                f"{total}s, letreiro {rot}: sobraram {nf_b - nf_s} quadros a "
                f"menos que a base ({nf_s} contra {nf_b})")
            assert abs(dv_s - da_s) <= abs(dv_b - da_b) + 0.005, (
                f"{total}s, letreiro {rot}: o overlay AFASTOU video e audio "
                f"(base {dv_b - da_b:+.3f}s, saida {dv_s - da_s:+.3f}s)")


def test_overlay_sobrevive_a_peca_mais_curta_que_a_base(tmp_path, monkeypatch):
    """Se por qualquer motivo a imagem acabar antes do video, o filme nao pode
    encolher junto. Quem garante isso e `eof_action=pass`.

    Para forcar o caso, mentimos a duracao da base: `com_overlay` corta a
    imagem em `duracao + 0.05`, entao uma duracao menor produz uma imagem que
    acaba no meio do filme."""
    from motor import probe as mod_probe
    base = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.2, 3.3)], total=3.5)
    peca = arte.letreiro("CURTA", None, tmp_path / "p.png", base=1400)
    verdadeira = mod_probe.dur(base)

    monkeypatch.setattr("motor.tratamentos.probe.dur", lambda _: 1.0)
    saida = tratamentos.com_overlay(base, peca, tmp_path / "s.mov")
    monkeypatch.undo()

    assert abs(mod_probe.dur(saida) - verdadeira) < 0.02, (
        "a imagem acabou antes e levou o filme junto")


# ---------------------------------------------------------------------------
# Trocar o fundo verde
# ---------------------------------------------------------------------------

def _fracoes(caminho):
    """(quanto do quadro e azul, quanto e a cor da figura, quanto sobrou de
    verde). Medir cor por cor e o unico jeito de saber se o corte pegou o pano
    e SO o pano."""
    from motor import imagem
    azul = figura = verde = total = 0
    for q in imagem._quadros_rgb(caminho, lado=64):
        for i in range(0, len(q) - 2, 3):
            r, g, b = q[i], q[i + 1], q[i + 2]
            total += 1
            if b > 120 and b > r * 1.6 and b > g * 1.6:
                azul += 1
            if 90 < r < 190 and 40 < g < 130 and b < 90 and r > b * 1.5:
                figura += 1
            if imagem._e_verde(r, g, b):
                verde += 1
    t = max(1, total)
    return azul / t, figura / t, verde / t


def test_trocar_fundo_poe_a_imagem_nova_e_mantem_a_pessoa(tmp_path):
    from motor import imagem
    take = fixtures.clipe_croma(tmp_path / "croma.mov")
    _, figura_antes, verde_antes = _fracoes(take)
    assert verde_antes > 0.3, "a fixture nao produziu pano verde suficiente"

    saida = tratamentos.trocar_fundo(
        take, tmp_path / "trocado.mov", "#1030c0",
        cor=imagem.cor_do_fundo_verde(take))
    azul, figura, verde = _fracoes(saida)

    assert verde < 0.02, f"sobrou pano verde no quadro ({verde * 100:.1f}%)"
    assert azul > 0.5, f"o fundo novo nao entrou ({azul * 100:.1f}%)"
    assert abs(figura - figura_antes) < 0.02, (
        f"a pessoa foi comida pelo corte: era {figura_antes * 100:.1f}% do "
        f"quadro e ficou {figura * 100:.1f}%")


def test_trocar_fundo_nao_muda_a_duracao(tmp_path):
    """A armadilha do `-shortest`, que come quadros de video e deixa o audio
    inteiro. Aqui quem fixa a duracao e o corte na saida."""
    from motor import imagem
    take = fixtures.clipe_croma(tmp_path / "c2.mov", total=2.0)
    saida = tratamentos.trocar_fundo(
        take, tmp_path / "t2.mov", "#101010",
        cor=imagem.cor_do_fundo_verde(take))
    assert abs(probe.dur(saida) - probe.dur(take)) < 0.10, (
        f"a duracao mudou: {probe.dur(take):.3f}s virou {probe.dur(saida):.3f}s")


def test_a_tolerancia_do_corte_esta_provada_dos_dois_lados(tmp_path):
    """Frouxa demais come a pessoa; apertada demais deixa pano por trocar.
    MEDIDO: a janela boa vai de 0,04 a 0,18."""
    from motor import config, imagem
    take = fixtures.clipe_croma(tmp_path / "c3.mov")
    cor = imagem.cor_do_fundo_verde(take)
    _, figura_antes, _ = _fracoes(take)

    frouxa = tratamentos.trocar_fundo(take, tmp_path / "frouxa.mov", "#1030c0",
                                      cor=cor, tolerancia=0.40)
    _, figura_frouxa, _ = _fracoes(frouxa)
    assert figura_frouxa < figura_antes - 0.05, (
        "tolerancia de 0,40 deveria comer a pessoa -- se nao come, o limite "
        "de cima nao esta onde a medicao disse")

    escolhida = tratamentos.trocar_fundo(take, tmp_path / "boa.mov", "#1030c0",
                                         cor=cor)
    azul_boa, figura_boa, verde_boa = _fracoes(escolhida)
    assert verde_boa < 0.02 and abs(figura_boa - figura_antes) < 0.02, (
        f"a tolerancia escolhida ({config.VERDE_TOLERANCIA}) nao esta na "
        f"janela boa")

    # O outro lado. O que sobra de pano nao volta como verde puro -- o corte
    # suave e o despill deixam um cinza esverdeado que a leitura de verde nao
    # pega. Quem denuncia e o fundo novo, que cobre menos do quadro do que
    # deveria. MEDIDO: com 0,002 o fundo novo cobriu 37% onde deveria cobrir 67.
    apertada = tratamentos.trocar_fundo(take, tmp_path / "apertada.mov",
                                        "#1030c0", cor=cor, tolerancia=0.002)
    azul_apertada, _, _ = _fracoes(apertada)
    assert azul_apertada < azul_boa - 0.10, (
        f"tolerancia de 0,002 deveria deixar muito pano por trocar: o fundo "
        f"novo cobriu {azul_apertada * 100:.0f}% contra {azul_boa * 100:.0f}% "
        f"com a tolerancia escolhida")


def test_trocar_fundo_por_uma_imagem(tmp_path):
    from PIL import Image
    from motor import imagem
    arte = tmp_path / "fundo.png"
    Image.new("RGB", (1080, 1920), (16, 48, 192)).save(arte)
    take = fixtures.clipe_croma(tmp_path / "c4.mov")
    saida = tratamentos.trocar_fundo(take, tmp_path / "t4.mov", arte,
                                     cor=imagem.cor_do_fundo_verde(take))
    azul, _, verde = _fracoes(saida)
    assert azul > 0.5 and verde < 0.02


def test_a_peca_animada_nao_muda_a_duracao_do_video(tmp_path):
    """A mesma armadilha do `-shortest` de com_overlay(), no caminho novo. Se
    a peca animada encurtar o video, o filme dessincroniza a cada cena e o
    erro se acumula ate o fim."""
    from motor import arte
    base = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.2, 2.0)], total=3.0)
    peca = arte.letreiro_animado("ANIMADO", None, tmp_path / "p.mov", dur=1.5)
    saida = tratamentos.com_peca_animada(base, peca, tmp_path / "o.mov",
                                         entra=0.5)
    assert abs(probe.dur(saida) - probe.dur(base)) < 0.08, (
        f"a duracao mudou: {probe.dur(base):.3f}s virou {probe.dur(saida):.3f}s")


def test_a_peca_animada_entra_na_hora_pedida(tmp_path):
    """`entra` conta no relogio do video de baixo. Se o deslocamento no tempo
    errar, o letreiro aparece cedo ou tarde -- e a coordenada de tempo inteira
    perde o sentido."""
    from PIL import Image
    from motor import arte
    base = fixtures.clipe_fala(tmp_path / "b2.mov", falas=[(0.2, 2.5)], total=3.5)
    peca = arte.letreiro_animado("TARDE", None, tmp_path / "p2.mov", dur=1.0,
                                 base=1300)
    saida = tratamentos.com_peca_animada(base, peca, tmp_path / "o2.mov",
                                         entra=1.5)

    ref = arte.letreiro("TARDE", None, tmp_path / "ref.png", base=1300)
    x0, y0, x1, y1 = Image.open(ref).convert("RGBA").getchannel("A").getbbox()
    crop = f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}"

    def regiao(t):
        import subprocess
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(saida),
             "-frames:v", "1", "-vf", f"{crop},scale=60:20",
             "-pix_fmt", "gray", "-f", "rawvideo", "-"], capture_output=True)
        return list(r.stdout[:1200])

    def dif(a, b):
        return sum(abs(x - y) for x, y in zip(a, b)) / max(1, len(a))

    limpo = regiao(0.2)
    assert dif(limpo, regiao(1.2)) < 20, (
        "o letreiro ja aparece antes da hora pedida")
    assert dif(limpo, regiao(2.2)) > 20, (
        "o letreiro nao apareceu depois da hora pedida")


def test_o_corte_ja_entrega_o_tamanho_final_quando_recebe_a_area(tmp_path):
    """O defeito que isto impede: guardar 4K nos arquivos de passagem, para
    escalar tudo para 1080x1920 no passo seguinte.

    MEDIDO num arquivo de celular de 4K: cortar tres segundos mantendo o
    tamanho da camera custou 6,7 segundos e 8,6 MB; cortando ja enquadrado, 2,4
    segundos e 2,8 MB. Numa montagem de onze cenas isso foi a diferenca entre
    minutos e segundos."""
    grande = fixtures.clipe_fala(tmp_path / "g4k.mov", falas=[(0.3, 1.2)],
                                 total=2.5, w=1440, h=2560)
    assert probe.dimensao(grande) == (1440, 2560)

    ini, fim = fala.bordas(grande)
    enquadrado = tratamentos.aperta(grande, tmp_path / "e.mov", ini, fim,
                                    area="")[0]
    assert probe.dimensao(enquadrado) == (config.W, config.H), (
        "o corte devolveu a resolucao da camera; o enquadramento nao entrou")


def test_sem_a_area_o_corte_preserva_a_resolucao(tmp_path):
    """Quem chama sem `area` continua recebendo o que sempre recebeu -- e o que
    mantem `aperta` util fora da montagem."""
    grande = fixtures.clipe_fala(tmp_path / "g2.mov", falas=[(0.3, 1.2)],
                                 total=2.5, w=720, h=1280)
    ini, fim = fala.bordas(grande)
    igual = tratamentos.aperta(grande, tmp_path / "i.mov", ini, fim)[0]
    assert probe.dimensao(igual) == (720, 1280)


# ---------------------------------------------------------------------------
# O estalo de abertura
# ---------------------------------------------------------------------------

def _clipe_colorido(destino, total=2.5, escuro=True):
    """Um clipe com COR e DETALHE, e escuro.

    O clipe cinza uniforme de `fixtures` nao serve aqui por duas razoes
    medidas: deslocar os canais de cor numa imagem onde R=G=B nao muda nada
    visivel, e sobre um cinza claro o clarao satura em 243 e a forca deixa de
    ser medivel."""
    import subprocess
    escala = "0.25" if escuro else "1.0"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-t", str(total), "-i", "testsrc2=s=1080x1920:r=30",
         "-f", "lavfi", "-t", str(total),
         "-i", "sine=frequency=220:sample_rate=48000",
         "-vf", f"eq=brightness=-{escala}",
         "-c:v", "libx264", "-crf", "20", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-ar", "48000",
         str(destino)], check=True)
    return destino


def _brilhos(caminho, quantos=8):
    """O brilho medio dos primeiros quadros, LIDOS EM SEQUENCIA.

    Sem `-ss`, de proposito: buscar um instante perto de zero devolve o quadro
    que o ffmpeg achar, e nao o primeiro. Medindo assim, dois videos com
    claroes bem diferentes davam exatamente o mesmo numero -- o efeito
    funcionava e o teste dizia que nao."""
    import subprocess
    lado = 32
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(caminho),
         "-frames:v", str(quantos), "-vf", f"scale={lado}:{lado},format=gray",
         "-f", "rawvideo", "-"], capture_output=True)
    n = lado * lado
    d = r.stdout
    return [sum(d[i * n:(i + 1) * n]) / n for i in range(len(d) // n)]


def _clipe_cinza_com_bordas(destino, total=2.0):
    """Padrao NITIDO e SEM COR: R=G=B em todo pixel.

    Assim qualquer diferenca entre os canais so pode ter vindo do efeito. Num
    clipe colorido a medida nao serve: a diferenca natural entre vermelho e azul
    da propria imagem e maior que a do deslocamento, e muda sozinha ao longo do
    video -- medido, deu 61 no comeco e 120 no fim, sem efeito nenhum ali."""
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", str(total),
         "-i", "testsrc2=s=1080x1920:r=30",
         "-f", "lavfi", "-t", str(total),
         "-i", "sine=frequency=220:sample_rate=48000",
         "-vf", "format=gray,format=yuv420p,eq=brightness=-0.25",
         "-c:v", "libx264", "-crf", "20", "-preset", "ultrafast",
         "-c:a", "pcm_s16le", "-ar", "48000", str(destino)], check=True)
    return destino


def _quadros_cinza(caminho, quantos=8, lado=64):
    import subprocess
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(caminho),
         "-frames:v", str(quantos), "-vf", f"scale={lado}:{lado},format=gray",
         "-f", "rawvideo", "-"], capture_output=True)
    n = lado * lado
    return [r.stdout[i * n:(i + 1) * n] for i in range(len(r.stdout) // n)], lado


def _grao(caminho, quadro=0):
    """Quanto a imagem chia: a diferenca media entre pixels VIZINHOS.

    Grao e alta frequencia -- muda de um pixel para o outro. Brilho e contraste
    nao mexem nisso, entao a medida isola o chuvisco."""
    quadros, lado = _quadros_cinza(caminho, quantos=quadro + 1)
    if len(quadros) <= quadro:
        return 0.0
    q = quadros[quadro]
    difs = [abs(q[i] - q[i + 1]) for i in range(len(q) - 1) if (i + 1) % lado]
    return sum(difs) / max(1, len(difs))


def _cor_fora_de_registro(caminho, t):
    """Quanto os canais vermelho e azul estao deslocados um do outro.

    A separacao de cor aparece como diferenca entre os canais na MESMA posicao:
    onde a imagem e cinza, ela deixa de ser."""
    import subprocess
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(caminho),
         "-frames:v", "1", "-vf", "scale=64:114,format=rgb24",
         "-f", "rawvideo", "-"], capture_output=True)
    b = r.stdout
    if len(b) < 300:
        return 0.0
    return sum(abs(b[i] - b[i + 2]) for i in range(0, len(b) - 2, 3)) \
        / max(1, len(b) // 3)






def test_a_abertura_nao_muda_duracao_nem_tamanho(tmp_path):
    """O estalo entra no filme pronto. Se mexesse na duracao, o mapa de tempo e
    a legenda passariam a apontar para o lugar errado."""
    base = fixtures.clipe_fala(tmp_path / "b3.mov", falas=[(0.2, 2.0)],
                               total=2.5)
    com = tratamentos.abertura(base, tmp_path / "a3.mp4")
    assert abs(probe.dur(com) - probe.dur(base)) < 0.10
    assert probe.dimensao(com) == probe.dimensao(base)


def test_a_abertura_desligada_nao_mexe_na_imagem(tmp_path):
    base = _clipe_colorido(tmp_path / "b4.mov", total=2.0)
    com = tratamentos.abertura(base, tmp_path / "a4.mp4", forca=0)
    assert abs(_brilhos(com)[0] - _brilhos(base)[0]) < 3



def test_a_abertura_guarda_o_som(tmp_path):
    base = fixtures.clipe_fala(tmp_path / "b6.mov", falas=[(0.2, 1.5)],
                               total=2.0)
    com = tratamentos.abertura(base, tmp_path / "a6.mp4")
    assert probe.tem_audio(com) is True


# ---------------------------------------------------------------------------
# O estalo de abertura
#
# As medidas aqui usam um clipe de REFERENCIA: fundo escuro liso com um
# quadrado branco de 200px no centro. Assim o zoom vira um numero (a largura do
# quadrado) e o grao vira outro (a variacao no fundo, que deveria ser lisa).
#
# As primeiras versoes destes testes mediam sobre `testsrc2` e sobre o clipe
# cinza das fixtures, e nao serviam: num padrao cheio de bordas o grao proprio
# da imagem e maior que o do efeito, e reduzindo o quadro para 64x64 antes de
# medir o grao ele desaparece na media.
# ---------------------------------------------------------------------------

def _clipe_de_referencia(destino, total=2.0):
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-t", str(total),
         "-i", "color=c=0x202020:s=1080x1920:r=30",
         "-f", "lavfi", "-t", str(total),
         "-i", "sine=frequency=220:sample_rate=48000",
         "-vf", "drawbox=x=440:y=860:w=200:h=200:c=white@1:t=fill",
         "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-ar", "48000",
         str(destino)], check=True)
    return destino


def _largura_do_alvo(caminho, quadro):
    """Quantas colunas do meio da tela estao claras. Com o zoom, o quadrado de
    200px aparece maior."""
    import subprocess
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(caminho),
         "-frames:v", str(quadro + 1), "-vf", "crop=1080:2:0:960,format=gray",
         "-f", "rawvideo", "-"], capture_output=True)
    n = 1080 * 2
    q = r.stdout[quadro * n:(quadro + 1) * n][:1080]
    return sum(1 for p in q if p > 140)


def _grao_no_fundo(caminho, quadro):
    """A variacao entre pixels vizinhos num pedaco do fundo, na RESOLUCAO
    ORIGINAL. O fundo e liso, entao tudo o que variar ali e chuvisco."""
    import subprocess
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(caminho),
         "-frames:v", str(quadro + 1), "-vf", "crop=120:120:60:200,format=gray",
         "-f", "rawvideo", "-"], capture_output=True)
    n = 120 * 120
    q = r.stdout[quadro * n:(quadro + 1) * n]
    if len(q) < n:
        return 0.0
    difs = [abs(q[i] - q[i + 1]) for i in range(len(q) - 1) if (i + 1) % 120]
    return sum(difs) / max(1, len(difs))


def test_o_crash_zoom_entra_muito_ampliado_e_desaba(tmp_path):
    """Crash zoom OUT: a imagem entra mais que o dobro do tamanho e desaba para
    o normal em menos de meio segundo. MEDIDO no clipe de referencia: o
    quadrado de 200px aparece com 480 no primeiro quadro e volta a 200 no
    nono."""
    base = _clipe_de_referencia(tmp_path / "ref.mov")
    com = tratamentos.abertura(base, tmp_path / "ref-com.mp4")
    assert _largura_do_alvo(base, 0) == 200, "a fixture nao esta como esperado"
    assert _largura_do_alvo(com, 0) > 380, (
        f"o primeiro quadro entrou com {_largura_do_alvo(com, 0)}px de alvo, e "
        f"deveria passar de 380 — nao houve crash")
    assert abs(_largura_do_alvo(com, 14) - 200) <= 8, (
        f"meio segundo depois o alvo esta em {_largura_do_alvo(com, 14)}px: o "
        f"zoom nao desabou")


def test_a_abertura_poe_grao_e_ele_some(tmp_path):
    base = _clipe_de_referencia(tmp_path / "g.mov")
    com = tratamentos.abertura(base, tmp_path / "g-com.mp4")
    assert _grao_no_fundo(base, 0) < 1.0, "a fixture deveria ter fundo liso"
    assert _grao_no_fundo(com, 0) > 8, (
        f"quase nao ha grao no comeco: {_grao_no_fundo(com, 0):.1f}")
    assert _grao_no_fundo(com, 14) < 2, (
        f"o grao nao sumiu: {_grao_no_fundo(com, 14):.1f} no quadro 14")


def test_a_abertura_nao_da_clarao_branco(tmp_path):
    """Existiu numa versao e foi tirado: somar luz por cima de uma imagem que
    ja esta se desmontando lava tudo, e o pouco que ha para ver some. O grao
    ainda mexe um pouco no brilho medio, e a folga aqui e para ele."""
    base = _clipe_de_referencia(tmp_path / "c.mov")
    com = tratamentos.abertura(base, tmp_path / "c-com.mp4")
    antes, depois = _brilhos(base)[0], _brilhos(com)[0]
    assert depois < antes + 45, (
        f"o primeiro quadro clareou de {antes:.0f} para {depois:.0f}: voltou o "
        f"clarao")


def test_a_abertura_separa_as_cores_e_depois_junta(tmp_path):
    base = _clipe_cinza_com_bordas(tmp_path / "b2.mov")
    com = tratamentos.abertura(base, tmp_path / "a2.mp4")
    assert _cor_fora_de_registro(base, 0.0) < 3, (
        "a fixture nao esta em cinza: a medida nao vale")
    cedo = _cor_fora_de_registro(com, 0.0)
    tarde = _cor_fora_de_registro(com, 1.5)
    assert cedo > tarde + 3, (
        f"as cores nao se separaram no comeco (cedo={cedo:.1f}, "
        f"tarde={tarde:.1f})")


def test_a_forca_regula_o_estalo(tmp_path):
    """Medida pelo GRAO e pelo ZOOM, e nao pelo brilho: sem clarao, o brilho do
    primeiro quadro nao diz mais nada sobre a forca."""
    base = _clipe_de_referencia(tmp_path / "f.mov")
    # nomes que diferem SO por maiuscula sao o mesmo arquivo neste Mac
    fraco = tratamentos.abertura(base, tmp_path / "fraco.mp4", forca=0.3)
    forte = tratamentos.abertura(base, tmp_path / "forte.mp4", forca=1.0)
    assert _grao_no_fundo(forte, 0) > _grao_no_fundo(fraco, 0) + 3, (
        f"a forca nao mudou o grao: fraco {_grao_no_fundo(fraco, 0):.1f}, "
        f"forte {_grao_no_fundo(forte, 0):.1f}")
    assert _largura_do_alvo(forte, 0) > _largura_do_alvo(fraco, 0) + 40, (
        "a forca nao mudou o tamanho do crash")


# ---------------------------------------------------------------------------
# O glitch das emendas: a versao curta e fraca, no meio do filme
# ---------------------------------------------------------------------------

def test_o_glitch_acontece_so_nos_instantes_pedidos(tmp_path):
    """No meio do filme o efeito marca uma virada de assunto. Fora dos
    instantes escolhidos a imagem tem de estar limpa -- senao ele deixa de ser
    marcacao e vira ruido no video inteiro."""
    base = _clipe_de_referencia(tmp_path / "gl.mov", total=3.0)
    com = tratamentos.glitch(base, tmp_path / "gl-com.mp4", [1.0])
    limpo_antes = _grao_no_fundo(com, 20)     # ~0,67s
    no_estalo = _grao_no_fundo(com, 31)       # ~1,03s
    limpo_depois = _grao_no_fundo(com, 45)    # ~1,50s
    assert no_estalo > 6, f"nao ha estalo em 1,0s: {no_estalo:.1f}"
    assert limpo_antes < 2, f"ha ruido antes da hora: {limpo_antes:.1f}"
    assert limpo_depois < 2, f"o estalo nao acabou: {limpo_depois:.1f}"


def test_o_glitch_e_mais_fraco_que_a_abertura(tmp_path):
    """Ali o efeito abre o video e pode ser violento; aqui ele acontece no meio
    da fala e nao pode roubar a atencao dela."""
    base = _clipe_de_referencia(tmp_path / "cmp.mov")
    forte = tratamentos.abertura(base, tmp_path / "cmp-abre.mp4")
    fraco = tratamentos.glitch(base, tmp_path / "cmp-gl.mp4", [0.0])
    assert _largura_do_alvo(fraco, 0) < _largura_do_alvo(forte, 0) - 100, (
        "o tranco de escala do glitch ficou tao grande quanto o crash da "
        "abertura")
    assert _grao_no_fundo(fraco, 0) < _grao_no_fundo(forte, 0), (
        "o grao do glitch nao e mais fraco que o da abertura")


def test_o_glitch_em_varios_instantes(tmp_path):
    base = _clipe_de_referencia(tmp_path / "v.mov", total=3.0)
    com = tratamentos.glitch(base, tmp_path / "v-com.mp4", [0.5, 1.5])
    assert _grao_no_fundo(com, 16) > 6, "faltou o estalo de 0,5s"
    assert _grao_no_fundo(com, 46) > 6, "faltou o estalo de 1,5s"
    assert _grao_no_fundo(com, 31) < 2, "ha ruido entre os dois estalos"


def test_sem_instante_nenhum_a_imagem_nao_muda(tmp_path):
    base = _clipe_de_referencia(tmp_path / "n.mov")
    com = tratamentos.glitch(base, tmp_path / "n-com.mp4", [])
    assert _grao_no_fundo(com, 0) < 1.0
    assert _largura_do_alvo(com, 0) == _largura_do_alvo(base, 0)


def test_o_glitch_nao_muda_duracao_nem_som(tmp_path):
    base = _clipe_de_referencia(tmp_path / "d.mov")
    com = tratamentos.glitch(base, tmp_path / "d-com.mp4", [0.5])
    assert abs(probe.dur(com) - probe.dur(base)) < 0.10
    assert probe.tem_audio(com) is True
    assert probe.dimensao(com) == probe.dimensao(base)


def test_a_cadencia_do_glitch_e_por_tempo(tmp_path):
    """Uma a cada 6 a 8 segundos, na emenda que cair mais perto.

    Contando emendas o resultado ficava irregular, porque as cenas nao tem o
    mesmo tamanho: quatro curtas seguidas juntavam dois estalos quase colados,
    e uma longa deixava meio minuto sem nenhum."""
    emendas = [2.5, 8.0, 10.7, 12.8, 16.4, 23.2, 25.8, 28.8, 30.9, 34.6]
    escolhidas = tratamentos.emendas_do_glitch(emendas)
    assert escolhidas, "nenhuma emenda escolhida"
    assert all(t in emendas for t in escolhidas), (
        "escolheu um instante que nao e emenda: o estalo tem de bater no corte")
    for a, b in zip(escolhidas, escolhidas[1:]):
        assert b - a >= config.GLITCH_MIN, (
            f"dois estalos a {b - a:.1f}s um do outro, e o minimo e "
            f"{config.GLITCH_MIN}")


def test_o_glitch_nunca_pega_a_primeira_emenda(tmp_path):
    """Ali ja esta o estalo de abertura, e os dois juntos viram uma borra so."""
    escolhidas = tratamentos.emendas_do_glitch([1.2, 2.0, 9.0, 17.0])
    assert 1.2 not in escolhidas and 2.0 not in escolhidas, (
        "escolheu uma emenda dentro dos primeiros segundos")


def test_sem_emenda_longe_o_bastante_nao_ha_glitch(tmp_path):
    """Video curto, todo cortado no comeco: melhor nenhum estalo que um colado
    na abertura."""
    assert tratamentos.emendas_do_glitch([1.0, 2.0, 3.0]) == []


def test_uma_cena_longa_nao_deixa_o_filme_sem_estalo(tmp_path):
    """O contrario do caso acima: se ha emenda depois do intervalo, ela entra,
    mesmo que tenha demorado."""
    escolhidas = tratamentos.emendas_do_glitch([20.0, 21.0, 40.0])
    assert 20.0 in escolhidas and 40.0 in escolhidas
