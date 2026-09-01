# O contrato: o arquivo `cenas.json`

Este arquivo é a única coisa que os agentes escrevem. O motor lê e executa.

## A regra que vale para todo número de tempo

**Todo instante escrito aqui é segundo da GRAVAÇÃO, contado do começo do arquivo
original.** Sem exceção: onde a cena começa, onde termina, quando um texto grande
aparece na tela e quando ele some.

Quem escreve olha a transcrição da gravação e anota o segundo que vê ali. Não
existe conta a fazer, e não é preciso montar o filme antes para descobrir número
nenhum. Quem converte para o tempo do filme pronto é o motor, em `motor/tempo.py`,
e só ele.

**Por que a regra existe.** Entre a gravação e o filme o tempo encolhe duas vezes:
as pausas dentro da fala são cortadas, e o que sobra é acelerado. As duas coisas
juntas fazem o mesmo instante cair em lugares diferentes conforme quantas pausas
vieram antes dele. Escrever o tempo do filme à mão errava pouco no começo da cena
e muito no fim — e o erro aparecia só depois, no vídeo pronto, com o texto entrando
fora de hora.

## Exemplo completo

```json
{
  "velocidade": 1.15,
  "legenda_estilo": {"fonte": "sem serifa", "paleta": "branco e preto",
                     "efeito": "caixa"},
  "letreiro_estilo": {"fonte": "estreita", "paleta": "amarelo",
                      "efeito": "contorno"},
  "legenda": true,
  "legenda_split": "esquerda",
  "proprios": ["Ginsu", "Anthropic"],
  "trilha": "audio/trilha.mp3",
  "cenas": [
    {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov",
     "de": 12.0, "ate": 25.4,
     "letreiro": {"texto": "COMENTA QUERO", "de": 13.1, "ate": 14.9,
                  "base": 1400, "box": false}},
    {"n": 2, "trat": "split", "arquivo": "gravacoes/take-01.mov",
     "de": 41.2, "ate": 52.0,
     "topo": {"arquivo": "broll/faca.mp4", "ancora": 0.3}}
  ]
}
```

As duas cenas do exemplo saem do **mesmo arquivo**, em trechos diferentes. É assim
que se escolhe a melhor tomada de uma frase que a pessoa repetiu, e é assim que um
take longo vira um filme.

## Os campos da produção

| campo | precisa? | o que é |
|---|---|---|
| `velocidade` | não | quanto o filme acelera. 1.15 é o padrão, e não se nota |
| `legenda_estilo` | não | como a legenda aparece: `fonte`, `paleta` e `efeito`. O que faltar vira o padrão |
| `letreiro_estilo` | não | o mesmo para o texto grande na tela. As fontes são outras |
| `legenda` | não | queimar a legenda no fim. Padrão `true`. **Desligar pula a transcrição inteira**, que é a etapa mais demorada |
| `legenda_split` | não | onde a legenda fica quando a tela está dividida em duas: `esquerda`, `direita` ou `centro`. Padrão `esquerda` |
| `proprios` | não | nomes que a transcrição costuma errar, escritos do jeito certo. **Só nome próprio, e só com 4 letras ou mais**. Conserta erro de escrita parecido com o nome, não erro de som |
| `trocas` | não | trocas ditadas: `{"sidense": "Seedance"}`. É o único jeito de consertar quando a transcrição ouviu errado. **A chave pode ter mais de uma palavra** — `{"2 .5": "2.5"}` junta as três peças em que ela parte um número decimal |
| `trilha` | não | a música de fundo. Ela abaixa sozinha quando a pessoa fala. Sem este campo, o filme sai sem música |
| `abertura` | não | o estalo dos primeiros meio segundo: um clarão, as cores se separando e a imagem fechando de um zoom. `true`, `false`, ou um número de 0 a 1 para regular |
| `glitch` | não | o mesmo estalo, curto e fraco, numa emenda a cada quatro. `true`, `false`, ou um número de 0 a 1 |
| `contraste` | não | `true` mede cada gravação e corrige a que estiver lavada; `false` deixa a imagem como veio; um número força o mesmo ajuste em todas. Padrão `true` |
| `hud` | não | o painel fixo sobre a imagem: `{"texto": "a frase que passa", "vu": true}`. Só a frase também vale: `"hud": "a frase"`. **Sem este campo não há painel** |
| `cenas` | sim | a lista de cenas, em ordem |

## Os campos de cada cena

