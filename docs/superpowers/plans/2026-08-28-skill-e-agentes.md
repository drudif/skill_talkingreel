# A skill e os agentes — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar a skill: o `SKILL.md` que orquestra, os quatro agentes, o perfil que roda uma vez, e o que vem embutido das skills do autor — tudo escrito para alguém que não entende de montagem.

**Architecture:** O motor já existe e é testado. Esta camada é texto: instruções. O `SKILL.md` conduz as três fases e despacha os agentes; cada agente tem um arquivo próprio, lido só quando ele é despachado. Nenhum agente escreve comando de vídeo nem HTML — eles preenchem um `cenas.json` e uma lista de itens, e o motor executa.

**Tech Stack:** Markdown + o motor em Python que já está pronto.

---

## O princípio que rege todo o texto desta camada

Quem usa isto **não entende de montagem, edição ou áudio**. Vale para cada linha que a pessoa vai ler:

- Sem termo técnico. Se um for inevitável, explicar em uma frase, ali mesmo.
- Sem metáfora difícil.
- Sem resumir demais o problema — dizer o que está errado de verdade.
- Sem verborragia. Não descrever em detalhe cada entrega.
- Sempre fechar com um checklist enxuto do que foi feito, e esperar a resposta.

**Isto é testável, e será testado**: a tarefa 7 varre todo o texto que a pessoa lê atrás de uma lista de jargão, e falha se achar algum sem explicação na mesma frase.

---

## Task 1: A estrutura da skill e o SKILL.md

**Files:**
- Create: `SKILL.md`
- Create: `referencias/.gitkeep`
- Test: `tests/test_skill.py`

**O que o `SKILL.md` faz.** É o único arquivo lido na entrada. Ele diz: verifica o perfil, pergunta o mínimo, conduz as três fases, despacha os agentes, e nunca detalha o que os agentes fazem por dentro — isso mora no arquivo de cada um, lido só na hora.

**Teto de tamanho: 120 linhas.** Carrega em toda invocação da skill.

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_skill.py
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "SKILL.md"


def _frontmatter(caminho):
    texto = caminho.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
    assert m, f"{caminho.name} nao tem frontmatter"
    return dict(
        (k.strip(), v.strip().strip('"'))
        for k, v in (l.split(":", 1) for l in m.group(1).split("\n") if ":" in l))


def test_o_skill_existe_e_tem_frontmatter():
    fm = _frontmatter(SKILL)
    assert fm["name"] == "talking-reel-done"
    assert len(fm["description"]) > 80, "a descricao precisa dizer quando usar"


def test_a_descricao_diz_quando_usar_sem_jargao():
    d = _frontmatter(SKILL)["description"].lower()
    assert any(x in d for x in ("falando", "camera", "talking head")), (
        "a descricao nao diz que tipo de video e")
    assert any(x in d for x in ("instagram", "tiktok", "reel", "vertical")), (
        "a descricao nao diz para onde o video vai")


def test_o_skill_cabe_no_teto():
    n = len(SKILL.read_text(encoding="utf-8").rstrip().split("\n"))
    assert n <= 120, f"o SKILL.md tem {n} linhas, teto 120"


def test_as_tres_fases_estao_no_skill():
    t = SKILL.read_text(encoding="utf-8").lower()
    for fase in ("estrutura", "arte", "corte"):
        assert fase in t, f"a fase '{fase}' nao aparece no SKILL.md"


def test_os_quatro_agentes_estao_no_skill():
    t = SKILL.read_text(encoding="utf-8")
    for agente in ("Bluey", "Bandit", "Chili", "Bingo"):
        assert agente in t, f"o agente {agente} nao aparece no SKILL.md"


def test_todo_arquivo_citado_existe():
    """Um caminho que nao existe e uma instrucao que o agente nao consegue
    seguir, e ele descobre isso no meio do trabalho da pessoa."""
    texto = SKILL.read_text(encoding="utf-8")
    for rel in re.findall(r"`(referencias/[\w/.-]+\.md)`", texto):
        assert (RAIZ / rel).exists(), f"o SKILL.md cita {rel}, que nao existe"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_skill.py -v`
Expected: FAIL — `SKILL.md` não existe

- [ ] **Step 3: Escrever o `SKILL.md`**

```markdown
---
name: talking-reel-done
description: "Transforma um video em que a pessoa fala para a camera num vertical montado para Instagram e TikTok, com corte de ritmo, letreiro, legenda queimada e trilha. Use quando alguem tiver uma gravacao falando para a camera — um take longo, um desabafo, uma aula, um comentario — e quiser publicar como Reel, TikTok ou Shorts. Tambem quando pedir para cortar as pausas, acelerar, legendar, por texto na tela ou por musica embaixo. Nao serve para video que ja esta montado."
---

# talking reel: done

