import pytest

from motor import registro


def test_registro_novo_esta_vazio(tmp_path):
    r = registro.carregar(tmp_path / "registro.json")
    assert r == {}


def test_grava_e_le_de_volta(tmp_path):
    p = tmp_path / "registro.json"
    registro.gravar(p, {"cena-1": {"decisao": "aprovado", "nota": ""}})
    assert registro.carregar(p)["cena-1"]["decisao"] == "aprovado"


def test_pendentes_tira_o_que_ja_foi_decidido(tmp_path):
    p = tmp_path / "registro.json"
    registro.gravar(p, {"a": {"decisao": "aprovado", "nota": ""},
                        "b": {"decisao": "descartado", "nota": "nao gostei"}})
    itens = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    assert [i["id"] for i in registro.pendentes(itens, p)] == ["c"]


def test_item_sem_decisao_continua_pendente(tmp_path):
    p = tmp_path / "registro.json"
    registro.gravar(p, {"a": {"decisao": None, "nota": "pensando"}})
    assert [i["id"] for i in registro.pendentes([{"id": "a"}], p)] == ["a"]


def test_anotar_nao_apaga_o_que_ja_havia(tmp_path):
    p = tmp_path / "registro.json"
    registro.anotar(p, {"a": {"decisao": "aprovado", "nota": ""}})
    registro.anotar(p, {"b": {"decisao": "descartado", "nota": ""}})
    assert set(registro.carregar(p)) == {"a", "b"}


def test_anotar_atualiza_decisao_que_mudou(tmp_path):
    p = tmp_path / "registro.json"
    registro.anotar(p, {"a": {"decisao": "aprovado", "nota": ""}})
    registro.anotar(p, {"a": {"decisao": "descartado", "nota": "mudei de ideia"}})
    assert registro.carregar(p)["a"]["decisao"] == "descartado"
    assert registro.carregar(p)["a"]["nota"] == "mudei de ideia"


def test_decisao_desconhecida_e_recusada(tmp_path):
    with pytest.raises(ValueError, match="talvez"):
        registro.anotar(tmp_path / "r.json", {"a": {"decisao": "talvez"}})


def test_arquivo_corrompido_nao_derruba_o_programa(tmp_path):
    p = tmp_path / "registro.json"
    p.write_text("isto nao e json", encoding="utf-8")
    with pytest.raises(registro.RegistroIlegivel, match="registro"):
        registro.carregar(p)
