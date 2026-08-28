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
    filme = montar.montar(_producao(tmp_path), tmp_path / "filme.mp4")
    mapa = json.loads((tmp_path / "cenas-mapa.json").read_text(encoding="utf-8"))
    assert len(mapa) == 3
    assert mapa[0]["ini"] == 0.0
    # "ini" e "fim" vem do mesmo total corrente (montar.py soma "d" nos dois
    # ao mesmo tempo): mapa[0]["fim"] == mapa[1]["ini"] e tautologia, sempre
    # bate mesmo que "d" esteja errado. O que prova algo de verdade e
    # comparar contra uma medida INDEPENDENTE -- a duracao real do filme.
    assert abs(mapa[-1]["fim"] - probe.dur(filme)) < 0.10


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


def test_pausa_interna_longa_e_comprimida(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    # duas falas de 0.6s com 1.0s de silencio entre elas
    fixtures.clipe_fala(tmp_path / "gravacoes" / "take-01.mov",
                        falas=[(0.3, 0.6), (1.9, 0.6)], total=3.0)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]}),
        encoding="utf-8")
    filme = montar.montar(p, tmp_path / "filme.mp4")
    # sem comprimir daria ~2.5s; com a pausa reduzida a 0.10s cai bem abaixo
    assert probe.dur(filme) < 2.0


def test_pausa_comprimida_preserva_a_fala(tmp_path):
    """K: a compressao nao pode destruir a fala. Tres falas de 0.6s com duas
    pausas de 1.0s no meio: depois de comprimir, as tres tem que sobreviver
    no audio final, e a pausa entre elas tem que cair para perto de
    PAUSA_FICA (0.10s), bem abaixo do 1.0s original."""
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "take-01.mov",
                        falas=[(0.3, 0.6), (1.9, 0.6), (3.5, 0.6)], total=4.5)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]}),
        encoding="utf-8")
    filme = montar.montar(p, tmp_path / "filme.mp4")

    regioes = _regioes_altas(filme)
    print("\nregioes de fala depois da compressao:")
    for ini, fim in regioes:
        print(f"  {ini:.3f}s-{fim:.3f}s")
    assert len(regioes) == 3, (
        f"esperava 3 falas sobreviventes, achei {len(regioes)}: {regioes}")

    gaps = [b_ini - a_fim for (_, a_fim), (b_ini, _) in zip(regioes, regioes[1:])]
    print("gaps entre as falas (original era 1.0s):", [f"{g:.3f}s" for g in gaps])
    for g in gaps:
        assert g < 0.4, (
            f"gap de {g:.3f}s ainda perto do original de 1.0s -- "
            f"a pausa nao foi comprimida")


def test_pausa_ausente_nao_altera_a_cena(tmp_path):
    """L: uma fala continua, sem pausa interna, nao pode ser tocada pela
    compressao. A duracao do filme tem que bater com o span que
    fala.bordas mede para o arquivo (o mesmo span que a montagem usava
    antes desta mudanca), e o mapa de cenas tem que reportar 0 pausas."""
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    arq = fixtures.clipe_fala(tmp_path / "gravacoes" / "take-01.mov",
                              falas=[(0.5, 2.0)], total=3.5)
    ini, fim = fala.bordas(arq)
    esperado = fim - ini

    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]}),
        encoding="utf-8")
    filme = montar.montar(p, tmp_path / "filme.mp4")

    assert abs(probe.dur(filme) - esperado) < 0.15
    mapa = json.loads((tmp_path / "cenas-mapa.json").read_text(encoding="utf-8"))
    assert mapa[0]["pausas"] == 0


def test_split_funciona_com_pausa_comprimida(tmp_path):
    """M: split agora recebe o arquivo ja cortado por aperta() (ja_cortado=
    True). Nada testava essa combinacao antes desta mudanca."""
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "take-01.mov",
                        falas=[(0.3, 0.6), (1.9, 0.6)], total=3.0)
    fixtures.clipe_mudo(tmp_path / "gravacoes" / "broll.mp4",
                        total=3.0, w=1920, h=1080)

    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "cenas": [
        {"n": 1, "trat": "split", "arquivo": "gravacoes/take-01.mov",
         "topo": {"arquivo": "gravacoes/broll.mp4", "ancora": 0.0}}]}),
        encoding="utf-8")

    filme = montar.montar(p, tmp_path / "filme.mp4")
    assert probe.dimensao(filme) == (1080, 1920)
    assert probe.tem_audio(filme) is True


