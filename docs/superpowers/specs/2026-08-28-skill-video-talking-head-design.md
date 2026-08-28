# talking reel: done — desenho

Data: 2026-08-28
Mora em: `VIBECODING/conteudo/skill_talkingreel`
Origem: o projeto `agentes-ginsu`, que produziu um vídeo vertical de 61s a partir de takes
gravados pelo Drudi. Esta skill generaliza aquele trabalho.

## O que ela faz

A pessoa gravou um vídeo falando para a câmera — pode ter 4 minutos. A skill devolve um vídeo
vertical montado, com ritmo, arte e legenda queimada, pronto para Instagram e TikTok.

O material da pessoa é usado como está. Gerar imagem ou vídeo por IA só acontece se ela pedir.

## O que ela não faz

- Não escreve o que a pessoa fala. O texto do vídeo é a fala dela, transcrita.
- Não reescreve fala. A seleção é subtrativa: escolhe trechos e apaga outros.
- Não edita o rosto nem a voz da pessoa por modelo de IA, a menos que ela peça.
- Não fixa duração. Se a pessoa quiser o vídeo inteiro, monta inteiro.

## Quem é quem

| agente | responsabilidade |
|---|---|
| **Bluey** (principal, QA) | faz as perguntas e analisa o material. **É o controle de qualidade da skill:** ouve a gravação logo na fase 1 e avisa se o som tem problema sério, confere o trabalho dos outros três antes de qualquer coisa subir na folha, roda o laudo automático. Monta a folha. Passa o `deslopar` na legenda do post |
| **Bandit** (roteiro) | transcreve, monta a estrutura, sugere o que fica e o que sai, marca **onde** entra material complementar, sugere os letreiros. Se faltar material complementar: escreve o briefing, entrega à Chili, recebe de volta e avalia — sem mandar refazer, só registra o parecer na folha |
| **Chili** (arte e som) | **imagem:** estilo, letreiros, grafismos simples, **como** o material complementar aparece — incluindo **de onde cortar** cada material que não seja deitado, cena a cena. Gera imagem e vídeo por serviço externo quando pedido, a partir do briefing do Bandit. **Som:** nivela e limpa o áudio, escolhe a trilha (fase 2), faz os efeitos sonoros (fase 3). Ensina a conectar os serviços |
| **Bingo** (montagem) | monta o filme, aplica arte, split e legenda, devolve os quadros para a folha, queima a legenda no fim e finaliza em 1080p |

São quatro ao todo: um principal e três subagentes. O revisor foi cortado e o agente de som
também. A revisão inteira é do Bluey; a Chili acumula imagem e som, porque as duas decisões
saem do mesmo estilo escolhido e caem na mesma fase.

### Paralelismo real

Só há dois pontos de paralelismo verdadeiro, e a skill não deve prometer mais que isso:

- **Fase 2**: Bandit e Chili trabalham ao mesmo tempo sobre o mesmo material com perguntas
  diferentes — Bandit responde *onde* entra cada coisa, Chili responde *como* aparece e
  escolhe a trilha.
- **Fase 3**: a Bingo monta enquanto a Chili faz os efeitos sonoros.
- Transcrição de vários takes ao mesmo tempo, dentro do trabalho do Bandit.

O resto é fila: a Bingo não monta antes de o Bandit decidir; a Chili não desenha antes de o
estilo ser escolhido.

## As três fases

| fase | quem trabalha | a folha decide |
|---|---|---|
| 1 · estrutura | Bandit (+ parecer de áudio do Bluey) | o que fica do que a pessoa falou, onde entra material extra |
| 2 · arte e trilha | Bandit ‖ Chili | estilo, letreiros, posição da legenda, trilha sonora, **de onde cortar cada material complementar** |
| 3 · corte | Bingo ‖ Chili | o filme montado, antes de queimar a legenda |

**A trilha é aprovada antes da montagem.** O efeito sonoro, ao contrário, entra durante a
montagem.

### A folha de aprovação

Artefato HTML publicado, uma folha por fase. **Extremamente minimalista, e o mínimo de token
possível** — é a única coisa que herda o visual do projeto de origem.

- Cada folha carrega **só o que falta decidir**. O que é aprovado ou descartado sai da folha e
  vai para um registro em disco.
- Cada peça mostra o **fato medido**, não a opinião do agente. "A legenda aparece 0,2 segundo
  depois de você falar a palavra", não "a legenda ficou boa".
- Uma linha por decisão: miniatura pequena, uma frase de fato, aprovar, descartar, campo de nota.
- Sem vídeo embutido na página. O arquivo fica em disco e a pessoa abre lá.
- Sem fonte carregada da web, sem sistema de design, sem seção explicativa longa.

