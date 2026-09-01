"""O painel fixo: a barra de som e a frase que passa.

As duas pecas falham em silencio. Uma barra alimentada pelo audio errado
continua subindo e descendo -- so que com a musica. Uma frase com o laco mal
fechado some da tela por um instante a cada volta. Nos dois casos o filme monta
e o erro so aparece assistindo, que e o que estes testes evitam.
"""
import subprocess

import pytest
from PIL import Image

from motor import config, hud, imagem, probe
from tests import fixtures


def _faixa(caminho, t, y, alto, largura=None):
    """Um recorte horizontal do quadro, como imagem."""
    largura = largura or config.W
    bruto = imagem._um_quadro(
        caminho, t, f"crop={largura}:{alto}:0:{y},format=rgb24")
    if len(bruto) < largura * alto * 3:
        pytest.fail(f"nao consegui ler o quadro em {t}s")
    return Image.frombytes("RGB", (largura, alto), bytes(bruto[:largura * alto * 3]))


def _brilho_por_coluna(im):
    """Quanto de tinta clara ha em cada coluna. E assim que se mede DESLOCAMENTO
    sem comparar pixel a pixel: a frase e um padrao de colunas acesas, e ele
    anda inteiro."""
    px = im.load()
    return [sum(px[x, y][0] + px[x, y][1] + px[x, y][2] for y in range(im.height))
            for x in range(im.width)]


def _clipe(tmp_path, total=6.0, falas=((0.5, 1.5), (3.0, 2.0))):
    """Um clipe escuro com fala em dois momentos: fundo liso para a tinta clara
    do painel se destacar, e silencio no meio para a barra ter onde descer."""
    arq = tmp_path / "base.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-t", str(total),
         "-i", f"color=c=0x101010:s={config.W}x{config.H}:r={config.FPS}",
         "-f", "lavfi", "-t", str(total),
         "-i", f"sine=frequency=200:sample_rate={config.SR}",
         "-filter_complex",
         "[1:a]volume='" + "+".join(
             f"between(t,{i},{i + d})" for i, d in falas) + "':eval=frame[a]",
         "-map", "0:v", "-map", "[a]",
         "-c:v", "libx264", "-crf", "26", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-ar", str(config.SR),
         "-ac", "2", str(arq)], check=True)
    return arq


# --- a frase que passa -------------------------------------------------------

def test_a_frase_anda_para_a_direita(tmp_path):
    """Para a DIREITA, que foi o pedido. O sinal trocado na expressao de tempo
    faz ela andar para a esquerda, e o filme monta igual."""
    base = _clipe(tmp_path)
    saida = hud.aplicar(base, tmp_path / "h.mp4", texto="ABCDE FGHIJ KLMNO",
                        vu=False, velocidade=120)
    antes = _brilho_por_coluna(_faixa(saida, 1.0, hud.FRASE_Y - 4, 44))
    depois = _brilho_por_coluna(_faixa(saida, 2.0, hud.FRASE_Y - 4, 44))

    # Onde o padrao de colunas de `antes` reaparece em `depois`. Se a frase
    # andou D pixels para a direita, entao depois[x + D] == antes[x], e o
    # deslocamento que melhor casa e POSITIVO e igual a D.
    def casa(desl):
        a = antes[:len(antes) - abs(desl)]
        b = (depois[desl:] if desl >= 0 else depois[:desl])
        return sum(x * y for x, y in zip(a, b))

    melhor = max(range(-200, 201, 4), key=casa)
    assert melhor > 40, (
        f"a frase andou {melhor} pixels em 1 segundo: negativo quer dizer que "
        "ela esta indo para a esquerda")
    assert abs(melhor - 120) <= 8, (
        f"a 120 pixels por segundo, em 1 segundo ela tem de andar 120; andou "
        f"{melhor}")


