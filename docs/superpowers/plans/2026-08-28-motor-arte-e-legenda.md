# Motor, arte e legenda — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Letreiro, moldura e legenda queimada sobre o filme que o plano 1 já monta, com sete estilos visuais para escolher.

**Architecture:** Três módulos novos. `estilos` guarda as sete fichas — cor, fonte, contorno, posições. `arte` desenha letreiro e moldura em PNG com Pillow. `legenda` transcreve, quebra em blocos, desenha e compõe uma faixa RGBA única. `tratamentos` ganha a aplicação de sobreposição. O contrato de cenas cresce para carregar estilo e letreiro.

**Tech Stack:** Python 3.9 · ffmpeg 8.1.1 · Pillow · mlx-whisper · pytest.

**Escopo deste plano:** as sete fichas de estilo, letreiro com contorno e box opcional, legenda transcrita com correção de nome próprio, as quatro posições de legenda, e a omissão da legenda sob letreiro grande.

**Fora deste plano:** folha de aprovação, os quatro agentes, integração com serviços de IA.

**Grafismo esta fora, por decisao do dono.** A Chili nao faz enfeite: faz letreiro, e no
maximo um box ou moldura que de sustentacao ao proprio letreiro. Nao ha moldura de cena,
nao ha grafismo decorativo.

---

## O que o plano 1 deixou pronto

| módulo | interface |
|---|---|
| `motor/config.py` | `W, H, FPS, SR, DIVISORIA, SPLIT_TETO, VELOCIDADE, LUFS, TETO_DB, VOL_TRILHA`, e as constantes de tempo |
| `motor/probe.py` | `dur`, `dimensao`, `tem_audio`, `area_util` |
| `motor/fala.py` | `envelope`, `bordas`, `bordas_com_teto`, `pausas_internas`, `PASSO` |
| `motor/cenas.py` | `carregar`, `Producao`, `Cena`, `Topo`, `CenasInvalidas`, `TRATAMENTOS` |
| `motor/tratamentos.py` | `tela_cheia`, `split`, `aperta`, `enquadrar`, `recorte_topo`, `_roda`, `_saida_padrao` |
| `motor/montar.py` | `montar`, `duracoes`, `_bordas`, `_segmento` |
| `motor/trilha.py` | `aplicar` |
| `motor/laudo.py` | `rodar`, `em_portugues`, `TOLERANCIA_SYNC` |
| `tests/fixtures.py` | `clipe_fala`, `clipe_mudo`, `dimensao` |

**Restrição do ffmpeg desta máquina:** não tem `drawtext`, `subtitles` nem `ass`. Todo texto sobre imagem sai do Pillow em PNG e entra por `overlay`. Isso não é preferência — é o que existe.

---

## Estrutura de arquivos

| arquivo | responsabilidade |
|---|---|
| `motor/estilos.py` | as sete fichas: cor, fonte, contorno, posição de legenda e de letreiro |
| `motor/arte.py` | desenhar letreiro em PNG, com box opcional atras |
| `motor/legenda.py` | transcrever, corrigir nome próprio, quebrar em blocos, desenhar, compor a faixa |
| `motor/tratamentos.py` | ganha `com_overlay` |
| `motor/cenas.py` | contrato cresce: `estilo`, `letreiro`, `legenda` |
| `tests/fixtures.py` | ganha um gerador de fonte, para o teste não depender de fonte instalada |

---

## Task 1: As sete fichas de estilo

**Files:**
- Create: `motor/estilos.py`
- Test: `tests/test_estilos.py`

**De onde vêm.** São os sete estilos da skill de carrossel, reduzidos ao que atravessa para vídeo: cor, par tipográfico e como o texto se apoia no quadro. O que não atravessa — grafismo de página, retícula, colagem — fica de fora.

**A fonte é um problema real.** A do projeto de origem é licenciada e mora na máquina do autor. A ficha guarda uma lista de candidatas em ordem; quem resolve o caminho é `fonte()`, que devolve a primeira que existir e cai numa fonte do sistema se nenhuma existir. Sem isso a skill quebra na máquina de outra pessoa.

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_estilos.py
import pytest

from motor import estilos


def test_sao_sete():
    assert len(estilos.ESTILOS) == 7


def test_todo_estilo_tem_o_que_a_arte_precisa():
    campos = {"nome", "fundo", "texto", "contorno", "legenda_caixa",
              "legenda_texto", "fontes", "peso_letreiro"}
    for chave, e in estilos.ESTILOS.items():
        faltando = campos - set(e)
        assert not faltando, f"estilo {chave} sem: {faltando}"


def test_cores_sao_hexadecimais_de_seis_digitos():
    import re
    for chave, e in estilos.ESTILOS.items():
        for campo in ("fundo", "texto", "contorno", "legenda_caixa", "legenda_texto"):
            valor = e[campo]
            assert re.fullmatch(r"#[0-9A-Fa-f]{6}", valor), \
                f"{chave}.{campo} = {valor!r} nao e cor hexadecimal"


def test_carrega_um_estilo_pelo_nome():
    e = estilos.carregar("terminal")
    assert e["nome"]


def test_estilo_inexistente_diz_quais_existem():
    with pytest.raises(estilos.EstiloDesconhecido) as erro:
        estilos.carregar("roxo-neon")
    assert "terminal" in str(erro.value)


def test_a_fonte_resolvida_existe_no_disco():
    from pathlib import Path
    for chave in estilos.ESTILOS:
        caminho = estilos.fonte(chave)
        assert Path(caminho).exists(), f"{chave}: {caminho} nao existe"


def test_contraste_entre_texto_e_contorno():
    """Letreiro sem contraste entre preenchimento e contorno some no fundo."""
    for chave, e in estilos.ESTILOS.items():
        d = estilos.distancia_de_cor(e["texto"], e["contorno"])
        assert d > 120, f"{chave}: texto e contorno quase iguais ({d})"


def test_contraste_entre_legenda_e_caixa():
    for chave, e in estilos.ESTILOS.items():
        d = estilos.distancia_de_cor(e["legenda_texto"], e["legenda_caixa"])
        assert d > 120, f"{chave}: legenda ilegivel sobre a propria caixa ({d})"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_estilos.py -v`
Expected: FAIL — `motor.estilos` não existe

- [ ] **Step 3: Escrever o módulo**

```python
# motor/estilos.py
"""As sete fichas de estilo, reduzidas da skill de carrossel ao que atravessa
para video: cor, fonte e como o texto se apoia no quadro.

A FONTE E UM PROBLEMA REAL: a do projeto de origem e licenciada e mora na
maquina do autor. Cada ficha lista candidatas em ordem, e `fonte()` devolve a
primeira que existir. Sem isso a skill quebra na maquina de outra pessoa."""
from pathlib import Path

FONTES_DO_SISTEMA = "/System/Library/Fonts"
FONTES_DO_USUARIO = str(Path.home() / "Library" / "Fonts")

# ultima linha de defesa: existe em todo Mac
RESERVA = f"{FONTES_DO_SISTEMA}/Helvetica.ttc"


class EstiloDesconhecido(Exception):
    """O estilo pedido nao existe. A mensagem lista os que existem."""


def _u(nome):
    return f"{FONTES_DO_USUARIO}/{nome}"


