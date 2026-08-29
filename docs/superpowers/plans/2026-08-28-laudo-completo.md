# Laudo completo — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completar a bateria de medição que o Bluey roda antes de publicar qualquer folha de aprovação, para que a folha mostre fato medido e não opinião de agente.

**Architecture:** `motor/laudo.py` hoje mede quatro coisas (som existe, imagem existe, imagem e som terminam juntos, tamanho certo). Faltam as três que pegaram erro de verdade no projeto de origem: palavra decepada na emenda, legenda fora da faixa segura, e material complementar repetindo em loop. Cada uma vira uma função própria num módulo novo (`motor/medidas.py`), e `laudo.rodar` apenas as chama e junta o resultado. Isso mantém `laudo.py` como orquestrador fino e deixa cada medição testável sozinha.

**Tech Stack:** Python + ffmpeg + Pillow. Reaproveita `motor/fala.envelope` (energia do áudio em janelas de 10 ms) e `motor/legenda.png` (para saber onde a legenda cai).

---

## Por que estas três medições, e não outras

Cada uma corresponde a um erro que já aconteceu e que ninguém viu no olho:

| medição | o erro que ela pega | como apareceu |
|---|---|---|
| palavra decepada na emenda | o corte come o começo ou o fim de uma palavra | "sobrou um pouquinho da palavra seguinte"; depois, "corto o tudo, volte um pouco" |
| legenda fora da faixa segura | a legenda cai sob a interface do Instagram/TikTok | base 1500 caía sob a interface; foi para 1375 |
| material complementar em loop | um b-roll de 2,4s repetindo 30 vezes numa cena de 71s | medido nesta sessão, com gravação real |

**A regra que rege as três:** medir, nunca julgar. O laudo diz "a energia do áudio no ponto de corte da cena 3 está a −18 dB, quando o silêncio da mesma gravação está a −52 dB". Não diz "o corte ficou ruim".

---

## Task 1: O módulo de medidas e a emenda que decepa palavra

**Files:**
- Create: `motor/medidas.py`
- Test: `tests/test_medidas.py`

**O problema.** `montar` corta cada cena pelas pontas da fala e depois emenda tudo. Se uma ponta cair no meio de uma palavra, sobra um pedaço de som que a pessoa ouve como um engasgo. No projeto de origem isso aconteceu duas vezes seguidas, e nas duas foi o ouvido humano que pegou, não o teste.

**Como medir sem transcrever.** A tentação é transcrever o corte e comparar com a transcrição do take. É caro (um modelo de 2,9 GB por emenda) e indireto. A medida direta é a energia: numa emenda limpa, o áudio nos milissegundos ao redor do ponto de corte está no nível do silêncio daquela gravação. Se estiver perto do nível da fala, a emenda cortou som. O nível de referência sai da própria gravação — comparar com um número absoluto não funciona, porque os takes chegam a −36 dB.

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_medidas.py
import subprocess

from motor import medidas
from tests import fixtures


def _cola(destino, a, b):
    """Emenda dois arquivos, para simular a costura que o montar faz."""
    lista = destino.parent / "lista.txt"
    lista.write_text(f"file '{a}'\nfile '{b}'\n", encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lista), "-c", "copy", str(destino)], check=True)
    return destino


def test_emenda_no_silencio_nao_reclama(tmp_path):
    a = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.3, 1.0)], total=2.0)
    b = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.6, 1.2)], total=2.0)
    filme = _cola(tmp_path / "f.mov", a, b)
    achados = medidas.emendas(filme, [2.0])
    assert achados == [], f"reclamou de uma emenda limpa: {achados}"


def test_emenda_no_meio_do_som_reclama(tmp_path):
    """Fala colada na emenda dos dois lados: e exatamente o engasgo."""
    a = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.3, 2.0)], total=2.0)
    b = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.0, 1.5)], total=2.0)
    filme = _cola(tmp_path / "f.mov", a, b)
    achados = medidas.emendas(filme, [2.0])
    assert len(achados) == 1
    assert achados[0]["instante"] == 2.0
    assert achados[0]["dB"] > achados[0]["silencio_dB"] + 10


