# Motor, núcleo — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um script que lê um arquivo de cenas e devolve um filme vertical montado, com ritmo e trilha — sem arte e sem legenda, que ficam para o plano 2.

**Architecture:** Módulos pequenos com uma responsabilidade cada. `config` guarda as constantes calibradas; `probe` mede arquivos; `fala` acha onde a voz começa e termina; `cenas` valida o contrato entre os agentes e o motor; `tratamentos` produz um segmento por cena; `trilha` mistura a música; `laudo` mede o resultado; `montar` orquestra. Nenhum módulo fora de `tratamentos` e `montar` chama ffmpeg para produzir vídeo.

**Tech Stack:** Python 3.9 · ffmpeg 8.1.1 · pytest. Sem dependência externa além do pytest — o motor usa só a biblioteca padrão e chama `ffmpeg`/`ffprobe` por `subprocess`.

**Escopo deste plano:** cenas de tela cheia e de split, corte de silêncio, compressão de pausa, velocidade por cena, concatenação sem dessincronia, trilha com abaixamento sob a voz, e o laudo de qualidade.

**Fora deste plano:** legenda, letreiros, grafismos, estilos, moldura de GC, folha de aprovação, agentes, MCP.

---

## Estrutura de arquivos

| arquivo | responsabilidade |
|---|---|
| `motor/config.py` | constantes calibradas, cada uma com o porquê no comentário |
| `motor/probe.py` | ler duração, dimensão e área útil de um arquivo |
| `motor/fala.py` | envelope de energia; onde a fala começa e termina; pausas internas |
| `motor/cenas.py` | carregar e validar o arquivo de cenas |
| `motor/tratamentos.py` | produzir o segmento de uma cena (tela cheia, split) |
| `motor/trilha.py` | misturar música com abaixamento sob a voz |
| `motor/laudo.py` | medir o resultado: sincronismo, duração, palavras perdidas |
| `motor/montar.py` | orquestrar: cenas → segmentos → filme |
| `tests/fixtures.py` | gerar clipes de teste com ffmpeg, sem usar gravação real |

**Por que material de teste gerado:** os testes precisam de vídeo com voz e silêncio em posições conhecidas. Gravação real não serve — o valor esperado seria chute, e o repositório carregaria vídeo pessoal.

---

## Task 0: Esqueleto do projeto

**Files:**
- Create: `motor/__init__.py`
- Create: `requirements-dev.txt`
- Create: `pytest.ini`

- [ ] **Step 1: Criar o pacote e a configuração de teste**

```bash
cd ~/Desktop/VIBECODING/conteudo/skill_talkingreel
mkdir -p motor tests
touch motor/__init__.py tests/__init__.py
```

```
# requirements-dev.txt
pytest==8.3.4
```

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

- [ ] **Step 2: Criar o ambiente e instalar**

Run:
```bash
python3 -m venv .venv
.venv/bin/pip install -q -r requirements-dev.txt
.venv/bin/pytest --version
```
Expected: `pytest 8.3.4`

- [ ] **Step 3: Confirmar que o ffmpeg tem o que o motor precisa**

Run:
```bash
ffmpeg -hide_banner -filters 2>/dev/null | grep -cE " (overlay|silencedetect|atempo|sidechaincompress|alimiter|concat) "
```
Expected: `6`

Se der menos de 6, pare: o motor depende desses filtros. Este ffmpeg **não** tem `drawtext`, `subtitles` nem `ass` — nenhum módulo pode usá-los.

- [ ] **Step 4: Commit**

```bash
git add motor tests requirements-dev.txt pytest.ini
git commit -m "chore: esqueleto do motor e ambiente de teste"
```

---

## Task 1: Constantes calibradas

**Files:**
- Create: `motor/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_config.py
from motor import config


def test_formato_vertical_de_reels():
    assert (config.W, config.H, config.FPS) == (1080, 1920, 30)


def test_divisoria_do_split_dentro_do_quadro():
    assert 0 < config.DIVISORIA < config.H
    assert config.DIVISORIA == 807


def test_janela_de_cima_do_split_e_deitada():
    largura, altura = config.W, config.DIVISORIA
    assert largura > altura


def test_pausa_comprimida_encurta():
    assert config.PAUSA_FICA < config.PAUSA_MAX


def test_saida_tem_mais_respiro_que_a_entrada():
    assert config.RESPIRO_OUT > config.RESPIRO_IN
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_config.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'motor.config'`

- [ ] **Step 3: Escrever o módulo**

```python
# motor/config.py
"""Constantes calibradas. Cada numero aqui custou uma rodada de erro no projeto
`conteudo/agentes-ginsu`. Nao "arredondar" nem "simplificar" sem medir de novo."""

W, H, FPS = 1080, 1920, 30      # vertical de Reels/TikTok

DIVISORIA = 807                 # linha do split, medida no pixel. A janela de cima
                                # fica 1080x807 (deitada); a de baixo, 1080x1113
SPLIT_TETO = 380                # quanto do teto sai no crop da janela de baixo.
                                # Sem isso o rosto nao cabe na janela

VELOCIDADE = 1.15               # padrao dos talking heads

RESPIRO_IN = 0.06               # folga antes da primeira palavra
RESPIRO_OUT = 0.32              # folga depois da ultima. Maior que a entrada porque
                                # a cauda da palavra decai devagar e colar corta o som

PAUSA_MAX = 0.22                # silencio interno acima disso e comprimido
PAUSA_FICA = 0.10               # para este tamanho

DB_PAUSA = -45                  # limiar para achar pausa interna. A -34 dB a cauda
                                # da palavra era lida como silencio e sumia
DB_ENVELOPE = -32               # limiar do envelope de energia nas pontas

LUFS = -14                      # normalizacao. As gravacoes chegam por volta de -36 dB
TETO_DB = -1.5                  # teto do limitador, para a voz nao estourar

VOL_TRILHA = 0.34               # musica bem abaixo da voz
SR = 48000                      # taxa de amostragem, igual em TODA etapa. Misturar
                                # taxas foi uma das tres causas do dessync progressivo
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_config.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add motor/config.py tests/test_config.py
git commit -m "feat: constantes calibradas do motor"
```

---

## Task 2: Material de teste gerado

**Files:**
- Create: `tests/fixtures.py`
- Test: `tests/test_fixtures.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_fixtures.py
import subprocess
from tests import fixtures


def _dur(caminho):
    saida = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(caminho)],
        capture_output=True, text=True).stdout.strip()
    return float(saida)


def test_clipe_de_fala_tem_a_duracao_pedida(tmp_path):
    c = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.5, 1.0), (2.0, 1.0)], total=3.5)
    assert abs(_dur(c) - 3.5) < 0.05


def test_clipe_de_fala_e_vertical(tmp_path):
    c = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.2, 0.5)], total=1.5)
    w, h = fixtures.dimensao(c)
    assert (w, h) == (1080, 1920)


def test_clipe_deitado_para_material_complementar(tmp_path):
    c = fixtures.clipe_mudo(tmp_path / "c.mp4", total=2.0, w=1920, h=1080)
    assert fixtures.dimensao(c) == (1920, 1080)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_fixtures.py -v`
