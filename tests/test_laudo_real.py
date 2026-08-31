"""Roda contra gravacao de verdade, se houver. Pula sozinho quando nao houver
-- ninguem que clonar este repositorio tem os arquivos do autor.

POR QUE ESTE ARQUIVO EXISTE. Quatro defeitos desta skill so apareceram com
material do usuario, nunca com clipe sintetico: o `alimiter` que nao segurava
o teto, o recorte do split que pegava a faixa errada, a deteccao de area util
que ficava cega abaixo de 1s, e a medicao de emenda que usava o silencio como
referencia num filme que quase nao tem silencio."""
import json
import os
import shutil
from pathlib import Path

import pytest

from motor import laudo, montar, probe

ORIGEM = Path(os.environ.get(
    "GRAVACOES_REAIS",
    Path.home() / "Desktop/VIBECODING/conteudo/agentes-ginsu/assets"))

REAL = pytest.mark.skipif(
    not (ORIGEM / "gravacoes").is_dir(),
    reason=f"sem gravacao real em {ORIGEM}; aponte com GRAVACOES_REAIS=")


def _cenario(tmp_path, teto=5.0):
    takes = sorted((ORIGEM / "gravacoes").glob("*.mov"))[:2]
    brolls = sorted((ORIGEM / "broll").glob("*.mp4"))[:1]
    if len(takes) < 2 or not brolls:
        pytest.skip("faltou take ou material de apoio")

    (tmp_path / "gravacoes").mkdir(exist_ok=True)
    (tmp_path / "broll").mkdir(exist_ok=True)
    for t in takes:
        shutil.copy(t, tmp_path / "gravacoes" / t.name)
    shutil.copy(brolls[0], tmp_path / "broll" / brolls[0].name)

    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({
        "velocidade": 1.15, "estilo": "brutalista", "legenda": False,
        "cenas": [
            {"n": 1, "trat": "cheia", "arquivo": f"gravacoes/{takes[0].name}",
             "teto": teto,
             "letreiro": {"texto": "TESTE", "de": 0.8, "ate": 2.3}},
            {"n": 2, "trat": "split", "arquivo": f"gravacoes/{takes[1].name}",
             "teto": teto,
             "topo": {"arquivo": f"broll/{brolls[0].name}"}}]}),
        encoding="utf-8")
    return p


@REAL
def test_um_filme_de_verdade_passa_no_laudo(tmp_path):
    p = _cenario(tmp_path)
    filme = montar.montar(p, tmp_path / "f.mp4")
    r = laudo.rodar(filme, p)
    assert r["dimensao"] == [1080, 1920]
    assert r["cenas"] == 2
    assert abs(r["dif_video_audio"]) < 0.10, (
        f"imagem e som se afastaram {r['dif_video_audio']:.3f}s")
    assert r["ok"] is True, r["problemas"]


@REAL
def test_o_letreiro_nao_afasta_imagem_e_som_em_material_real(tmp_path):
    """O `-shortest` do overlay comia quadros e so aparecia medindo. Com
    gravacao real o efeito era maior que com clipe sintetico."""
    p = _cenario(tmp_path)
    dados = json.loads(p.read_text(encoding="utf-8"))
    sem = tmp_path / "sem.json"
    for c in dados["cenas"]:
        c.pop("letreiro", None)
    sem.write_text(json.dumps(dados), encoding="utf-8")

    com_letreiro = montar.montar(p, tmp_path / "com.mp4", tmp=tmp_path / "t1")
    sem_letreiro = montar.montar(sem, tmp_path / "sem.mp4", tmp=tmp_path / "t2")

    dif_com = abs(laudo.rodar(com_letreiro, p)["dif_video_audio"])
    dif_sem = abs(laudo.rodar(sem_letreiro, sem)["dif_video_audio"])
    assert dif_com <= dif_sem + 0.005, (
        f"o letreiro afastou imagem e som: {dif_com:.3f}s com, "
        f"{dif_sem:.3f}s sem")


@REAL
def test_a_medida_de_emenda_nao_acusa_corte_bom_em_material_real(tmp_path):
    """O risco desta medicao e o falso alarme: respiracao e ruido de boca perto
    do corte podem passar do limiar num take de verdade, coisa que o clipe
    sintetico nunca reproduz. Se este teste acusar, a margem esta apertada."""
    p = _cenario(tmp_path)
    filme = montar.montar(p, tmp_path / "f.mp4")
    r = laudo.rodar(filme, p)
    assert r["emendas"] == [], (
        f"acusou emenda em corte que o motor fez sozinho: {r['emendas']}. "
        "Se o corte estiver bom mesmo, a margem de MARGEM_EMENDA esta apertada "
        "para material real.")
    assert probe.tem_audio(filme) is True
