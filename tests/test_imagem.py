"""Contraste: quanto da escala de brilho a imagem ocupa, e quanto corrigir.

Os numeros de config.py vieram de medicao em seis gravacoes reais e de um
experimento de lavagem e correcao. Cada limiar aqui e provado dos dois lados:
um teste falha se ele subir demais, outro se descer demais. Sem isso o numero
seria chute com aparencia de medida.
"""
import subprocess

import pytest

from motor import config, imagem


def _clipe(destino, contraste=1.0, seg=1.5):
    """Um clipe com desenho de verdade, lavado no grau pedido. `contraste`
    menor que 1 encolhe a faixa de brilho, que e o defeito a corrigir."""
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", str(seg),
         "-i", "testsrc2=s=320x568:r=10",
         "-vf", f"eq=contrast={contraste}", "-an",
         "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", str(destino)], check=True)
    return destino


# --- a medida ---

def test_imagem_lavada_ocupa_menos_da_escala(tmp_path):
    cheia = imagem.contraste(_clipe(tmp_path / "a.mov", 1.0))
    lavada = imagem.contraste(_clipe(tmp_path / "b.mov", 0.35))
    assert lavada < cheia, "a lavagem tinha de encolher a faixa de brilho"
    assert lavada < config.CONTRASTE_LAVADO, (
        f"um clipe lavado a 0,35 deu faixa {lavada:.0f}, que o motor ainda "
        f"considera boa (limite {config.CONTRASTE_LAVADO})")


def test_a_faixa_nao_e_o_brilho_medio(tmp_path):
    """Media cancela sinal: uma imagem meio preta e meio branca e uma imagem
    toda cinza tem a mesma media e contrastes opostos. Por isso a medida e a
    distancia entre os percentis, nao a media."""
    chapado = tmp_path / "cinza.mov"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", "1",
         "-i", "color=c=gray:s=320x568:r=10", "-an", "-c:v", "libx264",
         "-crf", "18", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         str(chapado)], check=True)
    metade = tmp_path / "metade.mov"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", "1",
         "-i", "color=c=black:s=320x568:r=10",
         "-vf", "drawbox=x=0:y=0:w=320:h=284:c=white@1:t=fill", "-an",
         "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", str(metade)], check=True)
    assert imagem.contraste(metade) > imagem.contraste(chapado) + 100, (
        "a medida nao separou a imagem chapada da imagem de contraste maximo")


# --- a decisao de corrigir ---

def test_imagem_ja_boa_nao_e_esticada(tmp_path):
    """O caso mais importante. MEDIDO: material que ja esta na faixa de 163
    perde 0,47% dos pixels no estouro com esticamento de so 1,15. Corrigir o
    que esta bom nao e neutro, e prejuizo."""
    boa = _clipe(tmp_path / "boa.mov", 1.0)
    assert imagem.contraste(boa) >= config.CONTRASTE_LAVADO
    assert imagem.ganho(boa) == config.CONTRASTE_BASE


def test_imagem_lavada_e_esticada(tmp_path):
    lavada = _clipe(tmp_path / "lav.mov", 0.35)
    assert imagem.ganho(lavada) > config.CONTRASTE_BASE


def test_o_esticamento_tem_teto(tmp_path):
    """Imagem quase chapada pediria um esticamento enorme. Acima do teto o que
    cresce e o granulado, e o problema passa a ser da gravacao."""
    chapada = _clipe(tmp_path / "chap.mov", 0.08)
    assert imagem.ganho(chapada) == config.CONTRASTE_MAX


def test_o_numero_forcado_passa_direto(tmp_path):
    boa = _clipe(tmp_path / "f.mov", 1.0)
    assert imagem.ganho(boa, quando_lavado=1.5) == 1.5


# --- os limiares, provados dos dois lados ---

def test_o_alvo_e_a_faixa_do_material_bem_gravado():
    """Se o alvo subir acima do que o material real ocupa, a correcao passa a
    estourar pixel de proposito; se descer muito, deixa a imagem lavada."""
    assert 160 <= config.CONTRASTE_ALVO <= 170, (
        "as seis gravacoes reais medidas ocupam de 163,7 a 165,7 da escala. "
        "Um alvo fora dessa vizinhanca nao veio de medida nenhuma")


def test_o_limiar_de_lavado_tem_folga_para_o_alvo():
    """Provado dos dois lados. Alto demais: material bom entra em correcao, e
    medido que a 1,15 ele ja estoura 0,47% dos pixels. Baixo demais: imagem
    lavada de verdade passa sem correcao."""
    assert config.CONTRASTE_LAVADO < config.CONTRASTE_ALVO / 1.14, (
        "o limiar esta perto demais do alvo: material que ja esta bom seria "
        "corrigido, e a correcao estoura pixel")
    assert config.CONTRASTE_LAVADO > config.CONTRASTE_ALVO / 1.5, (
        "o limiar esta baixo demais: imagem visivelmente lavada passaria sem "
        "correcao nenhuma")


def test_o_teto_do_esticamento_e_maior_que_o_realce_de_sempre():
    assert config.CONTRASTE_MAX > config.CONTRASTE_BASE


# --- o dano, para o laudo poder avisar ---

def test_estouro_conta_pixel_preso_no_preto_ou_no_branco(tmp_path):
    boa = _clipe(tmp_path / "e1.mov", 1.0)
    estourada = _clipe(tmp_path / "e2.mov", 4.0)
    assert imagem.estouro(estourada) > imagem.estouro(boa) + 0.05, (
        "esticar 4x tinha de prender pixels no preto e no branco")


