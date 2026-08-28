# Folha de aprovação — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A folha de aprovação: uma página HTML mínima, uma por fase, que carrega só o que falta decidir, e que devolve as decisões da pessoa sem que ela precise copiar ou colar nada.

**Architecture:** Três módulos pequenos. `motor/registro.py` guarda em disco o que já foi decidido. `motor/folha.py` gera o HTML a partir de uma lista de itens — o template mora no Python, não no prompt. `motor/folha.ler` recupera as decisões de uma página republicada. O agente nunca escreve HTML: passa uma lista de itens e recebe um arquivo pronto.

**Tech Stack:** Python (gera o HTML) + ffmpeg (miniaturas) + a capacidade `artifact` do runtime da claude.ai (a página se republica sozinha quando a pessoa decide).

---

## O que encareceu a folha no projeto de origem

O custo real não foi o tamanho do arquivo — foi **o modelo reescrever 50 KB de HTML a cada rodada**. Some-se a isso peças que se acumulavam: chegou a 15 numa página só, com vídeo embutido, 5 MB.

As duas decisões que atacam isso na raiz:

1. **O template mora em `motor/folha.py`, escrito uma vez.** Por rodada, o modelo produz só a lista de itens — algumas centenas de bytes de JSON, não 50 KB de HTML.
2. **O que foi decidido sai da folha.** Cada folha carrega só o pendente. Uma folha de 15 itens vira três folhas de 5.

E nada de vídeo embutido: o arquivo fica em disco e a pessoa abre lá. Na página entra no máximo uma miniatura pequena.

## A armadilha do estado, resolvida na raiz

A página guarda o estado dentro de si mesma e se republica quando a pessoa decide. Para reler esse estado, o agente precisa achar o bloco de dados no HTML.

No projeto de origem isso quebrou: o HTML tinha **dois** trechos parecidos com `<script id="dados">` — o bloco de verdade, e a mesma string escrita literalmente dentro do JavaScript que regenera a página. Quem lesse o segundo pegava o template vazio e apagava o feedback da pessoa.

**A solução não é documentar a armadilha, é eliminá-la.** O estado fica entre dois marcadores que aparecem **uma vez só** no arquivo, porque o JavaScript que regenera a página monta esses marcadores por concatenação e nunca os escreve inteiros:

```html
<script id="dados" type="application/json">/*E-INI*/{ ... }/*E-FIM*/</script>
```

```javascript
// no JS da pagina, os marcadores NUNCA aparecem inteiros:
const INI = "/*E-" + "INI*/", FIM = "/*E-" + "FIM*/";
```

O leitor procura `/*E-INI*/` e falha alto se achar mais de uma ocorrência.

---

## Task 1: O registro em disco

**Files:**
- Create: `motor/registro.py`
- Test: `tests/test_registro.py`

**O que ele guarda.** Uma decisão por item: aprovado, descartado, ou ainda pendente, com a nota que a pessoa escreveu. É o que permite a folha seguinte carregar só o que falta.

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_registro.py
import pytest

from motor import registro


def test_registro_novo_esta_vazio(tmp_path):
    r = registro.carregar(tmp_path / "registro.json")
    assert r == {}


def test_grava_e_le_de_volta(tmp_path):
    p = tmp_path / "registro.json"
    registro.gravar(p, {"cena-1": {"decisao": "aprovado", "nota": ""}})
    assert registro.carregar(p)["cena-1"]["decisao"] == "aprovado"


def test_pendentes_tira_o_que_ja_foi_decidido(tmp_path):
    p = tmp_path / "registro.json"
    registro.gravar(p, {"a": {"decisao": "aprovado", "nota": ""},
                        "b": {"decisao": "descartado", "nota": "nao gostei"}})
    itens = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    assert [i["id"] for i in registro.pendentes(itens, p)] == ["c"]


def test_item_sem_decisao_continua_pendente(tmp_path):
    p = tmp_path / "registro.json"
    registro.gravar(p, {"a": {"decisao": None, "nota": "pensando"}})
    assert [i["id"] for i in registro.pendentes([{"id": "a"}], p)] == ["a"]


