from motor import config


def test_formato_vertical_de_reels():
    assert (config.W, config.H, config.FPS) == (1080, 1920, 30)


def test_divisoria_do_split_dentro_do_quadro():
    assert 0 < config.DIVISORIA < config.H
    assert config.DIVISORIA == 807


def test_janela_de_cima_do_split_e_deitada():
    largura, altura = config.W, config.DIVISORIA
    assert largura > altura


def test_pausa_comprimida_encurta():
    assert config.PAUSA_FICA < config.PAUSA_MAX


def test_saida_tem_mais_respiro_que_a_entrada():
    assert config.RESPIRO_OUT > config.RESPIRO_IN
