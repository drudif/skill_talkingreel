import subprocess

from motor import medidas
from motor import fala
from tests import fixtures

# Piso de ruido de uma sala silenciosa. Sem ele o silencio do clipe e zero
# DIGITAL (-120 dB) e nenhum limiar de nivel mede coisa alguma.
RUIDO = -50


def _cola(destino, a, b):
    """Emenda dois arquivos, para simular a costura que o montar faz."""
    lista = destino.parent / "lista.txt"
    lista.write_text(f"file '{a}'\nfile '{b}'\n", encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lista), "-c", "copy", str(destino)], check=True)
    return destino


def test_emenda_no_silencio_nao_reclama(tmp_path):
    a = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.3, 1.0)], total=2.0, ruido_dB=RUIDO)
    b = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.6, 1.2)], total=2.0, ruido_dB=RUIDO)
    filme = _cola(tmp_path / "f.mov", a, b)
    achados = medidas.emendas(filme, [2.0])
    assert achados == [], f"reclamou de uma emenda limpa: {achados}"


def test_emenda_no_meio_do_som_reclama(tmp_path):
    """Fala colada na emenda dos dois lados: e exatamente o engasgo."""
    a = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.3, 2.0)], total=2.0, ruido_dB=RUIDO)
    b = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.0, 1.5)], total=2.0, ruido_dB=RUIDO)
    filme = _cola(tmp_path / "f.mov", a, b)
    achados = medidas.emendas(filme, [2.0])
    assert len(achados) == 1
    assert achados[0]["instante"] == 2.0
    assert achados[0]["abaixo_da_fala"] < medidas.MARGEM_EMENDA


def test_emenda_fora_do_filme_e_ignorada(tmp_path):
    a = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.3, 1.0)], total=2.0, ruido_dB=RUIDO)
    assert medidas.emendas(a, [99.0]) == []


def test_filme_sem_emenda_nenhuma(tmp_path):
    a = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.3, 1.0)], total=2.0, ruido_dB=RUIDO)
    assert medidas.emendas(a, []) == []


def test_legenda_na_base_padrao_esta_segura(tmp_path):
    from motor import legenda
    p = legenda.png("uma frase", "brutalista", tmp_path / "a.png")
    assert medidas.dentro_da_faixa_segura(p) == []


def test_legenda_baixa_demais_e_apontada(tmp_path):
    from PIL import Image, ImageDraw
    from motor import config
    im = Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([200, 1600, 800, 1700], fill=(255, 255, 255, 255))
    p = tmp_path / "baixa.png"
    im.save(p)
    achados = medidas.dentro_da_faixa_segura(p)
    assert len(achados) == 1
    assert achados[0]["onde"] == "embaixo"


def test_legenda_alta_demais_e_apontada(tmp_path):
    from PIL import Image, ImageDraw
    from motor import config
    im = Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([200, 40, 800, 120], fill=(255, 255, 255, 255))
    p = tmp_path / "alta.png"
    im.save(p)
    assert medidas.dentro_da_faixa_segura(p)[0]["onde"] == "em cima"


def test_peca_sem_tinta_nenhuma_nao_reclama(tmp_path):
    from PIL import Image
    from motor import config
    p = tmp_path / "vazia.png"
    Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0)).save(p)
    assert medidas.dentro_da_faixa_segura(p) == []


def test_as_quatro_posicoes_da_legenda_estao_seguras(tmp_path):
    """Nenhuma das quatro posicoes medidas pode cair sob a interface."""
    from motor import legenda
    for posicao in legenda.POSICOES:
        p = legenda.png("uma frase um pouco mais longa", "brutalista",
                        tmp_path / f"{posicao}.png", posicao=posicao)
        assert medidas.dentro_da_faixa_segura(p) == [], (
            f"a posicao '{posicao}' cai fora da faixa segura")


def test_broll_do_tamanho_da_cena_nao_reclama(tmp_path):
    fixtures.clipe_mudo(tmp_path / "b.mp4", total=6.0, w=1920, h=1080)
    mapa = [{"n": 1, "trat": "split", "ini": 0.0, "fim": 5.0}]
    topos = {1: tmp_path / "b.mp4"}
    assert medidas.repeticao_do_complementar(mapa, topos) == []


def test_broll_curto_demais_e_apontado(tmp_path):
    fixtures.clipe_mudo(tmp_path / "b.mp4", total=2.0, w=1920, h=1080)
    mapa = [{"n": 1, "trat": "split", "ini": 0.0, "fim": 20.0}]
    achados = medidas.repeticao_do_complementar(mapa, {1: tmp_path / "b.mp4"})
    assert len(achados) == 1
    assert achados[0]["n"] == 1
    assert achados[0]["vezes"] == 10


def test_cena_sem_complementar_e_ignorada(tmp_path):
    mapa = [{"n": 1, "trat": "cheia", "ini": 0.0, "fim": 20.0}]
    assert medidas.repeticao_do_complementar(mapa, {}) == []


def test_repeticao_no_limite_nao_reclama(tmp_path):
    """Exatamente no limite ainda passa; e o limite que decide, nao o acaso."""
    fixtures.clipe_mudo(tmp_path / "b.mp4", total=2.0, w=1920, h=1080)
    fim = 2.0 * medidas.REPETICOES_DEMAIS
    mapa = [{"n": 1, "trat": "split", "ini": 0.0, "fim": fim}]
    assert medidas.repeticao_do_complementar(mapa, {1: tmp_path / "b.mp4"}) == []