def test_a_frase_nao_some_no_ponto_de_volta(tmp_path):
    """O laco. A imagem tem duas repeticoes lado a lado justamente para que,
    quando a primeira sai pela direita, a segunda ja esteja atras dela. Com uma
    so, a tela ficaria vazia por um instante a cada volta -- e a frase pisca."""
    base = _clipe(tmp_path, total=8.0)
    saida = hud.aplicar(base, tmp_path / "h.mp4", texto="OI", vu=False,
                        velocidade=300)
    vazios = []
    t = 0.2
    while t < 7.5:
        tinta = sum(_brilho_por_coluna(_faixa(saida, t, hud.FRASE_Y - 4, 44)))
        if tinta < 200_000:
            vazios.append(round(t, 1))
        t += 0.25
    assert not vazios, f"a frase sumiu da tela nos instantes {vazios}"


def test_frase_curta_se_repete_para_cobrir_a_tela(tmp_path):
    """Uma frase de duas letras mede menos que a tela. Sem repetir, o ponto de
    volta cairia no meio do quadro."""
    arq, passo = hud.tira("OI", tmp_path / "t.png")
    assert passo >= config.W, (
        f"uma repeticao mede {passo}px, menos que os {config.W} da tela")
    assert Image.open(arq).width == passo * 2


def test_a_frase_longa_demais_e_recusada_no_contrato(tmp_path):
    """Ela ANDA. Uma frase que nao cabe numa passada ninguem termina de ler, e
    o lugar de dizer isso e antes de montar 54 segundos de video."""
    import json

    from motor import cenas
    (tmp_path / "gravacoes").mkdir()
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.2, 1.0)], total=2.0)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({
        "hud": {"texto": "palavra " * 30},
        "cenas": [{"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov"}]}))
    with pytest.raises(cenas.CenasInvalidas, match="limite"):
        cenas.carregar(p)


def test_sem_frase_e_sem_barra_o_painel_e_recusado(tmp_path):
    with pytest.raises(ValueError):
        hud.aplicar(_clipe(tmp_path, total=1.0), tmp_path / "h.mp4",
                    texto=None, vu=False)


# --- a barra de som ----------------------------------------------------------

def _tinta_da_barra(caminho, t):
    im = _faixa(caminho, t, hud.VU_Y - 2, hud.VU_ALTURA + 4,
                largura=hud.VU_X + hud.VU_LARGURA + 20)
    px = im.load()
    return sum(1 for x in range(im.width) for y in range(im.height)
               if px[x, y][0] > 150 and px[x, y][1] > 150 and px[x, y][2] > 150)


def test_a_barra_sobe_com_a_fala_e_desce_no_silencio(tmp_path):
    """A prova de que ela RESPONDE. Uma barra parada no lugar certo passa por
    todos os outros testes: tem tinta, esta na posicao, nao muda a duracao."""
    base = _clipe(tmp_path, total=6.0, falas=((0.5, 1.5), (4.0, 1.5)))
    saida = hud.aplicar(base, tmp_path / "h.mp4", texto=None, vu=True)
    falando = _tinta_da_barra(saida, 1.2)
    calado = _tinta_da_barra(saida, 3.4)
    assert falando > calado * 1.5, (
        f"a barra marcou {falando} falando e {calado} no silencio: ela nao "
        "esta respondendo ao som")


def test_a_barra_responde_a_voz_e_nao_a_musica(tmp_path):
    """O erro que isto pega e o mais silencioso dos dois: alimentada pelo audio
    final, a barra continua se mexendo -- so que com a batida da musica, no
    silencio de quem fala."""
    voz = _clipe(tmp_path, total=6.0, falas=((0.5, 1.0),))
    # o "filme" tem som do comeco ao fim, como se a musica cobrisse tudo
    cheio = tmp_path / "cheio.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(voz),
         "-f", "lavfi", "-t", "6", "-i",
         f"sine=frequency=300:sample_rate={config.SR}",
         "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-c:a", "pcm_s16le", "-ar", str(config.SR), "-ac", "2",
         str(cheio)], check=True)

    com_voz = hud.aplicar(cheio, tmp_path / "a.mp4", texto=None, voz=voz)
    sem_voz = hud.aplicar(cheio, tmp_path / "b.mp4", texto=None)
    assert _tinta_da_barra(com_voz, 4.0) < _tinta_da_barra(sem_voz, 4.0) * 0.6, (
        "no silencio da fala a barra ficou igual com e sem o audio da voz: "
        "ela esta sendo alimentada pelo filme, e nao por quem fala")