Alguem grava falando para a camera. Esta skill devolve o video montado, no formato certo, com
legenda queimada e pronto para publicar.

## Como falar com quem usa

Quem usa isto **nao entende de montagem, edicao ou audio**. Isto nao e uma sugestao de tom, e a
regra do trabalho:

- Sem termo tecnico. Se um for inevitavel, explique em uma frase, ali mesmo.
- Sem metafora dificil. Sem verborragia. Nao descreva em detalhe cada entrega.
- Nao resuma demais o problema: diga o que esta errado de verdade.
- Sempre feche com um checklist enxuto do que foi feito, e **espere a resposta**.

## Antes de qualquer coisa

1. Leia `referencias/limites.md`. Sao as recusas que nao se negociam.
2. Procure o perfil, na ordem: `~/.claude/talkingreel-perfil.md`, depois `talkingreel-perfil.md`
   na pasta do trabalho. Se existir, mostre um resumo de tres linhas e pergunte so o que mudou.
   Se nao existir, conduza `referencias/perfil.md` — uma pergunta por mensagem, todas puláveis.
3. Pergunte onde esta a gravacao, se o perfil nao disser.

## As tres fases

Cada fase termina numa folha de aprovacao. **Nao passe para a fase seguinte sem a resposta.**

| fase | quem trabalha | a folha decide |
|---|---|---|
| 1 · estrutura | Bandit, com o parecer de audio do Bluey | o que fica do que a pessoa falou, e onde entra material extra |
| 2 · arte e trilha | Bandit e Chili, em paralelo | estilo, letreiros, posicao da legenda, trilha, e de onde cortar cada material extra |
| 3 · corte | Bingo e Chili, em paralelo | o filme montado, antes de queimar a legenda |

A trilha e aprovada ANTES da montagem. O efeito sonoro, ao contrario, entra durante.

## Quem e quem

Cada agente tem um arquivo. **Leia o arquivo do agente na hora de despacha-lo, nao antes.**

| agente | o que faz | arquivo |
|---|---|---|
| Bluey | conduz, mede e reprova. E ele quem fala com a pessoa | `referencias/agentes/bluey.md` |
| Bandit | escolhe o que fica da fala e o que sai | `referencias/agentes/bandit.md` |
| Chili | estilo, letreiro, posicao da legenda, trilha e efeito | `referencias/agentes/chili.md` |
| Bingo | preenche o `cenas.json` e roda o motor | `referencias/agentes/bingo.md` |

Bandit e Chili trabalham ao mesmo tempo na fase 2; Bingo e Chili, na fase 3. Bluey junta.

## A regra de ferro do motor

**Nenhum agente escreve comando de video, nem HTML.** Eles preenchem um `cenas.json` e uma lista
de itens; o motor executa. Toda a calibragem mora no motor, medida, e nao no que o agente escreve.

- Montar: `python3 -m motor <cenas.json> <saida.mp4>` — monta e imprime o laudo
- O contrato do `cenas.json`: `referencias/contrato.md`
- A folha: `motor/folha.py`, a partir de uma lista de itens

## O que a pessoa recebe no fim

- o video com legenda queimada, 1080x1920
- o mesmo video sem legenda, para quando o aplicativo legenda sozinho
- a legenda do post, escrita por `referencias/legenda-do-post.md`

## Quando a pessoa pede outra coisa

- **acelerar, ou tirar as pausas, e so isso**: `referencias/corte-rapido.md`, sem entrar nas fases
- **editar o video com efeito de IA**: `referencias/servicos.md`. So se ela pedir
- **o material dela nao entra como esta**: nao acontece. Gerar imagem ou video por IA so se ela pedir
```

- [ ] **Step 4: Criar a pasta**

```bash
mkdir -p referencias/agentes && touch referencias/.gitkeep
```

- [ ] **Step 5: Rodar**

Run: `.venv/bin/pytest tests/test_skill.py -v`
Expected: o teste de arquivos citados ainda falha — os arquivos de referência vêm nas tarefas seguintes. Os outros passam.

- [ ] **Step 6: Commit**

```bash
git add SKILL.md referencias/.gitkeep tests/test_skill.py
git commit -m "feat: o SKILL.md que conduz as tres fases"
```

---

## Task 2: Os limites, o contrato e o perfil

**Files:**
- Create: `referencias/limites.md`
- Create: `referencias/contrato.md`
- Create: `referencias/perfil.md`
- Create: `talkingreel-perfil-modelo.md`
- Test: `tests/test_skill.py`

**`referencias/limites.md`** não repete as regras: ele **gera** o texto a partir de `motor/limites.py`, que é onde elas moram com soma de verificação. Duplicar o texto criaria duas fontes de verdade e uma delas ficaria para trás.

**`talkingreel-perfil-modelo.md`** é um template **vazio**. O perfil preenchido do autor mora em `~/.claude/`, fora deste repositório, e não vem junto.

- [ ] **Step 1: Escrever os testes**

```python
def test_os_limites_apontam_para_o_modulo_e_nao_repetem_a_regra():
    """Duplicar o texto das regras cria duas fontes de verdade, e uma delas
    fica para tras. A soma de verificacao vigia so uma."""
    t = (RAIZ / "referencias/limites.md").read_text(encoding="utf-8")
    assert "motor/limites.py" in t
    assert "python3 -c" in t or "python3 -m" in t, (
        "o arquivo tem de dizer COMO ler as regras do modulo")


