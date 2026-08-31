"""Onde a voz comeca, onde termina, e onde ela para no meio.

Regra que vale para todo corte deste motor: a TRANSCRICAO diz qual e a palavra,
o ENVELOPE diz onde cortar. Timestamp de palavra do reconhecimento de fala e
aproximado — o instante que ele marca como inicio de uma palavra nao e o
instante em que ela fica audivel.

E consoante oclusiva (p t k b d g) tem silencio DENTRO da palavra: uma /d/ tem
uma oclusao muda e depois a explosao. Cortar no primeiro silencio depois de
"tudo" decepa o "do". Quem for fixar um corte fino, meça a 5 ms.
"""
import array
import re
import subprocess

from motor import config, probe

PASSO = 0.010          # 10 ms por janela de envelope
_TAXA_ENV = 8000       # o envelope nao precisa de qualidade, so de energia


def envelope(caminho, passo=PASSO, de=None, ate=None):
    """Devolve a energia normalizada (0 a 1) em janelas de `passo` segundos.

    `de` e `ate` limitam a leitura a um trecho do arquivo, em segundos do
    ORIGINAL. O corte e feito pelo ffmpeg, nao depois: o valor volta
    normalizado pelo pico DAQUELE trecho, e nao pelo pico do arquivo inteiro.
    A diferenca importa quando um take tem um pedaco falado alto e outro baixo
    -- normalizado pelo arquivo todo, o trecho baixo ficaria inteiro abaixo do
    limiar e a cena sairia sem fala nenhuma."""
    corte = []
    if de is not None:
        corte += ["-ss", f"{de:.3f}"]      # ANTES do -i, sempre
    if ate is not None:
        corte += ["-to", f"{ate:.3f}"]
    r = subprocess.run(
        ["ffmpeg", "-v", "error", *corte, "-i", str(caminho),
         "-ac", "1", "-ar", str(_TAXA_ENV), "-f", "f32le", "-"],
        capture_output=True)
    amostras = array.array("f")
    amostras.frombytes(r.stdout[:len(r.stdout) - len(r.stdout) % 4])
    n = max(1, int(_TAXA_ENV * passo))
    blocos = len(amostras) // n
    saida = []
    for i in range(blocos):
        fatia = amostras[i * n:(i + 1) * n]
        soma = sum(x * x for x in fatia)
        saida.append((soma / n) ** 0.5)
    topo = max(saida) if saida else 0.0
    return [x / topo for x in saida] if topo else saida


def bordas(caminho, de=None, ate=None):
    """(inicio, fim) da fala, em segundos do arquivo ORIGINAL, com respiro. O
    respiro de saida e maior porque a cauda da palavra decai devagar.

    `de` e `ate` restringem a busca a um trecho. O respiro nunca vaza para fora
    desse trecho: quem pediu um recorte pediu que o corte parasse ali."""
    total = probe.dur(caminho)
    piso = 0.0 if de is None else max(0.0, de)
    teto = total if ate is None else min(total, ate)
    env = envelope(caminho, de=de, ate=ate)
    if not env:
        return piso, teto
    limiar = 10 ** (config.DB_ENVELOPE / 20)
    acesos = [i for i, v in enumerate(env) if v > limiar]
    if not acesos:
        return piso, teto
    ini = max(piso, piso + acesos[0] * PASSO - config.RESPIRO_IN)
    fim = min(teto, piso + acesos[-1] * PASSO + PASSO + config.RESPIRO_OUT)
    return ini, max(ini + 0.10, fim)


def bordas_com_teto(caminho, teto=None, de=None, ate=None):
    ini, fim = bordas(caminho, de=de, ate=ate)
    if teto is not None:
        fim = min(fim, ini + teto)
    return ini, fim


def pausas_internas(caminho, ini, fim):
    """Pares (inicio, fim) de silencio inteiramente dentro do trecho, acima de
    PAUSA_MAX. Usa o detector do ffmpeg a -45 dB: a -34 dB a cauda da palavra
    era lida como silencio."""
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}",
         "-i", str(caminho),
         "-af", f"silencedetect=n={config.DB_PAUSA}dB:d={config.PAUSA_MAX}",
         "-f", "null", "-"],
        capture_output=True, text=True)
    comecos = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", r.stderr)]
    fins = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", r.stderr)]
    dur_trecho = fim - ini
    pausas = []
    for a in comecos:
        b = next((x for x in fins if x > a), None)
        if b is None:
            continue
        if a > 0.05 and b < dur_trecho - 0.05 and b - a > config.PAUSA_MAX:
            pausas.append((a, b))
    return pausas
