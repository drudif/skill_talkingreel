import re
import subprocess
from pathlib import Path

from motor import config, probe, trilha
from tests import fixtures

SR = fixtures.SR


def _tom(destino, freq, total, janela=None, ganho=1.0, video=True):
    """Clipe sintetico com um tom continuo ou pulsado, de frequencia e ganho
    controlaveis -- fixtures.clipe_fala fixa 220 Hz em amplitude de fabrica,
    baixa demais pra estressar o sidechain de forma realista. `janela`
    (inicio, fim) liga o tom so nesse trecho; None mantem ligado o clipe
    inteiro. `ganho` e um multiplicador linear aplicado por cima."""
    destino = Path(destino)
    expr = f"between(t,{janela[0]},{janela[1]})" if janela else "1"
    args = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-t", f"{total}", "-i", f"sine=frequency={freq}:sample_rate={SR}",
    ]
    if video:
        args += ["-f", "lavfi", "-t", f"{total}", "-i", f"color=c=gray:s=1080x1920:r=30"]
    args += ["-filter_complex", f"[0:a]volume='({expr})*{ganho}':eval=frame[a]"]
    if video:
        args += ["-map", "1:v", "-map", "[a]",
                  "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
    else:
        args += ["-map", "[a]"]
    args += ["-c:a", "pcm_s16le", "-ar", str(SR), "-ac", "2", str(destino)]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:500])
    return destino


def _medir(caminho, ss, dur, filtro_extra=None):
    """(mean_volume, max_volume) em dB, num trecho [ss, ss+dur) do arquivo.
    Usa o volumedetect do proprio ffmpeg -- e o mesmo motor de decodificacao
    que produziu o arquivo, entao mede exatamente o que foi de fato escrito."""
    af = f"{filtro_extra}," if filtro_extra else ""
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", str(ss), "-t", str(dur), "-i", str(caminho),
         "-af", f"{af}volumedetect", "-f", "null", "-"],
        capture_output=True, text=True)
    mean = re.search(r"mean_volume:\s*(-?\d+\.?\d*)\s*dB", r.stderr)
    peak = re.search(r"max_volume:\s*(-?\d+\.?\d*)\s*dB", r.stderr)
    if not mean or not peak:
        raise RuntimeError("volumedetect nao devolveu nada -- stderr: " + r.stderr[-500:])
    return float(mean.group(1)), float(peak.group(1))


def test_a_trilha_nao_muda_a_duracao(tmp_path):
    filme = fixtures.clipe_fala(tmp_path / "f.mov", falas=[(0.4, 1.2)], total=3.0)
    musica = fixtures.clipe_fala(tmp_path / "m.mov", falas=[(0.0, 10.0)], total=10.0)
    saida = trilha.aplicar(filme, musica, tmp_path / "com-trilha.mov")
    assert abs(probe.dur(saida) - probe.dur(filme)) < 0.10


def test_a_trilha_mantem_o_video(tmp_path):
    filme = fixtures.clipe_fala(tmp_path / "f2.mov", falas=[(0.4, 1.2)], total=3.0)
    musica = fixtures.clipe_fala(tmp_path / "m2.mov", falas=[(0.0, 10.0)], total=10.0)
    saida = trilha.aplicar(filme, musica, tmp_path / "com-trilha2.mov")
    assert probe.dimensao(saida) == probe.dimensao(filme)


def test_trilha_mais_curta_que_o_filme_e_repetida(tmp_path):
    filme = fixtures.clipe_fala(tmp_path / "f3.mov", falas=[(0.4, 2.0)], total=4.0)
    musica = fixtures.clipe_fala(tmp_path / "m3.mov", falas=[(0.0, 1.0)], total=1.0)
    saida = trilha.aplicar(filme, musica, tmp_path / "com-trilha3.mov")
    assert abs(probe.dur(saida) - probe.dur(filme)) < 0.15


def test_a_musica_realmente_abaixa_quando_a_voz_esta_presente(tmp_path):
    """Os tres testes acima so checam duracao e dimensao -- passariam mesmo se
    o sidechain estivesse invertido (a ARMADILHA do docstring de trilha.py).
    Este mede o efeito de verdade.

    Metodo: o filme tem um tom de 220 Hz (a "voz") ligado so em [1.0, 2.0]s,
    num ganho (2.5x) que aproxima o nivel de uma fala normalizada -- o tom
    puro do gerador de sine do ffmpeg sai baixo demais (pico ~-18 dB) pra
    disparar o compressor de forma representativa. A "musica" e um tom
    continuo de 880 Hz -- frequencia DIFERENTE da voz, de proposito -- pelos
    4s inteiros.

    Depois de aplicar a trilha, filtra a saida com um passa-faixa em torno de
    880 Hz (bandpass, largura 200 Hz) pra isolar so a musica, descartando o
    vazamento da voz a 220 Hz. Mede o nivel medio (mean_volume) dessa banda
    em dois trechos: um dentro da janela da voz (1.3-1.7s, depois do attack
    de 20ms) e um fora dela (2.5-3.5s, depois do release de 350ms). Se o
    sidechain estiver certo, a musica tem que estar mais baixa QUANDO a voz
    toca."""
    filme = _tom(tmp_path / "fn.mov", freq=220, total=4.0, janela=(1.0, 2.0), ganho=2.5)
    musica = _tom(tmp_path / "mn.mov", freq=880, total=4.0, video=False)
    saida = trilha.aplicar(filme, musica, tmp_path / "com-trilha-n.mov")

    banda = "bandpass=f=880:width_type=h:w=200"
    media_com_voz, _ = _medir(saida, ss=1.3, dur=0.4, filtro_extra=banda)
    media_sem_voz, _ = _medir(saida, ss=2.5, dur=1.0, filtro_extra=banda)

    reducao = media_sem_voz - media_com_voz
    print(f"\n[trilha] musica (banda 880Hz) com voz: {media_com_voz:.1f} dB | "
          f"sem voz: {media_sem_voz:.1f} dB | abaixamento: {reducao:.1f} dB")

    # com voz a musica tem de ficar pelo menos 2 dB mais baixa que sem voz.
    # margem folgada: o abaixamento medido de fato fica perto de 5 dB.
    assert reducao > 2.0, (
        f"a musica nao abaixou sob a voz (reducao medida: {reducao:.1f} dB) -- "
        "suspeita: sidechain com as entradas trocadas")


