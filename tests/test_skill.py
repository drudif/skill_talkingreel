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


def test_as_duas_aprovacoes_estao_no_skill():
    """Duas, nao tres. A pessoa espera uma resposta a cada folha, e cada folha
    a mais e uma rodada a mais de espera dela."""
    t = SKILL.read_text(encoding="utf-8").lower()
    assert "duas aprova" in t, "o SKILL.md nao diz que sao duas aprovacoes"
    for palavra in ("primeira", "segunda"):
        assert palavra in t, f"a aprovacao '{palavra}' nao aparece no SKILL.md"
    assert "sem a resposta" in t, (
        "o SKILL.md nao diz que nao se passa de uma folha sem a resposta")


def test_o_skill_diz_o_que_e_obrigatorio_receber():
    """Sem a gravacao nao ha trabalho. O resto e opcional, e a skill nao pode
    cobrar da pessoa o que nao precisa."""
    t = SKILL.read_text(encoding="utf-8").lower()
    assert "obrigatório" in t or "obrigatorio" in t
    assert "opcional" in t


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


def test_o_contrato_descreve_todo_campo_que_o_motor_le():
    """Um campo sem documentacao e um campo que nenhum agente vai usar."""
    from motor import cenas
    t = (RAIZ / "referencias/contrato.md").read_text(encoding="utf-8")
    for campo in ("legenda_estilo", "letreiro_estilo", "legenda",
                  "legenda_split", "proprios",
                  "velocidade", "trilha", "cenas", "trat", "arquivo",
                  "topo", "teto", "letreiro", "de", "ate",
                  "fundo", "contraste", "trocas", "abertura", "glitch"):
        assert f"`{campo}`" in t, f"o contrato nao explica o campo '{campo}'"


def test_o_contrato_diz_que_todo_tempo_e_da_gravacao():
    """A coordenada unica so funciona se estiver escrita onde quem preenche o
    arquivo le. Sem isso alguem volta a anotar o tempo do filme pronto."""
    t = (RAIZ / "referencias/contrato.md").read_text(encoding="utf-8").lower()
    assert "segundo da grava" in t, (
        "o contrato nao diz que todo instante e segundo da gravacao")
    assert "motor/tempo.py" in t, "nao diz quem faz a conversao"


def test_o_skill_manda_medir_perguntar_e_so_entao_trabalhar():
    """A ordem das tres etapas e o que evita gastar a etapa cara a toa. Medir e
    barato e nao decide nada; perguntar e de graca; transcrever custa."""
    t = SKILL.read_text(encoding="utf-8").lower()
    assert "meça primeiro, pergunte depois, trabalhe por último" in t, (
        "o SKILL.md nao fixa a ordem das tres etapas")
    assert "não transcreva" in t, (
        "o SKILL.md nao proibe transcrever antes das respostas")
    assert "puláveis" in t, "as perguntas precisam poder ser puladas"


def test_o_skill_diz_o_que_acontece_quem_nao_responde():
    """Pergunta pulavel sem padrao definido trava o trabalho de quem so quer o
    video pronto."""
    t = SKILL.read_text(encoding="utf-8").lower()
    assert "quem pular todas recebe o padrão" in t


def test_o_skill_apresenta_o_caminho_inteiro_antes_de_comecar():
    """Quem chega nao sabe o que vai ser perguntado, quantas vezes vai precisar
    responder, nem quanto tempo leva. Descobrir isso no meio, a conta-gotas, e
    o que faz desistir na metade."""
    t = SKILL.read_text(encoding="utf-8").lower()
    assert "como vai funcionar" in t, (
        "o SKILL.md nao manda apresentar o fluxo na primeira mensagem")
    assert "duas vezes" in t, "nao diz quantas vezes a pessoa vai ser chamada"
    for etapa in ("manda a gravação", "quatro perguntas", "folha de aprovação",
                  "para assistir"):
        assert etapa in t, f"a apresentacao nao cita '{etapa}'"


def test_a_apresentacao_diz_o_que_e_obrigatorio_logo_no_comeco():
    """Pedir tudo de uma vez e melhor que pedir uma coisa de cada vez, e a
    pessoa precisa saber que so a gravacao e indispensavel."""
    t = SKILL.read_text(encoding="utf-8").lower()
    assert "só ela é obrigatória" in t or "so ela e obrigatoria" in t
    assert "dá certo sem nada disso" in t or "da certo sem nada disso" in t
