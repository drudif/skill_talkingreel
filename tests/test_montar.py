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
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": lista}), encoding="utf-8")
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
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": lista}), encoding="utf-8")

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
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
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
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
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
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
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
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
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
    p.write_text(json.dumps({"velocidade": 1.3, "legenda": False, "cenas": [
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
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
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


def test_letreiro_aparece_no_filme(tmp_path):
    from PIL import Image
    from motor import arte
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 2.5)], total=3.5)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov",
         "letreiro": {"texto": "APARECE", "entra": 1.0, "base": 1300}}]}),
        encoding="utf-8")
    filme = montar.montar(p, tmp_path / "f.mp4")

    # descobre onde a tinta cai, em vez de chutar coordenada
    ref = arte.letreiro("APARECE", "brutalista", tmp_path / "ref.png", base=1300)
    x0, y0, x1, y1 = Image.open(ref).convert("RGBA").getchannel("A").getbbox()
    crop = f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}"

    def regiao(t):
        import subprocess
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(filme),
             "-frames:v", "1", "-vf", f"{crop},scale=60:20",
             "-pix_fmt", "gray", "-f", "rawvideo", "-"], capture_output=True)
        return list(r.stdout[:1200])

    antes, depois = regiao(0.4), regiao(2.0)
    dif = sum(abs(a - b) for a, b in zip(antes, depois)) / max(1, len(antes))
    assert dif > 20, f"o letreiro nao apareceu no filme montado (dif={dif})"


def test_letreiro_entra_e_relativo_a_cena(tmp_path):
    """L: 'entra' e relativo ao INICIO DA CENA, nao ao filme. So a SEGUNDA
    cena tem letreiro, com 'entra' bem dentro dela. Se 'entra' fosse lido
    como tempo do filme, o letreiro apareceria ainda na cena 1 (t=1.0s
    global); o que se espera e que ele apareca em cena2.ini + entra, lido do
    cenas-mapa.json que a montagem grava."""
    from PIL import Image
    from motor import arte
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t1.mov",
                        falas=[(0.3, 2.5)], total=3.2)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t2.mov",
                        falas=[(0.3, 2.5)], total=3.5)
    entra = 1.0
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t1.mov"},
        {"n": 2, "trat": "cheia", "arquivo": "gravacoes/t2.mov",
         "letreiro": {"texto": "SEGUNDA", "entra": entra, "base": 1300}}]}),
        encoding="utf-8")
    filme = montar.montar(p, tmp_path / "f.mp4")
    mapa = json.loads((tmp_path / "cenas-mapa.json").read_text(encoding="utf-8"))
    assert len(mapa) == 2
    scene2_ini = mapa[1]["ini"]
    esperado = scene2_ini + entra

    ref = arte.letreiro("SEGUNDA", "brutalista", tmp_path / "ref.png", base=1300)
    x0, y0, x1, y1 = Image.open(ref).convert("RGBA").getchannel("A").getbbox()
    crop = f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}"

    def regiao(t):
        import subprocess
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", str(max(t, 0)), "-i", str(filme),
             "-frames:v", "1", "-vf", f"{crop},scale=60:20",
             "-pix_fmt", "gray", "-f", "rawvideo", "-"], capture_output=True)
        return list(r.stdout[:1200])

    def dif(a, b):
        return sum(abs(x - y) for x, y in zip(a, b)) / max(1, len(a))

    sem_letreiro = regiao(0.05)  # inicio da cena 1: nunca tem letreiro

    # se 'entra' fosse global, o letreiro estaria visivel em t=entra (1.0s),
    # ainda dentro da cena 1 -- confirma que NAO esta
    assert dif(sem_letreiro, regiao(entra)) < 20, (
        "o letreiro ja aparece no instante 'entra' global -- 'entra' esta "
        "sendo lido como tempo do FILME, nao da cena")

    # varre a partir do inicio da cena 2 ate achar o instante em que a
    # tinta aparece de verdade
    medido = None
    t = scene2_ini
    while t < scene2_ini + entra + 1.5:
        if dif(sem_letreiro, regiao(t)) > 20:
            medido = t
            break
        t += 0.1
    assert medido is not None, "o letreiro nunca apareceu na cena 2"
    print(f"\nL: esperado cena2.ini({scene2_ini:.3f}) + entra({entra}) = "
          f"{esperado:.3f}s | medido ~= {medido:.3f}s")
    assert abs(medido - esperado) < 0.5, (
        f"esperava o letreiro perto de {esperado:.3f}s, apareceu em {medido:.3f}s")