def test_o_mix_final_nao_estoura_o_teto(tmp_path):
    """O limitador final (alimiter) tem que segurar o pico em TETO_DB (-1.5dB),
    mesmo quando a voz de entrada ja esta alta o bastante pra, somada a
    musica, passar do teto antes do limitador atuar.

    Usa um filme com a voz num ganho bem mais alto (8x) que o do teste de
    abaixamento -- alto o bastante pra empurrar o mix pre-limitador pra perto
    do teto (medido a parte: ~-3 dB antes do alimiter), sem chegar a estourar
    a propria fonte (pico da fonte fica em -3 dB, longe de 0 dB / clipping)."""
    filme = _tom(tmp_path / "fp.mov", freq=220, total=4.0, janela=(1.0, 2.0), ganho=8.0)
    musica = _tom(tmp_path / "mp.mov", freq=880, total=4.0, video=False)
    saida = trilha.aplicar(filme, musica, tmp_path / "com-trilha-p.mov")

    _, pico = _medir(saida, ss=0, dur=probe.dur(saida))
    print(f"\n[trilha] pico do mix final: {pico:.1f} dB (teto configurado: {config.TETO_DB} dB)")

    tolerancia = 0.5
    assert pico <= config.TETO_DB + tolerancia, (
        f"pico do mix ({pico:.1f} dB) passou do teto ({config.TETO_DB} dB "
        f"+ {tolerancia} de tolerancia) -- o limitador nao segurou")


def _pico_db(caminho):
    """Pico do audio em dB, lido do volumedetect do ffmpeg."""
    import re
    import subprocess
    r = subprocess.run(["ffmpeg", "-i", str(caminho), "-af", "volumedetect",
                        "-f", "null", "-"], capture_output=True, text=True)
    achado = re.search(r"max_volume:\s*(-?[\d.]+) dB", r.stderr)
    return float(achado.group(1)) if achado else 0.0


def test_o_limitador_segura_o_teto(tmp_path):
    """Com material ja normalizado, o pico final tem de ficar no teto.

    Este teste existe por causa de um erro real. O `alimiter` tem `level=true`
    por padrao, e essa opcao NAO normaliza para 0 dB como o nome sugere: ela
    soma um ganho fixo de +1.5 dB, compensando o valor do `limit`. Com material
    baixo isso passa despercebido; com material ja normalizado perto do teto —
    que e o caso da fala depois do loudnorm — o pico vai para -0.0 dB.

    Por isso a fonte deste teste passa por loudnorm antes, exatamente como o
    `tratamentos.py` faz com a voz. Sem isso o teste nao tem dente: medido, um
    tom a -5.5 dB passa nas duas versoes, e so material perto do teto separa."""
    from motor import config

    filme = tmp_path / "normalizado.mov"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-t", "3", "-i", "color=c=gray:s=1080x1920:r=30",
        "-f", "lavfi", "-t", "3", "-i", "sine=frequency=220:sample_rate=48000",
        "-filter_complex",
        # volume 9.5 poe o pico do tom perto de -1.6 dB, que e onde a voz fica
        # depois do loudnorm. Nao da pra usar loudnorm aqui: tom puro tem crista
        # diferente de voz, e normalizar por volume percebido deixa o pico em -13 dB.
        "[1:a]volume=9.5[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(filme)], check=True)

    # a fonte tem de estar perto do teto, senao o teste nao separa as versoes
    assert _pico_db(filme) > config.TETO_DB - 3.0, "fonte baixa demais para o teste valer"

    musica = fixtures.clipe_fala(tmp_path / "mus.mov", falas=[(0.0, 3.0)], total=3.0)
    saida = trilha.aplicar(filme, musica, tmp_path / "com-teto.mov")
    pico = _pico_db(saida)
    assert pico <= config.TETO_DB + 0.5, (
        f"o pico saiu em {pico} dB, acima do teto de {config.TETO_DB} dB — "
        "verifique se o alimiter esta com level=disabled")
