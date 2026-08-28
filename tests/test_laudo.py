import json
import subprocess

from motor import laudo, montar
from tests import fixtures


def _filme(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    for i in (1, 2):
        fixtures.clipe_fala(tmp_path / "gravacoes" / f"take-{i:02d}.mov",
                            falas=[(0.4, 1.2)], total=3.0)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"},
        {"n": 2, "trat": "cheia", "arquivo": "gravacoes/take-02.mov"}]}),
        encoding="utf-8")
    return montar.montar(p, tmp_path / "filme.mp4"), p


def test_laudo_aprova_um_filme_bem_montado(tmp_path):
    filme, cenas_json = _filme(tmp_path)
    r = laudo.rodar(filme, cenas_json)
    assert r["ok"] is True
    assert r["problemas"] == []


def test_laudo_mede_a_diferenca_entre_video_e_audio(tmp_path):
    filme, cenas_json = _filme(tmp_path)
    r = laudo.rodar(filme, cenas_json)
    assert abs(r["dif_video_audio"]) < 0.10


def test_laudo_reclama_de_filme_vazio(tmp_path):
    vazio = fixtures.clipe_mudo(tmp_path / "v.mp4", total=0.5)
    r = laudo.rodar(vazio, None)
    assert r["ok"] is False
    assert any("audio" in p for p in r["problemas"])


def test_laudo_escreve_em_portugues_sem_jargao(tmp_path):
    filme, cenas_json = _filme(tmp_path)
    r = laudo.rodar(filme, cenas_json)
    texto = laudo.em_portugues(r)
    for proibido in ("LUFS", "fps", "PTS", "codec", "bitrate"):
        assert proibido not in texto


# --- Q: filme no tamanho errado, mas com audio, tem de ser pego -----------

def test_laudo_pega_filme_no_tamanho_errado(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    errado = fixtures.clipe_fala(tmp_path / "gravacoes" / "errado.mov",
                                 falas=[(0.4, 1.2)], total=3.0, w=720, h=1280)
    r = laudo.rodar(errado, None)
    assert r["ok"] is False
    assert any("720x1280" in p for p in r["problemas"])


# --- R: audio e video terminando em momentos diferentes tem de ser pego ---

def _filme_dessincronizado(destino, dur_video=3, dur_audio=5):
    """Muxa um video de dur_video segundos com um audio de dur_audio segundos,
    sem -shortest, para que os dois fluxos fiquem com duracao diferente."""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-t", str(dur_video), "-i", "color=c=gray:s=1080x1920:r=30",
        "-f", "lavfi", "-t", str(dur_audio), "-i", "sine=frequency=220:sample_rate=48000",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000",
        str(destino)], check=True, capture_output=True)
    return destino


def test_laudo_pega_video_e_audio_com_duracoes_diferentes(tmp_path):
    dessincronizado = _filme_dessincronizado(tmp_path / "dessinc.mp4")
    r = laudo.rodar(dessincronizado, None)
    assert r["ok"] is False
    assert any("imagem" in p and "som" in p for p in r["problemas"])


# --- S: buraco entre cenas no mapa tem de ser pego -------------------------

def test_laudo_pega_buraco_entre_cenas(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    filme = fixtures.clipe_fala(tmp_path / "filme.mp4",
                                falas=[(0.4, 1.2)], total=3.0)
    cenas_json = tmp_path / "cenas.json"
    cenas_json.write_text("{}", encoding="utf-8")   # so o diretorio importa
    (tmp_path / "cenas-mapa.json").write_text(json.dumps([
        {"n": 1, "trat": "cheia", "pausas": 0, "ini": 0.0, "fim": 2.0},
        {"n": 2, "trat": "cheia", "pausas": 0, "ini": 2.5, "fim": 4.5}]),
        encoding="utf-8")

    r = laudo.rodar(filme, cenas_json)
    assert r["ok"] is False
    assert any("cena 1" in p and "cena 2" in p for p in r["problemas"])


# --- T: o texto para a pessoa tem de estar livre de jargao tecnico ---------

JARGAO = ("LUFS", "fps", "PTS", "codec", "bitrate", "ffmpeg", "stream", "mux",
          "chroma", "pixel", "frame", "dB", "sync", "dessync", "crop",
          "overlay", "render", "encode", "resolução")


def test_laudo_texto_livre_de_jargao_filme_aprovado(tmp_path):
    filme, cenas_json = _filme(tmp_path)
    r = laudo.rodar(filme, cenas_json)
    texto = laudo.em_portugues(r)
    for proibido in JARGAO:
        assert proibido not in texto, f"'{proibido}' vazou no texto: {texto!r}"


def test_laudo_texto_livre_de_jargao_filme_reprovado(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    errado = fixtures.clipe_fala(tmp_path / "gravacoes" / "errado.mov",
                                 falas=[(0.4, 1.2)], total=3.0, w=720, h=1280)
    r = laudo.rodar(errado, None)
    texto = laudo.em_portugues(r)
    for proibido in JARGAO:
        assert proibido not in texto, f"'{proibido}' vazou no texto: {texto!r}"

    dessincronizado = _filme_dessincronizado(tmp_path / "dessinc.mp4")
    r2 = laudo.rodar(dessincronizado, None)
    texto2 = laudo.em_portugues(r2)
    for proibido in JARGAO:
        assert proibido not in texto2, f"'{proibido}' vazou no texto: {texto2!r}"


def test_o_laudo_traz_as_medidas_novas(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 1.0)], total=2.5, ruido_dB=-50)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov"}]}),
        encoding="utf-8")
    filme = montar.montar(p, tmp_path / "f.mp4")
    r = laudo.rodar(filme, p)
    for chave in ("emendas", "repeticao"):
        assert chave in r, f"o laudo nao trouxe '{chave}'"
    assert r["ok"] is True, r["problemas"]


def test_material_em_loop_avisa_mas_nao_reprova(tmp_path):
    """Repetir pode ser deliberado. E observacao, nao defeito."""
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    (tmp_path / "broll").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 5.5)], total=6.0, ruido_dB=-50)
    fixtures.clipe_mudo(tmp_path / "broll" / "b.mp4", total=0.8, w=1920, h=1080)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "split", "arquivo": "gravacoes/t.mov",
         "topo": {"arquivo": "broll/b.mp4"}}]}), encoding="utf-8")
    filme = montar.montar(p, tmp_path / "f.mp4")
    r = laudo.rodar(filme, p)
    assert r["repeticao"], "nao viu o material repetindo"
    assert r["ok"] is True, "repeticao nao deveria reprovar o filme"
    texto = laudo.em_portugues(r)
    assert "repete" in texto
    for jargao in ("loop", "b-roll", "buffer", "frame"):
        assert jargao not in texto.lower(), f"vazou jargao: {jargao}"


def test_emenda_que_corta_palavra_reprova(tmp_path):
    """Duas cenas cuja fala vai ate a ultima fracao de segundo: a costura cai
    no meio do som, que e exatamente o engasgo que o ouvido pega."""
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "a.mov",
                        falas=[(0.05, 2.9)], total=3.0, ruido_dB=-50)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "b.mov",
                        falas=[(0.05, 2.9)], total=3.0, ruido_dB=-50)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/a.mov"},
        {"n": 2, "trat": "cheia", "arquivo": "gravacoes/b.mov"}]}),
        encoding="utf-8")
    filme = montar.montar(p, tmp_path / "f.mp4")
    r = laudo.rodar(filme, p)
    assert r["emendas"], "nao viu a emenda no meio do som"
    assert r["ok"] is False
    assert any("pedaco de palavra" in x for x in r["problemas"])
