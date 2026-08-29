"""Testes do SKILL.md e das referencias que ele cita: a camada de instrucao
que orquestra os agentes por cima do motor."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "SKILL.md"


def _frontmatter(caminho):
    texto = caminho.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
    assert m, f"{caminho.name} nao tem frontmatter"
    return dict(
        (k.strip(), v.strip().strip('"'))
        for k, v in (l.split(":", 1) for l in m.group(1).split("\n") if ":" in l))


def test_o_skill_existe_e_tem_frontmatter():
    fm = _frontmatter(SKILL)
    assert fm["name"] == "talking-reel-done"
    assert len(fm["description"]) > 80, "a descricao precisa dizer quando usar"


def test_a_descricao_diz_quando_usar_sem_jargao():
    d = _frontmatter(SKILL)["description"].lower()
    assert any(x in d for x in ("falando", "camera", "talking head")), (
        "a descricao nao diz que tipo de video e")
    assert any(x in d for x in ("instagram", "tiktok", "reel", "vertical")), (
        "a descricao nao diz para onde o video vai")


def test_o_skill_cabe_no_teto():
    n = len(SKILL.read_text(encoding="utf-8").rstrip().split("\n"))
    assert n <= 120, f"o SKILL.md tem {n} linhas, teto 120"


def test_as_tres_fases_estao_no_skill():
    t = SKILL.read_text(encoding="utf-8").lower()
    for fase in ("estrutura", "arte", "corte"):
        assert fase in t, f"a fase '{fase}' nao aparece no SKILL.md"


def test_os_quatro_agentes_estao_no_skill():
    t = SKILL.read_text(encoding="utf-8")
    for agente in ("Bluey", "Bandit", "Chili", "Bingo"):
        assert agente in t, f"o agente {agente} nao aparece no SKILL.md"


def test_todo_arquivo_citado_existe():
    """Um caminho que nao existe e uma instrucao que o agente nao consegue
    seguir, e ele descobre isso no meio do trabalho da pessoa."""
    texto = SKILL.read_text(encoding="utf-8")
    for rel in re.findall(r"`(referencias/[\w/.-]+\.md)`", texto):
        assert (RAIZ / rel).exists(), f"o SKILL.md cita {rel}, que nao existe"


def test_os_limites_apontam_para_o_modulo_e_nao_repetem_a_regra():
    """Duplicar o texto das regras cria duas fontes de verdade, e uma delas
    fica para tras. A soma de verificacao vigia so uma."""
    t = (RAIZ / "referencias/limites.md").read_text(encoding="utf-8")
    assert "motor/limites.py" in t
    assert "python3 -c" in t or "python3 -m" in t, (
        "o arquivo tem de dizer COMO ler as regras do modulo")


def test_o_modelo_de_perfil_esta_vazio():
    """O perfil preenchido do autor nao pode vazar para o repositorio."""
    t = (RAIZ / "talkingreel-perfil-modelo.md").read_text(encoding="utf-8")
    for dado in ("Drudi", "Fernando", "@drudif", "gmail", "instagram.com/",
                 "linkedin.com/in"):
        assert dado.lower() not in t.lower(), f"o modelo traz '{dado}'"
    assert t.count("[") >= 5, "o modelo deveria ser so lacunas para preencher"


def test_o_contrato_descreve_todo_campo_que_o_motor_le():
    """Um campo sem documentacao e um campo que nenhum agente vai usar."""
    from motor import cenas
    t = (RAIZ / "referencias/contrato.md").read_text(encoding="utf-8")
    for campo in ("estilo", "legenda", "legenda_split", "proprios",
                  "velocidade", "trilha", "cenas", "trat", "arquivo",
                  "topo", "teto", "letreiro"):
        assert f"`{campo}`" in t, f"o contrato nao explica o campo '{campo}'"


def test_o_contrato_avisa_da_escala_de_tempo_do_letreiro():
    """A armadilha mais facil de cair: ler o instante da gravacao crua."""
    t = (RAIZ / "referencias/contrato.md").read_text(encoding="utf-8").lower()
    assert "depois do corte" in t and "velocidade" in t
