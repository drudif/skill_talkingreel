"""Testes do contrato entre agentes e motor: leitura e validacao do arquivo de cenas."""
import json

import pytest

from motor import cenas


def _grava(tmp_path, dados, arquivos=("gravacoes/take-01.mov",)):
    """Helper: cria arquivos de teste e escreve o JSON de cenas."""
    for rel in arquivos:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps(dados), encoding="utf-8")
    return p


def test_carrega_o_minimo(tmp_path):
    """Minimo: uma cena de tratamento 'cheia', sem velocidade ou teto sobreposto."""
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    r = cenas.carregar(p)
    assert r.velocidade == 1.15
    assert len(r.cenas) == 1
    assert r.cenas[0].n == 1
    assert r.cenas[0].velocidade == 1.15


def test_velocidade_da_cena_sobrepoe_a_geral(tmp_path):
    """Velocidade da cena sobrepoe a velocidade geral."""
    p = _grava(tmp_path, {"velocidade": 1.15, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "velocidade": 1.0}]})
    assert cenas.carregar(p).cenas[0].velocidade == 1.0


def test_split_sem_topo_e_erro(tmp_path):
    """Split sem topo e um erro."""
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "split", "arquivo": "gravacoes/take-01.mov"}]})
    with pytest.raises(cenas.CenasInvalidas, match="topo"):
        cenas.carregar(p)


def test_tratamento_desconhecido_e_erro(tmp_path):
    """Tratamento desconhecido e um erro."""
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "voadora", "arquivo": "gravacoes/take-01.mov"}]})
    with pytest.raises(cenas.CenasInvalidas, match="voadora"):
        cenas.carregar(p)


def test_arquivo_que_nao_existe_e_erro(tmp_path):
    """Arquivo inexistente e um erro."""
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/sumiu.mov"}]})
    with pytest.raises(cenas.CenasInvalidas, match="sumiu.mov"):
        cenas.carregar(p)


def test_numero_repetido_e_erro(tmp_path):
    """Numero de cena repetido e um erro."""
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"},
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    with pytest.raises(cenas.CenasInvalidas, match="repetid"):
        cenas.carregar(p)


def test_ancora_fora_do_intervalo_e_erro(tmp_path):
    """Ancora fora de [0.0, 1.0] e um erro."""
    p = _grava(tmp_path,
               {"cenas": [{"n": 1, "trat": "split",
                           "arquivo": "gravacoes/take-01.mov",
                           "topo": {"arquivo": "broll/tv.mp4", "ancora": 2.0}}]},
               arquivos=("gravacoes/take-01.mov", "broll/tv.mp4"))
    with pytest.raises(cenas.CenasInvalidas, match="ancora"):
        cenas.carregar(p)


def test_json_invalido_e_erro(tmp_path):
    """JSON invalido produz erro util, nao crash."""
    p = tmp_path / "cenas.json"
    p.write_text('{"cenas": [', encoding="utf-8")
    with pytest.raises(cenas.CenasInvalidas, match="JSON"):
        cenas.carregar(p)


def test_lista_vazia_de_cenas_e_erro(tmp_path):
    """Lista vazia de cenas produz erro util."""
    p = _grava(tmp_path, {"cenas": []})
    with pytest.raises(cenas.CenasInvalidas, match="nenhuma cena"):
        cenas.carregar(p)


def test_o_visual_padrao_quando_nao_e_dito(tmp_path):
    """Quem nao escolhe nada recebe algo que funciona, e nao um erro."""
    from motor import estilos
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    prod = cenas.carregar(p)
    assert prod.legenda_estilo == {} and prod.letreiro_estilo == {}
    # vazio nao quer dizer sem visual: e o padrao, resolvido na hora de desenhar
    assert estilos.compor(prod.legenda_estilo, "legenda")["arquivo"]



def test_o_visual_escolhido_e_lido(tmp_path):
    p = _grava(tmp_path, {
        "legenda_estilo": {"fonte": "serifa", "paleta": "verde"},
        "letreiro_estilo": {"fonte": "pesada", "efeito": "caixa"},
        "cenas": [{"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    prod = cenas.carregar(p)
    assert prod.legenda_estilo["fonte"] == "serifa"
    assert prod.letreiro_estilo["efeito"] == "caixa"


def test_escolher_uma_coisa_nao_obriga_a_escolher_as_outras(tmp_path):
    """A pessoa escolhe a cor sem ter de escolher a letra junto."""
    from motor import estilos
    p = _grava(tmp_path, {
        "legenda_estilo": {"paleta": "rosa"},
        "cenas": [{"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    peca = estilos.compor(cenas.carregar(p).legenda_estilo, "legenda")
    assert peca["paleta"] == "rosa"
    assert peca["fonte"] == estilos.PADRAO_LEGENDA["fonte"]



def test_opcao_inexistente_diz_quais_existem(tmp_path):
    p = _grava(tmp_path, {"legenda_estilo": {"paleta": "roxo-neon"}, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    with pytest.raises(cenas.CenasInvalidas, match="amarelo"):
        cenas.carregar(p)


def test_campo_desconhecido_no_visual_e_erro(tmp_path):
    """Um campo com nome errado seria ignorado em silencio, e a pessoa acharia
    que escolheu."""
    p = _grava(tmp_path, {"legenda_estilo": {"cor": "amarelo"}, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    with pytest.raises(cenas.CenasInvalidas, match="fonte, paleta e efeito"):
        cenas.carregar(p)



def test_letreiro_e_lido(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "letreiro": {"texto": "OLA", "de": 1.0, "ate": 3.0, "box": True}}]})
    c = cenas.carregar(p).cenas[0]
    assert c.letreiro.texto == "OLA"
    assert c.letreiro.de == 1.0
    assert c.letreiro.ate == 3.0
    assert c.letreiro.box is True


def test_letreiro_tem_padroes(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "letreiro": {"texto": "OLA"}}]})
    c = cenas.carregar(p).cenas[0]
    assert c.letreiro.de == 0.0
    assert c.letreiro.ate is None
    assert c.letreiro.box is False


def test_letreiro_sem_texto_e_erro(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "letreiro": {"de": 1.0}}]})
    with pytest.raises(cenas.CenasInvalidas, match="texto"):
        cenas.carregar(p)


def test_letreiro_com_de_negativo_e_erro(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "letreiro": {"texto": "OLA", "de": -1.0}}]})
    with pytest.raises(cenas.CenasInvalidas, match="negativo"):
        cenas.carregar(p)