def test_letreiro_mais_longo_que_a_cena_nao_quebra_montagem(tmp_path):
    """M: 'dura' maior que a propria cena nao pode quebrar a montagem. O
    letreiro so teria tempo de aparecer ate o fim da cena mesmo assim; o que
    importa e que o filme monte, saia no tamanho certo e o audio/video
    continuem sincronizados."""
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 2.5)], total=3.5)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov",
         "letreiro": {"texto": "MAIS LONGO QUE A CENA", "entra": 0.0,
                      "dura": 999.0}}]}),
        encoding="utf-8")
    filme = montar.montar(p, tmp_path / "f.mp4")
    assert probe.dimensao(filme) == (1080, 1920)
    d_v, d_a = montar.duracoes(filme)
    print(f"\nM: d_v={d_v:.3f}s d_a={d_a:.3f}s diff={abs(d_v - d_a):.3f}s")
    assert abs(d_v - d_a) < 0.10


def test_letreiro_nao_altera_o_audio(tmp_path):
    """N: a presenca de um letreiro nao pode mexer no som. Monta o MESMO
    filme duas vezes, com e sem letreiro, e compara as duas trilhas de
    audio: duracao e envelope de energia (RMS por janela de 10ms) tem que
    bater de perto. com_overlay so copia o audio (-c:a copy); qualquer
    diferenca aqui indica que o overlay mexeu em algo que nao devia."""
    import array
    import subprocess

    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 1.5)], total=2.5)
    dados_base = {"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov"}]}
    dados_com = {"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov",
         "letreiro": {"texto": "SOM IGUAL", "entra": 0.5, "dura": 1.0}}]}
    p_sem = tmp_path / "cenas-sem.json"
    p_sem.write_text(json.dumps(dados_base), encoding="utf-8")
    p_com = tmp_path / "cenas-com.json"
    p_com.write_text(json.dumps(dados_com), encoding="utf-8")

    filme_sem = montar.montar(p_sem, tmp_path / "sem.mp4", tmp=tmp_path / "tmp-sem")
    filme_com = montar.montar(p_com, tmp_path / "com.mp4", tmp=tmp_path / "tmp-com")

    def envelope(caminho, passo=0.01, taxa=8000):
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(caminho),
             "-ac", "1", "-ar", str(taxa), "-f", "f32le", "-"],
            capture_output=True)
        amostras = array.array("f")
        amostras.frombytes(r.stdout[:len(r.stdout) - len(r.stdout) % 4])
        n = max(1, int(taxa * passo))
        blocos = len(amostras) // n
        return [(sum(x * x for x in amostras[i * n:(i + 1) * n]) / n) ** 0.5
                for i in range(blocos)]

    d_v1, d_a1 = montar.duracoes(filme_sem)
    d_v2, d_a2 = montar.duracoes(filme_com)
    print(f"\nN: audio sem={d_a1:.3f}s com={d_a2:.3f}s")
    assert abs(d_a1 - d_a2) < 0.05

    env_sem, env_com = envelope(filme_sem), envelope(filme_com)
    n = min(len(env_sem), len(env_com))
    assert n > 0
    dif = sum(abs(a - b) for a, b in zip(env_sem[:n], env_com[:n])) / n
    print(f"N: {n} janelas de 10ms comparadas, diferenca media = {dif:.5f}")
    assert dif < 0.01, (
        f"o envelope de audio mudou com o letreiro presente (diff={dif:.5f})")