def _s(nome):
    return f"{FONTES_DO_SISTEMA}/{nome}"


ESTILOS = {
    "terminal": {
        "nome": "Terminal — vazio, tipografia seca, sem enfeite",
        "fundo": "#0A0A0A", "texto": "#F2F2F2", "contorno": "#0A0A0A",
        "legenda_caixa": "#0A0A0A", "legenda_texto": "#F2F2F2",
        "fontes": [_u("Satoshi-Black.otf"), _s("Menlo.ttc"), RESERVA],
        "peso_letreiro": 96,
    },
    "brutalista": {
        "nome": "Brutalista — amarelo puro, contorno preto grosso",
        "fundo": "#FFE800", "texto": "#FFE800", "contorno": "#000000",
        "legenda_caixa": "#FFFFFF", "legenda_texto": "#000000",
        "fontes": [_u("Satoshi-Black.otf"), _s("Impact.ttf"), RESERVA],
        "peso_letreiro": 104,
    },
    "neubrutal": {
        "nome": "Neubrutal — cor chapada, contorno duro, sombra deslocada",
        "fundo": "#3D5AFE", "texto": "#FFFFFF", "contorno": "#0A0A0A",
        "legenda_caixa": "#3D5AFE", "legenda_texto": "#FFFFFF",
        "fontes": [_u("Satoshi-Black.otf"), _s("Avenir Next.ttc"), RESERVA],
        "peso_letreiro": 96,
    },
    "editorial": {
        "nome": "Editorial — creme e tinta, uma imagem grande",
        "fundo": "#F4F1EA", "texto": "#1A1A1A", "contorno": "#F4F1EA",
        "legenda_caixa": "#F4F1EA", "legenda_texto": "#1A1A1A",
        "fontes": [_u("Satoshi-Bold.otf"), _s("Georgia.ttf"), RESERVA],
        "peso_letreiro": 88,
    },
    "riso": {
        "nome": "Risografia — duas tintas, rosa e azul",
        "fundo": "#FF4F7B", "texto": "#FFF8E7", "contorno": "#1B2A88",
        "legenda_caixa": "#FFF8E7", "legenda_texto": "#1B2A88",
        "fontes": [_u("Satoshi-Black.otf"), _s("Avenir Next.ttc"), RESERVA],
        "peso_letreiro": 96,
    },
    "colagem": {
        "nome": "Colagem — recorte de papel, tipografia cortada",
        "fundo": "#E8E2D0", "texto": "#111111", "contorno": "#E8E2D0",
        "legenda_caixa": "#111111", "legenda_texto": "#E8E2D0",
        "fontes": [_u("Satoshi-Black.otf"), _s("Helvetica.ttc"), RESERVA],
        "peso_letreiro": 92,
    },
    "superminimal": {
        "nome": "Superminimal — branco, uma cor de acento",
        "fundo": "#FFFFFF", "texto": "#111111", "contorno": "#FFFFFF",
        "legenda_caixa": "#FFFFFF", "legenda_texto": "#111111",
        "fontes": [_u("Satoshi-Bold.otf"), _s("HelveticaNeue.ttc"), RESERVA],
        "peso_letreiro": 84,
    },
}

PADRAO = "brutalista"


def carregar(chave):
    if chave not in ESTILOS:
        raise EstiloDesconhecido(
            f"nao conheco o estilo '{chave}'. Os que existem sao: "
            + ", ".join(sorted(ESTILOS)))
    return ESTILOS[chave]


def fonte(chave):
    """Primeira fonte da lista que existir no disco."""
    for caminho in carregar(chave)["fontes"]:
        if Path(caminho).exists():
            return caminho
    return RESERVA


def rgb(cor):
    """'#RRGGBB' -> (r, g, b)."""
    cor = cor.lstrip("#")
    return tuple(int(cor[i:i + 2], 16) for i in (0, 2, 4))


def distancia_de_cor(a, b):
    """Distancia simples entre duas cores. Serve para provar contraste, nao
    para julgar estetica."""
    ra, rb = rgb(a), rgb(b)
    return sum(abs(x - y) for x, y in zip(ra, rb))
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_estilos.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add motor/estilos.py tests/test_estilos.py
git commit -m "feat: as sete fichas de estilo"
```

---

## Task 2: Desenhar letreiro

**Files:**
- Create: `motor/arte.py`
- Test: `tests/test_arte.py`

**Por que Pillow e não modelo de imagem.** Modelo de imagem erra acento em português — "não" vira "nao", "você" vira "vocé". Letreiro e legenda são texto vetorial desenhado, sempre.

**O contorno importa.** No projeto de origem o letreiro de abertura ficou ilegível sobre o rosto até ganhar contorno preto de 7px, como legenda de televisão.

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_arte.py
from PIL import Image

from motor import arte, config, estilos


def _tinta(caminho):
    """(x0, x1, y0, y1) do que nao e transparente, ou None se estiver vazio."""
    im = Image.open(caminho).convert("RGBA")
    alpha = im.getchannel("A")
    caixa = alpha.getbbox()
    if caixa is None:
        return None
    x0, y0, x1, y1 = caixa
    return x0, x1, y0, y1


def test_o_letreiro_sai_no_formato_do_filme(tmp_path):
    p = arte.letreiro("QUERO", "brutalista", tmp_path / "l.png")
    im = Image.open(p)
    assert im.size == (config.W, config.H)
    assert im.mode == "RGBA"


def test_o_letreiro_tem_texto_desenhado(tmp_path):
    p = arte.letreiro("QUERO", "brutalista", tmp_path / "l.png")
    assert _tinta(p) is not None


def test_o_letreiro_respeita_a_base_pedida(tmp_path):
    p = arte.letreiro("TESTE", "brutalista", tmp_path / "l.png", base=1200)
    _, _, _, y1 = _tinta(p)
    assert abs(y1 - 1200) < 30


def test_texto_longo_quebra_em_linhas(tmp_path):
    curto = arte.letreiro("UM", "brutalista", tmp_path / "a.png")
    longo = arte.letreiro("UMA FRASE BEM MAIS COMPRIDA QUE A OUTRA",
                          "brutalista", tmp_path / "b.png")
    _, _, y0c, y1c = _tinta(curto)
    _, _, y0l, y1l = _tinta(longo)
    assert (y1l - y0l) > (y1c - y0c)


def test_o_letreiro_nao_vaza_a_margem(tmp_path):
    p = arte.letreiro("UMA FRASE MUITO LONGA QUE PRECISA CABER NO QUADRO",
                      "brutalista", tmp_path / "l.png")
    x0, x1, _, _ = _tinta(p)
    assert x0 >= arte.MARGEM - 12
    assert x1 <= config.W - arte.MARGEM + 12


def test_o_contorno_aparece(tmp_path):
    """Sem contorno o letreiro some sobre imagem clara."""
    com = arte.letreiro("A", "brutalista", tmp_path / "com.png")
    sem = arte.letreiro("A", "brutalista", tmp_path / "sem.png", contorno=0)
    def conta_opacos(caminho):
        im = Image.open(caminho).convert("RGBA")
        return sum(1 for p in im.getchannel("A").getdata() if p > 200)
    assert conta_opacos(com) > conta_opacos(sem)


def test_cada_estilo_desenha(tmp_path):
    for chave in estilos.ESTILOS:
        p = arte.letreiro("TESTE", chave, tmp_path / f"{chave}.png")
        assert _tinta(p) is not None, f"{chave} saiu vazio"


def test_acento_e_desenhado_certo(tmp_path):
    """Modelo de imagem erra acento; texto vetorial nao. Este teste garante que
    o caractere acentuado ocupa mais altura que o sem acento."""
    sem = arte.letreiro("NAO", "brutalista", tmp_path / "sem.png")
    com = arte.letreiro("NÃO", "brutalista", tmp_path / "com.png")
    _, _, y0s, _ = _tinta(sem)
    _, _, y0c, _ = _tinta(com)
    assert y0c < y0s, "o til nao foi desenhado"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_arte.py -v`