| campo | precisa? | o que é |
|---|---|---|
| `n` | sim | o número da cena |
| `trat` | sim | como a cena aparece: `cheia`, `split`, `material` ou `atras`. As três últimas usam o material extra — veja abaixo |
| `arquivo` | sim | a gravação, relativa à pasta do `cenas.json`. **Pode se repetir entre cenas** |
| `de` | não | segundo da gravação em que este trecho começa. Sem ele, começa no início do arquivo |
| `ate` | não | segundo da gravação em que este trecho termina. Sem ele, vai até o fim do arquivo |
| `velocidade` | não | troca a velocidade só nesta cena. Sem este campo, vale a velocidade geral da produção |
| `teto` | não | limite de duração, em segundos, contado a partir de onde a fala começa |
| `material` | nas três | `{"arquivo": ..., "ancora": 0.0 a 1.0}`. A âncora escolhe que parte da imagem fica visível: 0 é o topo, 1 é o pé. `topo` é o nome antigo do mesmo campo, e continua valendo |
| `letreiro` | não | texto grande sobre a imagem |
| `fundo` | não | troca o fundo por uma imagem ou por uma cor escrita como `#101010`. **Só funciona com pano verde** — veja abaixo |

**`de` e `ate` recortam antes de tudo.** O motor procura onde a voz começa e termina
**dentro** desse recorte, e nunca passa dele. Duas cenas do mesmo arquivo com
recortes diferentes acham falas diferentes, que é o esperado.

**`teto` e `ate` não são a mesma coisa.** `ate` diz onde parar na gravação. `teto`
diz quantos segundos a cena pode durar depois que a fala começa — serve para cortar
uma cena que se alongou, sem precisar saber em que segundo a voz entra.

## O painel fixo

Duas peças finas no alto da tela, sobre o vídeo inteiro, com cara de câmera
ligada: uma **barra que responde ao som da fala** e uma **frase que passa
devagar para a direita**, em laço.

| campo | precisa? | o que é |
|---|---|---|
| `texto` | não | a frase que passa. Até 90 letras — ela anda, e uma frase longa ninguém termina de ler |
| `vu` | não | a barra de som. Padrão ligada |

**A barra responde a quem fala, não à música.** O motor a alimenta com o som de
antes de a trilha entrar. Alimentada pelo som final, ela dançaria com a batida
da música — inclusive no silêncio de quem fala, que é o contrário do que ela
diz.

**O painel não segue o estilo escolhido para a legenda.** Ele é a moldura, e
tem letra e cor próprias, sempre as mesmas.

## As quatro formas de uma cena

| `trat` | o que aparece na tela | o som |
|---|---|---|
| `cheia` | só a pessoa | a voz dela |
| `split` | o material em cima, a pessoa embaixo | a voz dela; o material entra mudo |
| `material` | só o material, na tela inteira | a voz dela continua por baixo |
| `atras` | a pessoa recortada, com o material atrás dela | a voz dela |

**A escolha entre as três últimas é da pessoa, na folha** — não do agente. Ela
era uma só, e a skill nem perguntava: todo material extra virava tela dividida.

**`material` repete o material até cobrir a fala.** Um material de 4 segundos
num trecho de 9 deixaria cinco segundos de tela parada com voz correndo por
baixo. Quem repete é o motor.

**`atras` só funciona com pano verde.** É o verde que diz ao programa o que é
cenário e o que é pessoa; numa sala comum o programa apagaria pedaços dela. O
motor mede a gravação antes de montar qualquer coisa e recusa, dizendo isso.
Com `atras`, o campo `fundo` não pode vir junto: seriam dois fundos para o
mesmo lugar.

## O letreiro

| campo | precisa? | o que é |
|---|---|---|
| `texto` | sim | o que aparece escrito |
| `de` | não | segundo da gravação em que o texto aparece. Padrão 0, que é o começo da cena |
| `ate` | não | segundo da gravação em que o texto some. Sem isso, fica até o fim da cena |
| `base` | não | onde o texto se apoia na altura da tela |
| `box` | não | caixa sólida atrás do texto. Padrão sem caixa |

**`de` e `ate` do letreiro são segundos da gravação, iguais aos da cena** — o
instante em que a pessoa fala aquela frase no arquivo original. O motor desconta
sozinho o corte das pausas e a aceleração.

**O letreiro precisa cair dentro do recorte da cena.** Um letreiro marcado para
aparecer fora dele nunca apareceria, e o motor recusa o arquivo dizendo isso, em
vez de montar um filme silenciosamente sem o texto.

**Como o texto entra: a frase se monta palavra a palavra.** É a única entrada, e
não há o que escolher. Ela dura menos de meio segundo — o suficiente para o olho
acompanhar as palavras entrando, sem atrasar a leitura.

O texto se apoia sempre na posição da frase inteira, e não pula de lugar
enquanto monta. E termina exatamente onde o texto parado ficaria.

**Texto que ficaria menos de 0,4 segundo na tela é esticado até 0,4.** Acontece
quando o letreiro foi ancorado num trecho que o corte de pausa removeu. Menos que
isso ninguém lê, e o texto sumiria sem explicação.

## Como o texto aparece: `legenda_estilo` e `letreiro_estilo`

Cada um aceita três campos, e todos são opcionais:

| campo | o que é |
|---|---|
| `fonte` | a letra. A legenda escolhe entre três de leitura; o letreiro, entre cinco de chamar atenção |
| `paleta` | as cores. São cinco, e valem para os dois |
| `efeito` | `contorno` (traço escuro em volta da letra) ou `caixa` (letra dentro de um retângulo cheio) |

As opções de cada campo estão em `referencias/estilos.md`. Escolher um campo não
obriga a escolher os outros: o que faltar vira o padrão.

**A cor da letra muda conforme o efeito, e isso é de propósito.** Amarelo com
contorno preto se lê bem sobre vídeo, mas amarelo dentro de caixa amarela
sumiria. Cada paleta traz as duas cores, e o motor pega a certa.

## Consertar nome na legenda: `proprios` e `trocas`

São duas coisas diferentes, e a diferença importa.

**`proprios` conserta erro de escrita.** A transcrição escreveu quase certo — "Anthropik" no
lugar de "Anthropic" — e o motor troca sozinho, comparando letra por letra.

**`trocas` conserta erro de som.** A transcrição ouviu outra coisa: escreveu "Sidense" onde a
pessoa disse "Seedance". Aí não há semelhança de escrita nenhuma entre o que saiu e o que devia
sair, e o motor não tem como adivinhar — você diz qual palavra vira qual.

**Por que não basta afrouxar a comparação de escrita para pegar os dois casos.** Foi medido: para
"guinco" virar "Ginsu" a comparação teria de aceitar semelhança de 0,545, e nesse ponto "verdade"
(0,533) e "bastante" (0,588) também viram nome próprio na legenda queimada. As duas faixas se
encostam. Comparar letras não diz nada sobre som.

## Trocar o fundo: `fundo`

**Só funciona se a pessoa gravou na frente de um pano ou parede verde.** É o
verde que diz ao programa o que é cenário e o que é pessoa. Numa sala comum não
existe essa separação, e o programa apagaria pedaços da pessoa junto com o
fundo.

O motor **confere sozinho, antes de começar a montar**. Se a gravação não tiver
pano verde, ele recusa o arquivo e explica — não monta um vídeo estragado.

O que ele confere é quanto da **borda** do quadro é verde forte. A borda, e não
o quadro inteiro, porque é ela que separa um pano de fundo de uma camiseta
verde: a pessoa fica no meio, o pano aparece em volta dela. Medido, pano de
fundo de verdade ocupa de 58% a 85% da borda; camiseta verde, planta num canto
e imagem colorida qualquer ficam todas por volta de 13%.

A cor do corte sai da própria gravação, não de um verde fixo: panos verdes não
são todos iguais e a luz muda o tom, e cortar pela cor errada deixa uma borda
esverdeada no contorno da pessoa.

## O estalo de abertura: `abertura`

Nos primeiros meio segundo do vídeo acontecem três coisas ao mesmo tempo: um
clarão que some, as cores se separando um pouco e voltando ao lugar, e a imagem
fechando de um zoom.

**Por que só no começo.** É ali que o dedo de quem rola a tela ainda está
decidindo, e movimento forte segura. Depois de meio segundo o mesmo efeito
atrapalha a leitura, e por isso ele acaba.

Um número de 0 a 1 regula a força: `0.5` deixa o efeito mais discreto, `0`
desliga — o mesmo que `false`.

## O glitch das emendas: `glitch`

O mesmo estalo, curto e fraco, entrando **numa emenda a cada quatro** para marcar
uma virada de assunto.

É outra coisa do que a abertura, e por isso é mais fraco: ali o efeito abre o
vídeo e pode ser violento; aqui ele acontece no meio da fala e não pode roubar a
atenção dela. Dura um terço do tempo, e o zoom é um tranco em vez de um mergulho.

**Em uma a cada quatro, e nunca na primeira.** Em todas as emendas vira tique, e
a pessoa para de ver o vídeo para ver o efeito. Na primeira ele se somaria ao
estalo de abertura, e os dois juntos viram uma borra só.

## Corrigir a imagem lavada: `contraste`

Imagem lavada é aquela em que tudo fica perto do mesmo cinza — sem preto de
verdade nem branco de verdade. O motor mede quanto da escala de brilho cada
gravação ocupa e estica só as que estiverem abaixo do normal.

O alvo não é um número escolhido: é a faixa que as gravações bem feitas já
ocupam, medida em seis delas. Material que já está bom **não é tocado**, porque
esticar o que já está bom só faz perder desenho nas partes claras e escuras.

## O que sai junto: `cenas-mapa.json`

A montagem grava esse arquivo ao lado do `cenas.json`. Cada cena aparece com os
dois tempos lado a lado: `de` e `ate` são da gravação, `ini` e `fim` são do filme
pronto. É por ele que se descobre de que ponto da gravação veio qualquer instante
do filme, sem montar de novo. Vem também `contraste`, o quanto a imagem daquela
cena foi esticada, e `pausas`, quantos silêncios foram cortados dentro dela.
