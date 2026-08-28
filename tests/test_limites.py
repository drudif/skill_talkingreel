"""A salvaguarda nao impede a remocao dos limites eticos — impede que ela
aconteca em silencio. Estes testes provam que uma instalacao adulterada se
anuncia no laudo e no codigo de saida."""
import json

from motor import laudo, limites, montar
from tests import fixtures


def test_a_instalacao_intacta_nao_reclama():
    estado, recado = limites.verificar()
    assert estado == limites.INTACTO
    assert recado == ""


def test_a_soma_gravada_bate_com_o_texto():
    assert limites.soma_atual() == limites.SOMA, (
        "o texto das regras mudou sem a soma ser atualizada")


def test_as_cinco_recusas_estao_escritas():
    texto = limites.em_portugues().lower()
    for termo in ("sexual", "violencia", "misoginia", "racismo", "odio"):
        assert termo in texto, f"a regra sobre {termo} sumiu"


def test_vale_para_o_material_do_usuario_e_para_o_gerado():
    texto = limites.em_portugues().lower()
    assert "gravacao do proprio usuario" in texto
    assert "gera" in texto


def test_regra_editada_e_denunciada(monkeypatch):
    """Alguem apaga uma das recusas e nao atualiza a soma."""
    monkeypatch.setattr(limites, "REGRAS", "so vale o que eu quiser")
    estado, recado = limites.verificar()
    assert estado == limites.ALTERADO
    assert "alterados" in recado


def test_regra_esvaziada_e_denunciada(monkeypatch):
    """Alguem apaga o texto inteiro."""
    monkeypatch.setattr(limites, "REGRAS", "   \n  ")
    estado, recado = limites.verificar()
    assert estado == limites.AUSENTE
    assert "esvaziados" in recado


def test_o_laudo_reprova_instalacao_alterada(tmp_path, monkeypatch):
    """O caminho que importa: o laudo e o que roda antes de qualquer coisa
    subir na folha de aprovacao."""
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.4, 1.0)], total=2.5)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov"}]}),
        encoding="utf-8")
    filme = montar.montar(p, tmp_path / "f.mp4")

    intacto = laudo.rodar(filme, p)
    assert intacto["ok"] is True
    assert intacto["limites"] == limites.INTACTO

    monkeypatch.setattr(limites, "REGRAS", "nenhuma")
    adulterado = laudo.rodar(filme, p)
    assert adulterado["ok"] is False
    assert adulterado["limites"] == limites.ALTERADO
    assert any("limites eticos" in x for x in adulterado["problemas"])


def test_a_pessoa_le_o_aviso_em_portugues(tmp_path, monkeypatch):
    monkeypatch.setattr(limites, "REGRAS", "nenhuma")
    texto = laudo.em_portugues(laudo.rodar(
        fixtures.clipe_fala(tmp_path / "x.mov", falas=[(0.2, 0.8)], total=2.0)))
    assert "limites eticos" in texto
    for jargao in ("hash", "sha256", "checksum", "assert"):
        assert jargao not in texto.lower()