def test_o_modelo_de_perfil_esta_vazio():
    """O perfil preenchido do autor nao pode vazar para o repositorio."""
    t = (RAIZ / "talkingreel-perfil-modelo.md").read_text(encoding="utf-8")
    for dado in ("Drudi", "Fernando", "@drudif", "gmail", "instagram.com/",
                 "linkedin.com/in"):
        assert dado.lower() not in t.lower(), f"o modelo traz '{dado}'"
    assert t.count("[") >= 5, "o modelo deveria ser so lacunas para preencher"


def test_o_contrato_descreve_todo_campo_que_o_motor_le():
    """Um campo sem documentacao e um campo que nenhum agente vai usar."""
    from motor import cenas
    t = (RAIZ / "referencias/contrato.md").read_text(encoding="utf-8")
    for campo in ("estilo", "legenda", "legenda_split", "proprios",
                  "velocidade", "trilha", "cenas", "trat", "arquivo",
                  "topo", "teto", "letreiro"):
        assert f"`{campo}`" in t, f"o contrato nao explica o campo '{campo}'"


def test_o_contrato_avisa_da_escala_de_tempo_do_letreiro():
    """A armadilha mais facil de cair: ler o instante da gravacao crua."""
    t = (RAIZ / "referencias/contrato.md").read_text(encoding="utf-8").lower()
    assert "depois do corte" in t and "velocidade" in t
```

- [ ] **Step 2: Escrever `referencias/limites.md`**

```markdown
# Os limites que esta skill nao ultrapassa

**As regras nao estao escritas aqui.** Elas moram em `motor/limites.py`, com uma soma de
verificacao que denuncia se alguem mexer. Repetir o texto aqui criaria duas fontes de verdade, e
uma delas ficaria para tras.

Leia sempre do modulo:

```bash
python3 -c "from motor import limites; print(limites.em_portugues())"
```

E verifique a instalacao antes de qualquer folha:

```bash
python3 -c "from motor import limites; print(limites.verificar())"
```

Se o resultado nao for `('intacto', '')`, **pare** e diga a pessoa o que apareceu. Uma instalacao
adulterada nao e motivo para continuar em silencio.

Quem para e o Bluey, no controle de qualidade, antes da folha. Ele diz o que achou e onde, em uma
frase, sem sermao e sem moralizar sobre quem pediu. Nao limpa calado. Nao vira classificador
automatico: sem pontuacao, sem lista de palavras. Material ambiguo — ironia, citacao critica,
jornalismo, relato de vitima — nao e alvo; na duvida, pergunte e acredite na resposta.
```

- [ ] **Step 3: Escrever `referencias/contrato.md`**

O arquivo tem de documentar **todo** campo que `motor/cenas.py` lê, com o significado em português simples e um exemplo completo. Estrutura obrigatória:

```markdown
# O contrato: o arquivo `cenas.json`

Este arquivo e a unica coisa que os agentes escrevem. O motor le e executa.

## Exemplo completo

```json
{
  "velocidade": 1.15,
  "estilo": "brutalista",
  "legenda": true,
  "legenda_split": "esquerda",
  "proprios": ["Ginsu", "Anthropic"],
  "trilha": "audio/trilha.mp3",
  "cenas": [
    {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov", "teto": 6.0,
     "letreiro": {"texto": "COMENTA QUERO", "entra": 1.1, "dura": 1.8,
                  "base": 1400, "box": false}},
    {"n": 2, "trat": "split", "arquivo": "gravacoes/take-02.mov",
     "topo": {"arquivo": "broll/faca.mp4", "ancora": 0.3}}
  ]
}
```

## Os campos da producao

| campo | precisa? | o que e |
|---|---|---|
| `velocidade` | nao | quanto o filme acelera. 1.15 e o padrao, e nao se nota |
| `estilo` | nao | uma das sete fichas. Padrao `brutalista` |
| `legenda` | nao | queimar a legenda no fim. Padrao `true`. **Desligar pula a transcricao inteira**, que e a etapa mais demorada |
| `legenda_split` | nao | onde a legenda fica quando a tela esta dividida: `esquerda`, `direita` ou `centro`. Padrao `esquerda` |
| `proprios` | nao | nomes que a transcricao costuma errar, escritos do jeito certo. **So nome proprio, e so com 4 letras ou mais** |
| `trilha` | nao | a musica de fundo. Ela abaixa sozinha quando a pessoa fala |
| `cenas` | sim | a lista, em ordem |

