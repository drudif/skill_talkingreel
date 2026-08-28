import json
import re

import pytest

from motor import folha


def _itens(n=2):
    return [{"id": f"i{k}", "titulo": f"Item {k}",
             "fato": f"Fato medido numero {k}."} for k in range(n)]


def test_gera_um_documento_completo(tmp_path):
    p = folha.escrever(_itens(), "estrutura", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "</html>" in html


def test_cada_item_aparece_uma_vez(tmp_path):
    p = folha.escrever(_itens(3), "estrutura", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    for k in range(3):
        assert html.count(f"Fato medido numero {k}.") == 1


def test_o_estado_esta_entre_os_marcadores_uma_vez_so(tmp_path):
    """A armadilha do projeto de origem: dois blocos parecidos no mesmo
    arquivo, e quem lesse o segundo apagava o feedback da pessoa."""
    p = folha.escrever(_itens(), "estrutura", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    assert html.count(folha.INI) == 1, "o marcador de inicio aparece mais de uma vez"
    assert html.count(folha.FIM) == 1, "o marcador de fim aparece mais de uma vez"


def test_o_estado_e_json_valido_e_traz_os_itens(tmp_path):
    p = folha.escrever(_itens(2), "arte", tmp_path / "f.html")
    estado = folha.ler(p)
    assert estado["fase"] == "arte"
    assert [i["id"] for i in estado["itens"]] == ["i0", "i1"]
    assert all(i["decisao"] is None for i in estado["itens"])


def test_ler_devolve_as_decisoes_que_a_pessoa_tomou(tmp_path):
    p = folha.escrever(_itens(2), "estrutura", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    estado = folha.ler(p)
    estado["itens"][0]["decisao"] = "aprovado"
    estado["itens"][1]["decisao"] = "descartado"
    estado["itens"][1]["nota"] = "esse trecho nao"
    novo = html.replace(
        html[html.index(folha.INI):html.index(folha.FIM) + len(folha.FIM)],
        folha.INI + json.dumps(estado, ensure_ascii=False) + folha.FIM)
    (tmp_path / "g.html").write_text(novo, encoding="utf-8")
    lido = folha.ler(tmp_path / "g.html")
    assert lido["itens"][0]["decisao"] == "aprovado"
    assert lido["itens"][1]["nota"] == "esse trecho nao"


def test_texto_com_html_dentro_nao_quebra_a_pagina(tmp_path):
    itens = [{"id": "x", "titulo": "<script>alert(1)</script>",
              "fato": 'aspas " e < e &'}]
    p = folha.escrever(itens, "estrutura", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert folha.ler(p)["itens"][0]["titulo"] == "<script>alert(1)</script>"


def test_folha_sem_item_nenhum_diz_isso(tmp_path):
    p = folha.escrever([], "corte", tmp_path / "f.html")
    assert "nada" in p.read_text(encoding="utf-8").lower()


def test_id_repetido_e_recusado(tmp_path):
    itens = [{"id": "a", "titulo": "A", "fato": "."},
             {"id": "a", "titulo": "B", "fato": "."}]
    with pytest.raises(ValueError, match="repetid"):
        folha.escrever(itens, "estrutura", tmp_path / "f.html")


def test_item_sem_id_e_recusado(tmp_path):
    with pytest.raises(ValueError, match="id"):
        folha.escrever([{"titulo": "A", "fato": "."}], "estrutura",
                       tmp_path / "f.html")


def test_a_pagina_e_pequena(tmp_path):
    """O custo de token de uma pagina grande e real: no projeto de origem o
    modelo reescrevia 50 KB de HTML a cada rodada."""
    p = folha.escrever(_itens(5), "estrutura", tmp_path / "f.html")
    assert len(p.read_bytes()) < 12_000, (
        f"a folha de 5 itens saiu com {len(p.read_bytes())} bytes")


def test_a_folha_seguinte_carrega_so_o_pendente(tmp_path):
    from motor import registro
    itens = [{"id": f"i{k}", "titulo": f"Item {k}", "fato": "."}
             for k in range(5)]
    reg = tmp_path / "registro.json"

    p1 = folha.publicar(itens, "estrutura", tmp_path / "f1.html", reg)
    assert len(folha.ler(p1)["itens"]) == 5

    # a pessoa decide tres e a pagina se republica
    estado = folha.ler(p1)
    for k, d in ((0, "aprovado"), (1, "descartado"), (2, "aprovado")):
        estado["itens"][k]["decisao"] = d
    folha.recolher(estado, reg)

    p2 = folha.publicar(itens, "estrutura", tmp_path / "f2.html", reg)
    assert [i["id"] for i in folha.ler(p2)["itens"]] == ["i3", "i4"]


def test_recolher_guarda_a_nota_junto(tmp_path):
    from motor import registro
    reg = tmp_path / "r.json"
    folha.recolher({"fase": "arte", "itens": [
        {"id": "a", "decisao": "descartado", "nota": "muito rapido"}]}, reg)
    assert registro.carregar(reg)["a"]["nota"] == "muito rapido"


def test_recolher_ignora_quem_nao_decidiu(tmp_path):
    from motor import registro
    reg = tmp_path / "r.json"
    folha.recolher({"fase": "arte", "itens": [
        {"id": "a", "decisao": None, "nota": ""}]}, reg)
    assert registro.carregar(reg) == {}


def test_tudo_decidido_da_uma_folha_vazia(tmp_path):
    reg = tmp_path / "r.json"
    itens = [{"id": "a", "titulo": "A", "fato": "."}]
    folha.recolher({"fase": "corte", "itens": [
        {"id": "a", "decisao": "aprovado", "nota": ""}]}, reg)
    p = folha.publicar(itens, "corte", tmp_path / "f.html", reg)
    assert folha.ler(p)["itens"] == []
    assert "nada" in p.read_text(encoding="utf-8").lower()
