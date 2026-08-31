"""Como o texto aparece: fonte, paleta e efeito, escolhidos em separado.

Antes eram sete fichas fechadas, cada uma com fonte, cor e efeito amarrados.
Fechado nao deixava a pessoa gostar da letra de uma e da cor de outra, que foi
o que apareceu no uso. Agora sao tres escolhas, duas vezes -- uma para a legenda
e outra para o letreiro.
"""
import re
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from motor import estilos


# --- as listas ---------------------------------------------------------------

def test_as_tres_fontes_de_legenda_existem():
    """Legenda e texto pequeno e corrido: as tres sao de leitura, e o pedido
    foi uma de cada familia."""
    assert len(estilos.FONTES_LEGENDA) == 3
    assert set(estilos.FONTES_LEGENDA) == {"sem serifa", "serifa", "monoespaço"}


def test_as_cinco_fontes_de_letreiro_existem():
    assert len(estilos.FONTES_LETREIRO) == 5


def test_as_cinco_paletas_existem():
    assert len(estilos.PALETAS) == 5


def test_os_dois_efeitos_existem():
    """Sao dois porque sao os dois que sobrevivem a imagem em movimento.
    Sombra, brilho e degrade somem quando o fundo muda de cor -- e o fundo aqui
    e o rosto de alguem se mexendo."""
    assert set(estilos.EFEITOS) == {"contorno", "caixa"}


@pytest.mark.parametrize("grupo", ["FONTES_LEGENDA", "FONTES_LETREIRO",
                                   "PALETAS", "EFEITOS"])
def test_toda_opcao_diz_como_e(grupo):
    """Quem escolhe le esta frase. Opcao sem descricao e opcao escolhida no
    chute."""
    for chave, valor in getattr(estilos, grupo).items():
        texto = valor if isinstance(valor, str) else valor["como e"]
        assert len(texto) > 25, f"'{chave}' nao diz como e"


# --- as fontes no disco ------------------------------------------------------

def test_cada_fonte_tem_candidata_real_alem_da_reserva():
    """Uma entrada que so tivesse a reserva seria uma opcao que nao muda nada."""
    for grupo in (estilos.FONTES_LEGENDA, estilos.FONTES_LETREIRO):
        for chave, ficha in grupo.items():
            reais = [c for c in ficha["arquivos"] if c != estilos.RESERVA]
            assert reais, f"'{chave}' so tem a reserva"


def test_as_fontes_da_skill_estao_todas_no_disco():
    """Elas vem junto com a skill. Se uma faltar, aquela opcao cai calada numa
    fonte do sistema e deixa de ser o que promete."""
    faltando = []
    for grupo in (estilos.FONTES_LEGENDA, estilos.FONTES_LETREIRO):
        for chave, ficha in grupo.items():
            primeira = ficha["arquivos"][0]
            if primeira.startswith(estilos.FONTES_DA_SKILL) \
                    and not Path(primeira).exists():
                faltando.append((chave, Path(primeira).name))
    assert not faltando, f"fontes que a skill promete e nao tem: {faltando}"


def test_cada_opcao_de_fonte_resolve_uma_fonte_diferente():
    """Duas opcoes que caissem no mesmo arquivo seriam uma escolha sem escolha
    -- e foi o que aconteceu antes desta separacao, quando as sete fichas
    usavam duas fontes no total."""
    for nome, resolver, grupo in (
            ("legenda", estilos.fonte_da_legenda, estilos.FONTES_LEGENDA),
            ("letreiro", estilos.fonte_do_letreiro, estilos.FONTES_LETREIRO)):
        usadas = {}
        for chave in grupo:
            usadas.setdefault(resolver(chave), []).append(chave)
        repetidas = {f: q for f, q in usadas.items() if len(q) > 1}
        assert not repetidas, (
            f"na {nome}, estas opcoes caem na mesma fonte: "
            f"{ {Path(f).name: q for f, q in repetidas.items()} }")


def test_fonte_que_falta_cai_na_reserva(tmp_path, monkeypatch):
    """A regra que impede a skill de quebrar na maquina de outra pessoa: fonte
    licenciada nunca e exigida."""
    monkeypatch.setitem(estilos.FONTES_LEGENDA, "inventada",
                        {"como e": "so para o teste, com texto suficiente aqui",
                         "arquivos": [str(tmp_path / "nao-existe.ttf")]})
    assert estilos.fonte_da_legenda("inventada") == estilos.RESERVA
    assert Path(estilos.RESERVA).exists(), "a reserva tem de existir em todo Mac"