## Os campos de cada cena

| campo | precisa? | o que e |
|---|---|---|
| `n` | sim | o numero da cena |
| `trat` | sim | `cheia` (so a pessoa) ou `split` (material extra em cima, pessoa embaixo) |
| `arquivo` | sim | a gravacao, relativa a pasta do `cenas.json` |
| `teto` | nao | limite de duracao, em segundos, para essa cena |
| `topo` | so no split | `{"arquivo": ..., "ancora": 0.0 a 1.0}`. A ancora escolhe que parte da imagem fica visivel: 0 e o topo, 1 e o pe |
| `letreiro` | nao | texto grande sobre a imagem |

## O letreiro

| campo | precisa? | o que e |
|---|---|---|
| `texto` | sim | o que aparece escrito |
| `entra` | nao | quando aparece. Padrao 0 |
| `dura` | nao | quanto fica. Sem isso, fica ate o fim da cena |
| `base` | nao | onde o texto se apoia na altura da tela |
| `box` | nao | caixa solida atras do texto |

**A armadilha do tempo do letreiro.** `entra` e `dura` contam na cena **ja pronta** — depois do
corte de silencio e depois da velocidade. Nao sao o instante da gravacao crua. As duas etapas
mudam a escala do tempo, e nao de forma proporcional. O jeito certo de achar o numero: monte
uma vez, olhe o `cenas-mapa.json`, e some `entra` ao `ini` da cena.
```

- [ ] **Step 4: Escrever `referencias/perfil.md` e `talkingreel-perfil-modelo.md`**

O `perfil.md` conduz a conversa. Regras que ele tem de carregar: **uma pergunta por mensagem**, **toda pergunta pode ser pulada**, **sem jargão** — quem instala isto pode nunca ter aberto um terminal por vontade própria. Pergunta pulada vira `[A CONFIRMAR]` no arquivo e o trabalho segue com o padrão.

Quatro rodadas curtas: **quem publica**, **onde publica**, **como as coisas parecem**, **onde ficam as gravações**.

O modelo é só lacunas:

```markdown
# Perfil — talking reel

Preenchido uma vez. Nos trabalhos seguintes a skill mostra um resumo e pergunta so o que mudou.

- **Quem assina**: [nome ou @]
- **Onde publica**: [Instagram, TikTok, YouTube Shorts, LinkedIn]
- **Estilo padrao**: [brutalista, terminal, neubrutal, editorial, riso, colagem, superminimal]
- **Onde ficam as gravacoes**: [caminho da pasta]
- **Legenda queimada**: [sim, ou nao quando o aplicativo legenda sozinho]
- **Velocidade**: [1.15 e o padrao]
```

- [ ] **Step 5: Rodar e commitar**

```bash
.venv/bin/pytest tests/test_skill.py -v
git add referencias/ talkingreel-perfil-modelo.md tests/test_skill.py
git commit -m "feat: limites, contrato e perfil"
```

---

## Task 3: Os quatro agentes

**Files:**
- Create: `referencias/agentes/bluey.md`
- Create: `referencias/agentes/bandit.md`
- Create: `referencias/agentes/chili.md`
- Create: `referencias/agentes/bingo.md`
- Test: `tests/test_skill.py`

**Teto: 80 linhas por agente.** Cada arquivo é lido só quando aquele agente é despachado.

**O que cada um faz, e o que nenhum deles faz.**

- **Bluey** conduz e mede. É o único que fala com a pessoa. Roda o laudo antes de qualquer folha, e é ele quem para o trabalho quando os limites são violados. Ele **ouve** o material — o parecer de áudio da fase 1 é dele.
- **Bandit** escolhe o que fica da fala. Pode sugerir um corte menor, **selecionando trechos e apagando outros — nunca inventando frase que a pessoa não falou**. Também escreve a legenda do post.
- **Chili** cuida do estilo, do letreiro, da posição da legenda, da trilha e do efeito sonoro. **A arte dela é lettering, e no máximo um box atrás do lettering.** Ela não cria grafismo, ilustração nem elemento decorativo.
- **Bingo** preenche o `cenas.json` e roda o motor. É o único que toca no motor.

- [ ] **Step 1: Escrever os testes**

```python
import pytest

AGENTES = ["bluey", "bandit", "chili", "bingo"]


@pytest.mark.parametrize("nome", AGENTES)
def test_cada_agente_cabe_no_teto(nome):
    p = RAIZ / f"referencias/agentes/{nome}.md"
    n = len(p.read_text(encoding="utf-8").rstrip().split("\n"))
    assert n <= 80, f"{nome}.md tem {n} linhas, teto 80"


