"""Testes das sete fichas de estilo: campos completos, cores validas, contraste
legivel e fonte resolvivel no disco (com fallback provado, nao so assumido)."""
import re

import pytest
from PIL import Image, ImageDraw, ImageFont

from motor import estilos


def test_sao_sete():
    assert len(estilos.ESTILOS) == 7


def test_todo_estilo_tem_o_que_a_arte_precisa():
    campos = {"nome", "fundo", "texto", "contorno", "legenda_caixa",
              "legenda_texto", "fontes", "peso_letreiro"}
    for chave, e in estilos.ESTILOS.items():
        faltando = campos - set(e)
        assert not faltando, f"estilo {chave} sem: {faltando}"


def test_cores_sao_hexadecimais_de_seis_digitos():
    for chave, e in estilos.ESTILOS.items():
        for campo in ("fundo", "texto", "contorno", "legenda_caixa", "legenda_texto"):
            valor = e[campo]
            assert re.fullmatch(r"#[0-9A-Fa-f]{6}", valor), \
                f"{chave}.{campo} = {valor!r} nao e cor hexadecimal"


def test_carrega_um_estilo_pelo_nome():
    e = estilos.carregar("terminal")
    assert e["nome"]


def test_estilo_inexistente_diz_quais_existem():
    with pytest.raises(estilos.EstiloDesconhecido) as erro:
        estilos.carregar("roxo-neon")
    assert "terminal" in str(erro.value)


def test_a_fonte_resolvida_existe_no_disco():
    from pathlib import Path
    for chave in estilos.ESTILOS:
        caminho = estilos.fonte(chave)
        assert Path(caminho).exists(), f"{chave}: {caminho} nao existe"


def test_contraste_entre_texto_e_contorno():
    """Letreiro sem contraste entre preenchimento e contorno some no fundo."""
    for chave, e in estilos.ESTILOS.items():
        d = estilos.distancia_de_cor(e["texto"], e["contorno"])
        assert d > 120, f"{chave}: texto e contorno quase iguais ({d})"


def test_contraste_entre_legenda_e_caixa():
    for chave, e in estilos.ESTILOS.items():
        d = estilos.distancia_de_cor(e["legenda_texto"], e["legenda_caixa"])
        assert d > 120, f"{chave}: legenda ilegivel sobre a propria caixa ({d})"


# --- Checagens extras: a lista de candidatas e o fallback tem que funcionar
# de verdade nesta maquina, nao so na maquina do autor. ---

def test_cada_estilo_tem_candidata_real_alem_da_reserva():
    """Se toda candidata de um estilo estiver ausente, fonte() sempre cai na
    RESERVA e a ficha perde a identidade visual sem que nenhum teste avise.
    Aqui exigimos que exista pelo menos uma candidata (nao-reserva) real."""
    for chave, e in estilos.ESTILOS.items():
        candidatas_reais = [c for c in e["fontes"] if c != estilos.RESERVA]
        existentes = [c for c in candidatas_reais if __import__("pathlib").Path(c).exists()]
        assert existentes, f"{chave}: nenhuma candidata real existe, so a RESERVA"


def test_fallback_cai_na_reserva_quando_nada_existe(monkeypatch):
    """Prova que o fallback funciona: com toda candidata apontando para um
    caminho inexistente, fonte() devolve RESERVA, e RESERVA existe no disco."""
    from pathlib import Path

    falsas = ["/caminho/que/nao/existe/Fake-Bold.ttf",
              "/outro/caminho/inexistente/Fake-Black.otf"]
    original = estilos.ESTILOS["terminal"]["fontes"]
    monkeypatch.setitem(estilos.ESTILOS["terminal"], "fontes", falsas)
    try:
        assert estilos.fonte("terminal") == estilos.RESERVA
        assert Path(estilos.RESERVA).exists()
    finally:
        estilos.ESTILOS["terminal"]["fontes"] = original


def test_pillow_abre_a_fonte_resolvida_e_desenha_acentuacao():
    """Caminho existir no disco nao prova que o Pillow consiga abrir: .ttc
    as vezes precisa de indice, e a fonte pode nao ter os glifos do pt-BR."""
    img = Image.new("RGB", (10, 10))
    desenho = ImageDraw.Draw(img)
    for chave in estilos.ESTILOS:
        caminho = estilos.fonte(chave)
        fonte = ImageFont.truetype(caminho, 48)
        caixa = desenho.textbbox((0, 0), "ÃÉÍÓÚÇ", font=fonte)
        largura = caixa[2] - caixa[0]
        assert largura > 0, f"{chave}: {caminho} desenhou largura zero"
