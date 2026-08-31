"""O que vem embutido: estilos, corte rapido, legenda do post e servicos."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


# --- Task 4: os estilos, em portugues ---

def test_toda_escolha_do_motor_esta_descrita():
    """Uma opcao que existe no motor e nao aparece aqui e uma opcao que ninguem
    vai pedir."""
    from motor import estilos
    t = (RAIZ / "referencias/estilos.md").read_text(encoding="utf-8")
    for grupo in (estilos.FONTES_LEGENDA, estilos.FONTES_LETREIRO,
                  estilos.PALETAS, estilos.EFEITOS):
        for chave in grupo:
            assert f"`{chave}`" in t, f"a opcao '{chave}' nao esta descrita"



def test_nenhuma_opcao_descrita_deixou_de_existir():
    """O contrario: o arquivo prometendo o que o motor nao tem."""
    from motor import estilos
    t = (RAIZ / "referencias/estilos.md").read_text(encoding="utf-8")
    existem = (set(estilos.FONTES_LEGENDA) | set(estilos.FONTES_LETREIRO)
               | set(estilos.PALETAS) | set(estilos.EFEITOS))
    citadas = set(re.findall(r"^\| `([^`]+)`", t, re.M))
    assert citadas <= existem, (
        f"o arquivo cita opcao que o motor nao tem: {citadas - existem}")



def test_o_arquivo_de_estilos_nao_repete_cor_nem_fonte():
    """Repetir valor cria duas fontes de verdade. Aqui so entra a descricao;
    cor, fonte e peso moram em motor/estilos.py."""
    t = (RAIZ / "referencias/estilos.md").read_text(encoding="utf-8")
    assert not re.search(r"#[0-9A-Fa-f]{6}", t), "vazou codigo de cor"
    assert ".otf" not in t and ".ttf" not in t, "vazou nome de arquivo de fonte"


# --- Task 5: o que vem embutido ---

def test_o_corte_rapido_avisa_que_o_pipeline_usa_outra_coisa():
    t = (RAIZ / "referencias/corte-rapido.md").read_text(encoding="utf-8").lower()
    assert "avulso" in t or "fora das fases" in t or "nao usa" in t, (
        "alguem vai usar a ferramenta avulsa dentro do pipeline")
    assert "energia" in t, "nao explica por que a do motor e melhor"


def test_os_servicos_trazem_o_numero_medido():
    t = (RAIZ / "referencias/servicos.md").read_text(encoding="utf-8")
    for servico in ("Seedance", "Veed", "MiniMax", "Kling"):
        assert servico in t, f"falta {servico} na tabela"
    assert "255" in t, "a tabela nao traz a escala da medicao"


def test_os_servicos_dizem_qual_nao_serve():
    t = (RAIZ / "referencias/servicos.md").read_text(encoding="utf-8").lower()
    assert "regenera" in t, "nao avisa que o MiniMax regenera em vez de editar"


def test_os_creditos_nomeiam_a_origem_de_cada_coisa():
    """A `deslopar` saiu da lista junto com a legenda do post, que deixou de
    fazer parte desta skill. O que ficou continua creditado."""
    t = (RAIZ / "CREDITOS.md").read_text(encoding="utf-8")
    for origem in ("audio-speed", "audio-silence-cut", "um-carrossel-por-favor"):
        assert origem in t, f"falta creditar {origem}"


def test_as_fontes_estao_creditadas_uma_a_uma():
    """Fonte no repositorio sem credito e sem licenca e um problema que aparece
    depois de publicar."""
    from motor import estilos
    t = (RAIZ / "CREDITOS.md").read_text(encoding="utf-8").lower()
    assert "assets/fontes" in t, "os creditos nao dizem onde as fontes moram"
    for familia in ("cascadia", "anton", "chivo", "fraunces", "bodoni",
                    "karla", "jakarta"):
        assert familia in t, f"a fonte '{familia}' nao esta creditada"


def test_nenhum_dado_pessoal_alem_de_credito_de_autoria():
    """Medido: o unico dado pessoal nas skills incorporadas e credito de
    autoria, que fica. Qualquer outra coisa e vazamento."""
    suspeitos = re.compile(r"gmail|@drudif|instagram\.com/|linkedin\.com/in|\+55",
                           re.I)
    for p in RAIZ.glob("referencias/**/*.md"):
        achado = suspeitos.search(p.read_text(encoding="utf-8"))
        assert not achado, f"{p.name} traz dado pessoal: {achado.group(0)}"
