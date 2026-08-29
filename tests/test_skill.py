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