Expected: FAIL com `ImportError: cannot import name 'fixtures'`

- [ ] **Step 3: Escrever o gerador**

```python
# tests/fixtures.py
"""Clipes sinteticos para teste. Um tom de 220 Hz marca onde ha fala; o resto e
silencio digital. Assim o valor esperado de cada teste e conhecido, e nenhum
video pessoal entra no repositorio."""
import subprocess
from pathlib import Path

W, H, FPS, SR = 1080, 1920, 30, 48000


def _roda(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:400])


def dimensao(caminho):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(caminho)],
        capture_output=True, text=True)
    nums = [int(x) for x in r.stdout.strip().split(",") if x.strip()]
    return nums[0], nums[1]


def clipe_fala(destino, falas, total, w=W, h=H):
    """falas: lista de (inicio, duracao) em segundos, onde ha tom audivel."""
    destino = Path(destino)
    volume = "+".join(
        f"between(t,{ini},{ini + dur})" for ini, dur in falas) or "0"
    _roda([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-t", f"{total}", "-i", f"color=c=gray:s={w}x{h}:r={FPS}",
        "-f", "lavfi", "-t", f"{total}", "-i", f"sine=frequency=220:sample_rate={SR}",
        "-filter_complex", f"[1:a]volume='{volume}':eval=frame[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "pcm_s16le", "-ar", str(SR), "-ac", "2",
        str(destino)])
    return destino


def clipe_mudo(destino, total, w=W, h=H, cor="teal"):
    destino = Path(destino)
    _roda([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-t", f"{total}", "-i", f"testsrc=s={w}x{h}:r={FPS}",
        "-vf", f"drawbox=c={cor}@0.3:t=fill",
        "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-an", str(destino)])
    return destino
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_fixtures.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures.py tests/test_fixtures.py
git commit -m "test: gerador de clipes sinteticos"
```

---

## Task 3: Medir arquivos

**Files:**
- Create: `motor/probe.py`
- Test: `tests/test_probe.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_probe.py
from motor import probe
from tests import fixtures


def test_duracao(tmp_path):
    c = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.5, 1.0)], total=3.0)
    assert abs(probe.dur(c) - 3.0) < 0.05


def test_dimensao(tmp_path):
    c = fixtures.clipe_mudo(tmp_path / "b.mp4", total=1.0, w=1920, h=1080)
    assert probe.dimensao(c) == (1920, 1080)


def test_vertical_nao_tem_area_util_para_cortar(tmp_path):
    c = fixtures.clipe_mudo(tmp_path / "c.mp4", total=1.0, w=1080, h=1920)
    assert probe.area_util(c) is None


def test_tem_audio(tmp_path):
    com = fixtures.clipe_fala(tmp_path / "d.mov", falas=[(0.2, 0.5)], total=1.5)
    sem = fixtures.clipe_mudo(tmp_path / "e.mp4", total=1.5)
    assert probe.tem_audio(com) is True
    assert probe.tem_audio(sem) is False
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_probe.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'motor.probe'`

- [ ] **Step 3: Escrever o módulo**

```python
# motor/probe.py
"""Leitura de arquivo. Nada aqui produz video."""
import re
import subprocess


def _ffprobe(args):
    return subprocess.run(["ffprobe", "-v", "error"] + args,
                          capture_output=True, text=True).stdout.strip()


def dur(caminho):
    saida = _ffprobe(["-show_entries", "format=duration", "-of", "csv=p=0", str(caminho)])
    return float(saida) if saida else 0.0


def dimensao(caminho):
    saida = _ffprobe(["-select_streams", "v:0", "-show_entries", "stream=width,height",
                      "-of", "csv=p=0", str(caminho)])
    nums = [int(x) for x in saida.split(",") if x.strip()]
    return (nums[0], nums[1]) if len(nums) >= 2 else (0, 0)


def tem_audio(caminho):
    saida = _ffprobe(["-select_streams", "a:0", "-show_entries", "stream=index",
                      "-of", "csv=p=0", str(caminho)])
    return bool(saida)


def area_util(caminho):
    """Gravacao exportada de app de edicao chega deitada com o vertical no meio e
    barra preta nos lados. Devolve o filtro de crop da area util, ou None se o
    arquivo ja for vertical."""
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", "1", "-i", str(caminho),
         "-vf", "cropdetect=24:2:0", "-frames:v", "12", "-f", "null", "-"],
        capture_output=True, text=True)
    achados = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", r.stderr)
    if not achados:
        return None
    cw, ch, cx, cy = map(int, achados[-1])
    if ch == 0 or cw / ch > 0.6:      # ja e vertical ou quase: nao mexe
        return None
    sw, sh = dimensao(caminho)
    if sw and sh and sw <= sh:        # o ffmpeg ja entregou vertical aos filtros
        return None                   # (bruto de iPhone tem rotacao nos metadados)
    return f"crop={cw}:{ch}:{cx}:{cy},"
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_probe.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add motor/probe.py tests/test_probe.py
git commit -m "feat: leitura de duracao, dimensao e area util"
```

---

## Task 4: Achar a fala pelo envelope de energia

**Files:**
- Create: `motor/fala.py`
- Test: `tests/test_fala.py`

**Por que envelope e não detector de silêncio:** o detector do ffmpeg deixa sobra depois da última palavra — um respiro baixo não conta como silêncio para ele, e o corte fica frouxo. O envelope mede a energia direto na amostra.

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_fala.py
from motor import fala
from tests import fixtures


def test_acha_o_inicio_da_fala(tmp_path):
    # tom de 1.0s comecando em 1.20s, dentro de um clipe de 3s
    c = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(1.20, 1.0)], total=3.0)
    ini, _ = fala.bordas(c)
    assert abs(ini - 1.20) < 0.12


def test_acha_o_fim_da_fala(tmp_path):
    c = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.5, 1.0)], total=3.0)
    _, fim = fala.bordas(c)
    assert abs(fim - 1.50) < 0.40      # o respiro de saida adiciona folga


def test_pausa_interna_e_encontrada(tmp_path):
    # duas falas com 0.8s de silencio entre elas: e pausa
    c = fixtures.clipe_fala(tmp_path / "c.mov", falas=[(0.3, 0.6), (1.7, 0.6)], total=3.0)
    pausas = fala.pausas_internas(c, 0.0, 3.0)
    assert len(pausas) == 1
    ini, fim = pausas[0]
    assert 0.8 < ini < 1.1
    assert 1.6 < fim < 1.9


def test_pausa_curta_nao_conta(tmp_path):
    # 0.15s entre as falas, abaixo do limite de 0.22s
    c = fixtures.clipe_fala(tmp_path / "d.mov", falas=[(0.3, 0.6), (1.05, 0.6)], total=2.5)
    assert fala.pausas_internas(c, 0.0, 2.5) == []