def test_legenda_desligada_nao_chama_a_transcricao(tmp_path):
    """Desligar a legenda tem de pular a transcricao INTEIRA, nao so a queima.
    Transcrever e a etapa mais cara do motor: num video de quatro minutos sao
    minutos de espera. Se o campo so evitasse a queima, quem desligou a legenda
    pagaria o preco sem receber nada."""
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 1.0)], total=2.0)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov"}]}),
        encoding="utf-8")

    chamadas = []

    def _espia(caminho):
        chamadas.append(caminho)
        return [{"p": "nada", "t": 0.2, "f": 0.6}]

    filme = montar.montar(p, tmp_path / "f.mp4", transcrever=_espia)
    assert chamadas == [], "transcreveu mesmo com a legenda desligada"
    assert probe.dimensao(filme) == (config.W, config.H)


def _fala_falsa(palavras):
    """Uma transcricao de mentira, com tempos escolhidos por nos. Serve para
    exercitar toda a fiacao da legenda sem baixar o modelo de 3GB nem depender
    de fala humana num clipe sintetico."""
    return lambda _caminho: [dict(w) for w in palavras]


def _crop_da_legenda(tmp_path, texto, posicao):
    from PIL import Image
    from motor import legenda as mod_leg
    ref = mod_leg.png(texto, "brutalista", tmp_path / f"_ref-{posicao}.png",
                      posicao=posicao)
    x0, y0, x1, y1 = Image.open(ref).convert("RGBA").getchannel("A").getbbox()
    return f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}"


def _tinta(caminho, t, crop):
    import subprocess
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(caminho),
         "-frames:v", "1", "-vf", f"{crop},scale=48:16",
         "-pix_fmt", "gray", "-f", "rawvideo", "-"], capture_output=True)
    return list(r.stdout[:768])


def _mudou(caminho, t1, t2, crop):
    a, b = _tinta(caminho, t1, crop), _tinta(caminho, t2, crop)
    assert a and b, "nao consegui ler o quadro"
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def test_a_legenda_e_queimada_no_filme(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 3.2)], total=4.0)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "proprios": ["Ginsu"],
                             "cenas": [{"n": 1, "trat": "cheia",
                                        "arquivo": "gravacoes/t.mov"}]}),
                 encoding="utf-8")
    filme = montar.montar(
        p, tmp_path / "f.mp4",
        transcrever=_fala_falsa([{"p": "guinco", "t": 1.0, "f": 1.8}]))

    # o nome proprio foi consertado antes de virar legenda
    crop = _crop_da_legenda(tmp_path, "Ginsu", "cheia")
    assert _mudou(filme, 1.4, 3.5, crop) > 20, "a legenda nao apareceu"


def test_a_legenda_desligada_nao_queima_nada(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 3.2)], total=4.0)
    dados = {"velocidade": 1.0,
             "cenas": [{"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov"}]}
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({**dados, "legenda": False}), encoding="utf-8")
    filme = montar.montar(
        p, tmp_path / "f.mp4",
        transcrever=_fala_falsa([{"p": "palavra", "t": 1.0, "f": 1.8}]))
    crop = _crop_da_legenda(tmp_path, "palavra", "cheia")
    assert _mudou(filme, 1.4, 3.5, crop) < 6, (
        "queimou legenda mesmo com legenda desligada")


def test_a_legenda_muda_de_lugar_conforme_a_cena(tmp_path):
    """Cena 1 em tela cheia, cena 2 com a tela dividida. A mesma palavra tem
    de cair centralizada na primeira e no canto escolhido na segunda."""
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    (tmp_path / "broll").mkdir(parents=True, exist_ok=True)
    for i in (1, 2):
        fixtures.clipe_fala(tmp_path / "gravacoes" / f"t{i}.mov",
                            falas=[(0.3, 2.2)], total=2.8)
    fixtures.clipe_mudo(tmp_path / "broll" / "b.mp4", total=3.0, w=1920, h=1080)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda_split": "esquerda",
                             "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t1.mov"},
        {"n": 2, "trat": "split", "arquivo": "gravacoes/t2.mov",
         "topo": {"arquivo": "broll/b.mp4"}}]}), encoding="utf-8")

    filme = montar.montar(p, tmp_path / "f.mp4", transcrever=_fala_falsa([
        {"p": "primeira", "t": 0.8, "f": 1.6},
        {"p": "segunda", "t": 3.4, "f": 4.2}]))

    mapa = json.loads((tmp_path / "cenas-mapa.json").read_text())
    assert mapa[1]["trat"] == "split"
    assert mapa[1]["ini"] < 3.8 < mapa[1]["fim"], "o teste mirou fora da cena 2"

    cheia = _crop_da_legenda(tmp_path, "primeira", "cheia")
    esquerda = _crop_da_legenda(tmp_path, "segunda", "esquerda")
    vazio = (mapa[0]["fim"] + mapa[1]["ini"]) / 2 - 0.4   # entre as duas falas

    assert _mudou(filme, 1.2, vazio, cheia) > 20, (
        "a legenda da cena cheia nao apareceu centralizada")
    assert _mudou(filme, 3.8, vazio, esquerda) > 20, (
        "a legenda da cena dividida nao apareceu no canto esquerdo")