@pytest.mark.parametrize("nome", AGENTES)
def test_cada_agente_diz_o_que_devolve(nome):
    t = (RAIZ / f"referencias/agentes/{nome}.md").read_text(encoding="utf-8")
    assert "## O que voce devolve" in t, (
        f"{nome}.md nao diz o que o agente tem de devolver")


def test_so_o_bingo_roda_o_motor():
    """A regra de ferro. Se outro agente rodar o motor, a calibragem sai do
    codigo e volta para o prompt, que e onde ela se perde."""
    for nome in AGENTES:
        t = (RAIZ / f"referencias/agentes/{nome}.md").read_text(encoding="utf-8")
        roda = "python3 -m motor" in t
        assert roda == (nome == "bingo"), (
            f"{nome}.md {'roda' if roda else 'nao roda'} o motor")


def test_a_chili_sabe_que_a_arte_dela_e_lettering():
    t = (RAIZ / "referencias/agentes/chili.md").read_text(encoding="utf-8").lower()
    assert "letreiro" in t or "lettering" in t
    assert "nao" in t and ("ilustra" in t or "grafismo" in t or "decor" in t), (
        "a chili.md nao diz o que ela NAO faz")


def test_o_bandit_nao_pode_inventar_fala():
    t = (RAIZ / "referencias/agentes/bandit.md").read_text(encoding="utf-8").lower()
    assert "nao invent" in t or "nunca invent" in t, (
        "o bandit.md nao proibe inventar frase que a pessoa nao falou")


def test_o_bluey_roda_o_laudo_antes_da_folha():
    t = (RAIZ / "referencias/agentes/bluey.md").read_text(encoding="utf-8").lower()
    assert "laudo" in t and "antes" in t
```

- [ ] **Step 2: Escrever os quatro arquivos**

Cada um segue esta forma, e nada além dela:

```markdown
# <Nome> — <uma linha do que ele faz>

## Quem voce e
<duas ou tres frases. O que este agente decide, e o que ele nao decide.>

## O que voce recebe
<lista curta: arquivos, resultado de outro agente, o registro de decisoes>

## Como voce trabalha
<passos numerados, curtos. As regras duras em negrito.>

## O que voce NAO faz
<a lista de limites deste agente. Esta secao e obrigatoria.>

## O que voce devolve
<o formato exato. Para Bingo e um `cenas.json`; para os outros, uma lista de itens
 no formato da folha: id, titulo, fato medido, detalhe.>
```

Regras duras que cada arquivo tem de conter, verbatim ou em substância:

- **Bluey**: roda `python3 -c "from motor import laudo, limites; ..."` e o laudo **antes** de publicar qualquer folha; é o único que escreve para a pessoa; segue as regras de linguagem do `SKILL.md`; para o trabalho quando `limites.verificar()` não devolve `intacto`.
- **Bandit**: seleciona e apaga trechos, **nunca inventa frase que a pessoa não falou**; não se preocupa com duração alvo; escreve a legenda do post seguindo `referencias/legenda-do-post.md`.
- **Chili**: escolhe uma das sete fichas de `referencias/estilos.md`; letreiro marca **uma frase que a pessoa falou**, e por isso não passa por deslopar; **a arte dela é lettering e no máximo um box atrás dele — não cria grafismo, ilustração nem elemento decorativo**; trilha aprovada antes da montagem, efeito sonoro durante.
- **Bingo**: o único que roda `python3 -m motor`; preenche o `cenas.json` seguindo `referencias/contrato.md`; quando o laudo reprova, conserta o `cenas.json` e roda de novo — não mexe no motor.

- [ ] **Step 3: Rodar e commitar**

```bash
.venv/bin/pytest tests/test_skill.py -v
git add referencias/agentes tests/test_skill.py
git commit -m "feat: os quatro agentes"
```

---

## Task 4: Os estilos, em português

**Files:**
- Create: `referencias/estilos.md`
- Test: `tests/test_skill.py`

**Uma fonte de verdade.** As sete fichas moram em `motor/estilos.py`, com cor, fonte e peso. Este arquivo é o que a Chili lê para **escolher** — descreve cada uma em uma frase, sem repetir os valores. Se repetisse, os dois ficariam fora de sincronia no primeiro ajuste.

- [ ] **Step 1: Escrever o teste**

```python
def test_todo_estilo_do_motor_esta_descrito():
    from motor import estilos
    t = (RAIZ / "referencias/estilos.md").read_text(encoding="utf-8")
    for chave in estilos.ESTILOS:
        assert f"`{chave}`" in t, f"o estilo '{chave}' nao esta descrito"


def test_nenhum_estilo_descrito_deixou_de_existir():
    import re
    from motor import estilos
    t = (RAIZ / "referencias/estilos.md").read_text(encoding="utf-8")
    citados = set(re.findall(r"^\| `(\w+)`", t, re.M))
    assert citados <= set(estilos.ESTILOS), (
        f"o arquivo cita estilo que o motor nao tem: "
        f"{citados - set(estilos.ESTILOS)}")


