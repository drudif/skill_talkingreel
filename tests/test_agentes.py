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


def test_a_armadilha_do_tempo_do_letreiro_esta_na_chili():
    """Quem escolhe o instante do letreiro e a Chili. Se ela ler o instante da
    gravacao crua, o letreiro cai no lugar errado e o erro cresce ao longo do
    filme."""
    t = _texto("chili").lower()
    assert "já pronta" in t and "velocidade" in t


def test_o_bingo_sabe_quando_ligar_a_legenda():
    """Transcrever e a etapa mais cara. Gastar num corte que ainda vai mudar e
    desperdicio que a pessoa espera sentada."""
    t = _texto("bingo").lower()
    assert '"legenda": true' in t and "false" in t
