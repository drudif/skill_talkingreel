from motor import cenas, probe, tratamentos
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
