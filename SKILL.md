---
name: talking-reel-done
description: "Transforma um video em que a pessoa fala direto para a camera num vertical pronto para Instagram e TikTok, com corte de ritmo, letreiro, legenda queimada e trilha sonora. Use quando alguem tiver uma gravacao falando para a camera — um take longo, um desabafo, uma aula, um comentario — e quiser publicar como Reel, TikTok ou Shorts. Tambem serve so para cortar pausas, acelerar, legendar, por texto na tela ou musica embaixo. Nao serve para um video que ja foi montado em outro programa."
---

# talking reel: done

Alguém grava falando para a câmera. Esta skill devolve o vídeo montado, no formato certo, com
legenda queimada e pronto para publicar.

## Como falar com quem usa

Quem usa isto **não entende de montagem, edição ou áudio**. Isto não é uma sugestão de tom, é a
regra do trabalho:

- Sem termo técnico. Se um for inevitável, explique em uma frase, ali mesmo.
- Sem metáfora difícil. Sem verborragia. Não descreva em detalhe cada entrega.
- Não resuma demais o problema: diga o que está errado de verdade.
- Sempre feche com um checklist enxuto do que foi feito, e **espere a resposta**.

## Antes de qualquer coisa

1. Leia `referencias/limites.md`. São as recusas que não se negociam.
2. Procure o perfil, nesta ordem: `~/.claude/talkingreel-perfil.md`, depois `talkingreel-perfil.md`
   na pasta do trabalho. Se existir, mostre um resumo de três linhas e pergunte só o que mudou.
   Se não existir, conduza `referencias/perfil.md` — uma pergunta por mensagem, todas puláveis.
3. Pergunte onde está a gravação, se o perfil não disser.

## As três fases

Cada fase termina numa folha de aprovação. **Não passe para a fase seguinte sem a resposta.**

| fase | quem trabalha | a folha decide |
|---|---|---|
| 1 · estrutura | Bandit, com o parecer de áudio do Bluey | o que fica do que a pessoa falou, e onde entra material extra |
| 2 · arte e trilha | Bandit e Chili, em paralelo | estilo, letreiros, posição da legenda, trilha, e de onde cortar cada material extra |
| 3 · corte | Bingo e Chili, em paralelo | o filme montado, antes de queimar a legenda |

A trilha é aprovada ANTES da montagem. O efeito sonoro, ao contrário, entra durante.

## Quem é quem

Cada agente tem um arquivo. **Leia o arquivo do agente na hora de despachá-lo, não antes.**

| agente | o que faz | arquivo |
|---|---|---|
| Bluey | conduz, mede e reprova. É ele quem fala com a pessoa | `referencias/agentes/bluey.md` |
| Bandit | escolhe o que fica da fala e o que sai | `referencias/agentes/bandit.md` |
| Chili | estilo, letreiro, posição da legenda, trilha e efeito | `referencias/agentes/chili.md` |
| Bingo | preenche o `cenas.json` e roda o motor | `referencias/agentes/bingo.md` |

Bandit e Chili trabalham ao mesmo tempo na fase 2; Bingo e Chili, na fase 3. Bluey junta tudo.

## A regra de ferro do motor

**Nenhum agente escreve comando de vídeo, nem HTML.** Eles preenchem um `cenas.json` e uma lista
de itens; o motor executa. Toda a calibragem mora no motor, medida, e não no que o agente escreve.

- Montar: `python3 -m motor <cenas.json> <saida.mp4>` — monta e imprime o laudo
- O contrato do `cenas.json`: `referencias/contrato.md`
- A folha: `motor/folha.py`, a partir de uma lista de itens

## O que a pessoa recebe no fim

- o vídeo com legenda queimada, 1080x1920
- o mesmo vídeo sem legenda, para quando o aplicativo legenda sozinho
- a legenda do post, escrita seguindo `referencias/legenda-do-post.md`

## Quando a pessoa pede outra coisa

- **acelerar, ou tirar as pausas, e só isso**: `referencias/corte-rapido.md`, sem entrar nas fases
- **editar o vídeo com efeito de IA**: `referencias/servicos.md`. Só se ela pedir
- **o material dela não entra como está**: não acontece. Gerar imagem ou vídeo por IA só se ela pedir