def test_o_arquivo_de_estilos_nao_repete_cor_nem_fonte():
    """Repetir valor cria duas fontes de verdade. Aqui so entra a descricao;
    cor, fonte e peso moram em motor/estilos.py."""
    import re
    t = (RAIZ / "referencias/estilos.md").read_text(encoding="utf-8")
    assert not re.search(r"#[0-9A-Fa-f]{6}", t), "vazou codigo de cor"
    assert ".otf" not in t and ".ttf" not in t, "vazou nome de arquivo de fonte"
```

- [ ] **Step 2: Escrever o arquivo**

Uma tabela: `| \`chave\` | como parece, em uma frase | quando serve |`. Nada de cor, fonte ou número.

Acrescentar, no fim, o parágrafo que fecha a porta para um oitavo estilo:

```markdown
O visual do projeto de origem — amarelo com contorno preto, legenda escura sobre caixa branca —
**nao e um oitavo estilo**. Ele sobrevive so na folha de aprovacao.
```

- [ ] **Step 3: Rodar e commitar**

```bash
.venv/bin/pytest tests/test_skill.py -v
git add referencias/estilos.md tests/test_skill.py
git commit -m "feat: as sete fichas de estilo, em portugues"
```

---

## Task 5: O que vem embutido

**Files:**
- Create: `referencias/corte-rapido.md`
- Create: `referencias/legenda-do-post.md`
- Create: `referencias/servicos.md`
- Create: `CREDITOS.md`
- Test: `tests/test_skill.py`

**Do express cut** entram só `audio-speed` e `audio-silence-cut`, como comandos avulsos que a pessoa aciona quando quiser. **O pipeline não os usa** — a versão do motor é melhor: corte por energia em vez de detector de silêncio, e compressão de pausa interna. O arquivo tem de dizer isso, senão alguém vai usar a ferramenta errada dentro do pipeline.

**Do deslopar** entra só a aplicação na legenda do post. Letreiro não passa por ele: letreiro marca uma frase que a pessoa falou, e mexer nela seria errado.

**Os serviços de IA** só entram em jogo se a pessoa pedir para editar o vídeo dela com efeito.

- [ ] **Step 1: Escrever os testes**

```python
def test_o_corte_rapido_avisa_que_o_pipeline_usa_outra_coisa():
    t = (RAIZ / "referencias/corte-rapido.md").read_text(encoding="utf-8").lower()
    assert "avulso" in t or "fora das fases" in t or "nao usa" in t, (
        "alguem vai usar a ferramenta avulsa dentro do pipeline")
    assert "energia" in t, "nao explica por que a do motor e melhor"


def test_a_legenda_do_post_vale_so_para_o_post():
    t = (RAIZ / "referencias/legenda-do-post.md").read_text(encoding="utf-8").lower()
    assert "letreiro" in t, "nao diz que letreiro fica de fora"


def test_os_servicos_trazem_o_numero_medido():
    t = (RAIZ / "referencias/servicos.md").read_text(encoding="utf-8")
    for servico in ("Seedance", "Veed", "MiniMax", "Kling"):
        assert servico in t, f"falta {servico} na tabela"
    assert "255" in t, "a tabela nao traz a escala da medicao"


def test_os_servicos_dizem_qual_nao_serve():
    t = (RAIZ / "referencias/servicos.md").read_text(encoding="utf-8").lower()
    assert "regenera" in t, "nao avisa que o MiniMax regenera em vez de editar"


def test_os_creditos_nomeiam_a_origem_de_cada_coisa():
    t = (RAIZ / "CREDITOS.md").read_text(encoding="utf-8")
    for origem in ("deslopar", "audio-speed", "audio-silence-cut"):
        assert origem in t, f"falta creditar {origem}"


def test_nenhum_dado_pessoal_alem_de_credito_de_autoria():
    """Medido: o unico dado pessoal nas skills incorporadas e credito de
    autoria, que fica. Qualquer outra coisa e vazamento."""
    import re
    suspeitos = re.compile(r"gmail|@drudif|instagram\.com/|linkedin\.com/in|\+55",
                           re.I)
    for p in RAIZ.glob("referencias/**/*.md"):
        achado = suspeitos.search(p.read_text(encoding="utf-8"))
        assert not achado, f"{p.name} traz dado pessoal: {achado.group(0)}"
```

- [ ] **Step 2: Escrever `referencias/corte-rapido.md`**

Os dois comandos, com os parâmetros. E, em destaque no topo:

```markdown
**Isto e avulso, fora das tres fases.** Use so quando a pessoa quiser exatamente isto e nada mais.
O pipeline NAO usa estes comandos: o motor corta por **energia do audio** e comprime as pausas de
dentro da fala, o que da um corte melhor que um detector de silencio. Rodar isto antes do
pipeline atrapalha, porque tira a margem que o motor precisa para achar as pontas da fala.
```