def test_pillow_abre_a_fonte_resolvida_e_desenha_acentuacao():
    """Portugues tem ç, ã e ê. Uma fonte sem esses caracteres desenha quadrado,
    e isso so aparece no video pronto."""
    for resolver, grupo in ((estilos.fonte_da_legenda, estilos.FONTES_LEGENDA),
                            (estilos.fonte_do_letreiro, estilos.FONTES_LETREIRO)):
        for chave in grupo:
            f = ImageFont.truetype(resolver(chave), 40)
            im = Image.new("L", (600, 80), 0)
            d = ImageDraw.Draw(im)
            d.text((5, 5), "ação ê ç ã", font=f, fill=255)
            assert im.getbbox() is not None, f"'{chave}' nao desenhou acentuacao"


# --- as paletas --------------------------------------------------------------

def test_toda_paleta_tem_as_quatro_cores():
    """Duas para o efeito de contorno e duas para o de caixa. A cor que se le
    bem com contorno nao e a mesma que se le dentro de uma caixa."""
    for nome, p in estilos.PALETAS.items():
        for campo in ("texto", "contorno", "caixa", "caixa_texto"):
            assert re.fullmatch(r"#[0-9A-Fa-f]{6}", p[campo]), (
                f"'{nome}' tem '{campo}' fora do formato #RRGGBB")


def test_contraste_dentro_e_fora_da_caixa():
    for nome, p in estilos.PALETAS.items():
        fora = estilos.distancia_de_cor(p["texto"], p["contorno"])
        dentro = estilos.distancia_de_cor(p["caixa_texto"], p["caixa"])
        assert fora > 200, f"'{nome}': letra e contorno perto demais ({fora})"
        assert dentro > 200, f"'{nome}': letra e caixa perto demais ({dentro})"


# --- compor ------------------------------------------------------------------

def test_compor_completa_o_que_faltou_com_o_padrao():
    """Escolher a cor nao obriga a escolher a letra."""
    p = estilos.compor({"paleta": "verde"}, "legenda")
    assert p["paleta"] == "verde"
    assert p["fonte"] == estilos.PADRAO_LEGENDA["fonte"]
    assert p["efeito"] == estilos.PADRAO_LEGENDA["efeito"]


def test_compor_sem_nada_da_o_padrao():
    for para in ("legenda", "letreiro"):
        p = estilos.compor(None, para)
        assert p["arquivo"] and p["texto"] and p["corpo"] > 0


def test_a_cor_da_letra_muda_com_o_efeito():
    """A metade de dentro da paleta existe por isso: amarelo com contorno preto
    se le sobre video, mas amarelo dentro de caixa amarela sumiria."""
    dentro = estilos.compor({"paleta": "amarelo", "efeito": "caixa"}, "letreiro")
    fora = estilos.compor({"paleta": "amarelo", "efeito": "contorno"}, "letreiro")
    assert dentro["texto"] != fora["texto"]


def test_a_legenda_e_o_letreiro_tem_corpos_diferentes():
    """Legenda e para ler; letreiro e para ver. Mesmo corpo nos dois faria um
    dos dois estar errado."""
    assert (estilos.compor(None, "letreiro")["corpo"]
            > estilos.compor(None, "legenda")["corpo"])


def test_a_legenda_nao_aceita_fonte_de_letreiro():
    """As listas sao separadas de proposito: fonte de display em texto pequeno
    e corrido cansa de ler."""
    with pytest.raises(estilos.EstiloDesconhecido, match="legenda"):
        estilos.compor({"fonte": "revista"}, "legenda")


def test_opcao_que_nao_existe_diz_quais_existem():
    for escolhas, palavra in (({"paleta": "roxo-neon"}, "amarelo"),
                              ({"efeito": "sombra"}, "contorno"),
                              ({"fonte": "gotica"}, "serifa")):
        with pytest.raises(estilos.EstiloDesconhecido, match=palavra):
            estilos.compor(escolhas, "legenda")


def test_compor_so_serve_para_legenda_ou_letreiro():
    with pytest.raises(ValueError):
        estilos.compor(None, "titulo")


# --- creditos ----------------------------------------------------------------

def test_toda_fonte_da_skill_tem_licenca_ao_lado():
    """Fonte sem licenca no repositorio e um problema de direito, e ele aparece
    quando o repositorio ja esta publicado."""
    pasta = Path(estilos.FONTES_DA_SKILL)
    if not pasta.is_dir():
        return
    licencas = " ".join(p.name.lower() for p in pasta.glob("LICENCA-*.txt"))
    sem = []
    for ttf in pasta.glob("*.ttf"):
        radical = ttf.stem.split("-")[0].lower()
        if radical not in licencas.replace("-", ""):
            sem.append(ttf.name)
    assert not sem, f"fontes sem arquivo de licenca ao lado: {sem}"