Expected: FAIL — `motor.arte` não existe

- [ ] **Step 3: Escrever o módulo**

```python
# motor/arte.py
"""Letreiro e moldura, desenhados com Pillow.

POR QUE NAO MODELO DE IMAGEM: modelo erra acento em portugues — "nao" no lugar
de "nao", "voce" no lugar de "voce". Letreiro e legenda sao texto vetorial,
sempre.

O CONTORNO IMPORTA: no projeto de origem o letreiro de abertura ficou ilegivel
sobre o rosto ate ganhar contorno preto de 7px, como legenda de televisao."""
from PIL import Image, ImageDraw, ImageFont

from motor import config, estilos

MARGEM = 60          # folga lateral minima
BASE_PADRAO = 1560   # onde o letreiro se apoia, quando ninguem diz
CONTORNO = 7         # espessura do contorno, em pixels
ENTRELINHA = 1.10


def _quebra(desenho, texto, fonte_pil, largura_max):
    linhas, atual = [], ""
    for palavra in texto.split():
        tentativa = (atual + " " + palavra).strip()
        if desenho.textlength(tentativa, font=fonte_pil) <= largura_max:
            atual = tentativa
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def _cabe(texto, caminho_fonte, corpo, largura_max):
    im = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(caminho_fonte, corpo)
    linhas = _quebra(d, texto, f, largura_max)
    maior = max(d.textlength(l, font=f) for l in linhas) if linhas else 0
    return linhas, f, maior


def letreiro(texto, estilo, destino, base=None, contorno=None):
    """PNG 1080x1920 transparente com o texto apoiado em `base`.

    O corpo encolhe ate o texto caber na largura. No projeto de origem um
    letreiro de 300pt vazou o quadro em 1075 de 1080 — a busca evita isso."""
    ficha = estilos.carregar(estilo)
    caminho_fonte = estilos.fonte(estilo)
    base = BASE_PADRAO if base is None else base
    contorno = CONTORNO if contorno is None else contorno
    largura_max = config.W - MARGEM * 2

    corpo = ficha["peso_letreiro"]
    while corpo > 24:
        linhas, f, maior = _cabe(texto, caminho_fonte, corpo, largura_max)
        if maior <= largura_max:
            break
        corpo -= 4

    im = Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    altura_linha = corpo * ENTRELINHA
    altura = altura_linha * len(linhas)
    y = base - altura
    for linha in linhas:
        largura = d.textlength(linha, font=f)
        d.text((( config.W - largura) / 2, y), linha, font=f,
               fill=estilos.rgb(ficha["texto"]) + (255,),
               stroke_width=contorno,
               stroke_fill=estilos.rgb(ficha["contorno"]) + (255,))
        y += altura_linha
    im.save(destino)
    return destino


def moldura(estilo, destino, janela=None):
    """Moldura de televendas: cor chapada com uma janela vazada no meio, por
    onde a imagem aparece. `janela` = (x, y, largura, altura)."""
    ficha = estilos.carregar(estilo)
    jx, jy, jw, jh = janela or (60, 429, 960, 1411)
    im = Image.new("RGBA", (config.W, config.H), estilos.rgb(ficha["fundo"]) + (255,))
    d = ImageDraw.Draw(im)
    d.rectangle([jx, jy, jx + jw, jy + jh], fill=(0, 0, 0, 0))
    im.save(destino)
    return destino, (jx, jy, jw, jh)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_arte.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add motor/arte.py tests/test_arte.py
git commit -m "feat: desenhar letreiro com contorno, em sete estilos"
```

---

## Task 3: Aplicar sobreposição no segmento

**Files:**
- Modify: `motor/tratamentos.py` (adicionar `com_overlay`)
- Test: `tests/test_tratamentos.py`

- [ ] **Step 1: Acrescentar ao fim de `tests/test_tratamentos.py`**

```python
def test_overlay_entra_no_instante_pedido(tmp_path):
    from motor import arte
    base = fixtures.clipe_fala(tmp_path / "base.mov", falas=[(0.2, 2.0)], total=3.0)
    peca = arte.letreiro("TESTE", "brutalista", tmp_path / "p.png", base=1200)
    saida = tratamentos.com_overlay(base, peca, tmp_path / "o.mov",
                                    entra=1.5, dura=None)

    def tem_tinta(t):
        import subprocess
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(saida),
             "-frames:v", "1", "-vf", "crop=600:200:240:1050,scale=1:1",
             "-pix_fmt", "gray", "-f", "rawvideo", "-"],
            capture_output=True)
        return r.stdout[0] if r.stdout else 0

    antes, depois = tem_tinta(0.5), tem_tinta(2.5)
    assert abs(int(depois) - int(antes)) > 20, (
        f"o letreiro nao mudou o quadro: antes {antes}, depois {depois}")


def test_overlay_nao_muda_formato_nem_audio(tmp_path):
    from motor import arte
    base = fixtures.clipe_fala(tmp_path / "b2.mov", falas=[(0.2, 1.0)], total=2.0)
    peca = arte.letreiro("X", "brutalista", tmp_path / "p2.png")
    saida = tratamentos.com_overlay(base, peca, tmp_path / "o2.mov", entra=0.0)
    assert probe.dimensao(saida) == (1080, 1920)
    assert probe.tem_audio(saida) is True
    assert abs(probe.dur(saida) - probe.dur(base)) < 0.10


def test_overlay_com_duracao_sai_do_quadro(tmp_path):
    from motor import arte
    base = fixtures.clipe_fala(tmp_path / "b3.mov", falas=[(0.2, 3.0)], total=4.0)
    peca = arte.letreiro("SOME", "brutalista", tmp_path / "p3.png", base=1200)
    saida = tratamentos.com_overlay(base, peca, tmp_path / "o3.mov",
                                    entra=0.5, dura=1.0)

    def tinta(t):
        import subprocess
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(saida),
             "-frames:v", "1", "-vf", "crop=600:200:240:1050,scale=1:1",
             "-pix_fmt", "gray", "-f", "rawvideo", "-"],
            capture_output=True)
        return int(r.stdout[0]) if r.stdout else 0

    assert abs(tinta(1.0) - tinta(3.5)) > 20, "o letreiro nao saiu do quadro"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_tratamentos.py -v`
Expected: FAIL — `com_overlay` não existe

- [ ] **Step 3: Acrescentar ao fim de `motor/tratamentos.py`**