def test_letreiro_no_jeito_antigo_e_recusado_dizendo_o_que_mudou(tmp_path):
    """`entra` e `dura` contavam no video ja cortado. Aceitar em silencio poria
    o texto na hora errada; recusar sem explicar deixaria quem escreveu sem
    saber o que fazer."""
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "letreiro": {"texto": "OLA", "entra": 1.0, "dura": 2.0}}]})
    with pytest.raises(cenas.CenasInvalidas, match="'de' e 'ate'"):
        cenas.carregar(p)


def test_letreiro_que_some_antes_de_aparecer_e_erro(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "letreiro": {"texto": "OLA", "de": 5.0, "ate": 2.0}}]})
    with pytest.raises(cenas.CenasInvalidas, match="depois do comeco"):
        cenas.carregar(p)


# --- o recorte da cena no arquivo original ---

def test_recorte_da_cena_e_lido(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "de": 12.0, "ate": 25.5}]})
    c = cenas.carregar(p).cenas[0]
    assert c.de == 12.0
    assert c.ate == 25.5


def test_sem_recorte_a_cena_e_o_arquivo_inteiro(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    c = cenas.carregar(p).cenas[0]
    assert c.de is None and c.ate is None


def test_duas_cenas_podem_sair_do_mesmo_arquivo(tmp_path):
    """E o que permite escolher a melhor tomada de uma frase repetida, e usar
    dois pedacos distantes do mesmo take."""
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "de": 0.0, "ate": 5.0},
        {"n": 2, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "de": 30.0, "ate": 40.0}]})
    c = cenas.carregar(p).cenas
    assert c[0].arquivo == c[1].arquivo
    assert (c[0].de, c[1].de) == (0.0, 30.0)


def test_recorte_invertido_e_erro(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "de": 20.0, "ate": 10.0}]})
    with pytest.raises(cenas.CenasInvalidas, match="depois do comeco"):
        cenas.carregar(p)


def test_recorte_negativo_e_erro(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "de": -3.0}]})
    with pytest.raises(cenas.CenasInvalidas, match="negativo"):
        cenas.carregar(p)


def test_letreiro_fora_do_recorte_e_erro(tmp_path):
    """O pior modo de falhar seria aceitar: o filme sai sem o texto e nada
    avisa por que."""
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "de": 10.0, "ate": 20.0,
         "letreiro": {"texto": "OLA", "de": 2.0}}]})
    with pytest.raises(cenas.CenasInvalidas, match="nunca apareceria"):
        cenas.carregar(p)


def test_letreiro_depois_do_fim_do_recorte_e_erro(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "de": 10.0, "ate": 20.0,
         "letreiro": {"texto": "OLA", "de": 25.0}}]})
    with pytest.raises(cenas.CenasInvalidas, match="nunca apareceria"):
        cenas.carregar(p)


def test_legenda_ligada_por_padrao(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    assert cenas.carregar(p).legenda is True


def test_legenda_pode_ser_desligada(tmp_path):
    p = _grava(tmp_path, {"legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    assert cenas.carregar(p).legenda is False


# --- trocas ditadas palavra por palavra ---

def test_trocas_sao_lidas(tmp_path):
    """O unico jeito de consertar erro de SOM na transcricao. Sem este campo no
    contrato, a descoberta de que a comparacao de letras nao pega erro de som
    deixaria a skill sem saida nenhuma para esses casos."""
    p = _grava(tmp_path, {"trocas": {"Sidense": "Seedance"}, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    assert cenas.carregar(p).trocas == {"sidense": "Seedance"}


def test_sem_trocas_o_campo_vem_vazio(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    assert cenas.carregar(p).trocas == {}


def test_trocas_em_formato_errado_e_erro(tmp_path):
    p = _grava(tmp_path, {"trocas": ["sidense", "Seedance"], "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    with pytest.raises(cenas.CenasInvalidas, match="jeito certo"):
        cenas.carregar(p)


def test_troca_com_lado_vazio_e_erro(tmp_path):
    p = _grava(tmp_path, {"trocas": {"sidense": "  "}, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    with pytest.raises(cenas.CenasInvalidas, match="texto"):
        cenas.carregar(p)