**O que encareceu a folha no projeto de origem, para não repetir:** o código da página tinha
50 KB e era reescrito a cada rodada — esse era o custo de token real, não o tamanho do arquivo.
E as peças se acumulavam: chegou a 15 numa página só, com vídeo embutido, 5 MB no total.

## O motor

Um script fixo executa toda a parte de vídeo e som. Os agentes **não escrevem comando de
vídeo** — eles preenchem uma lista de cenas, e o script executa.

A lista de cenas é a única interface entre os agentes e o motor. Cada cena traz: número,
tratamento (tela cheia, split, moldura), qual arquivo, onde corta no tempo, **de onde corta no
quadro quando o material não é deitado**, qual letreiro entra e quando, qual estilo.

### Constantes calibradas — vão presas no código, com o porquê no comentário

| constante | valor | por que |
|---|---|---|
| formato | 1080×1920, 30fps | vertical de Reels/TikTok |
| divisória do split | y=807 | medido no pixel |
| crop do teto na janela de baixo | 380 | sem isso o rosto não cabe |
| velocidade | 1,15x nos talking heads | padrão |
| pausa interna comprimida | acima de 0,22s vira 0,10s | ritmo sem pausa entre falas |
| respiro nas pontas | 0,06s na entrada, 0,32s na saída | saída maior para não colar na palavra |
| detecção de pausa interna | −45 dB | a −34 dB a cauda da palavra era lida como silêncio |
| normalização | −14 LUFS, teto −1,5 dB | as gravações chegam por volta de −36 dB |
| legenda | corpo 54, entrelinha 1,16, caixa branca, texto #FF00AA | Satoshi Bold |
| legenda em tela cheia | centralizada, base 1375 | a 1500 ficava sob a interface do app |
| legenda no split | esquerda x=60 / direita / centralizada — topo 827 nas duas primeiras, base 1375 na terceira | a centralizada usar a mesma base da tela cheia evita a legenda saltar na virada de cena |
| chroma key | similaridade 0,10 a 0,13 | a 0,30 apaga o quadro inteiro |

### Material complementar no split

A janela de cima do split é **1080 × 807** — deitada. Todo material complementar é **cortado**
para caber nela; nada entra com barra preta nem deformado.

Quanto sobra da altura do material original:

| formato de origem | sobra |
|---|---|
| deitado (16:9) | tudo; o corte é na largura |
| quadrado (1:1) | 75% |
| vertical 4:5 | 60% |
| vertical 9:16 | 42% |

Num vertical 9:16 mais da metade da imagem some, então **de onde cortar não é detalhe** — corte
pelo centro decepa cabeça com frequência.

**A Chili escolhe o ponto de corte de cada material, cena a cena**, e a escolha vai para a folha
da fase 2 junto com o resto da arte. Não há regra automática: material vertical que não seja
deitado sempre passa por essa decisão.

O corte horizontal é sempre centralizado, porque na largura sobra pouco.

### Armadilhas de ffmpeg que já custaram erro

Ficam resolvidas dentro do motor. Estão aqui para que ninguém as reintroduza:

1. `-ss` vai **antes** do `-i`. Depois do `-i` ele vira opção de saída e o corte escorrega para
   o arquivo seguinte.
2. Áudio sem compressão nos segmentos intermediários, comprimido só no arquivo final, e taxa de
   amostragem igual em tudo. As três coisas juntas resolvem a dessincronia progressiva; nenhuma
   delas sozinha resolve.
3. Juntar os segmentos por filtro, não por lista. A lista descartava trechos de áudio.
4. Normalizar o tamanho de cada segmento antes de juntar — alguma etapa devolve um pixel a menos.
5. Ao juntar imagens, a última entrada duplicada herda a duração da anterior. Cortar na duração
   total sempre.
6. Ruído artificial nunca no canal de transparência.
7. Quando um clipe volta mais curto que o segmento, segurar o último quadro para fechar a
   duração. Sem isso a cena encurta e o filme inteiro perde o sincronismo.

### Regra de corte

**A transcrição diz qual é a palavra; a energia do áudio diz onde cortar.**

O momento em que a transcrição marca o início de uma palavra não é o momento em que ela começa a
soar. E consoantes como p, t, k, b, d, g têm um silêncio **dentro** da palavra — cortar no
primeiro silêncio depois de "tudo" decepa o "do". Medir a 5 milissegundos antes de fixar o corte.

## O que vem embutido

**Sete estilos visuais**, herdados da skill de carrossel em versão reduzida. Cada um vira uma
ficha curta com: cor, fonte, peso, contorno, posição de legenda e posição de letreiro. Só a ficha
escolhida é lida.