def test_emenda_fora_do_filme_e_ignorada(tmp_path):
    a = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.3, 1.0)], total=2.0)
    assert medidas.emendas(a, [99.0]) == []


def test_filme_sem_emenda_nenhuma(tmp_path):
    a = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(0.3, 1.0)], total=2.0)
    assert medidas.emendas(a, []) == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_medidas.py -v`
Expected: FAIL — `motor.medidas` não existe

- [ ] **Step 3: Escrever o módulo**

```python
# motor/medidas.py
"""Medicoes que o laudo junta. Cada uma responde uma pergunta so, devolve
numero, e nunca julga.

A REGRA: o nivel de referencia sai da PROPRIA gravacao. Comparar com um numero
absoluto nao funciona -- os takes chegam a -36 dB, e o mesmo -20 dB que e fala
alta num take e ruido de fundo em outro."""
import math

from motor import config, fala

JANELA_EMENDA = 0.04       # 40 ms de cada lado do ponto de corte
FOLGA_EMENDA = 10.0        # dB acima do silencio da propria gravacao


def _dB(x):
    return 20 * math.log10(x) if x > 1e-9 else -120.0


def _percentil(valores, p):
    if not valores:
        return 0.0
    ordenado = sorted(valores)
    return ordenado[min(len(ordenado) - 1, int(len(ordenado) * p))]


def emendas(filme, instantes, janela=JANELA_EMENDA, folga=FOLGA_EMENDA):
    """Onde o filme foi costurado, o som deveria estar no nivel do silencio.

    Se estiver perto do nivel da fala, a emenda cortou palavra pela metade --
    a pessoa ouve como um engasgo. Devolve uma lista de achados; lista vazia
    quer dizer que todas as emendas estao limpas."""
    env = fala.envelope(filme)
    if not env:
        return []
    dur = len(env) * fala.PASSO
    silencio = _dB(_percentil(env, 0.10))

    achados = []
    for t in instantes:
        if t <= janela or t >= dur - janela:
            continue
        i, j = int((t - janela) / fala.PASSO), int((t + janela) / fala.PASSO)
        pedaco = env[i:j]
        if not pedaco:
            continue
        nivel = _dB(max(pedaco))
        if nivel > silencio + folga:
            achados.append({"instante": round(t, 3),
                            "dB": round(nivel, 1),
                            "silencio_dB": round(silencio, 1)})
    return achados
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_medidas.py -v`
Expected: 4 passed

- [ ] **Step 5: Provar que a medida tem dentes**

Suba `FOLGA_EMENDA` para 60 e rode de novo: `test_emenda_no_meio_do_som_reclama` tem de falhar, porque nenhuma emenda passa de 60 dB acima do silêncio. Restaure. Registre o valor de `dB - silencio_dB` que a emenda suja mediu — é o número que justifica a folga de 10 dB.

- [ ] **Step 6: Commit**

```bash
git add motor/medidas.py tests/test_medidas.py
git commit -m "feat: medir emenda que decepa palavra"
```

---

## Task 2: A legenda dentro da faixa segura

**Files:**
- Modify: `motor/medidas.py`
- Modify: `motor/config.py`
- Test: `tests/test_medidas.py`

**O problema.** Instagram e TikTok desenham a própria interface por cima do vídeo: nome do perfil, legenda do post, botões. Texto que cai nessas faixas fica ilegível. A base da legenda foi de 1500 para 1375 exatamente por isso.

**A faixa segura, em 1080×1920:** nada de texto acima de **y=180** nem abaixo de **y=1560**. Os números vêm de onde a interface das duas plataformas desenha; são medidos no projeto de origem, não estimados.

- [ ] **Step 1: Acrescentar as constantes em `motor/config.py`**

```python
SEGURO_TOPO = 180        # acima disto o aplicativo desenha a propria interface
SEGURO_BASE = 1560       # abaixo disto idem. A legenda a 1500 caia sob ela
```

- [ ] **Step 2: Acrescentar os testes**

```python
def test_legenda_na_base_padrao_esta_segura(tmp_path):
    from motor import legenda
    p = legenda.png("uma frase", "brutalista", tmp_path / "a.png")
    assert medidas.dentro_da_faixa_segura(p) == []