# ---------------------------------------------------------------------------
# Fundo verde
#
# A pergunta que estes testes protegem: da para trocar o fundo desta gravacao?
# Responder "sim" errado produz um video com pedacos da pessoa apagados, e
# ninguem descobre ate assistir.
# ---------------------------------------------------------------------------

from tests import fixtures       # noqa: E402


def test_pano_verde_e_reconhecido(tmp_path):
    c = fixtures.clipe_croma(tmp_path / "croma.mov")
    assert imagem.tem_fundo_verde(c) is True


def test_pano_verde_com_a_pessoa_ocupando_quase_tudo_ainda_e_reconhecido(tmp_path):
    """O enquadramento apertado e o caso limite do lado do sim: sobra pouco
    pano. MEDIDO em 58% da borda, contra 13% do pior falso positivo."""
    c = tmp_path / "apertado.mov"
    fixtures.clipe_croma(c, w=320, h=568)
    import subprocess
    grande = tmp_path / "grande.mov"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(c),
         "-vf", "drawbox=x=40:y=60:w=240:h=508:c=0x8d5524@1:t=fill", "-an",
         "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", str(grande)], check=True)
    assert imagem.tem_fundo_verde(grande) is True, (
        "enquadramento apertado com pano verde de verdade foi recusado")


def test_sala_comum_nao_e_confundida_com_pano_verde(tmp_path):
    c = fixtures.clipe_croma(tmp_path / "sala.mov", verde=False)
    assert imagem.tem_fundo_verde(c) is False


def test_camiseta_verde_nao_e_confundida_com_pano_verde(tmp_path):
    """O falso positivo que mais custaria caro: aceitar isto apagaria o torso
    da pessoa no video final."""
    c = fixtures.clipe_com_objeto_verde(tmp_path / "camiseta.mov")
    assert imagem.tem_fundo_verde(c) is False, (
        "uma camiseta verde foi lida como pano de fundo")


def test_imagem_colorida_qualquer_nao_e_pano_verde(tmp_path):
    import subprocess
    c = tmp_path / "colorida.mov"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", "1",
         "-i", "testsrc2=s=320x568:r=10", "-an", "-c:v", "libx264",
         "-crf", "18", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         str(c)], check=True)
    assert imagem.tem_fundo_verde(c) is False


def test_o_limiar_do_verde_esta_provado_dos_dois_lados():
    """Alto demais recusa pano verde de verdade no enquadramento apertado, que
    deu 58%. Baixo demais aceita camiseta verde, que deu 13%."""
    assert config.VERDE_DA_MOLDURA < 0.55, (
        "o limiar recusaria o enquadramento apertado, que e croma legitimo")
    assert config.VERDE_DA_MOLDURA > 0.20, (
        "o limiar aceitaria camiseta verde e planta, que medem 13%")


def test_a_cor_do_pano_e_lida_da_propria_gravacao(tmp_path):
    """Panos verdes nao sao todos iguais e a luz muda o tom. Cortar por uma cor
    fixa deixaria borda verde no contorno da pessoa."""
    c = fixtures.clipe_croma(tmp_path / "c.mov")
    cor = imagem.cor_do_fundo_verde(c)
    assert cor and cor.startswith("0x")
    r, g, b = int(cor[2:4], 16), int(cor[4:6], 16), int(cor[6:8], 16)
    assert g > r and g > b, f"a cor lida ({cor}) nao e verde"


def test_sem_pano_verde_nao_ha_cor_para_ler(tmp_path):
    c = fixtures.clipe_croma(tmp_path / "sala.mov", verde=False)
    assert imagem.cor_do_fundo_verde(c) is None


def test_a_leitura_de_quadros_busca_o_instante_em_vez_de_decodificar_tudo(
        tmp_path, monkeypatch):
    """O defeito que isto impede: pedir quadros espalhados com um filtro de
    taxa obriga o ffmpeg a decodificar o video INTEIRO para descartar quase
    todos os quadros.

    MEDIDO num arquivo de celular de 4K com 4,7 minutos: passou de DOIS MINUTOS
    do jeito antigo, contra 6,9 segundos buscando um quadro de cada vez. E a
    primeira coisa que roda no trabalho todo -- travar ali trava tudo."""
    import subprocess as sp
    c = _clipe(tmp_path / "q.mov", seg=2.0)
    vistos = []
    real = sp.run

    def espiao(args, *a, **k):
        if args and args[0] == "ffmpeg":
            vistos.append(list(args))
        return real(args, *a, **k)

    monkeypatch.setattr(imagem.subprocess, "run", espiao)
    quadros = imagem._quadros(c, quantos=4)

    assert len(quadros) == 4
    assert len(vistos) == 4, (
        f"esperava uma busca por quadro e vieram {len(vistos)} comandos")
    for cmd in vistos:
        assert "-ss" in cmd and cmd.index("-ss") < cmd.index("-i"), (
            "o quadro nao foi buscado direto no instante")
        assert not any("fps=" in str(x) for x in cmd), (
            "voltou o filtro de taxa, que decodifica o video inteiro")


def test_os_quadros_amostrados_ficam_longe_das_pontas(tmp_path):
    """O primeiro e o ultimo segundo costumam ter a mao na camera, a tela preta
    do corte, ou a pessoa ainda se ajeitando -- medir ali daria um retrato do
    que nao vai para o video."""
    ts = imagem._instantes("qualquer", 6)  # nao le o arquivo: _instantes usa dur
    assert all(t > 0 for t in ts)
    assert ts == sorted(ts), "os instantes sairam fora de ordem"