def test_anotar_nao_apaga_o_que_ja_havia(tmp_path):
    p = tmp_path / "registro.json"
    registro.anotar(p, {"a": {"decisao": "aprovado", "nota": ""}})
    registro.anotar(p, {"b": {"decisao": "descartado", "nota": ""}})
    assert set(registro.carregar(p)) == {"a", "b"}


def test_anotar_atualiza_decisao_que_mudou(tmp_path):
    p = tmp_path / "registro.json"
    registro.anotar(p, {"a": {"decisao": "aprovado", "nota": ""}})
    registro.anotar(p, {"a": {"decisao": "descartado", "nota": "mudei de ideia"}})
    assert registro.carregar(p)["a"]["decisao"] == "descartado"
    assert registro.carregar(p)["a"]["nota"] == "mudei de ideia"


def test_decisao_desconhecida_e_recusada(tmp_path):
    with pytest.raises(ValueError, match="talvez"):
        registro.anotar(tmp_path / "r.json", {"a": {"decisao": "talvez"}})


def test_arquivo_corrompido_nao_derruba_o_programa(tmp_path):
    p = tmp_path / "registro.json"
    p.write_text("isto nao e json", encoding="utf-8")
    with pytest.raises(registro.RegistroIlegivel, match="registro"):
        registro.carregar(p)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_registro.py -v`
Expected: FAIL — `motor.registro` não existe

- [ ] **Step 3: Escrever o módulo**

```python
# motor/registro.py
"""O que ja foi decidido, em disco.

E isto que faz a folha encolher: cada folha carrega SO o pendente. No projeto
de origem as pecas se acumulavam e a pagina chegou a 15 itens de uma vez."""
import json
from pathlib import Path

DECISOES = (None, "aprovado", "descartado")


class RegistroIlegivel(Exception):
    """O arquivo de registro existe mas nao da para ler."""


def carregar(caminho):
    caminho = Path(caminho)
    if not caminho.exists():
        return {}
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RegistroIlegivel(
            f"o registro em {caminho} esta corrompido e nao da para ler: {e}. "
            "Apague o arquivo para comecar de novo, ou conserte o JSON.")


def gravar(caminho, dados):
    Path(caminho).write_text(
        json.dumps(dados, indent=1, ensure_ascii=False), encoding="utf-8")


def anotar(caminho, novas):
    """Junta decisoes novas as que ja existiam, sem apagar as antigas."""
    for chave, d in novas.items():
        if d.get("decisao") not in DECISOES:
            raise ValueError(
                f"'{d.get('decisao')}' nao e uma decisao. So existe aprovado, "
                "descartado, ou nada ainda.")
    dados = carregar(caminho)
    dados.update(novas)
    gravar(caminho, dados)
    return dados


def pendentes(itens, caminho):
    """Os itens que ainda nao foram nem aprovados nem descartados."""
    dados = carregar(caminho)
    return [i for i in itens
            if dados.get(i["id"], {}).get("decisao") not in
            ("aprovado", "descartado")]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_registro.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add motor/registro.py tests/test_registro.py