```python
def com_overlay(base, peca, destino, entra=0.0, dura=None, area=None):
    """Poe um PNG por cima do video, entrando em `entra` e saindo depois de
    `dura` segundos. `dura=None` deixa ate o fim.

    Este ffmpeg nao tem drawtext nem subtitles — todo texto sobre imagem entra
    por aqui, como PNG desenhado pelo Pillow."""
    d = probe.dur(base)
    saida_fade = (f",fade=t=out:st={entra + dura:.2f}:d=0.3:alpha=1"
                  if dura else "")
    _roda([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(base),
        "-loop", "1", "-t", f"{d:.3f}", "-i", str(peca),
        "-filter_complex",
        f"[1:v]format=rgba,fade=t=in:st={entra:.2f}:d=0.25:alpha=1{saida_fade}[p];"
        f"[0:v][p]overlay=0:0,format=yuv420p[v]",
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "copy", "-shortest", str(destino)])
    return destino
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_tratamentos.py -v`
Expected: todos passam

- [ ] **Step 5: Commit**

```bash
git add motor/tratamentos.py tests/test_tratamentos.py
git commit -m "feat: aplicar letreiro sobre o segmento"
```

---

## Task 4: O contrato cresce

**Files:**
- Modify: `motor/cenas.py`
- Modify: `motor/montar.py`
- Test: `tests/test_cenas.py`

**O contrato passa a aceitar:**

```json
{
  "estilo": "brutalista",
  "legenda": true,
  "cenas": [
    {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov",
     "letreiro": {"texto": "COMENTA QUERO", "entra": 1.1, "dura": 1.8, "base": 1400}}
  ]
}
```

| campo | onde | obrigatório | o que é |
|---|---|---|---|
| `estilo` | produção | não | uma das sete fichas. Padrão `brutalista` |
| `legenda` | produção | não | queimar legenda no fim. Padrão `true` |
| `letreiro.texto` | cena | sim, se houver letreiro | o que aparece escrito |
| `letreiro.entra` | cena | não | segundos após o início da cena. Padrão 0 |
| `letreiro.dura` | cena | não | quanto fica. Ausente = até o fim da cena |
| `letreiro.base` | cena | não | onde o texto se apoia. Padrão 1560 |

- [ ] **Step 1: Acrescentar ao fim de `tests/test_cenas.py`**

```python
def test_estilo_padrao_quando_nao_dito(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    assert cenas.carregar(p).estilo == "brutalista"


def test_estilo_escolhido(tmp_path):
    p = _grava(tmp_path, {"estilo": "terminal", "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    assert cenas.carregar(p).estilo == "terminal"


def test_estilo_inexistente_diz_quais_existem(tmp_path):
    p = _grava(tmp_path, {"estilo": "roxo-neon", "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    with pytest.raises(cenas.CenasInvalidas, match="brutalista"):
        cenas.carregar(p)


def test_letreiro_e_lido(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "letreiro": {"texto": "OLA", "entra": 1.0, "dura": 2.0}}]})
    c = cenas.carregar(p).cenas[0]
    assert c.letreiro.texto == "OLA"
    assert c.letreiro.entra == 1.0
    assert c.letreiro.dura == 2.0


def test_letreiro_sem_texto_e_erro(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
         "letreiro": {"entra": 1.0}}]})
    with pytest.raises(cenas.CenasInvalidas, match="texto"):
        cenas.carregar(p)


def test_legenda_ligada_por_padrao(tmp_path):
    p = _grava(tmp_path, {"cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    assert cenas.carregar(p).legenda is True


def test_legenda_pode_ser_desligada(tmp_path):
    p = _grava(tmp_path, {"legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov"}]})
    assert cenas.carregar(p).legenda is False
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_cenas.py -v`
Expected: FAIL — `Producao` não tem `estilo`

- [ ] **Step 3: Estender `motor/cenas.py`**

Acrescente ao topo, junto dos outros imports:

```python
from motor import estilos
```

Acrescente a dataclass do letreiro, junto de `Topo`:

```python
@dataclass
class Letreiro:
    texto: str
    entra: float = 0.0
    dura: Optional[float] = None
    base: Optional[int] = None
```

Acrescente o campo em `Cena`, depois de `topo`:

```python
    letreiro: Optional[Letreiro] = None
```

Acrescente os campos em `Producao`, depois de `trilha`:

```python
    estilo: str = estilos.PADRAO
    legenda: bool = True
```

Dentro de `carregar`, depois da leitura de `velocidade`, acrescente:

```python
    estilo = dados.get("estilo", estilos.PADRAO)
    if estilo not in estilos.ESTILOS:
        raise CenasInvalidas(
            f"nao conheco o estilo '{estilo}'. Os que existem sao: "
            + ", ".join(sorted(estilos.ESTILOS)))
    legenda = bool(dados.get("legenda", True))
```

Dentro do laço de cenas, antes de `montadas.append`, acrescente:

```python
        letreiro = None
        bruto_letreiro = bruto.get("letreiro")
        if bruto_letreiro:
            if not bruto_letreiro.get("texto"):
                raise CenasInvalidas(
                    f"cena {n}: o letreiro precisa do campo 'texto'")
            letreiro = Letreiro(
                texto=bruto_letreiro["texto"],
                entra=float(bruto_letreiro.get("entra", 0.0)),
                dura=bruto_letreiro.get("dura"),
                base=bruto_letreiro.get("base"))
```

E passe `letreiro=letreiro` para o construtor de `Cena`.

No `return`, acrescente `estilo=estilo, legenda=legenda`.

- [ ] **Step 4: Aplicar o letreiro em `motor/montar.py`**

Dentro do laço, logo depois de `seg = _segmento(...)`, acrescente:

```python
        if cena.letreiro:
            peca = tmp / f"l{cena.n:03d}.png"
            arte.letreiro(cena.letreiro.texto, prod.estilo, peca,
                          base=cena.letreiro.base)
            com_arte = tmp / f"la{cena.n:03d}.mov"
            tratamentos.com_overlay(seg, peca, com_arte,
                                    entra=cena.letreiro.entra,
                                    dura=cena.letreiro.dura)
            seg = com_arte
```

E o import no topo:

```python
from motor import arte
```

- [ ] **Step 5: Rodar tudo**

Run: `.venv/bin/pytest -v`
Expected: todos passam

- [ ] **Step 6: Commit**

```bash
git add motor/cenas.py motor/montar.py tests/test_cenas.py
git commit -m "feat: estilo e letreiro no contrato de cenas"
```

---

## Task 5: Transcrever e quebrar em blocos

**Files:**
- Create: `motor/legenda.py`
- Test: `tests/test_legenda.py`

**A regra que custou duas rodadas de trabalho no projeto de origem.** A transcrição manda; o roteiro só corrige **nome próprio**. Uma regra mais larga destrói a fala: os takes se afastam do roteiro, e palavra curta bate 0,8 de similaridade com qualquer vizinha — "ter" vira "te", "quem" vira "que", "no" vira "Não". Numa rodada saíram 19 correções e **as 19 estavam erradas**.

**Quebra de bloco.** Só teto de palavras e respiro emenda frases: "que muito agente. você / que têm a minha / idade". Tem de quebrar também em fim de frase.

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_legenda.py
from motor import legenda


def _p(texto, t, f):
    return {"p": texto, "t": t, "f": f}


