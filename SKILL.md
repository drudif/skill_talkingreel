---
name: talking-reel-done
description: "Transforma um ou mais videos em que a pessoa fala direto para a camera num vertical pronto para Instagram e TikTok, com corte de ritmo, letreiro animado, legenda queimada e trilha. Escolhe a melhor tomada quando ela repetiu a frase, junta material complementar em tela dividida, corrige imagem lavada e troca fundo de pano verde. Use quando alguem tiver uma gravacao falando para a camera — um take longo, um desabafo, uma aula, um comentario — e quiser publicar como Reel, TikTok ou Shorts. Tambem serve so para cortar pausas, acelerar, legendar, por texto na tela ou musica embaixo. Nao serve para um video que ja foi montado em outro programa."
---

# talking reel: done

Alguém grava falando para a câmera. Esta skill devolve o vídeo montado, no formato certo, com
legenda queimada e pronto para publicar.

## Como começar

Se a pessoa ainda não mandou nada, abra assim, com estas palavras ou parecidas:

> Oi. Esta skill deixa pronto para publicar o vídeo em que você fala para a câmera: ela corta as
> pausas, põe legenda, texto na tela e música. Me manda a gravação.

## O que a skill precisa receber

| | o quê |
|---|---|
| **obrigatório** | uma ou mais gravações da pessoa falando para a câmera |
| opcional | outros vídeos ou imagens, para entrar junto |
| opcional | o roteiro dela — as falas, os textos de tela, onde dividir a tela |
| opcional | uma trilha |

Sem trilha da pessoa, a Chili propõe uma das que vêm com a skill, em `assets/trilhas/`.

## Como falar com quem usa

Quem usa isto **não entende de montagem, edição ou áudio**. Isto não é uma sugestão de tom, é a
regra do trabalho:

- Sem termo técnico. Se um for inevitável, explique em uma frase, ali mesmo.
- Sem metáfora difícil. Sem verborragia. Não descreva em detalhe cada entrega.
- Não resuma demais o problema: diga o que está errado de verdade.
- Sempre feche com um checklist enxuto do que foi feito, e **espere a resposta**.

## Antes de qualquer coisa

1. Leia `referencias/limites.md`. São as recusas que não se negociam.
2. Pergunte onde está a gravação, se a pessoa ainda não disse.

## As duas aprovações

| aprovação | quem trabalha | a folha decide |
|---|---|---|
| primeira | Bandit, Bingo e Chili, ao mesmo tempo | o que fica da fala, o estilo, os letreiros, o material extra e a trilha |
| segunda | Bingo | o filme leve, montado, para assistir |

**Não passe de uma folha sem a resposta.** A trilha é aprovada na primeira, antes de montar.

## Quem é quem

Os quatro **não são arquivos de subagente do Claude Code** — uma skill não instala nada em
`.claude/agents/`. São arquivos de instrução que ficam dentro desta pasta. Para despachar um,
leia o arquivo dele e passe o conteúdo como prompt de um subagente, junto com o que ele precisa
receber. **Leia o arquivo na hora de despachar, não antes**: é o que mantém esta página curta.

| agente | o que faz | arquivo |
|---|---|---|
| Bluey | conduz, mede e reprova. É ele quem fala com a pessoa | `referencias/agentes/bluey.md` |
| Bandit | decupa, transcreve, escolhe a melhor tomada e escreve o roteiro | `referencias/agentes/bandit.md` |
| Bingo | mede os arquivos, depois monta | `referencias/agentes/bingo.md` |
| Chili | estilo, letreiro, legenda e trilha | `referencias/agentes/chili.md` |

**Bandit e Bingo começam ao mesmo tempo**, e nenhum espera o outro: o Bandit ouve o que foi dito,
o Bingo mede os arquivos. A Chili entra assim que houver roteiro. Bluey junta tudo.

## A regra de ferro do motor

**Nenhum agente escreve comando de vídeo, nem HTML.** Eles preenchem um `cenas.json` e uma lista
de itens; o motor executa. Toda a calibragem mora no motor, medida, e não no que o agente escreve.

- Montar, de dentro da pasta do trabalho:
  `PYTHONPATH=<a pasta desta skill> python3 -m motor cenas.json saida.mp4`
  O `PYTHONPATH` **não é opcional**: sem ele o Python não acha o motor quando a gravação
  está em outra pasta, que é o caso normal. A pasta desta skill é a que aparece em
  "Base directory for this skill" quando ela carrega.
- O contrato do `cenas.json`: `referencias/contrato.md`
- A folha: `motor/folha.py`, a partir de uma lista de itens

## A regra do tempo

**Todo instante que um agente escreve é segundo da GRAVAÇÃO**, contado do começo do arquivo
original — onde a cena começa, onde termina, quando um texto aparece na tela. Nenhum agente faz
conta para descontar o corte das pausas ou a aceleração: quem converte é o motor, em
`motor/tempo.py`. Ver `referencias/contrato.md`.

## O que a pessoa recebe no fim

- o vídeo com legenda queimada, 1080x1920
- o mesmo vídeo sem legenda, para quando o aplicativo legenda sozinho

## Quando a pessoa pede outra coisa

- **acelerar, ou tirar as pausas, e só isso**: `referencias/corte-rapido.md`, sem entrar nas fases
- **trocar o fundo**: só funciona se ela gravou na frente de um pano verde. O motor confere
  sozinho e recusa quando não for o caso. Ver `referencias/contrato.md`
- **editar o vídeo com efeito de IA**: `referencias/servicos.md`. Só se ela pedir
- **o material dela não entra como está**: não acontece. Gerar imagem ou vídeo por IA só se ela pedir
