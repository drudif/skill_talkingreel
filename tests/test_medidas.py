import subprocess

from motor import medidas
from tests import fixtures


def _cola(destino, a, b):
    """Emenda dois arquivos, para simular a costura que o montar faz."""
    lista = destino.parent / "lista.txt"
    lista.write_text(f"file '{a}'\nfile '{b}'\n", encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lista), "-c", "copy", str(destino)], check=True)
    return destino


def test_emenda_no_silencio_nao_reclama(tmp_path):
    a = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.3, 1.0)], total=2.0)
    b = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.6, 1.2)], total=2.0)
    filme = _cola(tmp_path / "f.mov", a, b)
    achados = medidas.emendas(filme, [2.0])
    assert achados == [], f"reclamou de uma emenda limpa: {achados}"


def test_emenda_no_meio_do_som_reclama(tmp_path):
    """Fala colada na emenda dos dois lados: e exatamente o engasgo."""
    a = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.3, 2.0)], total=2.0)
    b = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.0, 1.5)], total=2.0)
    filme = _cola(tmp_path / "f.mov", a, b)
    achados = medidas.emendas(filme, [2.0])
    assert len(achados) == 1
    assert achados[0]["instante"] == 2.0
    assert achados[0]["dB"] > achados[0]["silencio_dB"] + 10


def test_emenda_fora_do_filme_e_ignorada(tmp_path):
    a = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.3, 1.0)], total=2.0)
    assert medidas.emendas(a, [99.0]) == []


def test_filme_sem_emenda_nenhuma(tmp_path):
    a = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.3, 1.0)], total=2.0)
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