def test_quebra_em_fim_de_frase():
    palavras = [_p("muito", 0.0, 0.3), _p("agente.", 0.3, 0.6),
                _p("Voce", 0.7, 1.0), _p("que", 1.0, 1.2)]
    blocos = legenda.blocos(palavras)
    assert len(blocos) == 2
    assert blocos[0][-1]["p"] == "agente."


def test_quebra_no_respiro():
    palavras = [_p("uma", 0.0, 0.3), _p("frase", 0.3, 0.6),
                _p("outra", 1.5, 1.8)]      # 0.9s de silencio
    assert len(legenda.blocos(palavras)) == 2


def test_teto_de_palavras():
    palavras = [_p(f"w{i}", i * 0.2, i * 0.2 + 0.15) for i in range(9)]
    for b in legenda.blocos(palavras):
        assert len(b) <= legenda.MAX_PALAVRAS


def test_bloco_orfao_junta_com_o_vizinho():
    palavras = [_p("a", 0.0, 0.2), _p("b", 0.2, 0.4),
                _p("c", 0.4, 0.6), _p("d", 0.6, 0.8), _p("e", 0.85, 1.0)]
    blocos = legenda.blocos(palavras)
    assert all(len(b) > 1 for b in blocos), "sobrou bloco de uma palavra so"


def test_nome_proprio_e_corrigido():
    palavras = [_p("as", 0.0, 0.2), _p("facas", 0.2, 0.5), _p("guinco", 0.5, 0.9)]
    trocas = legenda.corrigir(palavras, ["Ginsu"])
    assert len(trocas) == 1
    assert palavras[2]["p"] == "Ginsu"


def test_palavra_curta_nao_e_trocada():
    """A regra larga destruia a fala: 'ter' virava 'te', 'quem' virava 'que'."""
    originais = ["ter", "quem", "no", "teu", "meus", "deles"]
    palavras = [_p(w, i * 0.3, i * 0.3 + 0.2) for i, w in enumerate(originais)]
    legenda.corrigir(palavras, ["Ginsu", "te", "que", "Nao"])
    assert [w["p"] for w in palavras] == originais


def test_pontuacao_colada_sobrevive_a_troca():
    palavras = [_p("guinco?", 0.0, 0.4)]
    legenda.corrigir(palavras, ["Ginsu"])
    assert palavras[0]["p"] == "Ginsu?"


def test_troca_pedida_pode_inserir_mais_de_uma_palavra():
    palavras = [_p("a", 0.0, 0.2), _p("generativa", 0.2, 0.8)]
    legenda.corrigir(palavras, [], pedidas={"generativa": "I.A. generativa"})
    assert palavras[1]["p"] == "I.A. generativa"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_legenda.py -v`
Expected: FAIL — `motor.legenda` não existe

- [ ] **Step 3: Escrever a parte de texto do módulo**

```python
# motor/legenda.py
"""Legenda queimada: transcricao, correcao, blocos, desenho e composicao.

A TRANSCRICAO MANDA. O roteiro so conserta NOME PROPRIO. Qualquer regra mais
larga destroi a fala: os takes se afastam do roteiro, e palavra curta bate 0,8
de similaridade com qualquer vizinha. Numa rodada do projeto de origem sairam
19 correcoes e as 19 estavam erradas — "ter" virou "te", "quem" virou "que",
"no" virou "Nao", "contar" virou "continuar".

QUEBRA DE BLOCO: so teto de palavras e respiro emenda frases. Tem de quebrar
tambem em fim de frase."""
import difflib
import re
import unicodedata

MAX_PALAVRAS = 4
RESPIRO = 0.35            # silencio que separa dois blocos
LIMIAR_PROPRIO = 0.50     # sobre a forma sem acento
MIN_LETRAS = 4            # palavra menor que isto nunca e corrigida
FIM_DE_FRASE = re.compile(r"[.!?…]$")


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")


def normal(s):
    return re.sub(r"[^\wÀ-ſ]", "", s.lower())


def corrigir(palavras, proprios, pedidas=None):
    """Conserta SO nome proprio mal reconhecido, e as trocas explicitamente
    pedidas. Mantem o timestamp e a pontuacao colada.

    Devolve a lista de (antes, depois, instante) para auditoria."""
    pedidas = pedidas or {}
    trocas = []
    for w in palavras:
        n = normal(w["p"])
        sufixo = re.sub(r"^[\wÀ-ſ]+", "", w["p"])

        if n in pedidas:
            novo = pedidas[n] + sufixo
            trocas.append((w["p"], novo, round(w["t"], 2)))
            w["p"] = novo
            continue

        if not n or len(n) < MIN_LETRAS:
            continue

        melhor, semelhanca = None, 0.0
        for pr in proprios:
            s = difflib.SequenceMatcher(None, sem_acento(n), sem_acento(pr)).ratio()
            if s > semelhanca:
                melhor, semelhanca = pr, s
        if (melhor and semelhanca >= LIMIAR_PROPRIO
                and sem_acento(melhor) != sem_acento(n)):
            novo = melhor + sufixo
            trocas.append((w["p"], novo, round(w["t"], 2)))
            w["p"] = novo
    return trocas


def blocos(palavras):
    """Agrupa em blocos curtos. Quebra em fim de frase, em respiro, e no teto
    de palavras — nesta ordem."""
    saida, atual = [], []
    for w in palavras:
        if atual:
            corta = (FIM_DE_FRASE.search(atual[-1]["p"])
                     or w["t"] - atual[-1]["f"] > RESPIRO
                     or len(atual) >= MAX_PALAVRAS)
            if corta:
                saida.append(atual)
                atual = []
        atual.append(w)
    if atual:
        saida.append(atual)

    junto = []
    for b in saida:
        if (junto and len(b) == 1 and len(junto[-1]) < MAX_PALAVRAS
                and b[0]["t"] - junto[-1][-1]["f"] <= RESPIRO
                and not FIM_DE_FRASE.search(junto[-1][-1]["p"])):
            junto[-1].extend(b)
        else:
            junto.append(b)
    return junto
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_legenda.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add motor/legenda.py tests/test_legenda.py
git commit -m "feat: correcao de nome proprio e quebra de bloco da legenda"
```

---

## Task 6: Desenhar a legenda nas quatro posições

**Files:**
- Modify: `motor/legenda.py`
- Modify: `motor/config.py`
- Test: `tests/test_legenda.py`

**As quatro posições, medidas:**

| enquadramento | posição |
|---|---|
| tela cheia | centralizada, base **1375** |
| split, esquerda | x=60, topo em **827** |
| split, direita | alinhada à direita, topo em **827** |
| split, centralizada | centralizada, base **1375** |

A base 1375 vale para os dois porque assim a legenda não salta de lugar quando a cena vira. A base anterior, 1500, caía sob a interface do aplicativo.

- [ ] **Step 1: Acrescentar as constantes em `motor/config.py`**

```python
LEG_CORPO = 54                  # corpo da legenda
LEG_ENTRELINHA = 1.16
LEG_PAD_X, LEG_PAD_Y = 24, 12   # respiro dentro da caixa
LEG_LARGURA_MAX = 840           # forca quebra antes de vazar
LEG_BASE = 1375                 # base em tela cheia. A 1500 caia sob a
                                # interface do aplicativo