def test_legenda_baixa_demais_e_apontada(tmp_path):
    from PIL import Image, ImageDraw
    from motor import config
    im = Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([200, 1600, 800, 1700], fill=(255, 255, 255, 255))
    p = tmp_path / "baixa.png"
    im.save(p)
    achados = medidas.dentro_da_faixa_segura(p)
    assert len(achados) == 1
    assert achados[0]["onde"] == "embaixo"


def test_legenda_alta_demais_e_apontada(tmp_path):
    from PIL import Image, ImageDraw
    from motor import config
    im = Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([200, 40, 800, 120], fill=(255, 255, 255, 255))
    p = tmp_path / "alta.png"
    im.save(p)
    assert medidas.dentro_da_faixa_segura(p)[0]["onde"] == "em cima"


def test_peca_sem_tinta_nenhuma_nao_reclama(tmp_path):
    from PIL import Image
    from motor import config
    p = tmp_path / "vazia.png"
    Image.new("RGBA", (config.W, config.H), (0, 0, 0, 0)).save(p)
    assert medidas.dentro_da_faixa_segura(p) == []


def test_as_quatro_posicoes_da_legenda_estao_seguras(tmp_path):
    """Nenhuma das quatro posicoes medidas pode cair sob a interface."""
    from motor import legenda
    for posicao in legenda.POSICOES:
        p = legenda.png("uma frase um pouco mais longa", "brutalista",
                        tmp_path / f"{posicao}.png", posicao=posicao)
        assert medidas.dentro_da_faixa_segura(p) == [], (
            f"a posicao '{posicao}' cai fora da faixa segura")
```

- [ ] **Step 3: Acrescentar ao `motor/medidas.py`**

```python
def dentro_da_faixa_segura(peca):
    """A tinta desta peca (legenda ou letreiro) cai onde o aplicativo desenha
    a propria interface?

    Instagram e TikTok escrevem nome de perfil, legenda do post e botoes por
    cima do video. Texto que cai ali fica ilegivel. A base da legenda foi de
    1500 para 1375 exatamente por causa disto."""
    from PIL import Image
    caixa = Image.open(peca).convert("RGBA").getchannel("A").getbbox()
    if caixa is None:
        return []
    _, y0, _, y1 = caixa
    achados = []
    if y0 < config.SEGURO_TOPO:
        achados.append({"onde": "em cima", "y": y0, "limite": config.SEGURO_TOPO})
    if y1 > config.SEGURO_BASE:
        achados.append({"onde": "embaixo", "y": y1, "limite": config.SEGURO_BASE})
    return achados
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_medidas.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add motor/medidas.py motor/config.py tests/test_medidas.py
git commit -m "feat: medir se a legenda cai sob a interface do aplicativo"
```

---

## Task 3: Material complementar repetindo em loop

**Files:**
- Modify: `motor/medidas.py`
- Test: `tests/test_medidas.py`

**O problema, medido com gravação real.** Um b-roll de 2,4 s debaixo de uma cena de 70,9 s repete 30 vezes. O motor faz a coisa certa — dá loop, não congela — mas o resultado é monótono e ninguém avisa. Isso não é defeito de motor, é decisão de conteúdo: quem preencheu o contrato pôs material curto demais debaixo de cena longa demais.

**Onde isso mora.** É a única medição que não olha o filme pronto, e sim o contrato mais os arquivos de origem. Por isso recebe o mapa de cenas e a produção, não o vídeo.

- [ ] **Step 1: Acrescentar os testes**

```python
def test_broll_do_tamanho_da_cena_nao_reclama(tmp_path):
    fixtures.clipe_mudo(tmp_path / "b.mp4", total=6.0, w=1920, h=1080)
    mapa = [{"n": 1, "trat": "split", "ini": 0.0, "fim": 5.0}]
    topos = {1: tmp_path / "b.mp4"}
    assert medidas.repeticao_do_complementar(mapa, topos) == []


def test_broll_curto_demais_e_apontado(tmp_path):
    fixtures.clipe_mudo(tmp_path / "b.mp4", total=2.0, w=1920, h=1080)
    mapa = [{"n": 1, "trat": "split", "ini": 0.0, "fim": 20.0}]
    achados = medidas.repeticao_do_complementar(mapa, {1: tmp_path / "b.mp4"})
    assert len(achados) == 1
    assert achados[0]["n"] == 1
    assert achados[0]["vezes"] == 10