git commit -m "feat: registro das decisoes em disco"
```

---

## Task 2: A miniatura

**Files:**
- Create: `motor/miniatura.py`
- Test: `tests/test_miniatura.py`

**Por que existe.** A folha mostra uma miniatura pequena por item, não o vídeo. Vídeo embutido foi o que levou a página do projeto de origem a 5 MB. A miniatura entra na página como `data:` URI, porque a página publicada não carrega arquivo de fora.

**O tamanho.** 160 px de largura, JPEG de qualidade média. Medido abaixo, na tarefa; se um quadro passar de 12 KB codificado em base64, a qualidade cai até caber.

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_miniatura.py
import base64

from motor import miniatura
from tests import fixtures


def test_devolve_um_data_uri_de_jpeg(tmp_path):
    filme = fixtures.clipe_fala(tmp_path / "f.mov", falas=[(0.3, 2.0)], total=3.0)
    uri = miniatura.de(filme, 1.0)
    assert uri.startswith("data:image/jpeg;base64,")
    bruto = base64.b64decode(uri.split(",", 1)[1])
    assert bruto[:2] == b"\xff\xd8", "nao e um JPEG"


def test_cabe_no_teto_de_tamanho(tmp_path):
    filme = fixtures.clipe_fala(tmp_path / "f.mov", falas=[(0.3, 2.0)], total=3.0)
    uri = miniatura.de(filme, 1.0)
    assert len(uri) <= miniatura.TETO_BYTES, (
        f"a miniatura ficou com {len(uri)} bytes, teto {miniatura.TETO_BYTES}")


def test_largura_pedida_e_respeitada(tmp_path):
    import io
    from PIL import Image
    filme = fixtures.clipe_fala(tmp_path / "f.mov", falas=[(0.3, 2.0)], total=3.0)
    uri = miniatura.de(filme, 1.0, largura=120)
    im = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1])))
    assert im.width == 120


def test_instante_fora_do_filme_devolve_nada(tmp_path):
    filme = fixtures.clipe_fala(tmp_path / "f.mov", falas=[(0.3, 2.0)], total=3.0)
    assert miniatura.de(filme, 99.0) is None


def test_arquivo_que_nao_existe_devolve_nada(tmp_path):
    assert miniatura.de(tmp_path / "nada.mov", 1.0) is None


def test_dois_instantes_diferentes_dao_miniaturas_diferentes(tmp_path):
    filme = fixtures.clipe_fala(tmp_path / "f.mov", falas=[(0.3, 2.0)], total=3.0)
    assert miniatura.de(filme, 0.5) != miniatura.de(filme, 2.5)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_miniatura.py -v`
Expected: FAIL — `motor.miniatura` não existe

- [ ] **Step 3: Escrever o módulo**

```python
# motor/miniatura.py
"""Um quadro do filme, pequeno, embutido na folha como texto.

A folha nao carrega arquivo de fora -- a pagina publicada roda isolada. Entao
a miniatura vira `data:` URI. Vale o teto: video embutido levou a folha do
projeto de origem a 5 MB, e o custo de token de uma pagina grande e real."""
import base64
import subprocess
from pathlib import Path

LARGURA = 160
TETO_BYTES = 12_000        # do data: URI ja codificado
QUALIDADES = (4, 7, 12)    # -q:v do ffmpeg: menor e melhor


def de(filme, instante, largura=LARGURA, teto=TETO_BYTES):
    """O quadro em `instante`, como data: URI. None se nao der para extrair.

    Tenta qualidades cada vez menores ate caber no teto. Devolver uma imagem
    grande demais e pior que devolver uma feia: a pagina inteira e o custo."""
    filme = Path(filme)
    if not filme.exists():
        return None
    for q in QUALIDADES:
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{instante:.3f}", "-i", str(filme),
             "-frames:v", "1", "-vf", f"scale={largura}:-2",
             "-q:v", str(q), "-f", "mjpeg", "-"],
            capture_output=True)
        if r.returncode != 0 or not r.stdout:
            return None
        uri = "data:image/jpeg;base64," + base64.b64encode(r.stdout).decode()
        if len(uri) <= teto:
            return uri
    return uri     # a ultima tentativa, mesmo estourando: melhor que nada
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_miniatura.py -v`
Expected: 6 passed

- [ ] **Step 5: Medir e registrar**

Rode este trecho e **registre os números no relatório** — eles justificam o teto:

```bash
.venv/bin/python -c "
import sys; sys.path.insert(0,'.')
from pathlib import Path
import tempfile
from motor import miniatura
from tests import fixtures
d = Path(tempfile.mkdtemp())
f = fixtures.clipe_fala(d/'f.mov', falas=[(0.3,2.0)], total=3.0)
for L in (120, 160, 240, 360):
    u = miniatura.de(f, 1.0, largura=L, teto=10**9)
    print(f'largura {L}: {len(u)} bytes de data URI')
"
```

- [ ] **Step 6: Commit**

```bash
git add motor/miniatura.py tests/test_miniatura.py
git commit -m "feat: miniatura embutida na folha, com teto de tamanho"
```

---

## Task 3: A folha, gerada em Python

**Files:**
- Create: `motor/folha.py`
- Test: `tests/test_folha.py`

**O contrato de um item:**