def test_teto_encurta_o_fim(tmp_path):
    c = fixtures.clipe_fala(tmp_path / "e.mov", falas=[(0.5, 2.0)], total=3.5)
    ini, fim = fala.bordas_com_teto(c, teto=1.0)
    assert abs(fim - (ini + 1.0)) < 0.01
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_fala.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'motor.fala'`

- [ ] **Step 3: Escrever o módulo**

```python
# motor/fala.py
"""Onde a voz comeca, onde termina, e onde ela para no meio.

Regra que vale para todo corte deste motor: a TRANSCRICAO diz qual e a palavra,
o ENVELOPE diz onde cortar. E consoante oclusiva (p t k b d g) tem silencio
DENTRO da palavra — cortar no primeiro silencio depois de "tudo" decepa o "do".
Quem for fixar um corte fino, meça a 5 ms."""
import array
import re
import subprocess

from motor import config, probe

PASSO = 0.010          # 10 ms por janela de envelope
_TAXA_ENV = 8000       # o envelope nao precisa de qualidade, so de energia


def envelope(caminho, passo=PASSO):
    """Devolve a energia normalizada (0 a 1) em janelas de `passo` segundos."""
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(caminho),
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


def bordas(caminho):
    """(inicio, fim) da fala, com respiro. O respiro de saida e maior porque a
    cauda da palavra decai devagar."""
    env = envelope(caminho)
    total = probe.dur(caminho)
    if not env:
        return 0.0, total
    limiar = 10 ** (config.DB_ENVELOPE / 20)
    acesos = [i for i, v in enumerate(env) if v > limiar]
    if not acesos:
        return 0.0, total
    ini = max(0.0, acesos[0] * PASSO - config.RESPIRO_IN)
    fim = min(total, acesos[-1] * PASSO + PASSO + config.RESPIRO_OUT)
    return ini, max(ini + 0.10, fim)


def bordas_com_teto(caminho, teto=None):
    ini, fim = bordas(caminho)
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_fala.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add motor/fala.py tests/test_fala.py
git commit -m "feat: bordas da fala por envelope de energia e pausas internas"
```

---

## Task 5: O contrato entre os agentes e o motor

**Files:**
- Create: `motor/cenas.py`
- Test: `tests/test_cenas.py`

**O contrato.** Um JSON. Os agentes escrevem; o motor lê. Nenhum agente escreve comando de vídeo.

```json
{
  "formato": {"w": 1080, "h": 1920, "fps": 30},
  "velocidade": 1.15,
  "trilha": "audio/lofi.mp3",
  "cenas": [
    {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"},
    {"n": 2, "trat": "cheia", "arquivo": "gravacoes/take-02.mov",
     "teto": 5.24, "velocidade": 1.0},
    {"n": 3, "trat": "split", "arquivo": "gravacoes/take-03.mov",
     "topo": {"arquivo": "broll/tv.mp4", "ancora": 0.0}}
  ]
}
```

| campo | obrigatório | o que é |
|---|---|---|
| `n` | sim | número da cena, único |
| `trat` | sim | `cheia` ou `split` |
| `arquivo` | sim | o take de talking head |
| `teto` | não | corta a cena N segundos depois do início da fala |
| `velocidade` | não | sobrepõe a velocidade geral nesta cena |
| `topo` | só em `split` | material da janela de cima |
| `topo.ancora` | não | de onde cortar quando o material não é deitado: 0.0 topo, 0.5 centro, 1.0 base |

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_cenas.py
import json

import pytest

from motor import cenas


def _grava(tmp_path, dados, arquivos=("gravacoes/take-01.mov",)):
    for rel in arquivos:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps(dados), encoding="utf-8")
    return p


def test_carrega_o_minimo(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    r = cenas.carregar(p)
    assert r.velocidade == 1.15
    assert len(r.cenas) == 1
    assert r.cenas[0].n == 1
    assert r.cenas[0].velocidade == 1.15


def test_velocidade_da_cena_sobrepoe_a_geral(tmp_path):
    p = _grava(tmp_path, {"velocidade": 1.15, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "velocidade": 1.0}]})
    assert cenas.carregar(p).cenas[0].velocidade == 1.0


def test_split_sem_topo_e_erro(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "split", "arquivo": "gravacoes/take-01.mov"}]})
    with pytest.raises(cenas.CenasInvalidas, match="topo"):
        cenas.carregar(p)


def test_tratamento_desconhecido_e_erro(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "voadora", "arquivo": "gravacoes/take-01.mov"}]})
    with pytest.raises(cenas.CenasInvalidas, match="voadora"):
        cenas.carregar(p)


def test_arquivo_que_nao_existe_e_erro(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/sumiu.mov"}]})
    with pytest.raises(cenas.CenasInvalidas, match="sumiu.mov"):
        cenas.carregar(p)


def test_numero_repetido_e_erro(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"},
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    with pytest.raises(cenas.CenasInvalidas, match="repetid"):
        cenas.carregar(p)


def test_ancora_fora_do_intervalo_e_erro(tmp_path):
    p = _grava(tmp_path,
               {"cenas": [{"n": 1, "trat": "split",
                           "arquivo": "gravacoes/take-01.mov",
                           "topo": {"arquivo": "broll/tv.mp4", "ancora": 2.0}}]},
               arquivos=("gravacoes/take-01.mov", "broll/tv.mp4"))
    with pytest.raises(cenas.CenasInvalidas, match="ancora"):
        cenas.carregar(p)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_cenas.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'motor.cenas'`

- [ ] **Step 3: Escrever o módulo**

```python
# motor/cenas.py
"""O contrato entre os agentes e o motor. Os agentes escrevem este arquivo;
o motor le. Nenhum agente escreve comando de video."""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from motor import config

TRATAMENTOS = ("cheia", "split")


class CenasInvalidas(Exception):
    """O arquivo de cenas nao pode ser usado. A mensagem diz o que corrigir."""


@dataclass
class Topo:
    arquivo: Path
    ancora: float = 0.0        # 0.0 topo, 0.5 centro, 1.0 base


@dataclass
class Cena:
    n: int
    trat: str
    arquivo: Path
    velocidade: float
    teto: Optional[float] = None
    topo: Optional[Topo] = None


@dataclass
class Producao:
    raiz: Path
    velocidade: float
    trilha: Optional[Path]
    cenas: list = field(default_factory=list)


def _caminho(raiz, rel, onde):
    p = (raiz / rel).resolve()
    if not p.exists():
        raise CenasInvalidas(f"cena {onde}: o arquivo {rel} nao existe")
    return p


def carregar(caminho):
    caminho = Path(caminho)
    raiz = caminho.parent
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise CenasInvalidas(f"o arquivo de cenas nao e um JSON valido: {e}") from e

    velocidade = float(dados.get("velocidade", config.VELOCIDADE))
    trilha = dados.get("trilha")
    lista = dados.get("cenas") or []
    if not lista:
        raise CenasInvalidas("o arquivo de cenas nao tem nenhuma cena")

    vistos, montadas = set(), []
    for bruto in lista:
        n = bruto.get("n")
        if n is None:
            raise CenasInvalidas("ha uma cena sem numero (campo 'n')")
        if n in vistos:
            raise CenasInvalidas(f"cena {n}: numero repetido")
        vistos.add(n)

        trat = bruto.get("trat")
        if trat not in TRATAMENTOS:
            raise CenasInvalidas(
                f"cena {n}: tratamento '{trat}' desconhecido. "
                f"Use um destes: {', '.join(TRATAMENTOS)}")

        arquivo = bruto.get("arquivo")
        if not arquivo:
            raise CenasInvalidas(f"cena {n}: falta o campo 'arquivo'")

        topo = None
        if trat == "split":
            bruto_topo = bruto.get("topo")
            if not bruto_topo or not bruto_topo.get("arquivo"):
                raise CenasInvalidas(
                    f"cena {n}: split precisa do campo 'topo' com um arquivo")
            ancora = float(bruto_topo.get("ancora", 0.0))
            if not 0.0 <= ancora <= 1.0:
                raise CenasInvalidas(
                    f"cena {n}: 'ancora' deve estar entre 0.0 e 1.0, veio {ancora}")
            topo = Topo(arquivo=_caminho(raiz, bruto_topo["arquivo"], n), ancora=ancora)

        montadas.append(Cena(
            n=n, trat=trat,
            arquivo=_caminho(raiz, arquivo, n),
            velocidade=float(bruto.get("velocidade", velocidade)),
            teto=bruto.get("teto"),
            topo=topo))

    return Producao(
        raiz=raiz, velocidade=velocidade,
        trilha=_caminho(raiz, trilha, "trilha") if trilha else None,
        cenas=montadas)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_cenas.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add motor/cenas.py tests/test_cenas.py
git commit -m "feat: contrato do arquivo de cenas, com validacao"
```

---

## Task 6: Segmento de tela cheia

**Files:**
- Create: `motor/tratamentos.py`
- Test: `tests/test_tratamentos.py`

**Regras de ffmpeg que este módulo tem de respeitar** — cada uma custou uma rodada de erro:

1. `-ss` vai **antes** do `-i`. Depois do `-i` vira opção de saída e o corte escorrega para o arquivo seguinte.
2. Áudio **sem compressão** (`pcm_s16le`) nos segmentos. Só o filme final é comprimido.
3. `-ar 48000` em toda etapa.
4. Cada segmento sai **exatamente** 1080x1920. Alguma etapa devolve um pixel a menos, e o concat quebra.

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_tratamentos.py
from motor import cenas, probe, tratamentos
from tests import fixtures


def _cena(tmp_path, nome="a.mov", falas=((0.5, 1.0),), total=3.0):
    arq = fixtures.clipe_fala(tmp_path / nome, falas=list(falas), total=total)
    return cenas.Cena(n=1, trat="cheia", arquivo=arq, velocidade=1.0)


def test_tela_cheia_sai_no_formato_do_filme(tmp_path):
    c = _cena(tmp_path)
    saida = tratamentos.tela_cheia(c, tmp_path / "s1.mov")
    assert probe.dimensao(saida) == (1080, 1920)


def test_tela_cheia_corta_o_silencio_das_pontas(tmp_path):
    # fala de 1.0s no meio de um clipe de 4s: o segmento tem de ficar bem menor
    c = _cena(tmp_path, falas=((1.5, 1.0),), total=4.0)
    saida = tratamentos.tela_cheia(c, tmp_path / "s2.mov")
    assert probe.dur(saida) < 2.2


def test_tela_cheia_mantem_audio(tmp_path):
    c = _cena(tmp_path)
    saida = tratamentos.tela_cheia(c, tmp_path / "s3.mov")
    assert probe.tem_audio(saida) is True


def test_teto_encurta_a_cena(tmp_path):
    arq = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.5, 2.5)], total=4.0)
    sem = cenas.Cena(n=1, trat="cheia", arquivo=arq, velocidade=1.0)
    com = cenas.Cena(n=2, trat="cheia", arquivo=arq, velocidade=1.0, teto=1.0)
    d_sem = probe.dur(tratamentos.tela_cheia(sem, tmp_path / "s4.mov"))
    d_com = probe.dur(tratamentos.tela_cheia(com, tmp_path / "s5.mov"))
    assert d_com < d_sem
    assert abs(d_com - 1.0) < 0.15