LEG_SPLIT_X = 60                # margem, na posicao alinhada a esquerda
LEG_SPLIT_TOPO = 827            # 20px abaixo da divisoria em 807
LEG_TOPO_LETREIRO = 1300        # letreiro com tinta abaixo disto tapa a legenda
```

- [ ] **Step 2: Acrescentar os testes**

```python
def test_as_quatro_posicoes_existem():
    assert set(legenda.POSICOES) == {"cheia", "esquerda", "direita", "centro"}


def test_legenda_em_tela_cheia_e_centralizada(tmp_path):
    from PIL import Image
    p = legenda.png("uma frase", "brutalista", tmp_path / "a.png", posicao="cheia")
    caixa = Image.open(p).convert("RGBA").getchannel("A").getbbox()
    x0, y0, x1, y1 = caixa
    centro = (x0 + x1) / 2
    assert abs(centro - 540) < 20, "nao ficou centralizada"
    assert abs(y1 - 1375) < 30, "a base nao e 1375"


def test_legenda_a_esquerda_no_split(tmp_path):
    from PIL import Image
    p = legenda.png("uma frase", "brutalista", tmp_path / "b.png", posicao="esquerda")
    x0, y0, _, _ = Image.open(p).convert("RGBA").getchannel("A").getbbox()
    assert abs(x0 - 60) < 12
    assert abs(y0 - 827) < 12


def test_legenda_a_direita_no_split(tmp_path):
    from PIL import Image
    p = legenda.png("uma frase", "brutalista", tmp_path / "c.png", posicao="direita")
    _, y0, x1, _ = Image.open(p).convert("RGBA").getchannel("A").getbbox()
    assert abs(x1 - (1080 - 60)) < 12
    assert abs(y0 - 827) < 12


def test_centro_do_split_usa_a_mesma_base_da_tela_cheia(tmp_path):
    from PIL import Image
    a = legenda.png("frase", "brutalista", tmp_path / "d.png", posicao="cheia")
    b = legenda.png("frase", "brutalista", tmp_path / "e.png", posicao="centro")
    ba = Image.open(a).convert("RGBA").getchannel("A").getbbox()
    bb = Image.open(b).convert("RGBA").getchannel("A").getbbox()
    assert abs(ba[3] - bb[3]) < 4, "a legenda saltaria na virada de cena"


def test_texto_longo_quebra_e_nao_vaza(tmp_path):
    from PIL import Image
    from motor import config
    p = legenda.png("uma frase bastante longa que precisa quebrar em duas linhas",
                    "brutalista", tmp_path / "f.png", posicao="cheia")
    x0, y0, x1, y1 = Image.open(p).convert("RGBA").getchannel("A").getbbox()
    assert (x1 - x0) <= config.LEG_LARGURA_MAX + 8
    assert (y1 - y0) > config.LEG_CORPO      # mais de uma linha
```

- [ ] **Step 3: Acrescentar ao `motor/legenda.py`**

```python
from PIL import Image, ImageDraw, ImageFont

from motor import config, estilos

POSICOES = ("cheia", "esquerda", "direita", "centro")


def _linhas(desenho, texto, fonte_pil, largura_max):
    saida, atual = [], ""
    for palavra in texto.split():
        tentativa = (atual + " " + palavra).strip()
        if desenho.textlength(tentativa, font=fonte_pil) <= largura_max:
            atual = tentativa
        else:
            if atual:
                saida.append(atual)
            atual = palavra
    if atual:
        saida.append(atual)
    return saida


def png(texto, estilo, destino, posicao="cheia"):
    """Um PNG 1080x1920 transparente com a legenda na posicao pedida.

    As quatro posicoes foram medidas: em tela cheia a base e 1375 (a 1500 caia
    sob a interface do aplicativo); no split, esquerda e direita se apoiam em
    827, logo abaixo da divisoria, e a centralizada usa a mesma base da tela
    cheia — assim a legenda nao salta quando a cena vira."""
    if posicao not in POSICOES:
        raise ValueError(f"posicao '{posicao}' desconhecida. Use uma de: "
                         + ", ".join(POSICOES))
    ficha = estilos.carregar(estilo)
    f = ImageFont.truetype(estilos.fonte(estilo), config.LEG_CORPO)

    im = Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    util = config.LEG_LARGURA_MAX - config.LEG_PAD_X * 2
    linhas = _linhas(d, texto, f, util)
    alt_linha = config.LEG_CORPO * config.LEG_ENTRELINHA
    largura = max(d.textlength(l, font=f) for l in linhas) + config.LEG_PAD_X * 2
    altura = alt_linha * len(linhas) + config.LEG_PAD_Y * 2

    if posicao == "esquerda":
        x0, y0 = config.LEG_SPLIT_X, config.LEG_SPLIT_TOPO
    elif posicao == "direita":
        x0, y0 = config.W - config.LEG_SPLIT_X - largura, config.LEG_SPLIT_TOPO
    else:                                  # cheia e centro
        x0, y0 = (config.W - largura) / 2, config.LEG_BASE - altura

    d.rectangle([x0, y0, x0 + largura, y0 + altura],
                fill=estilos.rgb(ficha["legenda_caixa"]) + (255,))
    cor = estilos.rgb(ficha["legenda_texto"]) + (255,)
    for i, linha in enumerate(linhas):
        cx = d.textlength(linha, font=f)
        alinhado = (x0 + config.LEG_PAD_X if posicao == "esquerda"
                    else x0 + (largura - cx) / 2)
        d.text((alinhado, y0 + config.LEG_PAD_Y + i * alt_linha),
               linha, font=f, fill=cor)
    im.save(destino)
    return destino
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_legenda.py -v`
Expected: todos passam

- [ ] **Step 5: Commit**

```bash
git add motor/legenda.py motor/config.py tests/test_legenda.py
git commit -m "feat: desenhar a legenda nas quatro posicoes medidas"
```

---

## Task 7: Transcrever de verdade

**Files:**
- Modify: `motor/legenda.py` (adicionar `transcrever`)
- Test: `tests/test_legenda.py`

**Cuidado com o teste.** Transcrever de verdade exige um modelo grande e áudio com fala humana — os clipes sintéticos de bipe não têm palavra nenhuma. O teste desta função tem de ser marcado como lento e pulável, e a suíte normal não pode depender dele.

- [ ] **Step 1: Acrescentar o teste**

```python
import os

import pytest


LENTO = pytest.mark.skipif(
    os.environ.get("TESTE_LENTO") != "1",
    reason="baixa e roda o modelo de transcricao; ligue com TESTE_LENTO=1")


def test_transcrever_devolve_o_formato_que_os_blocos_esperam():
    """Sem rodar o modelo: prova o contrato de dados que o resto consome."""
    palavras = [{"p": "ola", "t": 0.0, "f": 0.4}]
    assert legenda.blocos(palavras)[0][0]["p"] == "ola"


@LENTO
def test_transcrever_acha_as_palavras(tmp_path):
    import subprocess
    fala = tmp_path / "fala.wav"
    # voz sintetica do proprio macOS: fala de verdade, sem depender de gravacao
    subprocess.run(["say", "-v", "Luciana", "-o", str(fala),
                    "--data-format=LEF32@22050", "as facas ginsu cortam tudo"],
                   check=True)
    palavras = legenda.transcrever(fala, modelo="medium")
    texto = " ".join(w["p"] for w in palavras).lower()
    assert "facas" in texto
    assert all(w["f"] >= w["t"] for w in palavras)
    assert palavras == sorted(palavras, key=lambda w: w["t"])