```python
{"id": "cena-3",                        # obrigatorio, unico
 "titulo": "Cena 3",                    # obrigatorio, curto
 "fato": "A legenda aparece 0,2 segundo depois de voce falar a palavra.",
 "miniatura": "data:image/jpeg;base64,...",   # opcional
 "detalhe": "gravacoes/take-03.mov, 4,2 segundos"}   # opcional, uma linha
```

**O que a folha NÃO tem:** fonte da web, sistema de design, seção explicativa, vídeo, ícone, gradiente. Fundo claro, texto preto, uma linha por decisão.

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_folha.py
import json
import re

import pytest

from motor import folha


def _itens(n=2):
    return [{"id": f"i{k}", "titulo": f"Item {k}",
             "fato": f"Fato medido numero {k}."} for k in range(n)]


def test_gera_um_documento_completo(tmp_path):
    p = folha.escrever(_itens(), "estrutura", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "</html>" in html


def test_cada_item_aparece_uma_vez(tmp_path):
    p = folha.escrever(_itens(3), "estrutura", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    for k in range(3):
        assert html.count(f"Fato medido numero {k}.") == 1


def test_o_estado_esta_entre_os_marcadores_uma_vez_so(tmp_path):
    """A armadilha do projeto de origem: dois blocos parecidos no mesmo
    arquivo, e quem lesse o segundo apagava o feedback da pessoa."""
    p = folha.escrever(_itens(), "estrutura", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    assert html.count(folha.INI) == 1, "o marcador de inicio aparece mais de uma vez"
    assert html.count(folha.FIM) == 1, "o marcador de fim aparece mais de uma vez"


def test_o_estado_e_json_valido_e_traz_os_itens(tmp_path):
    p = folha.escrever(_itens(2), "arte", tmp_path / "f.html")
    estado = folha.ler(p)
    assert estado["fase"] == "arte"
    assert [i["id"] for i in estado["itens"]] == ["i0", "i1"]
    assert all(i["decisao"] is None for i in estado["itens"])


def test_ler_devolve_as_decisoes_que_a_pessoa_tomou(tmp_path):
    p = folha.escrever(_itens(2), "estrutura", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    estado = folha.ler(p)
    estado["itens"][0]["decisao"] = "aprovado"
    estado["itens"][1]["decisao"] = "descartado"
    estado["itens"][1]["nota"] = "esse trecho nao"
    novo = html.replace(
        html[html.index(folha.INI):html.index(folha.FIM) + len(folha.FIM)],
        folha.INI + json.dumps(estado, ensure_ascii=False) + folha.FIM)
    (tmp_path / "g.html").write_text(novo, encoding="utf-8")
    lido = folha.ler(tmp_path / "g.html")
    assert lido["itens"][0]["decisao"] == "aprovado"
    assert lido["itens"][1]["nota"] == "esse trecho nao"


def test_texto_com_html_dentro_nao_quebra_a_pagina(tmp_path):
    itens = [{"id": "x", "titulo": "<script>alert(1)</script>",
              "fato": 'aspas " e < e &'}]
    p = folha.escrever(itens, "estrutura", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert folha.ler(p)["itens"][0]["titulo"] == "<script>alert(1)</script>"


def test_folha_sem_item_nenhum_diz_isso(tmp_path):
    p = folha.escrever([], "corte", tmp_path / "f.html")
    assert "nada" in p.read_text(encoding="utf-8").lower()


def test_id_repetido_e_recusado(tmp_path):
    itens = [{"id": "a", "titulo": "A", "fato": "."},
             {"id": "a", "titulo": "B", "fato": "."}]
    with pytest.raises(ValueError, match="repetid"):
        folha.escrever(itens, "estrutura", tmp_path / "f.html")


def test_item_sem_id_e_recusado(tmp_path):
    with pytest.raises(ValueError, match="id"):
        folha.escrever([{"titulo": "A", "fato": "."}], "estrutura",
                       tmp_path / "f.html")


def test_a_pagina_e_pequena(tmp_path):
    """O custo de token de uma pagina grande e real: no projeto de origem o
    modelo reescrevia 50 KB de HTML a cada rodada."""
    p = folha.escrever(_itens(5), "estrutura", tmp_path / "f.html")
    assert len(p.read_bytes()) < 12_000, (
        f"a folha de 5 itens saiu com {len(p.read_bytes())} bytes")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_folha.py -v`
Expected: FAIL — `motor.folha` não existe

- [ ] **Step 3: Escrever o módulo**

```python
# motor/folha.py
"""A folha de aprovacao: HTML gerado em Python, nunca escrito pelo modelo.

POR QUE O TEMPLATE MORA AQUI. No projeto de origem o custo real nao foi o
tamanho do arquivo -- foi o modelo reescrever 50 KB de HTML a cada rodada. Com
o template no codigo, o modelo produz por rodada so a lista de itens.

O ESTADO FICA ENTRE MARCADORES QUE APARECEM UMA VEZ SO. A pagina se republica
sozinha quando a pessoa decide, e para reler o agente precisa achar o bloco de
dados. No projeto de origem havia DOIS trechos parecidos no mesmo arquivo -- o
bloco de verdade e a mesma string escrita dentro do JavaScript que regenera a
pagina -- e quem lesse o segundo apagava o feedback. Aqui o JavaScript monta os
marcadores por concatenacao e nunca os escreve inteiros."""
import html as _html
import json
import re
from pathlib import Path

INI = "/*E-INI*/"
FIM = "/*E-FIM*/"

FASES = {"estrutura": "O que fica do que voce falou",
         "arte": "Estilo, letreiros e trilha",
         "corte": "O filme montado"}

_CSS = """*{box-sizing:border-box;margin:0}
body{font:16px/1.5 system-ui,sans-serif;background:#fff;color:#111;
padding:24px;max-width:720px;margin:auto}
h1{font-size:19px;margin-bottom:2px}
p.sub{color:#666;font-size:14px;margin-bottom:20px}
.i{border-top:1px solid #e5e5e5;padding:14px 0;display:flex;gap:12px}
.i img{width:80px;height:auto;border-radius:2px;flex:none}
.c{flex:1;min-width:0}
.t{font-weight:600;font-size:15px}
.f{font-size:14px;margin:2px 0 8px}
.d{color:#777;font-size:13px;margin-bottom:8px}
button{font:inherit;font-size:14px;padding:5px 12px;margin-right:6px;
border:1px solid #ccc;background:#fff;border-radius:3px;cursor:pointer}
button[aria-pressed=true]{background:#111;color:#fff;border-color:#111}
input{font:inherit;font-size:14px;padding:5px 8px;border:1px solid #ddd;
border-radius:3px;width:100%;margin-top:6px}
.fim{margin-top:22px;color:#666;font-size:14px}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]) body
{background:#111;color:#eee}
:root:not([data-theme=light]) .i{border-color:#333}
:root:not([data-theme=light]) button{background:#1c1c1c;color:#eee;
border-color:#444}
:root:not([data-theme=light]) button[aria-pressed=true]{background:#eee;
color:#111}
:root:not([data-theme=light]) input{background:#1c1c1c;color:#eee;
border-color:#444}}"""

_JS = """const E=JSON.parse(document.getElementById('dados').textContent
.replace('/*E-'+'INI*/','').replace('/*E-'+'FIM*/',''));
function p(){const a=document.documentElement.outerHTML.replace(
new RegExp('(/\\\\*E-'+'INI\\\\*/)[\\\\s\\\\S]*?(/\\\\*E-'+'FIM\\\\*/)'),
(m,i,f)=>i+JSON.stringify(E)+f);
claude.use('artifact').then(a2=>a2&&a2.publish('<!doctype html>'+a)).catch(()=>{})}
document.addEventListener('click',ev=>{const b=ev.target.closest('button');
if(!b)return;const it=E.itens.find(x=>x.id===b.dataset.id);
it.decisao=it.decisao===b.dataset.d?null:b.dataset.d;
b.parentElement.querySelectorAll('button').forEach(o=>
o.setAttribute('aria-pressed',String(o.dataset.d===it.decisao)));p()});
document.addEventListener('change',ev=>{if(ev.target.tagName!=='INPUT')return;
E.itens.find(x=>x.id===ev.target.dataset.id).nota=ev.target.value;p()});"""


def _e(s):
    return _html.escape(str(s), quote=True)


def _linha(i):
    img = (f'<img src="{_e(i["miniatura"])}" alt="">' if i.get("miniatura")
           else "")
    det = f'<div class="d">{_e(i["detalhe"])}</div>' if i.get("detalhe") else ""
    return (f'<div class="i">{img}<div class="c">'
            f'<div class="t">{_e(i["titulo"])}</div>'
            f'<div class="f">{_e(i.get("fato", ""))}</div>{det}'
            f'<button data-id="{_e(i["id"])}" data-d="aprovado" '
            f'aria-pressed="false">Pode ir</button>'
            f'<button data-id="{_e(i["id"])}" data-d="descartado" '
            f'aria-pressed="false">Tira</button>'
            f'<input data-id="{_e(i["id"])}" placeholder="uma observacao, se '
            f'quiser">'
            f'</div></div>')


def escrever(itens, fase, destino):
    """Grava a folha em `destino` e devolve o caminho."""
    if fase not in FASES:
        raise ValueError(f"fase '{fase}' nao existe. Use uma de: "
                         + ", ".join(FASES))
    vistos = set()
    for i in itens:
        if not i.get("id"):
            raise ValueError("todo item precisa de um 'id'")
        if i["id"] in vistos:
            raise ValueError(f"o id '{i['id']}' esta repetido")
        vistos.add(i["id"])

    estado = {"fase": fase,
              "itens": [{"id": i["id"], "titulo": i.get("titulo", ""),
                         "decisao": None, "nota": ""} for i in itens]}
    corpo = ("".join(_linha(i) for i in itens) if itens else
             '<p class="fim">Nada para decidir por aqui.</p>')
    doc = (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>{_e(FASES[fase])}</title><style>{_CSS}</style></head><body>'
           f'<h1>{_e(FASES[fase])}</h1>'
           f'<p class="sub">Marque o que pode ir e o que sai. '
           f'Fecha a aba quando terminar.</p>'
           f'{corpo}'
           f'<script id="dados" type="application/json">'
           f'{INI}{json.dumps(estado, ensure_ascii=False)}{FIM}</script>'
           f'<script>{_JS}</script></body></html>')
    destino = Path(destino)
    destino.write_text(doc, encoding="utf-8")
    return destino


def ler(caminho_ou_texto):
    """As decisoes que estao dentro da folha.

    Falha alto se achar mais de um bloco de estado -- e exatamente o erro que
    apagou o feedback da pessoa no projeto de origem."""
    p = Path(caminho_ou_texto) if not str(caminho_ou_texto).lstrip().startswith(
        "<") else None
    texto = p.read_text(encoding="utf-8") if p else str(caminho_ou_texto)
    if texto.count(INI) != 1 or texto.count(FIM) != 1:
        raise ValueError(
            f"esperava um bloco de estado, achei {texto.count(INI)} de inicio "
            f"e {texto.count(FIM)} de fim. Ler o bloco errado apaga o que a "
            "pessoa decidiu.")
    bruto = texto[texto.index(INI) + len(INI):texto.index(FIM)]
    return json.loads(bruto)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_folha.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add motor/folha.py tests/test_folha.py
git commit -m "feat: a folha de aprovacao, gerada em Python"
```

---

## Task 4: A folha encolhe entre as rodadas

**Files:**
- Modify: `motor/folha.py`
- Test: `tests/test_folha.py`

**O comportamento que importa mais que todos os outros.** A pessoa decide cinco itens de quinze; a próxima folha tem dez. Sem isso a página cresce até virar o que era antes.

- [ ] **Step 1: Acrescentar os testes**

```python
def test_a_folha_seguinte_carrega_so_o_pendente(tmp_path):
    from motor import registro
    itens = [{"id": f"i{k}", "titulo": f"Item {k}", "fato": "."}
             for k in range(5)]
    reg = tmp_path / "registro.json"

    p1 = folha.publicar(itens, "estrutura", tmp_path / "f1.html", reg)
    assert len(folha.ler(p1)["itens"]) == 5

    # a pessoa decide tres e a pagina se republica
    estado = folha.ler(p1)
    for k, d in ((0, "aprovado"), (1, "descartado"), (2, "aprovado")):
        estado["itens"][k]["decisao"] = d
    folha.recolher(estado, reg)

    p2 = folha.publicar(itens, "estrutura", tmp_path / "f2.html", reg)
    assert [i["id"] for i in folha.ler(p2)["itens"]] == ["i3", "i4"]


def test_recolher_guarda_a_nota_junto(tmp_path):
    from motor import registro
    reg = tmp_path / "r.json"
    folha.recolher({"fase": "arte", "itens": [
        {"id": "a", "decisao": "descartado", "nota": "muito rapido"}]}, reg)
    assert registro.carregar(reg)["a"]["nota"] == "muito rapido"


def test_recolher_ignora_quem_nao_decidiu(tmp_path):
    from motor import registro
    reg = tmp_path / "r.json"
    folha.recolher({"fase": "arte", "itens": [
        {"id": "a", "decisao": None, "nota": ""}]}, reg)
    assert registro.carregar(reg) == {}


def test_tudo_decidido_da_uma_folha_vazia(tmp_path):
    reg = tmp_path / "r.json"
    itens = [{"id": "a", "titulo": "A", "fato": "."}]
    folha.recolher({"fase": "corte", "itens": [
        {"id": "a", "decisao": "aprovado", "nota": ""}]}, reg)
    p = folha.publicar(itens, "corte", tmp_path / "f.html", reg)
    assert folha.ler(p)["itens"] == []
    assert "nada" in p.read_text(encoding="utf-8").lower()
```

- [ ] **Step 2: Acrescentar ao `motor/folha.py`**

```python
def publicar(itens, fase, destino, caminho_registro):
    """A folha com SO o que falta decidir."""
    from motor import registro
    return escrever(registro.pendentes(itens, caminho_registro), fase, destino)


def recolher(estado, caminho_registro):
    """Guarda no registro o que a pessoa decidiu nesta folha.

    Quem nao foi decidido nao entra: continua pendente e volta na proxima."""
    from motor import registro
    novas = {i["id"]: {"decisao": i["decisao"], "nota": i.get("nota", "")}
             for i in estado.get("itens", [])
             if i.get("decisao") in ("aprovado", "descartado")}
    return registro.anotar(caminho_registro, novas) if novas else \
        registro.carregar(caminho_registro)
```

- [ ] **Step 3: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_folha.py -v`
Expected: 14 passed

- [ ] **Step 4: Commit**

```bash
git add motor/folha.py tests/test_folha.py
git commit -m "feat: a folha carrega so o que falta decidir"
```

---

## Task 5: Registrar

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/DIARIO.md`

- [ ] **Step 1: Trocar a linha de estado no `CLAUDE.md`**

```markdown
**Estado: motor, laudo e folha prontos. Faltam os agentes e o SKILL.md.**
```

E acrescentar uma armadilha, cortando outra para o arquivo continuar em 40 linhas:

```markdown
- **A folha e gerada em Python, nunca escrita pelo modelo.** O custo do projeto de origem foi
  reescrever 50 KB de HTML por rodada. O modelo produz so a lista de itens.
```

- [ ] **Step 2: Acrescentar ao `docs/DIARIO.md`**, no topo:

```markdown
---

## 2026-08-28 — folha de aprovacao

Uma pagina por fase, com so o que falta decidir. A pessoa marca, a pagina se republica sozinha,
o agente le de volta.

- **O template mora no Python.** O custo real do projeto de origem nao foi o tamanho do arquivo:
  foi o modelo reescrever 50 KB de HTML a cada rodada. Agora ele produz so a lista de itens.
- **O decidido sai da folha.** Uma folha de 15 itens vira tres de 5.
- **A armadilha do estado foi eliminada, nao documentada.** Antes havia dois trechos parecidos com
  `<script id="dados">` no mesmo arquivo — o bloco de verdade e a mesma string dentro do JavaScript
  que regenera a pagina — e quem lesse o segundo apagava o feedback. Agora o estado fica entre
  marcadores que o JavaScript monta por concatenacao, entao aparecem uma vez so, e o leitor falha
  alto se achar mais de um.
- **Miniatura, nunca video.** Video embutido levou a folha do projeto de origem a 5 MB.
```

- [ ] **Step 3: Rodar tudo e commitar**

```bash
.venv/bin/pytest
git add CLAUDE.md docs/DIARIO.md
git commit -m "docs: registrar a folha de aprovacao"
```
