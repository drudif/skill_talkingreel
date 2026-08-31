"""Os quatro agentes. Cada arquivo e lido so quando aquele agente e despachado,
entao ele tem de ser curto e tem de dizer os limites daquele agente."""
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
AGENTES = ["bluey", "bandit", "chili", "bingo"]


def _texto(nome):
    return (RAIZ / f"referencias/agentes/{nome}.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("nome", AGENTES)
def test_cada_agente_cabe_no_teto(nome):
    n = len(_texto(nome).rstrip().split("\n"))
    assert n <= 80, f"{nome}.md tem {n} linhas, teto 80"


@pytest.mark.parametrize("nome", AGENTES)
def test_cada_agente_tem_as_secoes_obrigatorias(nome):
    t = _texto(nome)
    for secao in ("## Quem você é", "## O que você recebe",
                  "## O que você NÃO faz", "## O que você devolve"):
        assert secao in t, f"{nome}.md nao tem a secao '{secao}'"


def test_so_o_bingo_roda_o_motor():
    """A regra de ferro. Se outro agente rodar o motor, a calibragem sai do
    codigo medido e volta para o prompt, que e onde ela se perde."""
    for nome in AGENTES:
        roda = "python3 -m motor" in _texto(nome)
        assert roda == (nome == "bingo"), (
            f"{nome}.md {'roda' if roda else 'nao roda'} o motor")


def test_nenhum_agente_escreve_ffmpeg():
    """Escrever ffmpeg na mao joga fora toda a calibragem medida, e o erro so
    aparece no video final."""
    for nome in AGENTES:
        t = _texto(nome)
        for linha in t.split("\n"):
            if "ffmpeg" in linha:
                assert "NÃO" in t or "Não escreve comando de ffmpeg" in t, (
                    f"{nome}.md cita ffmpeg sem proibir")


def test_o_bandit_nao_pode_inventar_fala():
    t = _texto("bandit").lower()
    assert "nunca invente frase que a pessoa não falou" in t, (
        "o bandit.md nao proibe inventar frase, com essas palavras")


def test_a_chili_sabe_que_a_arte_dela_e_letreiro():
    t = _texto("chili").lower()
    assert "sua arte é letreiro" in t
    for proibido in ("grafismo", "ilustra", "ícone", "decorativ"):
        assert proibido in t, f"a chili.md nao diz que nao faz '{proibido}'"


def test_o_bluey_roda_o_laudo_antes_da_folha():
    t = _texto("bluey").lower()
    assert "antes de publicar qualquer folha" in t
    assert "limites.verificar" in t, "o bluey nao verifica os limites"


def test_so_o_bluey_publica_folha():
    """Duas vozes falando com a pessoa e o caminho mais curto para ela receber
    duas versoes do mesmo fato."""
    assert "único que fala com a pessoa" in _texto("bluey")
    assert "folha.ler" in _texto("bluey") and "folha.recolher" in _texto("bluey")
    for outro in ("bandit", "chili", "bingo"):
        t = _texto(outro)
        assert "folha.ler" not in t and "folha.recolher" not in t, (
            f"{outro}.md mexe na folha, que e trabalho do Bluey")


def test_a_chili_ancora_o_letreiro_no_segundo_da_gravacao():
    """Quem escolhe o instante do letreiro e a Chili, e a regra e a coordenada
    unica: ela anota o segundo da GRAVACAO e nao faz conta nenhuma. Se ela
    voltar a somar tempos de cena a mao, o letreiro cai no lugar errado e o
    erro cresce ao longo do filme."""
    t = _texto("chili").lower()
    assert "segundos da grava" in t, (
        "a chili nao diz que o instante do letreiro e segundo da gravacao")
    assert "não faça conta" in t or "nao faca conta" in t, (
        "a chili nao diz que a conversao e do motor, nao dela")


def test_o_bingo_sabe_quando_ligar_a_legenda():
    """Transcrever e a etapa mais cara. Gastar num corte que ainda vai mudar e
    desperdicio que a pessoa espera sentada."""
    t = _texto("bingo").lower()
    assert '"legenda": true' in t and "false" in t


def test_o_bluey_pergunta_antes_de_mandar_transcrever():
    """A ordem que custa dinheiro se for invertida: medir, perguntar, trabalhar.

    Transcrever e a etapa mais cara do trabalho todo. Propor corte e letreiro
    para quem ja tem roteiro gasta duas vezes: uma para produzir, outra porque
    a pessoa tem de ler e recusar o que nao pediu."""
    t = _texto("bluey").lower()
    assert "quatro perguntas" in t, "o bluey nao faz as perguntas antes"
    assert "espere a resposta" in t
    for assunto in ("roteiro", "música", "quanto tempo"):
        assert assunto in t, f"as perguntas nao cobrem '{assunto}'"
    # o Bingo mede antes; o Bandit so entra depois das respostas
    pos_bingo = t.find("dispare só o bingo")
    pos_bandit = t.find("dispare o bandit")
    assert 0 <= pos_bingo < pos_bandit, (
        "o bluey manda transcrever antes de medir e perguntar")


def test_o_bandit_nao_comeca_sem_as_respostas():
    t = _texto("bandit").lower()
    assert "respostas da pessoa" in t
    assert "peça ao bluey" in t or "peca ao bluey" in t, (
        "o bandit nao diz o que fazer quando as respostas nao vem junto")


def test_nenhum_agente_sugere_material_que_a_pessoa_nao_tem():
    """Sugerir b-roll para quem nao mandou nenhum e propor trabalho que ela nao
    pode aceitar -- ou gravar de novo, ou pagar um servico."""
    t = _texto("bandit").lower()
    assert "se ela tiver mandado" in t or "só se ela tiver mandado" in t, (
        "o bandit pode propor material complementar que nao existe")
    assert "não sugira que ela grave" in t or "nao sugira que ela grave" in t
