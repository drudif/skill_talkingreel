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