def test_cena_sem_complementar_e_ignorada(tmp_path):
    mapa = [{"n": 1, "trat": "cheia", "ini": 0.0, "fim": 20.0}]
    assert medidas.repeticao_do_complementar(mapa, {}) == []


def test_repeticao_no_limite_nao_reclama(tmp_path):
    """Exatamente no limite ainda passa; e o limite que decide, nao o acaso."""
    fixtures.clipe_mudo(tmp_path / "b.mp4", total=2.0, w=1920, h=1080)
    fim = 2.0 * medidas.REPETICOES_DEMAIS
    mapa = [{"n": 1, "trat": "split", "ini": 0.0, "fim": fim}]
    assert medidas.repeticao_do_complementar(mapa, {1: tmp_path / "b.mp4"}) == []
```

- [ ] **Step 2: Acrescentar ao `motor/medidas.py`**

```python
REPETICOES_DEMAIS = 4      # acima disto o material complementar vira padronagem


def repeticao_do_complementar(mapa, topos):
    """O material que entra na metade de cima repete quantas vezes?

    Medido com gravacao real: um b-roll de 2,4s debaixo de uma cena de 70,9s
    repete 30 vezes. O motor faz a coisa certa -- da loop em vez de congelar --
    mas o resultado e monotono. Nao e defeito de motor, e decisao de conteudo:
    material curto demais debaixo de cena longa demais."""
    from motor import probe
    achados = []
    for c in mapa or []:
        arquivo = topos.get(c["n"])
        if not arquivo:
            continue
        d_topo = probe.dur(arquivo)
        d_cena = c["fim"] - c["ini"]
        if d_topo <= 0 or d_cena <= 0:
            continue
        vezes = d_cena / d_topo
        if vezes > REPETICOES_DEMAIS:
            achados.append({"n": c["n"], "vezes": round(vezes, 1),
                            "material_s": round(d_topo, 1),
                            "cena_s": round(d_cena, 1)})
    return achados
```

- [ ] **Step 3: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_medidas.py -v`
Expected: 13 passed

- [ ] **Step 4: Commit**

```bash
git add motor/medidas.py tests/test_medidas.py
git commit -m "feat: medir material complementar repetindo em loop"
```

---

## Task 4: O mapa de cenas carrega o que o laudo precisa

**Files:**
- Modify: `motor/montar.py`
- Test: `tests/test_montar.py`

**O que falta no mapa.** As medições das tarefas 1 e 3 precisam de dois dados que hoje ninguém grava: onde estão as emendas (é a lista de `ini` de cada cena a partir da segunda) e qual arquivo entrou na metade de cima de cada cena de split. O primeiro dá para derivar; o segundo não.

- [ ] **Step 1: Escrever o teste que falha**

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_montar.py -k mapa_registra -v`
Expected: FAIL — `KeyError: 'topo'`

- [ ] **Step 3: Acrescentar ao registro do mapa em `motor/montar.py`**

Logo depois da linha que monta `registro`, antes do bloco `if cena.letreiro:`:

```python
        if cena.topo:
            registro["topo"] = str(cena.topo.arquivo)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_montar.py -v`
Expected: todos passam

- [ ] **Step 5: Commit**

```bash
git add motor/montar.py tests/test_montar.py
git commit -m "feat: o mapa registra o material do topo"
```

---

## Task 5: O laudo junta tudo

**Files:**
- Modify: `motor/laudo.py`
- Test: `tests/test_laudo.py`

**O que muda.** `laudo.rodar` passa a chamar as três medições e a devolver os achados junto com os problemas que já devolvia. As três **não** derrubam o `ok` do laudo do mesmo jeito: emenda suja e legenda fora da faixa são defeito e reprovam; material em loop é observação e não reprova, porque pode ser deliberado.

- [ ] **Step 1: Escrever os testes**

```python
def test_o_laudo_traz_as_tres_medidas(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 1.0)], total=2.5)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov"}]}),
        encoding="utf-8")
    filme = montar.montar(p, tmp_path / "f.mp4")
    r = laudo.rodar(filme, p)
    for chave in ("emendas", "faixa_segura", "repeticao"):
        assert chave in r, f"o laudo nao trouxe '{chave}'"
    assert r["ok"] is True


