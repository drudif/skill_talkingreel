from motor import cenas, config, probe, tratamentos
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