O visual do projeto de origem — amarelo com contorno preto, Satoshi Black, legenda rosa sobre
caixa branca — **não vira um oitavo estilo**. Ele sobrevive só na folha de aprovação.

**Do express cut**, apenas `audio-speed` e `audio-silence-cut`, como comandos avulsos que a
pessoa aciona quando quiser. O pipeline usa a versão calibrada do motor, que é melhor: corte por
energia em vez de detector de silêncio, e compressão de pausa interna.

**Do deslopar**, só a aplicação na legenda do post. Letreiro não passa por ele — letreiro marca
uma frase que a pessoa falou, e mexer nela seria errado.

## Áudio

Serviços já conectados que resolvem trilha e efeito:

| serviço | música | efeito | limpar voz |
|---|---|---|---|
| Magnific | sim | sim | sim |
| Higgsfield | sim | sim | não |
| ElevenLabs direto | sim | — | — |

Para efeito sonoro gratuito, o Freesound é a opção sólida. Para música gratuita, os bancos livres
têm acervo pequeno e regra de crédito que varia por faixa — não depender deles.

A trilha abaixa sozinha quando a pessoa fala, e há um limitador no fim para a voz não estourar.

## Serviços de IA para vídeo — medido, não suposto

Só entra em jogo se a pessoa pedir para editar o vídeo dela com efeito.

| tarefa | serviço | resultado medido |
|---|---|---|
| editar o próprio vídeo | Seedance 2.5, modo de edição | 7,5 a 19,7 de diferença numa escala de 255 |
| trocar a boca no próprio vídeo | Veed Sync 2.0 (Magnific) | 23 na boca, 2 no resto do quadro |
| **não usar para editar** | MiniMax H3 com referência de vídeo | 13 a 99 no quadro inteiro; regenera o rosto e desloca o áudio em 0,95s |
| **não aceita vídeo** | Kling 3.0 | só imagem inicial |

Toda troca de imagem por modelo passa por um teste de fidelidade antes de entrar no corte: o
motor compara o clipe devolvido com o take e informa a diferença. O Bluey decide com esse número.

Armadilhas de prompt já conhecidas: marcação de tempo só é obedecida se dita em segundos **e** em
frações do clipe; geradores de imagem cortam os pés da figura se não for dito que ela ocupa 55%
da altura do quadro.

## Laudo automático antes de cada folha

O Bluey roda uma bateria fixa antes de publicar:

- diferença entre áudio e imagem, cena a cena
- palavras cortadas nas emendas — transcreve o corte e compara com a transcrição do take
- legenda dentro da faixa segura da tela
- duração do vídeo contra duração do áudio

É medição, não julgamento. Foi assim que quase todo erro apareceu no projeto de origem.

## Entregáveis

- o vídeo com legenda queimada, 1080×1920
- o mesmo vídeo sem legenda, para quando a plataforma legenda sozinha
- a legenda do post

## Como a skill fala com quem usa

Quem usa isto **não entende de montagem, edição ou áudio**.

- Sem termo técnico. Se um for inevitável, explicar em uma frase.
- Sem metáfora difícil.
- Sem resumir demais o problema — dizer o que está errado, de verdade.
- Sem verborragia. Não descrever em detalhe cada entrega.
- Sempre fechar com um checklist enxuto do que foi feito, e esperar a resposta.

## Perfil, para exigir o mínimo da pessoa

Um arquivo de perfil roda **uma vez** e vale para os vídeos seguintes: quem publica, plataforma,
estilo padrão, onde ficam as gravações. Nos trabalhos seguintes a skill mostra um resumo curto e
pergunta só o que mudou. Mesmo padrão da skill de carrossel.

## Limpeza de dados pessoais nas skills incorporadas

Medido, não estimado:

| skill | ocorrências de dado pessoal | o que fazer |
|---|---|---|
| `audio-speed`, `audio-silence-cut` | 0 | entram como estão |
| `deslopar` | 1 | verificar e limpar |
| `um-carrossel-por-favor` | 23, sendo 20 em `onepage/` | a pasta `onepage/` não vem junto. O resto é crédito de autoria, que fica |
| `carrossel-perfil.md` | público, voz e plataformas do Drudi | vira template vazio |

## Pendências

1. **Formato do arquivo de cenas.** O documento descreve os campos, não o formato. Fica para o
   plano de implementação.
2. **A divisão de trabalho entre Bandit e Chili na fase 2** (ele decide *onde* entra, ela decide
   *como* aparece) foi proposta e assumida como aceita, sem confirmação explícita.
