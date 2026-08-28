import itertools
import json

from motor import config, fala, montar, probe
from tests import fixtures


def _producao(tmp_path, n_cenas=3):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    lista = []
    for i in range(1, n_cenas + 1):
        fixtures.clipe_fala(tmp_path / "gravacoes" / f"take-{i:02d}.mov",
                            falas=[(0.4, 1.2)], total=3.0)
        lista.append({"n": i, "trat": "cheia",
                      "arquivo": f"gravacoes/take-{i:02d}.mov"})
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "cenas": lista}), encoding="utf-8")
    return p


def test_o_filme_sai_no_formato_certo(tmp_path):
    filme = montar.montar(_producao(tmp_path), tmp_path / "filme.mp4")
    assert probe.dimensao(filme) == (1080, 1920)


def test_o_filme_soma_as_cenas(tmp_path):
    filme = montar.montar(_producao(tmp_path, n_cenas=3), tmp_path / "filme.mp4")
    # cada cena tem ~1.2s de fala mais respiro; tres cenas passam de 3s
    assert probe.dur(filme) > 3.0


def test_audio_e_video_terminam_juntos(tmp_path):
    filme = montar.montar(_producao(tmp_path), tmp_path / "filme.mp4")
    d_v, d_a = montar.duracoes(filme)
    assert abs(d_v - d_a) < 0.10


def test_o_mapa_de_cenas_e_gravado(tmp_path):
    montar.montar(_producao(tmp_path), tmp_path / "filme.mp4")
    mapa = json.loads((tmp_path / "cenas-mapa.json").read_text(encoding="utf-8"))
    assert len(mapa) == 3
    assert mapa[0]["ini"] == 0.0
    assert mapa[0]["fim"] == mapa[1]["ini"]      # sem buraco entre as cenas


def test_dessync_nao_acumula_em_muitas_emendas(tmp_path):
    """A ARMADILHA CENTRAL: com o concat demuxer o atraso crescia a cada emenda
    e so aparecia depois de muitas cenas. Um filme de 3 cenas nao pega isso —
    aqui sao 10, e comparamos a soma dos segmentos individuais com o filme
    inteiro para flagrar audio descartado na juncao."""
    seg_dir = tmp_path / "segmentos"
    filme = montar.montar(_producao(tmp_path, n_cenas=10), tmp_path / "filme.mp4",
                          tmp=seg_dir)

    d_v, d_a = montar.duracoes(filme)
    assert abs(d_v - d_a) < 0.10

    segmentos = sorted(seg_dir.glob("s*.mov"))
    assert len(segmentos) == 10
    soma = sum(probe.dur(s) for s in segmentos)
    assert abs(probe.dur(filme) - soma) < 0.15


def _regioes_altas(caminho, limiar_db=config.DB_ENVELOPE, passo=fala.PASSO):
    """Reaproveita o metodo do envelope de energia de motor/fala.py: agrupa
    janelas consecutivas acima do limiar em regioes (inicio, fim) em segundos."""
    env = fala.envelope(caminho, passo=passo)
    limiar = 10 ** (limiar_db / 20)
    acesos = [i for i, v in enumerate(env) if v > limiar]
    regioes = []
    for _, grupo in itertools.groupby(enumerate(acesos), lambda par: par[1] - par[0]):
        indices = [i for _, i in grupo]
        regioes.append((indices[0] * passo, (indices[-1] + 1) * passo))
    # funde regioes separadas por menos de 50ms (ruido de quantizacao na borda)
    fundidas = []
    for ini, fim in regioes:
        if fundidas and ini - fundidas[-1][1] < 0.05:
            fundidas[-1] = (fundidas[-1][0], fim)
        else:
            fundidas.append((ini, fim))
    return fundidas


def test_audio_cai_onde_o_mapa_diz(tmp_path):
    """O teste mais forte: decodifica o audio do filme final, acha as regioes
    de energia alta e confere que cada uma comeca perto do 'ini' da cena
    correspondente no cenas-mapa.json. Se a juncao descartar ou deslocar
    audio, as regioes nao batem com o mapa."""
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    lista = []
    for i in range(1, 4):
        fixtures.clipe_fala(tmp_path / "gravacoes" / f"take-{i:02d}.mov",
                            falas=[(0.5, 1.0)], total=3.0)
        lista.append({"n": i, "trat": "cheia",
                      "arquivo": f"gravacoes/take-{i:02d}.mov"})
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "cenas": lista}), encoding="utf-8")

    filme = montar.montar(p, tmp_path / "filme.mp4")
    mapa = json.loads((tmp_path / "cenas-mapa.json").read_text(encoding="utf-8"))

    regioes = _regioes_altas(filme)
    print("\nregioes medidas vs mapa de cenas:")
    for j, (ini, fim) in enumerate(regioes):
        alvo = mapa[j]["ini"] if j < len(mapa) else None
        print(f"  regiao {j}: {ini:.3f}s-{fim:.3f}s  |  cena {j + 1} ini={alvo}")

    assert len(regioes) == 3
    for (ini, _fim), cena in zip(regioes, mapa):
        assert abs(ini - cena["ini"]) < 0.15