def test_velocidade_encurta_na_proporcao(tmp_path):
    arq = fixtures.clipe_fala(tmp_path / "c.mov", falas=[(0.3, 2.0)], total=3.0)
    normal = cenas.Cena(n=1, trat="cheia", arquivo=arq, velocidade=1.0)
    rapida = cenas.Cena(n=2, trat="cheia", arquivo=arq, velocidade=1.15)
    d1 = probe.dur(tratamentos.tela_cheia(normal, tmp_path / "s6.mov"))
    d2 = probe.dur(tratamentos.tela_cheia(rapida, tmp_path / "s7.mov"))
    assert abs(d2 - d1 / 1.15) < 0.15
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_tratamentos.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'motor.tratamentos'`

- [ ] **Step 3: Escrever o módulo**

```python
# motor/tratamentos.py
"""Produz o segmento de uma cena. E o unico modulo, junto com montar.py, que
chama ffmpeg para gerar video.

REGRAS QUE NAO PODEM SER QUEBRADAS:
  1. `-ss` vai ANTES do `-i`. Depois do `-i` ele vira opcao de saida e o corte
     escorrega para o arquivo seguinte. Custou meia hora de dessync.
  2. Audio dos segmentos em pcm_s16le. Comprimir aqui e comprimir de novo no
     final acumula atraso a cada emenda.
  3. -ar 48000 em toda etapa.
  4. Todo segmento sai EXATAMENTE 1080x1920. Alguma etapa devolve 1918 e o
     concat quebra.
"""
import subprocess

from motor import config, fala, probe

_SHARP = "unsharp=5:5:0.7:5:5:0,eq=contrast=1.08:saturation=1.04"


