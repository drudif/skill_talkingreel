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


# ---------------------------------------------------------------------------
# A medicao de emenda so vale onde da para ouvir emenda
# ---------------------------------------------------------------------------

def _com_musica(origem, destino, volume=0.34):
    """O mesmo filme com uma faixa continua por baixo, como a trilha faz."""
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(origem),
         "-f", "lavfi", "-t", "60", "-i",
         "sine=frequency=330:sample_rate=48000",
         "-filter_complex",
         f"[1:a]volume={volume}[m];[0:a][m]amix=inputs=2:duration=first"
         f":normalize=0[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "pcm_s16le",
         "-ar", "48000", str(destino)], check=True)
    return destino


def test_musica_por_baixo_cega_a_medicao_de_emenda(tmp_path):
    """O defeito que isto impede, medido com material real: as MESMAS dez
    emendas de um corte limpo passaram de zero acusadas para dez, so por a
    trilha ter entrado. O laudo mandava o Bluey devolver para o corte um filme
    que estava certo."""
    from motor import medidas
    limpo = fixtures.clipe_fala(tmp_path / "l.mov",
                                falas=[(0.3, 1.2), (2.0, 1.2), (3.8, 1.2)],
                                total=5.5, ruido_dB=-50)
    da_limpo, dist_limpo = medidas.da_para_ouvir_emenda(limpo)
    assert da_limpo, (
        f"num filme sem musica deveria dar para medir; deu {dist_limpo:.1f} dB")

    com_musica = _com_musica(limpo, tmp_path / "m.mov")
    da_musica, dist_musica = medidas.da_para_ouvir_emenda(com_musica)
    assert not da_musica, (
        f"com musica por baixo a medicao nao vale; a distancia entre a fala e "
        f"o fundo deu {dist_musica:.1f} dB e passou assim mesmo")
    assert dist_musica < dist_limpo - 5, (
        "a musica tinha de encolher a distancia entre a fala e o fundo")


def test_o_laudo_avisa_em_vez_de_acusar_quando_nao_da_para_medir(tmp_path):
    """Nao e defeito do filme, e limite da medicao — e o texto tem de dizer
    isso, senao a pessoa desmonta um corte que estava bom."""
    import json
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "a.mov",
                        falas=[(0.3, 1.2)], total=2.0, ruido_dB=-50)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "b.mov",
                        falas=[(0.3, 1.2)], total=2.0, ruido_dB=-50)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/a.mov"},
        {"n": 2, "trat": "cheia", "arquivo": "gravacoes/b.mov"}]}),
        encoding="utf-8")
    filme = montar.montar(p, tmp_path / "f.mp4")
    com_musica = _com_musica(filme, tmp_path / "fm.mov")

    r = laudo.rodar(com_musica, p)
    assert r["emenda_nao_medida"], "o laudo nao avisou que nao deu para medir"
    assert r["emendas"] == [], "o laudo acusou emenda com a medicao cega"
    texto = laudo.em_portugues(r).lower()
    assert "nao consegui conferir" in texto or "não consegui conferir" in texto
    assert "sem musica" in texto or "sem música" in texto, (
        "o aviso nao diz onde conferir")


def test_o_limiar_da_dinamica_esta_provado_dos_dois_lados():
    """MEDIDO em tres filmes, contra o FUNDO ABSOLUTO (percentil 2): fala do
    comeco ao fim da 44,2 dB; corte real limpo, 50,8; o mesmo corte com musica
    por baixo, 20,2.

    A primeira versao desta guarda comparava com o percentil 10 e barrava o
    filme de fala densa -- ali o percentil 10 JA E fala, e a distancia deu
    0,5 dB. O que sempre sobra, mesmo na fala mais corrida, sao os
    micro-silencios de dentro das palavras."""
    from motor import medidas
    assert medidas.FUNDO <= 0.05, (
        "o fundo tem de ser um percentil bem baixo: no percentil 10 um talking "
        "head denso ja e fala, e a guarda barra o caso legitimo")
    assert medidas.DINAMICA_MINIMA > 22.0, (
        "abaixo de 22 dB a medicao aceitaria o filme com musica, que mede 20,2")
    assert medidas.DINAMICA_MINIMA < 42.0, (
        "acima de 42 dB a medicao recusaria fala densa legitima, que mede 44,2")