# --- o painel nao pode estragar o filme --------------------------------------

def test_o_painel_nao_mexe_na_duracao(tmp_path):
    """A armadilha de sempre: numa composicao, `-shortest` come quadros de
    video e deixa o audio inteiro."""
    base = _clipe(tmp_path, total=5.0)
    antes_v, antes_a = probe.dur(base), probe.dur(base)
    saida = hud.aplicar(base, tmp_path / "h.mp4", texto="UMA FRASE QUALQUER")
    assert abs(probe.dur(saida) - antes_v) < 0.08
    from motor import montar
    v, a = montar.duracoes(saida)
    assert abs(v - a) < 0.12, f"imagem {v:.2f}s e som {a:.2f}s se separaram"


def test_o_painel_fica_fora_da_area_da_legenda():
    """Ele mora entre a interface do aplicativo, em cima, e a legenda, embaixo.
    Descer ate a legenda faria as duas se sobreporem no unico lugar do quadro
    onde ha texto para ler de verdade."""
    assert hud.VU_Y >= config.SEGURO_TOPO
    assert hud.FRASE_Y + 60 < config.LEG_TOPO_LETREIRO


def test_o_painel_so_aparece_se_alguem_pedir(tmp_path):
    """Ele muda a cara do video inteiro. Aparecer por descuido de quem escreveu
    o arquivo seria pior que faltar."""
    import json

    from motor import cenas
    (tmp_path / "gravacoes").mkdir()
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.2, 1.0)], total=2.0)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({
        "cenas": [{"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov"}]}))
    assert cenas.carregar(p).hud is None


def test_sem_contorno_a_frase_pede_fundo_escuro(tmp_path):
    """O custo de tirar o contorno, com numero. Foi um PEDIDO, nao um descuido,
    e por isso o que este teste faz e guardar o limite em vez de reprovar:

        fundo branco       contorno 0:  0,0   contorno 2: 71,7
        fundo cinza claro  contorno 0: 13,1   contorno 2: 62,8
        fundo escuro       contorno 0: 90,1   contorno 2: 93,6

    Na gravacao real, de parede bege, a frase mede 69,7 sem contorno e 62,8 com
    ele: ali ela se le MELHOR sem, porque a tinta subiu de 80% para 100%. Sobre
    parede branca ela sumiria inteira, e o conserto e `FRASE_CONTORNO = 2`.
    """
    branco = tmp_path / "branco.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", "2",
         "-i", f"color=c=white:s={config.W}x{config.H}:r={config.FPS}",
         "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
         str(branco)], check=True)

    def variacao(contorno):
        antes = hud.FRASE_CONTORNO
        hud.FRASE_CONTORNO = contorno
        try:
            saida = hud.aplicar(branco, tmp_path / f"h{contorno}.mp4",
                                texto="TESTE DE LEITURA", vu=False)
            col = _brilho_por_coluna(_faixa(saida, 1.0, hud.FRASE_Y - 4, 40))
            return (max(col) - min(col)) / 40 / 3
        finally:
            hud.FRASE_CONTORNO = antes

    assert variacao(0) < 5, (
        "sobre branco a frase sem contorno tem de sumir mesmo -- se este teste "
        "falhar, o desenho mudou e a medida acima nao vale mais")
    assert variacao(2) > 40, (
        "o contorno deixou de resolver o caso do fundo branco, e era ele o "
        "conserto guardado para quando a frase sumir")
