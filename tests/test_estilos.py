"""Testes das sete fichas de estilo: campos completos, cores validas, contraste
legivel e fonte resolvivel no disco (com fallback provado, nao so assumido)."""
import re
from pathlib import Path

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


# ---------------------------------------------------------------------------
# As fontes
#
# Antes desta separacao os sete estilos usavam a MESMA fonte na pratica: todas
# as fichas listavam a mesma primeira candidata e ela existia na maquina do
# autor. "Fonte" era um dos tres eixos que separam um estilo do outro, e era o
# unico que nao separava nada.
# ---------------------------------------------------------------------------

def test_cada_estilo_tem_a_propria_fonte_de_letreiro():
    usadas = {}
    for chave in estilos.ESTILOS:
        usadas.setdefault(estilos.fonte(chave), []).append(chave)
    repetidas = {f: q for f, q in usadas.items() if len(q) > 1}
    assert not repetidas, (
        f"estes estilos dividem a mesma fonte de letreiro: "
        f"{ {Path(f).name: q for f, q in repetidas.items()} }")


def test_a_legenda_usa_outra_fonte_que_o_letreiro():
    """A fonte de titulo num texto pequeno e corrido deixa a leitura pesada.
    No carrossel de onde as fichas vieram, cada estilo tem uma para cada uso."""
    iguais = [c for c in estilos.ESTILOS
              if estilos.fonte(c) == estilos.fonte_legenda(c)]
    assert not iguais, (
        f"nestes estilos a legenda usa a fonte do letreiro: {iguais}")


def test_as_fontes_da_skill_estao_todas_no_disco():
    """Elas vem junto com a skill. Se uma faltar, aquele estilo cai calado numa
    fonte do sistema e deixa de ser o que a ficha promete."""
    faltando = []
    for chave, ficha in estilos.ESTILOS.items():
        for lista in ("fontes", "fontes_legenda"):
            primeira = ficha[lista][0]
            if primeira.startswith(estilos.FONTES_DA_SKILL) \
                    and not Path(primeira).exists():
                faltando.append((chave, Path(primeira).name))
    assert not faltando, f"fontes que a skill promete e nao tem: {faltando}"


def test_fonte_que_falta_cai_na_reserva(tmp_path, monkeypatch):
    """A regra que impede a skill de quebrar na maquina de outra pessoa: fonte
    licenciada nunca e exigida."""
    monkeypatch.setitem(estilos.ESTILOS, "inventado", {
        "nome": "so para o teste", "fundo": "#000000", "texto": "#FFFFFF",
        "contorno": "#000000", "legenda_caixa": "#000000",
        "legenda_texto": "#FFFFFF", "peso_letreiro": 90,
        "fontes": [str(tmp_path / "nao-existe.ttf")],
        "fontes_legenda": [str(tmp_path / "tambem-nao.ttf")]})
    assert estilos.fonte("inventado") == estilos.RESERVA
    assert estilos.fonte_legenda("inventado") == estilos.RESERVA
    assert Path(estilos.RESERVA).exists(), "a reserva tem de existir em todo Mac"


def test_ficha_sem_fonte_de_legenda_cai_na_do_letreiro(monkeypatch):
    monkeypatch.setitem(estilos.ESTILOS, "meio", {
        "nome": "so para o teste", "fundo": "#000000", "texto": "#FFFFFF",
        "contorno": "#000000", "legenda_caixa": "#000000",
        "legenda_texto": "#FFFFFF", "peso_letreiro": 90,
        "fontes": [estilos.RESERVA]})
    assert estilos.fonte_legenda("meio") == estilos.fonte("meio")


def test_toda_fonte_da_skill_tem_licenca_ao_lado():
    """Fonte sem licenca no repositorio e um problema de direito, e ele aparece
    quando o repositorio ja esta publicado."""
    pasta = Path(estilos.FONTES_DA_SKILL)
    if not pasta.is_dir():
        return
    licencas = " ".join(p.name.lower() for p in pasta.glob("LICENCA-*.txt"))
    sem = []
    for fonte_ttf in pasta.glob("*.ttf"):
        radical = fonte_ttf.stem.split("-")[0].lower()
        if radical not in licencas.replace("-", ""):
            sem.append(fonte_ttf.name)
    assert not sem, f"fontes sem arquivo de licenca ao lado: {sem}"
