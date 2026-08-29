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


def test_estilo_padrao_quando_nao_dito(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    assert cenas.carregar(p).estilo == "brutalista"


def test_estilo_escolhido(tmp_path):
    p = _grava(tmp_path, {"estilo": "terminal", "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    assert cenas.carregar(p).estilo == "terminal"


def test_estilo_inexistente_diz_quais_existem(tmp_path):
    p = _grava(tmp_path, {"estilo": "roxo-neon", "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    with pytest.raises(cenas.CenasInvalidas, match="brutalista"):
        cenas.carregar(p)


def test_letreiro_e_lido(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "letreiro": {"texto": "OLA", "entra": 1.0, "dura": 2.0, "box": True}}]})
    c = cenas.carregar(p).cenas[0]
    assert c.letreiro.texto == "OLA"
    assert c.letreiro.entra == 1.0
    assert c.letreiro.dura == 2.0
    assert c.letreiro.box is True


def test_letreiro_tem_padroes(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "letreiro": {"texto": "OLA"}}]})
    c = cenas.carregar(p).cenas[0]
    assert c.letreiro.entra == 0.0
    assert c.letreiro.dura is None
    assert c.letreiro.box is False


def test_letreiro_sem_texto_e_erro(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "letreiro": {"entra": 1.0}}]})
    with pytest.raises(cenas.CenasInvalidas, match="texto"):
        cenas.carregar(p)


def test_letreiro_com_entra_negativo_e_erro(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "letreiro": {"texto": "OLA", "entra": -1.0}}]})
    with pytest.raises(cenas.CenasInvalidas, match="entra"):
        cenas.carregar(p)


def test_legenda_ligada_por_padrao(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    assert cenas.carregar(p).legenda is True


def test_legenda_pode_ser_desligada(tmp_path):
    p = _grava(tmp_path, {"legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    assert cenas.carregar(p).legenda is False