def test_o_limiar_fica_entre_a_emenda_limpa_e_a_suja(tmp_path):
    """O numero que justifica MARGEM_EMENDA.

    Medido: emenda limpa fica ~41 dB abaixo do nivel de fala do filme; emenda
    que corta palavra fica a 0-3 dB dela. Se este teste comecar a falhar, o
    limiar saiu do meio e a medicao virou enfeite."""
    def abaixo(fa, fb, rot):
        a = fixtures.clipe_fala(tmp_path / f"a{rot}.mov", falas=fa,
                                total=2.0, ruido_dB=RUIDO)
        b = fixtures.clipe_fala(tmp_path / f"b{rot}.mov", falas=fb,
                                total=2.0, ruido_dB=RUIDO)
        f = _cola(tmp_path / f"f{rot}.mov", a, b)
        return medidas.emendas(f, [2.0], margem=999)[0]["abaixo_da_fala"]

    limpa = abaixo([(0.3, 1.0)], [(0.6, 1.2)], "limpa")
    suja = abaixo([(0.3, 1.7)], [(0.0, 1.5)], "suja")

    assert limpa > medidas.MARGEM_EMENDA, (
        f"a emenda limpa fica {limpa:.1f} dB abaixo da fala e a margem e "
        f"{medidas.MARGEM_EMENDA}: vai acusar emenda que esta boa")
    assert suja < medidas.MARGEM_EMENDA, (
        f"a emenda suja fica {suja:.1f} dB abaixo da fala e a margem e "
        f"{medidas.MARGEM_EMENDA}: vai deixar passar corte no meio da palavra")
    assert limpa - suja > 25, (
        f"so {limpa - suja:.1f} dB separam emenda boa de emenda ruim; "
        "com margem tao pequena o limiar e chute")


def test_a_referencia_e_a_fala_e_nao_o_silencio(tmp_path):
    """O DEFEITO QUE ISTO GUARDA. Num talking head bem cortado quase nao sobra
    silencio. Se a referencia fosse o percentil de baixo do envelope, ela seria
    FALA — medido, um filme de duas cenas coladas devolvia 'silencio' a -0,8 dB
    e nenhuma emenda suja era detectada."""
    a = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.02, 1.96)],
                            total=2.0, ruido_dB=RUIDO)
    b = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.02, 1.96)],
                            total=2.0, ruido_dB=RUIDO)
    f = _cola(tmp_path / "f.mov", a, b)
    achados = medidas.emendas(f, [2.0])
    assert achados, (
        "filme quase todo fala: a emenda no meio do som passou despercebida")


def test_sem_ruido_o_clipe_mente_sobre_nivel(tmp_path):
    """POR QUE O PISO DE RUIDO EXISTE NOS OUTROS TESTES.

    Com silencio de zero digital o piso vira -120 dB, distancia que nao existe
    em gravacao nenhuma. Qualquer limiar calibrado ali e ficcao."""
    a = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.3, 1.0)], total=2.0)
    piso_seco = medidas._dB(medidas._percentil(fala.envelope(a), 0.10))
    assert piso_seco < -100, (
        f"o clipe sem ruido deveria ter piso irreal, deu {piso_seco:.1f} dB")

    b = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.3, 1.0)],
                            total=2.0, ruido_dB=RUIDO)
    piso_real = medidas._dB(medidas._percentil(fala.envelope(b), 0.10))
    assert -60 < piso_real < -30, (
        f"o piso com ruido deveria parecer com o de uma sala silenciosa, "
        f"deu {piso_real:.1f} dB")
    assert piso_real - piso_seco > 50, (
        "os dois pisos tem de ser MUITO diferentes; e essa diferenca que "
        "torna ficcao qualquer limiar calibrado no clipe seco")


def test_o_limite_de_baixo_pega_o_erro_que_o_motivou(tmp_path):
    """A legenda na base 1500 caiu sob a interface do aplicativo, e por isso
    virou 1375. Um limite que nao acusa 1500 nao serve para nada — foi esse
    exato caso que aconteceu."""
    from motor import config, legenda
    original = config.LEG_BASE
    try:
        config.LEG_BASE = 1375
        boa = legenda.png("uma frase", "brutalista", tmp_path / "boa.png")
        assert medidas.dentro_da_faixa_segura(boa) == [], (
            "acusou a posicao que sabemos que funciona")

        config.LEG_BASE = 1500
        ruim = legenda.png("uma frase", "brutalista", tmp_path / "ruim.png")
        achados = medidas.dentro_da_faixa_segura(ruim)
        assert achados and achados[0]["onde"] == "embaixo", (
            "deixou passar a posicao que caiu sob a interface do aplicativo")
    finally:
        config.LEG_BASE = original


def test_as_quatro_posicoes_seguem_seguras_com_o_limite_novo(tmp_path):
    from motor import legenda
    for posicao in legenda.POSICOES:
        p = legenda.png("uma frase um pouco mais longa", "brutalista",
                        tmp_path / f"{posicao}.png", posicao=posicao)
        assert medidas.dentro_da_faixa_segura(p) == [], (
            f"a posicao '{posicao}' passou a cair fora da faixa segura")