Acelerar, sem mudar o tom da voz:

```bash
ffmpeg -i entrada.mp4 -filter:v "setpts=PTS/1.5" -filter:a "atempo=1.5" saida.mp4
```

Tirar os silencios longos: descrever o método com `silencedetect`, e dizer que ele deixa sobra nas pontas — que é exatamente por que o motor usa outro.

- [ ] **Step 3: Escrever `referencias/legenda-do-post.md`**

O essencial do deslopar, reduzido ao que cabe numa legenda curta de Reel em pt-BR:

```markdown
# A legenda do post

Vale **so para a legenda do post**. Letreiro nao passa por aqui: letreiro marca uma frase que a
pessoa falou, e mexer nela seria errado.

Reduzido da skill `deslopar`, de Fernando Drudi, sobre Zero-Lero (MIT, Vinicius Stanula).

## O que nao entra

- **Numero que ninguem deu.** Metrica, estatistica, premio ou depoimento que nao veio da pessoa
  vira `[CONFIRMAR: ...]`, nunca um numero plausivel. E o defeito mais grave, e da problema legal.
- **Contraste binario** em qualquer forma: "nao e X, e Y", "e mais do que X", "vai muito alem de".
  Afirme o Y e corte a rampa. O tell e a reversao, nao o "nao".
- **Gerundio de beneficio** no fim da frase: "...otimizando seu tempo". Corte ou concretize.
- **Familia ressaltar/destacar**, moldura temporal de abertura, conclusao rotulada ("Em resumo").
- **"Simples assim.", "sem burocracia", "Chega de X. Chega de Y."** Demonstre em vez de declarar.
- **Substantivo pelado**: "virou gargalo", "e sistema". Rode uma passada so para isto.
- **Vazamento pt-pt**: "utilizador", "registar", "equipa".

## O teste que decide

Leia em voz alta. Se soa como locutor de comercial ou coach de LinkedIn, ainda tem slop.
E: a primeira linha serviria para o concorrente? Se sim, nao e primeira linha.

## Densidade

Um "alem disso" e humano; um por paragrafo e maquina. Flagre por acumulo, nao por ocorrencia.
```

- [ ] **Step 4: Escrever `referencias/servicos.md`**

A tabela medida, sem arredondar nem suavizar:

```markdown
# Editar o video com IA — medido, nao suposto

**So entra em jogo se a pessoa pedir.** O padrao e o material dela entrar como esta.

| tarefa | servico | resultado medido |
|---|---|---|
| editar o proprio video | Seedance 2.5, modo de edicao | muda 7,5 a 19,7 numa escala de 255 — edita de verdade |
| trocar a boca no proprio video | Veed Sync 2.0, no Magnific | 23 na boca, 2 no resto do quadro |
| **nao use para editar** | MiniMax H3 com referencia de video | 13 a 99 no quadro inteiro: **regenera** o rosto em vez de editar, e desloca o audio em 0,95s |
| **nao aceita video** | Kling 3.0 | so imagem inicial |

Toda troca de imagem por modelo passa por um teste de fidelidade antes de entrar no corte: compare
o clipe devolvido com o take e informe a diferenca. O Bluey decide com esse numero, nao com a
impressao de quem olhou.

## Armadilhas de prompt, ja pagas

- **Marcacao de tempo so e obedecida se dita em segundos E em fracao do clipe.** "Aos 2 segundos"
  sozinho e ignorado; "aos 2 segundos, a 40% do clipe" funciona.
- **Gerador de imagem corta os pes da figura** se nao for dito que ela ocupa 55% da altura do quadro.
- Para nao mudar o que ja existe, o pedido precisa dizer isso de forma incisiva: **incluir**, nao
  refazer.

## Para audio

| servico | musica | efeito | limpar voz |
|---|---|---|---|
| Magnific | sim | sim | sim |
| Higgsfield | sim | sim | nao |
| ElevenLabs direto | sim | — | — |

Efeito sonoro gratuito: Freesound e a opcao solida. Musica gratuita: os bancos livres tem acervo
pequeno e regra de credito que varia por faixa — nao dependa deles.
```

- [ ] **Step 5: Escrever `CREDITOS.md`**

Nomear cada origem e sua licença. O que é crédito de autoria **fica** — não é dado pessoal a limpar.

- [ ] **Step 6: Rodar e commitar**

```bash
.venv/bin/pytest tests/test_skill.py -v
git add referencias/ CREDITOS.md tests/test_skill.py
git commit -m "feat: corte rapido, legenda do post, servicos e creditos"
```

---

## Task 6: A varredura de jargão

**Files:**
- Test: `tests/test_linguagem.py`

**Por que isto é um teste e não uma recomendação.** "Sem termo técnico" é a instrução mais fácil de escrever e a mais fácil de esquecer. Um teste que varre todo o texto que a pessoa lê transforma a instrução em coisa verificável.