```

- [ ] **Step 2: Acrescentar ao `motor/legenda.py`**

```python
MODELO = "large-v3"


def transcrever(caminho, modelo=MODELO):
    """Transcreve com timestamp por palavra. Devolve
    [{"p": palavra, "t": inicio, "f": fim}, ...].

    O modelo baixa no primeiro uso. Isto e lento e nao entra na suite normal."""
    import mlx_whisper
    r = mlx_whisper.transcribe(
        str(caminho),
        path_or_hf_repo=f"mlx-community/whisper-{modelo}-mlx",
        language="pt", word_timestamps=True, verbose=False)
    palavras = []
    for seg in r["segments"]:
        for w in seg.get("words", []):
            palavras.append({"p": w["word"].strip(),
                             "t": float(w["start"]), "f": float(w["end"])})
    return palavras
```

- [ ] **Step 3: Rodar**

Run: `.venv/bin/pytest tests/test_legenda.py -v`
Expected: todos passam, um pulado

Depois, uma vez, com o modelo:

Run: `TESTE_LENTO=1 .venv/bin/pytest tests/test_legenda.py -k transcrever_acha -v`
Expected: passa. Registre quanto demorou.

- [ ] **Step 4: Commit**

```bash
git add motor/legenda.py tests/test_legenda.py
git commit -m "feat: transcricao com timestamp por palavra"
```

---

## Task 8: Compor a faixa de legenda e queimar

**Files:**
- Modify: `motor/legenda.py` (adicionar `sob_letreiro`, `compor`)
- Test: `tests/test_legenda.py`

**Duas armadilhas do projeto de origem:**

1. **No concat de imagens, a última entrada duplicada herda a duração da anterior.** Sem cortar na duração total, a faixa inflou de 48s para 90s e o vídeo saiu curto.
2. **A legenda repete o letreiro grande.** Nas cenas em que um letreiro ocupa a faixa da legenda, ela tem de sumir — senão a mesma frase aparece duas vezes, uma grande e uma miúda.

- [ ] **Step 1: Acrescentar os testes**

```python
def test_sob_letreiro_reconhece_a_janela():
    mapa = [{"n": 1, "ini": 0.0, "fim": 3.0, "letreiro": [0.0, 3.0]},
            {"n": 2, "ini": 3.0, "fim": 6.0}]
    assert legenda.sob_letreiro(0.5, 1.5, mapa) is True
    assert legenda.sob_letreiro(4.0, 5.0, mapa) is False


def test_sob_letreiro_pega_sobreposicao_parcial():
    mapa = [{"n": 1, "ini": 0.0, "fim": 3.0, "letreiro": [1.0, 2.0]}]
    assert legenda.sob_letreiro(1.8, 2.5, mapa) is True


def test_a_faixa_tem_a_duracao_do_filme(tmp_path):
    from motor import probe
    from tests import fixtures
    filme = fixtures.clipe_fala(tmp_path / "f.mov", falas=[(0.3, 2.0)], total=4.0)
    palavras = [{"p": "uma", "t": 0.5, "f": 0.8},
                {"p": "frase", "t": 0.8, "f": 1.2}]
    faixa = legenda.faixa(legenda.blocos(palavras), "brutalista",
                          tmp_path / "faixa.mov", total=probe.dur(filme),
                          mapa=[])
    assert abs(probe.dur(faixa) - 4.0) < 0.15, (
        "a faixa inflou — a ultima entrada duplicada herdou a duracao anterior")


def test_queimar_nao_muda_duracao_nem_audio(tmp_path):
    from motor import probe
    from tests import fixtures
    filme = fixtures.clipe_fala(tmp_path / "g.mov", falas=[(0.3, 2.0)], total=4.0)
    palavras = [{"p": "teste", "t": 0.5, "f": 1.0}]
    saida = legenda.queimar(filme, legenda.blocos(palavras), "brutalista",
                            tmp_path / "leg.mp4", mapa=[])
    assert abs(probe.dur(saida) - probe.dur(filme)) < 0.15
    assert probe.tem_audio(saida) is True
    assert probe.dimensao(saida) == (1080, 1920)


def test_a_legenda_aparece_no_quadro(tmp_path):
    import subprocess
    from tests import fixtures
    filme = fixtures.clipe_fala(tmp_path / "h.mov", falas=[(0.3, 2.0)], total=4.0)
    palavras = [{"p": "teste", "t": 1.0, "f": 1.8}]
    saida = legenda.queimar(filme, legenda.blocos(palavras), "brutalista",
                            tmp_path / "leg2.mp4", mapa=[])

    def brilho(t):
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(saida),
             "-frames:v", "1", "-vf", "crop=600:120:240:1240,scale=1:1",
             "-pix_fmt", "gray", "-f", "rawvideo", "-"], capture_output=True)
        return int(r.stdout[0]) if r.stdout else 0

    assert abs(brilho(1.4) - brilho(3.5)) > 20, "a legenda nao apareceu"


def test_bloco_sob_letreiro_e_omitido(tmp_path):
    import subprocess
    from tests import fixtures
    filme = fixtures.clipe_fala(tmp_path / "i.mov", falas=[(0.3, 3.0)], total=4.0)
    palavras = [{"p": "escondido", "t": 1.0, "f": 1.8}]
    mapa = [{"n": 1, "ini": 0.0, "fim": 4.0, "letreiro": [0.0, 4.0]}]
    saida = legenda.queimar(filme, legenda.blocos(palavras), "brutalista",
                            tmp_path / "leg3.mp4", mapa=mapa)

    def brilho(t):
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(saida),
             "-frames:v", "1", "-vf", "crop=600:120:240:1240,scale=1:1",
             "-pix_fmt", "gray", "-f", "rawvideo", "-"], capture_output=True)
        return int(r.stdout[0]) if r.stdout else 0

    assert abs(brilho(1.4) - brilho(3.5)) < 12, (
        "a legenda apareceu mesmo sob o letreiro")
```

- [ ] **Step 2: Acrescentar ao `motor/legenda.py`**

```python
import subprocess
import tempfile
from pathlib import Path


def sob_letreiro(ini, fim, mapa):
    """O bloco cai onde um letreiro grande ja ocupa a faixa da legenda?

    Nessas cenas o letreiro escreve a mesma frase em corpo grande; legendar por
    baixo duplica o texto e briga com a arte."""
    for c in mapa or []:
        janela = c.get("letreiro")
        if janela and ini < janela[1] and fim > janela[0]:
            return True
    return False