def test_a_legenda_some_sob_o_letreiro(tmp_path):
    """O letreiro escreve a frase em corpo grande; legendar por baixo mostra a
    mesma frase duas vezes."""
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 3.2)], total=4.0)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov",
         "letreiro": {"texto": "GRANDE", "entra": 0.0, "dura": 3.0}}]}),
        encoding="utf-8")
    filme = montar.montar(
        p, tmp_path / "f.mp4",
        transcrever=_fala_falsa([{"p": "escondida", "t": 1.0, "f": 1.8}]))

    mapa = json.loads((tmp_path / "cenas-mapa.json").read_text())
    assert "letreiro" in mapa[0], "o mapa nao registrou a janela do letreiro"

    crop = _crop_da_legenda(tmp_path, "escondida", "cheia")
    assert _mudou(filme, 1.4, 3.5, crop) < 6, (
        "a legenda apareceu por baixo do letreiro")


def test_o_mapa_registra_o_material_do_topo(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    (tmp_path / "broll").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 2.2)], total=2.8)
    fixtures.clipe_mudo(tmp_path / "broll" / "b.mp4", total=3.0, w=1920, h=1080)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "split", "arquivo": "gravacoes/t.mov",
         "topo": {"arquivo": "broll/b.mp4"}}]}), encoding="utf-8")
    montar.montar(p, tmp_path / "f.mp4")
    mapa = json.loads((tmp_path / "cenas-mapa.json").read_text())
    assert mapa[0]["topo"].endswith("broll/b.mp4")


def test_cena_cheia_nao_registra_topo(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 2.2)], total=2.8)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov"}]}),
        encoding="utf-8")
    montar.montar(p, tmp_path / "f.mp4")
    mapa = json.loads((tmp_path / "cenas-mapa.json").read_text())
    assert "topo" not in mapa[0]


def test_o_filme_sem_legenda_tambem_fica_em_disco(tmp_path):
    """E um dos entregaveis: serve para quando o aplicativo legenda sozinho.
    Antes ele so existia na pasta temporaria, que e descartada."""
    from motor import probe as mod_probe
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 3.2)], total=4.0)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov"}]}),
        encoding="utf-8")
    filme = montar.montar(
        p, tmp_path / "f.mp4",
        transcrever=_fala_falsa([{"p": "aparece", "t": 1.0, "f": 1.8}]))

    sem = tmp_path / "f-sem-legenda.mp4"
    assert sem.exists(), "o filme sem legenda nao foi guardado"
    assert abs(mod_probe.dur(sem) - mod_probe.dur(filme)) < 0.05
    assert mod_probe.dimensao(sem) == (config.W, config.H)

    crop = _crop_da_legenda(tmp_path, "aparece", "cheia")
    assert _mudou(filme, 1.4, 3.5, crop) > 20, "o filme entregue perdeu a legenda"
    assert _mudou(sem, 1.4, 3.5, crop) < 6, "a copia sem legenda veio legendada"


def test_sem_legenda_nao_cria_copia(tmp_path):
    """Com a legenda desligada os dois arquivos seriam iguais; um so basta."""
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 1.5)], total=2.0)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov"}]}),
        encoding="utf-8")
    montar.montar(p, tmp_path / "f.mp4")
    assert not (tmp_path / "f-sem-legenda.mp4").exists()
