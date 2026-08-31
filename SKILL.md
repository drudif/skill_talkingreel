---
name: talking-reel-done
description: "Transforma um ou mais videos em que a pessoa fala direto para a camera num vertical pronto para Instagram e TikTok, com corte de ritmo, letreiro animado, legenda queimada e trilha. Escolhe a melhor tomada quando ela repetiu a frase, junta material complementar em tela dividida, corrige imagem lavada e troca fundo de pano verde. Use quando alguem tiver uma gravacao falando para a camera — um take longo, um desabafo, uma aula, um comentario — e quiser publicar como Reel, TikTok ou Shorts. Tambem serve so para cortar pausas, acelerar, legendar, por texto na tela ou musica embaixo. Nao serve para um video que ja foi montado em outro programa."
---

# talking reel: done

Alguém grava falando para a câmera. Esta skill devolve o vídeo montado, no formato certo, com
legenda queimada e pronto para publicar.

## A primeira mensagem: apresente o caminho inteiro

**Antes de pedir qualquer coisa, diga como o trabalho vai correr.** Quem chega aqui não sabe o que
vai ser perguntado, quantas vezes vai precisar responder, nem quanto tempo leva — e descobrir isso
no meio, a conta-gotas, é o que faz desistir na metade. Abra com isto, ou parecido:

> Oi. Eu deixo pronto para publicar o vídeo em que você fala para a câmera: corto as pausas e os
> erros, escolho as melhores tomadas, ponho legenda, texto na tela e música.
>
> **Como vai funcionar:**
>
> 1. Você me manda a gravação. Só ela é obrigatória — se tiver outros vídeos, fotos, um roteiro ou
>    uma música, mandam junto, mas dá certo sem nada disso.
> 2. Eu olho o material e te faço **quatro perguntas rápidas**, todas puláveis.
> 3. Ouço tudo o que você falou e escolho o que fica. Isso demora alguns minutos.
> 4. Te mando **a primeira folha de aprovação**: os trechos que escolhi, onde entram seus vídeos
>    extras, e as opções de letra, cor e música — com exemplos no seu próprio vídeo. Você marca e
>    envia.
> 5. Monto e te mando **o vídeo para assistir**. Se estiver bom, acabou; se não, você me diz o que
>    mudar e eu refaço.
>
> São **duas vezes** em que preciso de você, e nas duas eu espero sua resposta. Me manda a gravação
> para eu começar.

Se ela já mandou a gravação junto com o pedido, diga o mesmo em versão curta e siga.

## O que a skill precisa receber

**Obrigatório:** uma ou mais gravações da pessoa falando para a câmera. **Opcional:** outros vídeos
ou imagens para entrar junto, o roteiro dela, e uma trilha.

**Peça os arquivos com nome.** `motor/entrada.py` lê a pasta por nome — `principal.mov`,
`complementar1.mp4`, `trilha.mp3` — e mostra a regra a quem não nomeou. Adivinhar pelo conteúdo
seria caro e falível; pedir é barato e não erra.

## Como falar com quem usa

Quem usa isto **não entende de montagem, edição ou áudio**. Não é sugestão de tom, é a regra do
trabalho: sem termo técnico — e se um for inevitável, explique em uma frase ali mesmo; sem metáfora
difícil; sem verborragia. Não resuma demais o problema: diga o que está errado de verdade. Feche
sempre com um checklist enxuto do que foi feito, e **espere a resposta**.

**Antes de qualquer coisa**, leia `referencias/limites.md` — são as recusas que não se negociam.

## A ordem do trabalho

**Meça primeiro, pergunte depois, trabalhe por último.** Nessa ordem, e sem pular.

O Bingo mede os arquivos com `motor/dossie.py` — rápido, e não decide nada. Com o que ele achou, o
Bluey conta o que viu e faz as **quatro perguntas, de uma vez, todas puláveis**: se ela já sabe o
que quer que fique ou prefere que você escolha; se tem outros vídeos ou fotos; se quer música; e
quanto tempo o vídeo deve ter.

**Não transcreva, não sugira letreiro e não proponha material antes dessas respostas.** Transcrever
é a etapa mais demorada de todas, e sugerir corte para quem já tem roteiro é trabalho jogado fora —
duas vezes, porque ela ainda tem de ler e recusar o que não pediu.

Quem pular todas recebe o padrão: você escolhe os trechos, sem material extra, sem música e sem
alvo de duração. Diga isso em uma linha e siga.

## As duas aprovações

| aprovação | quem trabalha | a folha decide |
|---|---|---|
| primeira | Bandit, Bingo e Chili, ao mesmo tempo | o que fica da fala, a letra, a cor, os letreiros, o material extra e a trilha |
| segunda | Bingo | o filme montado, para assistir |

**Não passe de uma folha sem a resposta.** A trilha é aprovada na primeira, antes de montar.

## Quem é quem

Os quatro **não são arquivos de subagente do Claude Code** — uma skill não instala nada em
`.claude/agents/`. São arquivos de instrução nesta pasta: para despachar um, leia o arquivo dele e
passe o conteúdo como prompt de um subagente. **Leia na hora de despachar, não antes** — é o que
mantém esta página curta.

| agente | o que faz |
|---|---|
| Bluey | conduz, mede e reprova. É ele quem fala com a pessoa |
| Bandit | decupa, transcreve, escolhe a melhor tomada e escreve o roteiro |
| Bingo | mede os arquivos, depois monta |
| Chili | letra, cor, letreiro e trilha |

Cada um em `referencias/agentes/<nome>.md`. **Bandit e Bingo começam ao mesmo tempo**, e nenhum
espera o outro; a Chili entra assim que houver roteiro; o Bluey junta tudo.

## As duas regras de ferro

**Nenhum agente escreve comando de vídeo, nem HTML.** Eles preenchem um `cenas.json` e uma lista de
itens; o motor executa. Toda a calibragem mora no motor, medida, e não no que o agente escreve. O
contrato está em `referencias/contrato.md`; a folha sai de `motor/folha.py`.

**Todo instante que um agente escreve é segundo da GRAVAÇÃO**, contado do começo do arquivo
original. Ninguém faz conta para descontar o corte das pausas ou a aceleração: quem converte é
`motor/tempo.py`.

Montar, de dentro da pasta do trabalho:
`PYTHONPATH=<a pasta desta skill> python3 -m motor cenas.json saida.mp4` — o `PYTHONPATH` **não é
opcional**: sem ele o Python não acha o motor quando a gravação está em outra pasta, que é o normal.

## No fim, e nos casos de fora

A pessoa recebe o vídeo com legenda queimada, 1080x1920, e o mesmo sem legenda, para quando o
aplicativo legenda sozinho.

- **acelerar, ou tirar as pausas, e só isso**: `referencias/corte-rapido.md`
- **trocar o fundo**: só com pano verde. O motor confere sozinho e recusa quando não for o caso
- **editar o vídeo com efeito de IA**: `referencias/servicos.md`. Só se ela pedir
- **o material dela não entra como está**: não acontece. Gerar imagem ou vídeo por IA só se ela pedir