def faixa(blocos_, estilo, destino, total, mapa=None):
    """Uma faixa RGBA com todos os blocos, para entrar num overlay so.

    ARMADILHA: no concat de imagens a ULTIMA entrada duplicada herda a duracao
    da anterior. Sem `-t` na duracao total a faixa infla — no projeto de origem
    passou de 48s para 90s e o video saiu curto."""
    tmp = Path(tempfile.mkdtemp(prefix="legenda-"))
    vazio = tmp / "vazio.png"
    Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0)).save(vazio)

    partes, t, omitidos = [], 0.0, 0
    for k, b in enumerate(blocos_):
        ini, fim = b[0]["t"], b[-1]["f"]
        if sob_letreiro(ini, fim, mapa):
            omitidos += 1
            continue
        if ini > t + 0.02:
            partes.append((vazio, ini - t))
        p = tmp / f"b{k:04d}.png"
        posicao = b[0].get("pos", "cheia")
        png(" ".join(w["p"] for w in b), estilo, p, posicao=posicao)
        partes.append((p, max(0.08, fim - ini)))
        t = fim
    if total > t:
        partes.append((vazio, total - t))
    if not partes:
        partes.append((vazio, total))

    lista = tmp / "faixa.txt"
    with open(lista, "w", encoding="utf-8") as fh:
        for p, d in partes:
            fh.write(f"file '{Path(p).resolve()}'\nduration {d:.3f}\n")
        fh.write(f"file '{Path(partes[-1][0]).resolve()}'\n")

    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(lista), "-vf", f"fps={config.FPS},format=rgba",
         "-t", f"{total:.3f}", "-c:v", "qtrle", str(destino)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("nao consegui montar a faixa de legenda: "
                           + r.stderr.strip()[:400])
    return destino, omitidos


def queimar(filme, blocos_, estilo, destino, mapa=None):
    """Queima a legenda no filme, com um overlay so."""
    from motor import probe
    total = probe.dur(filme)
    tmp = Path(tempfile.mkdtemp(prefix="queimar-"))
    trilha_leg, _ = faixa(blocos_, estilo, tmp / "faixa.mov", total, mapa)
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(filme), "-i", str(trilha_leg),
         "-filter_complex",
         "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]",
         "-map", "[v]", "-map", "0:a?", "-t", f"{total:.3f}",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-c:a", "copy", str(destino)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("nao consegui queimar a legenda: "
                           + r.stderr.strip()[:400])
    return destino
```

- [ ] **Step 3: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_legenda.py -v`
Expected: todos passam

- [ ] **Step 4: Commit**

```bash
git add motor/legenda.py tests/test_legenda.py
git commit -m "feat: compor a faixa de legenda e queimar no filme"
```

---

## Task 9: A legenda escolhe a posição pela cena

**Files:**
- Modify: `motor/legenda.py`
- Modify: `motor/montar.py`
- Test: `tests/test_legenda.py`

**Como a posição é decidida.** O mapa de cenas diz qual cena é `split`. Bloco que cai numa cena de split usa a posição escolhida na produção — esquerda, direita ou centro. Bloco em tela cheia usa `cheia`.

- [ ] **Step 1: Acrescentar os testes**

```python
def test_posicao_vem_do_mapa_de_cenas():
    mapa = [{"n": 1, "trat": "cheia", "ini": 0.0, "fim": 2.0},
            {"n": 2, "trat": "split", "ini": 2.0, "fim": 4.0}]
    assert legenda.posicao_do_bloco(0.5, 1.0, mapa, "esquerda") == "cheia"
    assert legenda.posicao_do_bloco(2.5, 3.0, mapa, "esquerda") == "esquerda"
    assert legenda.posicao_do_bloco(2.5, 3.0, mapa, "centro") == "centro"


def test_bloco_fora_do_mapa_usa_tela_cheia():
    assert legenda.posicao_do_bloco(9.0, 9.5, [], "esquerda") == "cheia"
```

- [ ] **Step 2: Acrescentar ao `motor/legenda.py`**

```python
def posicao_do_bloco(ini, fim, mapa, posicao_split="esquerda"):
    """Bloco numa cena de split usa a posicao escolhida na producao; em tela
    cheia usa 'cheia'."""
    meio = (ini + fim) / 2
    for c in mapa or []:
        if c["ini"] <= meio < c["fim"]:
            return posicao_split if c.get("trat") == "split" else "cheia"
    return "cheia"
```

E dentro de `faixa`, troque a linha da posição:

```python
        posicao = posicao_do_bloco(ini, fim, mapa, posicao_split)
```

Acrescente `posicao_split="esquerda"` à assinatura de `faixa` e de `queimar`, e repasse.

- [ ] **Step 3: Ligar no `motor/montar.py`**

No fim de `montar`, depois da trilha e antes de gravar o mapa:

```python
    if prod.legenda:
        palavras = legenda.transcrever(destino)
        legenda.corrigir(palavras, prod.proprios)
        blocos_ = legenda.blocos(palavras)
        com_leg = tmp / "legendado.mp4"
        legenda.queimar(destino, blocos_, prod.estilo, com_leg,
                        mapa=mapa, posicao_split=prod.legenda_split)
        os.replace(com_leg, str(destino).replace(".mp4", "-legendado.mp4"))
```

E acrescente `proprios: list` e `legenda_split: str = "esquerda"` a `Producao`, lidos do contrato (`"proprios": ["Ginsu"]`, `"legenda_split": "centro"`), com os testes correspondentes em `tests/test_cenas.py`.

- [ ] **Step 4: Rodar tudo**

Run: `.venv/bin/pytest -v`
Expected: todos passam

- [ ] **Step 5: Commit**

```bash
git add motor tests
git commit -m "feat: a legenda escolhe a posicao pela cena"
```

---

## Task 10: Registrar

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/DIARIO.md`

- [ ] **Step 1: Atualizar o estado no `CLAUDE.md`**

Trocar a linha de estado por:

```markdown
**Estado: motor pronto — montagem, arte e legenda. Falta a folha e os agentes.**
```

E acrescentar às armadilhas:

```markdown
- No concat de imagens a ULTIMA entrada duplicada herda a duracao da anterior.
  Sem `-t` na duracao total a faixa de legenda infla e o video sai curto.
- A transcricao manda; o roteiro so conserta NOME PROPRIO. Regra mais larga
  destroi a fala: numa rodada sairam 19 correcoes e as 19 estavam erradas.
- Fonte licenciada nao pode ser exigida. `estilos.fonte()` devolve a primeira
  candidata que existir e cai numa do sistema.
```

- [ ] **Step 2: Escrever a entrada do diário**

Acrescentar no topo, depois do cabeçalho:

```markdown
## 2026-08-28 — arte e legenda

Sete fichas de estilo, letreiro com contorno, moldura, e legenda queimada com
as quatro posicoes medidas.

- **A fonte e um problema de distribuicao.** A do projeto de origem e licenciada
  e mora na maquina do autor. Cada ficha lista candidatas em ordem e cai numa
  fonte do sistema. Sem isso a skill quebra na maquina de outra pessoa.
- **Texto vetorial, nunca modelo de imagem.** Modelo erra acento em portugues.
- **A legenda some sob letreiro grande**, senao a mesma frase aparece duas
  vezes, uma grande e uma miuda.
- **Base 1375 em tela cheia.** A 1500 caia sob a interface do aplicativo. A
  posicao centralizada do split usa a mesma base, para a legenda nao saltar na
  virada de cena.
```

- [ ] **Step 3: Rodar tudo e commitar**

```bash
.venv/bin/pytest
git add CLAUDE.md docs/DIARIO.md
git commit -m "docs: registrar arte e legenda"
```