def test_split_velocidade_alta_mantem_video_e_audio_juntos(tmp_path):
    """FIX 6: split() aplicava fps=30 nas janelas de cima e de baixo ANTES do
    setpts da velocidade (vf_vel), e nao tinha nenhum fps depois -- ao
    contrario de tela_cheia(), que poe fps={FPS} DEPOIS do setpts. Sem isso o
    encoder arredonda os quadros por conta propria e o video sai mais longo
    que o audio. Medido: em 1.3x a diferenca ficava a 3 milissegundos da
    tolerancia do laudo (0.10s) -- por um defeito sistematico, nao ruido."""
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "take-01.mov",
                        falas=[(0.4, 1.2)], total=3.0)
    fixtures.clipe_mudo(tmp_path / "gravacoes" / "broll.mp4",
                        total=3.0, w=1920, h=1080)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.3, "cenas": [
        {"n": 1, "trat": "split", "arquivo": "gravacoes/take-01.mov",
         "topo": {"arquivo": "gravacoes/broll.mp4", "ancora": 0.0}}]}),
        encoding="utf-8")

    filme = montar.montar(p, tmp_path / "filme.mp4")
    d_v, d_a = montar.duracoes(filme)
    assert abs(d_v - d_a) < 0.05, (
        f"video {d_v:.3f}s vs audio {d_a:.3f}s -- diferenca de "
        f"{abs(d_v - d_a):.3f}s (video mais longo que o audio)")


def _pillarbox_com_fala(destino, falas, total, cor="teal", vw=608, vh=1080, fw=1920, fh=1080, x=200):
    """Simula a gravacao real deste projeto: vertical (608x1080) dentro de um
    quadro deitado (1920x1080), pillarbox do CapCut, com audio de fala
    sintetica. Cor nao-preta (teal) para distinguir 'janela do rosto
    preenchida' de 'janela do rosto preta'. O conteudo NAO fica centralizado
    (x=200, nao (1920-608)/2=656) de proposito: se o crop cair no fallback
    'sem deteccao', que assume o conteudo centralizado, o resultado sai
    errado -- e a deteccao de verdade tem de achar o deslocamento certo."""
    import subprocess
    volume = "+".join(f"between(t,{ini},{ini + dur})" for ini, dur in falas) or "0"
    args = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-t", f"{total}", "-i", f"color=c={cor}:s={vw}x{vh}:r={config.FPS}",
        "-f", "lavfi", "-t", f"{total}", "-i", f"sine=frequency=220:sample_rate={config.SR}",
        "-filter_complex",
        f"[0:v]pad={fw}:{fh}:{x}:0:black[v];[1:a]volume='{volume}':eval=frame[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "pcm_s16le", "-ar", str(config.SR), "-ac", "2",
        str(destino)]
    r = subprocess.run(args, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return destino


def test_area_util_do_original_mesmo_com_pouca_fala_na_cena(tmp_path):
    """FIX 2 (as duas metades juntas): a gravacao chega pillarbox (vertical
    dentro de quadro deitado, barra preta nos lados, NAO centralizado). O
    fluxo antigo cortava as pontas com aperta() ANTES de detectar a area
    util, e a deteccao rodava sobre esse arquivo JA CORTADO. `teto` forca a
    cena a ficar com bem menos de 1s depois do corte (0.02s aqui) -- o caso
    em que o arquivo cortado nao tem quadro nenhum sobrando depois do -ss
    fixo em 1s do probe.area_util antigo, que devolvia None, lido por quem
    chama como 'ja esta vertical, nao corta nada'. Sem cortar a barra preta,
    a janela do rosto sai cortada do centro do quadro DEITADO inteiro (que
    aqui e maioria barra preta, ja que o conteudo real esta deslocado para a
    esquerda) -- ela sai preta."""
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    _pillarbox_com_fala(tmp_path / "gravacoes" / "take-01.mov",
                        falas=[(0.5, 0.3)], total=3.0)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "teto": 0.02}]}),
        encoding="utf-8")

    filme = montar.montar(p, tmp_path / "filme.mp4")

    import subprocess
    def _pixel(x, y):
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(filme), "-vf", f"crop=2:2:{x}:{y}",
             "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            capture_output=True)
        dado = r.stdout[:3]
        return tuple(dado) if len(dado) == 3 else (0, 0, 0)

    pontos = [(200, 700), (540, 960), (860, 1250)]
    for x, y in pontos:
        px = _pixel(x, y)
        assert px != (0, 0, 0), (
            f"pixel ({x},{y}) da janela do rosto saiu preto: {px} -- a area "
            f"util nao foi detectada no arquivo original")