def test_material_em_loop_avisa_mas_nao_reprova(tmp_path):
    """Repetir pode ser deliberado. E observacao, nao defeito."""
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    (tmp_path / "broll").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 5.5)], total=6.0)
    fixtures.clipe_mudo(tmp_path / "broll" / "b.mp4", total=0.8, w=1920, h=1080)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "split", "arquivo": "gravacoes/t.mov",
         "topo": {"arquivo": "broll/b.mp4"}}]}), encoding="utf-8")
    filme = montar.montar(p, tmp_path / "f.mp4")
    r = laudo.rodar(filme, p)
    assert r["repeticao"], "nao viu o material repetindo"
    assert r["ok"] is True, "repeticao nao deveria reprovar o filme"
    assert any("repete" in x for x in laudo.em_portugues(r).split("\n"))
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_laudo.py -v`
Expected: FAIL — `'emendas' not in resultado`

- [ ] **Step 3: Ligar no `motor/laudo.py`**

No topo, junto dos outros imports:

```python
from motor import medidas
```

Dentro de `rodar`, depois do bloco que lê `cenas_mapa` e antes de `estado_limites`:

```python
    emendas, faixa_fora, repeticao = [], [], []
    if cenas_mapa:
        # as emendas sao os inicios de cena, da segunda em diante
        emendas = medidas.emendas(filme, [c["ini"] for c in cenas_mapa[1:]])
        for e in emendas:
            problemas.append(
                f"na emenda aos {e['instante']:.1f} segundos ainda ha som de "
                f"fala: o corte pode ter comido um pedaco de palavra")

        raiz = Path(caminho_cenas).parent
        topos = {c["n"]: raiz / c["topo"] for c in cenas_mapa
                 if c.get("topo") and (raiz / c["topo"]).exists()}
        repeticao = medidas.repeticao_do_complementar(cenas_mapa, topos)
```

E logo antes do `return`:

```python
    return {"ok": not problemas,
            "limites": estado_limites,
            "duracao": round(max(d_v, d_a), 3),
            "dif_video_audio": round(d_v - d_a, 3),
            "dimensao": [w, h],
            "cenas": len(cenas_mapa),
            "emendas": emendas,
            "faixa_segura": faixa_fora,
            "repeticao": repeticao,
            "problemas": problemas}
```

`faixa_segura` fica vazio aqui: quem tem peça para medir é quem desenha a legenda, e essa checagem entra na folha, não no laudo do filme pronto. A chave existe para o formato do laudo ser estável.

- [ ] **Step 4: Acrescentar as observações ao texto em português**

Em `em_portugues`, antes do `return`:

```python
    for r in resultado.get("repeticao", []):
        linhas.append(
            f"- na cena {r['n']}, o video de apoio tem {r['material_s']:.0f} "
            f"segundos e a cena tem {r['cena_s']:.0f}: ele repete "
            f"{r['vezes']:.0f} vezes. Nao esta errado, mas cansa de ver.")
```

- [ ] **Step 5: Rodar tudo**

Run: `.venv/bin/pytest -v`
Expected: todos passam

- [ ] **Step 6: Commit**

```bash
git add motor/laudo.py tests/test_laudo.py
git commit -m "feat: o laudo junta emenda, faixa segura e repeticao"
```

---

## Task 6: Provar contra gravação real

**Files:**
- Create: `tests/test_laudo_real.py`

**Por que este teste existe.** Três defeitos desta skill só apareceram com material do usuário: o `alimiter` que não segurava o teto, o recorte do split que pegava a faixa errada, e a detecção de área útil que ficava cega abaixo de 1 s. Clipe sintético de bipe não pega nenhum dos três. Este teste roda contra as gravações reais quando elas existirem na máquina, e se pula sozinho quando não existirem.

- [ ] **Step 1: Escrever o teste**

```python
# tests/test_laudo_real.py
"""Roda contra gravacao de verdade, se houver. Pula sozinho quando nao houver
-- ninguem que clonar este repositorio tem os arquivos do autor."""
import json
import os
from pathlib import Path