def _roda(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg falhou: " + r.stderr.strip()[:500])


def _saida_padrao(destino):
    return ["-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-c:a", "pcm_s16le", "-ar", str(config.SR), "-ac", "2", str(destino)]


def _velocidade(vel):
    """Filtros de video e audio para mudar a velocidade sem mudar o tom."""
    if abs(vel - 1.0) < 0.001:
        return "", []
    return f",setpts=PTS/{vel}", ["-af", f"atempo={vel}"]


def enquadrar(caminho):
    """Preenche 1080x1920 cortando o excesso, nunca deformando."""
    pb = probe.area_util(caminho) or ""
    return (f"{pb}scale={config.W}:{config.H}"
            f":force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={config.W}:{config.H},{_SHARP},setsar=1")


def tela_cheia(cena, destino):
    ini, fim = fala.bordas_com_teto(cena.arquivo, cena.teto)
    vf_vel, _ = _velocidade(cena.velocidade)
    muda_vel = abs(cena.velocidade - 1.0) > 0.001
    af = ["-af", (f"atempo={cena.velocidade}," if muda_vel else "")
          + f"loudnorm=I={config.LUFS}:TP={config.TETO_DB}"]
    _roda(["ffmpeg", "-y", "-v", "error",
           "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(cena.arquivo),
           "-vf", f"{enquadrar(cena.arquivo)}{vf_vel},fps={config.FPS},format=yuv420p",
           *af] + _saida_padrao(destino))
    return destino
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_tratamentos.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add motor/tratamentos.py tests/test_tratamentos.py
git commit -m "feat: segmento de tela cheia, com corte de silencio e velocidade"
```

---

## Task 7: Segmento de split, com âncora de recorte

**Files:**
- Modify: `motor/tratamentos.py` (adicionar `split` e `_janela_topo`)
- Modify: `tests/test_tratamentos.py` (adicionar os testes de split)

**A regra do recorte.** A janela de cima é 1080x807, deitada. Material vertical perde altura: um 9:16 sobra 42%, um 1:1 sobra 75%. Por isso a âncora existe — cortar pelo centro decepa cabeça. O corte horizontal é sempre centralizado.

- [ ] **Step 1: Escrever os testes que falham**

Acrescente ao fim de `tests/test_tratamentos.py`:

```python
def _cena_split(tmp_path, topo_w, topo_h, ancora=0.0):
    take = fixtures.clipe_fala(tmp_path / f"t{topo_w}x{topo_h}.mov",
                               falas=[(0.4, 1.2)], total=3.0)
    broll = fixtures.clipe_mudo(tmp_path / f"b{topo_w}x{topo_h}.mp4",
                                total=3.0, w=topo_w, h=topo_h)
    return cenas.Cena(n=3, trat="split", arquivo=take, velocidade=1.0,
                      topo=cenas.Topo(arquivo=broll, ancora=ancora))


def test_split_sai_no_formato_do_filme(tmp_path):
    c = _cena_split(tmp_path, 1920, 1080)
    saida = tratamentos.split(c, tmp_path / "sp1.mov")
    assert probe.dimensao(saida) == (1080, 1920)


def test_split_mantem_o_audio_do_take(tmp_path):
    c = _cena_split(tmp_path, 1920, 1080)
    saida = tratamentos.split(c, tmp_path / "sp2.mov")
    assert probe.tem_audio(saida) is True


def test_material_deitado_nao_precisa_de_ancora():
    # 1920x1080 na janela 1080x807: a altura sobra inteira, o corte e na largura
    assert tratamentos.recorte_topo(1920, 1080, ancora=0.0) == \
           tratamentos.recorte_topo(1920, 1080, ancora=1.0)


def test_ancora_muda_o_corte_de_material_vertical():
    do_topo = tratamentos.recorte_topo(1080, 1920, ancora=0.0)
    do_meio = tratamentos.recorte_topo(1080, 1920, ancora=0.5)
    da_base = tratamentos.recorte_topo(1080, 1920, ancora=1.0)
    assert do_topo != do_meio != da_base


def test_ancora_zero_pega_o_topo_da_imagem():
    filtro = tratamentos.recorte_topo(1080, 1920, ancora=0.0)
    assert filtro.endswith(":0:0")


def test_ancora_um_pega_a_base_da_imagem():
    # 1080x1920 escalado para largura 1080 continua 1920 de altura;
    # a janela pede 807, entao o corte comeca em 1920-807 = 1113
    filtro = tratamentos.recorte_topo(1080, 1920, ancora=1.0)
    assert filtro.endswith(":0:1113")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_tratamentos.py -v`
Expected: FAIL com `AttributeError: module 'motor.tratamentos' has no attribute 'recorte_topo'`

- [ ] **Step 3: Escrever a implementação**

Acrescente ao fim de `motor/tratamentos.py`:

```python
def recorte_topo(largura, altura, ancora):
    """Filtro que encaixa um material de `largura`x`altura` na janela de cima do
    split (1080x807), cortando o que sobra.

    A janela e deitada. Material vertical perde altura: 9:16 sobra 42%, 1:1
    sobra 75%. Por isso a ancora existe — cortar pelo centro decepa cabeca.
    ancora 0.0 = topo, 0.5 = centro, 1.0 = base. Na largura o corte e sempre
    centralizado, porque ali sobra pouco."""
    jan_w, jan_h = config.W, config.DIVISORIA
    escala = max(jan_w / largura, jan_h / altura)
    esc_w, esc_h = round(largura * escala), round(altura * escala)
    y = int(round((esc_h - jan_h) * ancora))
    x = int(round((esc_w - jan_w) / 2))
    return (f"scale={esc_w}:{esc_h}:flags=lanczos,"
            f"crop={jan_w}:{jan_h}:{x}:{y}")


def split(cena, destino):
    """Cena 3-em-1: material complementar na janela de cima, o take embaixo.
    O audio e sempre o do take; o material de cima entra mudo."""
    alto, baixo = config.DIVISORIA, config.H - config.DIVISORIA
    ini, fim = fala.bordas_com_teto(cena.arquivo, cena.teto)
    d = fim - ini
    tw, th = probe.dimensao(cena.topo.arquivo)
    vf_vel, _ = _velocidade(cena.velocidade)
    pb = probe.area_util(cena.arquivo) or ""

    _roda([
        "ffmpeg", "-y", "-v", "error",
        "-stream_loop", "-1", "-i", str(cena.topo.arquivo),
        "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(cena.arquivo),
        "-filter_complex",
        # janela de cima: o complementar, recortado pela ancora
        f"[0:v]{recorte_topo(tw, th, cena.topo.ancora)},"
        f"trim=0:{d:.3f},setpts=PTS-STARTPTS,fps={config.FPS},setsar=1[cima];"
        # janela de baixo: o take, com o teto cortado para o rosto caber
        f"[1:v]{pb}scale={config.W}:{config.H}"
        f":force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={config.W}:{baixo}:0:{config.SPLIT_TETO},{_SHARP},"
        f"fps={config.FPS},setsar=1[baixo];"
        # empilha e fixa o tamanho: sem isto sai 1918 e o concat quebra
        f"[cima][baixo]vstack=inputs=2,scale={config.W}:{config.H},"
        f"setsar=1{vf_vel},format=yuv420p[v]",
        "-map", "[v]", "-map", "1:a",
        "-af", (f"atempo={cena.velocidade}," if abs(cena.velocidade - 1.0) > 0.001 else "")
                + f"loudnorm=I={config.LUFS}:TP={config.TETO_DB}",
    ] + _saida_padrao(destino))
    return destino
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_tratamentos.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add motor/tratamentos.py tests/test_tratamentos.py
git commit -m "feat: segmento de split com ancora de recorte no complementar"
```

---

## Task 8: Juntar os segmentos sem dessincronizar

**Files:**
- Create: `motor/montar.py`
- Test: `tests/test_montar.py`

**A armadilha central deste projeto.** Juntar por lista (`concat demuxer`) descartava trechos de áudio e o filme dessincronizava progressivamente. Juntar por **filtro** decodifica e re-sincroniza tudo. Antes de juntar, todo segmento precisa ter exatamente o mesmo tamanho.

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_montar.py
import json

from motor import montar, probe
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_montar.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'motor.montar'`

- [ ] **Step 3: Escrever o módulo**

```python
# motor/montar.py
"""Orquestra: le o arquivo de cenas, produz um segmento por cena, junta tudo.

A ARMADILHA CENTRAL: juntar por lista (concat demuxer) descartava trechos de
audio e o filme dessincronizava progressivamente. Juntar por FILTRO decodifica
e re-sincroniza. E antes de juntar, todo segmento tem de ter exatamente o mesmo
tamanho — alguma etapa devolve um pixel a menos."""
import json
import subprocess
import tempfile
from pathlib import Path

from motor import cenas as mod_cenas
from motor import config, probe, tratamentos


def duracoes(caminho):
    """(duracao do video, duracao do audio). Se diferirem muito, ha problema."""
    def _d(fluxo):
        saida = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", fluxo,
             "-show_entries", "stream=duration", "-of", "csv=p=0", str(caminho)],
            capture_output=True, text=True).stdout.strip()
        return float(saida.split(",")[0]) if saida else 0.0
    return _d("v:0"), _d("a:0")


def _segmento(cena, destino):
    if cena.trat == "cheia":
        return tratamentos.tela_cheia(cena, destino)
    if cena.trat == "split":
        return tratamentos.split(cena, destino)
    raise ValueError(f"tratamento sem implementacao: {cena.trat}")


def montar(caminho_cenas, destino, tmp=None):
    prod = mod_cenas.carregar(caminho_cenas)
    destino = Path(destino)
    tmp = Path(tmp or tempfile.mkdtemp(prefix="talkingreel-"))
    tmp.mkdir(parents=True, exist_ok=True)

    segmentos, mapa, t = [], [], 0.0
    for cena in prod.cenas:
        seg = _segmento(cena, tmp / f"s{cena.n:03d}.mov")
        d = probe.dur(seg)
        mapa.append({"n": cena.n, "trat": cena.trat,
                     "ini": round(t, 3), "fim": round(t + d, 3)})
        t += d
        segmentos.append(seg)

    args = ["ffmpeg", "-y", "-v", "error"]
    for seg in segmentos:
        args += ["-i", str(seg)]
    cadeia = "".join(f"[{i}:v][{i}:a]" for i in range(len(segmentos)))
    args += ["-filter_complex",
             f"{cadeia}concat=n={len(segmentos)}:v=1:a=1[v][a]",
             "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-crf", "18", "-preset", "medium",
             "-c:a", "aac", "-b:a", "192k", "-ar", str(config.SR),
             "-movflags", "+faststart", str(destino)]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg falhou ao juntar: " + r.stderr.strip()[:500])

    (Path(caminho_cenas).parent / "cenas-mapa.json").write_text(
        json.dumps(mapa, indent=1, ensure_ascii=False), encoding="utf-8")
    return destino
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_montar.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add motor/montar.py tests/test_montar.py
git commit -m "feat: juntar segmentos por filtro, com mapa de cenas"
```

---

## Task 9: Comprimir as pausas internas

**Files:**
- Modify: `motor/tratamentos.py` (adicionar `aperta`)
- Modify: `motor/montar.py` (usar `aperta` antes do tratamento)
- Modify: `tests/test_montar.py` (adicionar teste de ritmo)

**Por que.** Cortar só as pontas deixa buraco no meio da fala. Pausa acima de 0,22s é comprimida para 0,10s, e é isso que dá o ritmo sem pausa entre falas.

- [ ] **Step 1: Escrever o teste que falha**

Acrescente ao fim de `tests/test_montar.py`:

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_montar.py::test_pausa_interna_longa_e_comprimida -v`
Expected: FAIL — a duração fica acima de 2.0s porque a pausa não foi comprimida

- [ ] **Step 3: Escrever a implementação**

Acrescente ao fim de `motor/tratamentos.py`:

```python
def aperta(caminho, destino, ini, fim):
    """Corta as pontas E comprime as pausas internas. Devolve (arquivo, quantas
    pausas foram comprimidas).

    So cortar as pontas deixa buraco no meio da fala. Pausa acima de PAUSA_MAX
    vira PAUSA_FICA, e e isso que da o ritmo sem pausa entre falas."""
    pausas = fala.pausas_internas(caminho, ini, fim)
    if not pausas:
        _roda(["ffmpeg", "-y", "-v", "error",
               "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(caminho)]
              + _saida_padrao(destino))
        return destino, 0

    marcas, t = [], 0.0
    for a, b in pausas:
        marcas.append((t, a + config.PAUSA_FICA))
        t = b
    marcas.append((t, fim - ini))

    partes = []
    for k, (a, b) in enumerate(marcas):
        if b - a < 0.05:
            continue
        pedaco = f"{destino}.p{k}.mov"
        _roda(["ffmpeg", "-y", "-v", "error",
               "-ss", f"{ini + a:.3f}", "-to", f"{ini + b:.3f}", "-i", str(caminho)]
              + _saida_padrao(pedaco))
        partes.append(pedaco)

    args = ["ffmpeg", "-y", "-v", "error"]
    for p in partes:
        args += ["-i", p]
    cadeia = "".join(f"[{i}:v][{i}:a]" for i in range(len(partes)))
    args += ["-filter_complex", f"{cadeia}concat=n={len(partes)}:v=1:a=1[v][a]",
             "-map", "[v]", "-map", "[a]"] + _saida_padrao(destino)
    _roda(args)
    for p in partes:
        Path(p).unlink(missing_ok=True)
    return destino, len(pausas)
```

Acrescente o import no topo de `motor/tratamentos.py`:

```python
from pathlib import Path
```

`Path.unlink(missing_ok=True)` exige Python 3.8 ou mais novo. Este Mac tem 3.9 — confira
com `python3 --version` antes de seguir.

Em `motor/tratamentos.py`, faça `tela_cheia` e `split` aceitarem um arquivo já apertado. Substitua a primeira linha de `tela_cheia`:

```python
def tela_cheia(cena, destino, ja_cortado=False):
    if ja_cortado:
        ini, fim = 0.0, probe.dur(cena.arquivo)
    else:
        ini, fim = fala.bordas_com_teto(cena.arquivo, cena.teto)
```

E a primeira linha útil de `split`:

```python
def split(cena, destino, ja_cortado=False):
    alto, baixo = config.DIVISORIA, config.H - config.DIVISORIA
    if ja_cortado:
        ini, fim = 0.0, probe.dur(cena.arquivo)
    else:
        ini, fim = fala.bordas_com_teto(cena.arquivo, cena.teto)
    d = fim - ini
```

Em `motor/montar.py`, substitua `_segmento` e o laço que o chama:

```python
def _segmento(cena, destino, ja_cortado=False):
    if cena.trat == "cheia":
        return tratamentos.tela_cheia(cena, destino, ja_cortado)
    if cena.trat == "split":
        return tratamentos.split(cena, destino, ja_cortado)
    raise ValueError(f"tratamento sem implementacao: {cena.trat}")
```

```python
    segmentos, mapa, t = [], [], 0.0
    for cena in prod.cenas:
        ini, fim = _bordas(cena)
        apertado, n_pausas = tratamentos.aperta(
            cena.arquivo, tmp / f"a{cena.n:03d}.mov", ini, fim)
        cena_apertada = replace(cena, arquivo=Path(apertado))
        seg = _segmento(cena_apertada, tmp / f"s{cena.n:03d}.mov", ja_cortado=True)
        d = probe.dur(seg)
        mapa.append({"n": cena.n, "trat": cena.trat, "pausas": n_pausas,
                     "ini": round(t, 3), "fim": round(t + d, 3)})
        t += d
        segmentos.append(seg)
```

E acrescente ao topo de `motor/montar.py`:

```python
from dataclasses import replace

from motor import fala


def _bordas(cena):
    return fala.bordas_com_teto(cena.arquivo, cena.teto)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/ -v`
Expected: todos passam, incluindo `test_pausa_interna_longa_e_comprimida`

- [ ] **Step 5: Commit**

```bash
git add motor/tratamentos.py motor/montar.py tests/test_montar.py
git commit -m "feat: comprimir pausa interna para dar ritmo"
```

---

## Task 10: Trilha com abaixamento sob a voz

**Files:**
- Create: `motor/trilha.py`
- Modify: `motor/montar.py` (chamar a trilha quando houver)
- Test: `tests/test_trilha.py`

**Como funciona.** A música toca por baixo e abaixa sozinha quando a voz entra — o filtro `sidechaincompress` usa a voz como chave. A ordem importa: comprimir a música tendo a voz como chave, e só depois misturar as duas. Inverter faz o contrário do desejado.

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_trilha.py
from motor import probe, trilha
from tests import fixtures


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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_trilha.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'motor.trilha'`

- [ ] **Step 3: Escrever o módulo**

```python
# motor/trilha.py
"""Musica por baixo da voz.

A ORDEM IMPORTA: comprimir a MUSICA tendo a VOZ como chave, e so depois
misturar. Inverter as entradas do sidechaincompress comprime a voz usando a
musica como chave — o contrario do que se quer, e o erro passa despercebido
porque o arquivo sai sem erro."""
import subprocess

from motor import config, probe


def aplicar(filme, musica, destino, volume=None):
    volume = config.VOL_TRILHA if volume is None else volume
    total = probe.dur(filme)
    r = subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(filme),
        "-stream_loop", "-1", "-i", str(musica),
        "-filter_complex",
        f"[1:a]volume={volume},atrim=0:{total:.3f},asetpts=PTS-STARTPTS[m];"
        # a voz e a chave; quem abaixa e a musica
        f"[m][0:a]sidechaincompress=threshold=0.06:ratio=6:attack=20:release=350[duck];"
        f"[0:a][duck]amix=inputs=2:duration=first:normalize=0,"
        f"alimiter=limit={10 ** (config.TETO_DB / 20):.4f}[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "pcm_s16le", "-ar", str(config.SR), "-ac", "2",
        "-t", f"{total:.3f}", str(destino)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg falhou na trilha: " + r.stderr.strip()[:500])
    return destino
```

Em `motor/montar.py`, dentro de `montar`, logo antes de gravar o mapa, acrescente:

```python
    if prod.trilha:
        com_trilha = tmp / "com-trilha.mov"
        trilha.aplicar(destino, prod.trilha, com_trilha)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(com_trilha),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-ar", str(config.SR), "-movflags", "+faststart",
                        str(destino)], check=True)
```

E o import no topo de `motor/montar.py`:

```python
from motor import trilha
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/ -v`
Expected: todos passam

- [ ] **Step 5: Commit**

```bash
git add motor/trilha.py motor/montar.py tests/test_trilha.py
git commit -m "feat: trilha com abaixamento sob a voz"
```

---

## Task 11: Laudo de qualidade

**Files:**
- Create: `motor/laudo.py`
- Test: `tests/test_laudo.py`

**Para que serve.** O Bluey roda isto antes de publicar qualquer folha. É medição, não julgamento — e foi assim que quase todo erro apareceu no projeto de origem.

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_laudo.py
import json

from motor import laudo, montar
from tests import fixtures


def _filme(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    for i in (1, 2):
        fixtures.clipe_fala(tmp_path / "gravacoes" / f"take-{i:02d}.mov",
                            falas=[(0.4, 1.2)], total=3.0)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "cenas": [
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_laudo.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'motor.laudo'`

- [ ] **Step 3: Escrever o módulo**

```python
# motor/laudo.py
"""Medicao do resultado, para o Bluey rodar antes de publicar qualquer folha.

E medicao, nao julgamento. No projeto de origem quase todo erro apareceu aqui e
nao no olho: 0,475s de dessync, um pedaco de palavra que sobrou, uma cena que
encurtou 0,19s."""
import json
from pathlib import Path

from motor import montar, probe

TOLERANCIA_SYNC = 0.10      # segundos entre o fim do video e o fim do audio


def rodar(filme, caminho_cenas=None):
    d_v, d_a = montar.duracoes(filme)
    problemas = []

    if d_a <= 0:
        problemas.append("o filme esta sem audio")
    if d_v <= 0:
        problemas.append("o filme esta sem imagem")
    if d_v > 0 and d_a > 0 and abs(d_v - d_a) > TOLERANCIA_SYNC:
        problemas.append(
            f"a imagem e o som terminam em momentos diferentes: "
            f"{abs(d_v - d_a):.2f} segundo de diferenca")

    w, h = probe.dimensao(filme)
    if (w, h) != (1080, 1920):
        problemas.append(f"o filme saiu {w}x{h} em vez de 1080x1920")

    cenas_mapa = []
    if caminho_cenas:
        mapa = Path(caminho_cenas).parent / "cenas-mapa.json"
        if mapa.exists():
            cenas_mapa = json.loads(mapa.read_text(encoding="utf-8"))
            for a, b in zip(cenas_mapa, cenas_mapa[1:]):
                if abs(a["fim"] - b["ini"]) > 0.001:
                    problemas.append(
                        f"ha um buraco entre a cena {a['n']} e a cena {b['n']}")

    return {"ok": not problemas,
            "duracao": round(max(d_v, d_a), 3),
            "dif_video_audio": round(d_v - d_a, 3),
            "dimensao": [w, h],
            "cenas": len(cenas_mapa),
            "problemas": problemas}


def em_portugues(resultado):
    """O texto que vai para a pessoa. Sem termo tecnico — quem le nao entende de
    montagem nem de audio."""
    linhas = [f"O video tem {resultado['duracao']:.1f} segundos"]
    if resultado["cenas"]:
        linhas[0] += f", em {resultado['cenas']} cenas"
    linhas[0] += "."
    if resultado["ok"]:
        linhas.append("Imagem e som terminam juntos, e o tamanho esta certo "
                      "para Instagram e TikTok.")
    else:
        linhas.append("Encontrei isto:")
        linhas += [f"- {p}" for p in resultado["problemas"]]
    return "\n".join(linhas)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_laudo.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add motor/laudo.py tests/test_laudo.py
git commit -m "feat: laudo de qualidade em portugues sem jargao"
```

---

## Task 12: Linha de comando e prova de ponta a ponta

**Files:**
- Create: `motor/__main__.py`
- Test: `tests/test_ponta_a_ponta.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_ponta_a_ponta.py
import json
import subprocess
import sys

from motor import laudo, probe
from tests import fixtures


def test_um_filme_com_tela_cheia_e_split(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    (tmp_path / "broll").mkdir(parents=True, exist_ok=True)
    for i in (1, 2, 3):
        fixtures.clipe_fala(tmp_path / "gravacoes" / f"take-{i:02d}.mov",
                            falas=[(0.4, 1.0), (2.0, 0.8)], total=3.5)
    fixtures.clipe_mudo(tmp_path / "broll" / "deitado.mp4", total=4.0, w=1920, h=1080)
    fixtures.clipe_mudo(tmp_path / "broll" / "vertical.mp4", total=4.0, w=1080, h=1920)

    (tmp_path / "cenas.json").write_text(json.dumps({
        "velocidade": 1.15,
        "cenas": [
            {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"},
            {"n": 2, "trat": "split", "arquivo": "gravacoes/take-02.mov",
             "topo": {"arquivo": "broll/deitado.mp4"}},
            {"n": 3, "trat": "split", "arquivo": "gravacoes/take-03.mov",
             "topo": {"arquivo": "broll/vertical.mp4", "ancora": 0.0},
             "velocidade": 1.0},
        ]}), encoding="utf-8")

    saida = tmp_path / "filme.mp4"
    r = subprocess.run([sys.executable, "-m", "motor",
                        str(tmp_path / "cenas.json"), str(saida)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    assert probe.dimensao(saida) == (1080, 1920)
    resultado = laudo.rodar(saida, tmp_path / "cenas.json")
    assert resultado["ok"] is True, resultado["problemas"]
    assert resultado["cenas"] == 3


def test_erro_no_arquivo_de_cenas_explica_o_que_corrigir(tmp_path):
    (tmp_path / "cenas.json").write_text(json.dumps({
        "cenas": [{"n": 1, "trat": "split", "arquivo": "some.mov"}]}),
        encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "motor",
                        str(tmp_path / "cenas.json"), str(tmp_path / "f.mp4")],
                       capture_output=True, text=True)
    assert r.returncode == 1
    assert "topo" in r.stdout + r.stderr
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_ponta_a_ponta.py -v`
Expected: FAIL — `No module named motor.__main__`

- [ ] **Step 3: Escrever a linha de comando**

```python
# motor/__main__.py
"""Uso: python3 -m motor <cenas.json> <saida.mp4>"""
import sys

from motor import cenas, laudo, montar


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip())
        return 2
    try:
        filme = montar.montar(argv[1], argv[2])
    except cenas.CenasInvalidas as e:
        print(f"O arquivo de cenas tem um problema: {e}")
        return 1
    except RuntimeError as e:
        print(f"Nao consegui montar o filme: {e}")
        return 1
    print(laudo.em_portugues(laudo.rodar(filme, argv[1])))
    print(f"pronto: {filme}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/ -v`
Expected: todos passam

- [ ] **Step 5: Commit**

```bash
git add motor/__main__.py tests/test_ponta_a_ponta.py
git commit -m "feat: linha de comando do motor e prova de ponta a ponta"
```

---

## Task 13: Registrar o que ficou pronto

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/DIARIO.md`

- [ ] **Step 1: Atualizar a seção de comandos do `CLAUDE.md`**

Substitua a seção `## Comandos`:

```markdown
## Comandos
- `python3 -m motor <cenas.json> <saida.mp4>` — monta o filme e imprime o laudo
- `.venv/bin/pytest` — roda os testes do motor
```

E na primeira linha do arquivo, troque o estado:

```markdown
**Estado: motor do nucleo pronto (cena cheia, split, ritmo, trilha, laudo).
Falta arte, legenda, folha e agentes.**
```

- [ ] **Step 2: Escrever a entrada do diário**

Acrescente no topo de `docs/DIARIO.md`, depois do cabeçalho:

```markdown
## 2026-08-28 — motor do nucleo

Primeira parte do motor. Le um `cenas.json` e devolve o filme montado: corte de
silencio pelas pontas, compressao de pausa interna, velocidade por cena, split
com ancora de recorte, trilha com abaixamento sob a voz, e laudo de qualidade.

Decisoes que valem registro:

- **Material de teste gerado por ffmpeg**, nao gravacao real. O valor esperado
  de cada teste fica conhecido e nenhum video pessoal entra no repositorio.
- **Nove modulos pequenos** em vez de um script grande. So `tratamentos.py` e
  `montar.py` geram video; o resto so mede ou valida.
- **O `cenas.json` e o contrato.** Os agentes escrevem; o motor le. Nenhum
  agente escreve comando de video.
- **A ancora de recorte** existe porque a janela de cima do split e deitada
  (1080x807) e material vertical perde 58% da altura. Cortar pelo centro
  decepa cabeca.

Armadilhas herdadas do `conteudo/agentes-ginsu`, todas com teste:
`-ss` antes do `-i`; audio sem compressao nos segmentos; juntar por filtro e
nao por lista; fixar 1080x1920 antes de juntar; a voz e a chave do
`sidechaincompress`, nunca o contrario.
```

- [ ] **Step 3: Rodar tudo uma última vez**

Run: `.venv/bin/pytest tests/ -v`
Expected: todos passam

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md docs/DIARIO.md
git commit -m "docs: registrar o motor do nucleo"
```

---

## O que este plano deixa para os próximos

| plano | conteúdo |
|---|---|
| 2 · motor, arte e legenda | letreiros e grafismos por Pillow; legenda transcrita, com as duas posições e a omissão sob letreiro; as sete fichas de estilo; moldura de GC |
| 3 · folha de aprovação | folha minimalista por fase, com o registro do que foi resolvido saindo da página |
| 4 · a skill e os agentes | `SKILL.md`, Bluey, Bandit, Chili, Bingo, perfil, incorporação do `deslopar` e do express cut, tabela de MCP, limpeza de dados pessoais |
