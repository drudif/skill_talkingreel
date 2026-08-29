"""O que vem embutido: estilos, corte rapido, legenda do post e servicos."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


# --- Task 4: os estilos, em portugues ---

def test_todo_estilo_do_motor_esta_descrito():
    from motor import estilos
    t = (RAIZ / "referencias/estilos.md").read_text(encoding="utf-8")
    for chave in estilos.ESTILOS:
        assert f"`{chave}`" in t, f"o estilo '{chave}' nao esta descrito"


def test_nenhum_estilo_descrito_deixou_de_existir():
    from motor import estilos
    t = (RAIZ / "referencias/estilos.md").read_text(encoding="utf-8")
    citados = set(re.findall(r"^\| `(\w+)`", t, re.M))
    assert citados <= set(estilos.ESTILOS), (
        f"o arquivo cita estilo que o motor nao tem: "
        f"{citados - set(estilos.ESTILOS)}")


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


def test_a_legenda_do_post_vale_so_para_o_post():
    t = (RAIZ / "referencias/legenda-do-post.md").read_text(encoding="utf-8").lower()
    assert "letreiro" in t, "nao diz que letreiro fica de fora"


def test_os_servicos_trazem_o_numero_medido():
    t = (RAIZ / "referencias/servicos.md").read_text(encoding="utf-8")
    for servico in ("Seedance", "Veed", "MiniMax", "Kling"):
        assert servico in t, f"falta {servico} na tabela"
    assert "255" in t, "a tabela nao traz a escala da medicao"


def test_os_servicos_dizem_qual_nao_serve():
    t = (RAIZ / "referencias/servicos.md").read_text(encoding="utf-8").lower()
    assert "regenera" in t, "nao avisa que o MiniMax regenera em vez de editar"


def test_os_creditos_nomeiam_a_origem_de_cada_coisa():
    t = (RAIZ / "CREDITOS.md").read_text(encoding="utf-8")
    for origem in ("deslopar", "audio-speed", "audio-silence-cut"):
        assert origem in t, f"falta creditar {origem}"


def test_nenhum_dado_pessoal_alem_de_credito_de_autoria():
    """Medido: o unico dado pessoal nas skills incorporadas e credito de
    autoria, que fica. Qualquer outra coisa e vazamento."""
    suspeitos = re.compile(r"gmail|@drudif|instagram\.com/|linkedin\.com/in|\+55",
                           re.I)
    for p in RAIZ.glob("referencias/**/*.md"):
        achado = suspeitos.search(p.read_text(encoding="utf-8"))
        assert not achado, f"{p.name} traz dado pessoal: {achado.group(0)}"