**O que conta como texto que a pessoa lê:** o `SKILL.md`, os arquivos de `referencias/`, e o que `motor/laudo.em_portugues` devolve. **Não** conta: código, docstring, plano, diário.

- [ ] **Step 1: Escrever o teste**

```python
# tests/test_linguagem.py
"""Quem usa esta skill nao entende de montagem, edicao ou audio.

Isto varre o texto que a PESSOA le. Termo tecnico so passa se estiver explicado
na mesma frase — e a explicacao tem de estar ali, nao num arquivo ao lado."""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

# palavras que nao dizem nada para quem nunca editou video
JARGAO = ["codec", "bitrate", "container", "keyframe", "timeline", "render",
          "encode", "muxer", "demuxer", "sample rate", "loudness", "lufs",
          "crop", "overlay", "buffer", "pipeline", "commit", "hash",
          "checksum", "regex", "json", "stdout", "b-roll"]

# onde o jargao e legitimo: nomes de campo, comandos, caminhos de arquivo
_CODIGO = re.compile(r"`[^`]*`|```.*?```", re.S)


def _texto_que_a_pessoa_le(caminho):
    """Sem o que esta dentro de crase: nome de campo e comando sao codigo,
    nao conversa."""
    return _CODIGO.sub(" ", caminho.read_text(encoding="utf-8"))


def _arquivos():
    yield RAIZ / "SKILL.md"
    yield from sorted((RAIZ / "referencias").glob("**/*.md"))


@pytest.mark.parametrize("caminho", list(_arquivos()),
                         ids=lambda p: p.name)
def test_sem_jargao_sem_explicacao(caminho):
    texto = _texto_que_a_pessoa_le(caminho)
    achados = []
    for frase in re.split(r"(?<=[.!?])\s+|\n\n", texto):
        baixo = frase.lower()
        for termo in JARGAO:
            if termo in baixo:
                # passa se a propria frase explica
                explica = any(x in baixo for x in
                              ("quer dizer", "que e", "ou seja", "isto e",
                               "significa", "chamado"))
                if not explica:
                    achados.append((termo, frase.strip()[:90]))
    assert not achados, (
        f"{caminho.name} usa termo tecnico sem explicar na mesma frase:\n"
        + "\n".join(f"  '{t}' em: {f}" for t, f in achados))


def test_o_laudo_fala_a_lingua_da_pessoa():
    from motor import laudo
    r = {"duracao": 42.0, "cenas": 3, "ok": False,
         "problemas": ["a imagem e o som terminam em momentos diferentes: "
                       "0.42 segundo de diferenca"],
         "repeticao": [{"n": 2, "vezes": 30, "material_s": 2.4, "cena_s": 70.9}]}
    texto = laudo.em_portugues(r).lower()
    for termo in JARGAO:
        assert termo not in texto, f"o laudo vazou o termo '{termo}'"


def test_nada_de_metafora_batida():
    """O usuario pediu isto por escrito: nada de metafora, nada de frase de
    efeito. Estas sao as que aparecem sozinhas."""
    batidas = ["a cereja do bolo", "o pulo do gato", "na veia", "de bandeja",
               "colocar a mao na massa", "tirar do papel", "virada de chave",
               "nao e so", "muito mais do que"]
    for caminho in _arquivos():
        baixo = _texto_que_a_pessoa_le(caminho).lower()
        for b in batidas:
            assert b not in baixo, f"{caminho.name} usa '{b}'"
```

- [ ] **Step 2: Rodar, e consertar o texto — não o teste**

Run: `.venv/bin/pytest tests/test_linguagem.py -v`

Se falhar, **reescreva a frase**. Baixar o teste é abrir mão da única coisa que garante que a skill fala com quem ela é para.

- [ ] **Step 3: Commit**

```bash
git add tests/test_linguagem.py
git commit -m "test: varredura de jargao no texto que a pessoa le"
```

---

## Task 7: Registrar e fechar

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/DIARIO.md`
- Modify: `README.md`

- [ ] **Step 1: Estado no `CLAUDE.md`**

```markdown
**Estado: completa. Motor, laudo, folha, SKILL.md e os quatro agentes.**
```

- [ ] **Step 2: Entrada no diário**

Registrar: o que ficou embutido e por quê; a decisão de o `limites.md` apontar para o módulo em vez de repetir a regra; a varredura de jargão como teste; e o resultado medido da limpeza de dado pessoal (o único achado é crédito de autoria, que fica).

- [ ] **Step 3: `README.md`** — o que é, como instalar, e o aviso de que o motor precisa de ffmpeg.

- [ ] **Step 4: Rodar tudo e commitar**

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest
git add CLAUDE.md docs/DIARIO.md README.md
git commit -m "docs: fechar a skill"
```