import pytest

from motor import laudo, montar

ORIGEM = Path(os.environ.get(
    "GRAVACOES_REAIS",
    Path.home() / "Desktop/VIBECODING/conteudo/agentes-ginsu/assets"))

REAL = pytest.mark.skipif(
    not (ORIGEM / "gravacoes").is_dir(),
    reason=f"sem gravacao real em {ORIGEM}; aponte com GRAVACOES_REAIS=")


@REAL
def test_um_filme_de_verdade_passa_no_laudo(tmp_path):
    import shutil
    takes = sorted((ORIGEM / "gravacoes").glob("*.mov"))[:2]
    brolls = sorted((ORIGEM / "broll").glob("*.mp4"))[:1]
    if len(takes) < 2 or not brolls:
        pytest.skip("faltou take ou material de apoio")

    (tmp_path / "gravacoes").mkdir()
    (tmp_path / "broll").mkdir()
    for t in takes:
        shutil.copy(t, tmp_path / "gravacoes" / t.name)
    shutil.copy(brolls[0], tmp_path / "broll" / brolls[0].name)

    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({
        "velocidade": 1.15, "estilo": "brutalista", "legenda": False,
        "cenas": [
            {"n": 1, "trat": "cheia", "arquivo": f"gravacoes/{takes[0].name}",
             "teto": 6.0,
             "letreiro": {"texto": "TESTE", "entra": 0.5, "dura": 1.5}},
            {"n": 2, "trat": "split", "arquivo": f"gravacoes/{takes[1].name}",
             "teto": 6.0,
             "topo": {"arquivo": f"broll/{brolls[0].name}"}}]}),
        encoding="utf-8")

    filme = montar.montar(p, tmp_path / "f.mp4")
    r = laudo.rodar(filme, p)
    assert r["ok"] is True, r["problemas"]
    assert r["cenas"] == 2
    assert r["dimensao"] == [1080, 1920]
    assert abs(r["dif_video_audio"]) < 0.10
```

- [ ] **Step 2: Rodar**

Run: `.venv/bin/pytest tests/test_laudo_real.py -v`
Expected: passa (ou pula, se a máquina não tiver as gravações). Registre qual dos dois aconteceu e, se passou, quanto tempo levou e o que o laudo devolveu em `repeticao`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_laudo_real.py
git commit -m "test: laudo contra gravacao real, pulavel"
```

---

## Task 7: Registrar

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/DIARIO.md`

- [ ] **Step 1: Trocar a linha de estado no `CLAUDE.md`**

```markdown
**Estado: motor e laudo prontos. Falta a folha de aprovacao e os agentes.**
```

E acrescentar uma linha às armadilhas, cortando outra para o arquivo continuar em 40 linhas:

```markdown
- **Nivel de audio se mede contra a propria gravacao**, nunca contra numero absoluto: os takes
  chegam a -36 dB, e o mesmo -20 dB que e fala num take e ruido de fundo em outro.
```

- [ ] **Step 2: Acrescentar ao `docs/DIARIO.md`**, no topo, depois do cabeçalho:

```markdown
---

## 2026-08-28 — laudo completo

Tres medicoes novas, cada uma correspondendo a um erro que ja aconteceu e que ninguem viu no olho.

- **Emenda que decepa palavra**, medida por energia e nao por transcricao. Transcrever cada emenda
  custaria um modelo de 2,9GB por corte e responderia de forma indireta. A energia responde direto:
  numa emenda limpa o som esta no nivel do silencio DAQUELA gravacao. O nivel de referencia tem de
  sair da propria gravacao — os takes chegam a -36 dB.
- **Legenda sob a interface do aplicativo.** Nada de texto acima de y=180 nem abaixo de y=1560.
- **Material complementar em loop.** Medido com gravacao real: b-roll de 2,4s debaixo de cena de
  70,9s repete 30 vezes. O motor da loop em vez de congelar, que e o certo, mas o resultado cansa.
  Avisa e nao reprova: repetir pode ser deliberado.
```

- [ ] **Step 3: Rodar tudo e commitar**

```bash
.venv/bin/pytest
git add CLAUDE.md docs/DIARIO.md
git commit -m "docs: registrar o laudo completo"
```
