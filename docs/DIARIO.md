# Diario — skill_talkingreel

Historico de decisoes. Nao e carregado em toda sessao — lido sob demanda, pode crescer.
Entrada nova no topo, com data.


---

## 2026-08-31 — a revisao de escopo

Branch `revisao-escopo`. O pedido foi "comecar do zero"; o que se fez foi reforma, porque quase
todo o escopo listado como novo ja existia e funcionava, e o valor dele nao esta nas linhas de
codigo e sim nos numeros calibrados. Comecar do zero teria feito o projeto redescobrir as
armadilhas uma a uma, todas de falha silenciosa.

Cortado: as tres fases viraram duas aprovacoes; o questionario de perfil e a legenda do post
sairam. Entrou: coordenada unica de tempo, decupagem de varias tomadas, contraste medido, troca de
fundo com pano verde, letreiro animado, catalogo dos sete estilos aplicado no video da pessoa,
filme leve para aprovar, dossie para o paralelismo, e a lista de quatro trilhas.

### O que se mediu, e o que a medida mudou

- **A coordenada unica de tempo.** O problema nao era teorico: com uma pausa de 1,7s cortada no
  meio da cena, um letreiro ancorado em 4,5s da gravacao cai em **2,658s** do filme. O jeito
  antigo, somar o instante cru ao inicio da cena, poria em **4,240s** — 1,58s de erro, e crescendo
  a cada pausa. Agora `motor/tempo.py` converte, e `tempo.marcas()` e a fonte unica que o corte e
  a conversao compartilham. `tests/test_montar.py` mede isso no video renderizado, nao na conta.

- **O alvo de contraste saiu do material, nao de um numero bonito.** Seis gravacoes reais do
  projeto de origem ocupam de **163,7 a 165,7** da escala de brilho, todas com zero pixel
  estourado. Dai o alvo 165. O que fechou o limiar de "lavado" foi a medida do outro lado:
  material que ja esta em 163,5 perde **0,47%** dos pixels no estouro com esticamento de so 1,15,
  e **2,61%** com 1,25. Corrigir o que ja esta bom nao e neutro. Limiar em 143, que e 165/1,15.

- **Pano verde se detecta na borda do quadro.** Primeira tentativa foi a fracao do quadro inteiro,
  e ela quase falhou: croma com enquadramento apertado deu **33%**, camiseta verde deu **20%** —
  perto demais para um limiar seguro. Medindo so a borda, os mesmos casos deram **58%** e **13%**,
  fator quatro. A pessoa fica no meio do quadro; o pano aparece em volta dela. Limiar em 40%.

- **A tolerancia do corte do pano: o palpite estava errado.** Escrevi 0,20 de cabeca. Medindo com
  um pano de luz irregular e uma figura na frente, a janela boa vai de **0,04 a 0,18**: em 0,02
  sobra pano (o fundo novo cobre 37% do quadro onde devia cobrir 67); em **0,20 a figura comeca a
  ser comida** e em 0,28 ela some por completo. Fixado em 0,11, no meio da janela. Sem a medicao,
  o valor que eu tinha escrito apagaria pedaco de gente.

- **Os sete estilos usavam duas fontes, nao sete.** O teste do catalogo reprovou sozinho:
  `terminal` e `neubrutal` sairam identicos. A causa apareceu ao conferir qual fonte cada ficha
  usava de fato: **todas listavam a mesma primeira candidata**, e como ela existe na maquina do
  autor, ganhava sempre — cinco fichas com um peso, duas com outro. O usuario pediu sete estilos
  de "fonte, cor e estilo"; a fonte era um eixo que existia so no papel, e os sete diferiam so por
  cor.

  A correcao veio pronta da skill de carrossel, que ja tinha o par de fontes de cada estilo
  resolvido. As catorze entraram em `assets/fontes/` com as licencas, e `estilos.py` ganhou
  `fonte_legenda()` separada de `fonte()` — a fonte de titulo num texto pequeno e corrido deixa a
  leitura pesada. Medido na gravacao real, sobre os 21 pares possiveis: o par mais parecido saiu de
  **20,8 para 37,0**, `terminal` contra `neubrutal` saiu de **20,8 para 57,5**, e a media dos pares
  subiu de 57,6 para 65,7. A regra de nunca EXIGIR fonte licenciada continua: cada ficha lista a
  fonte da skill, depois uma do sistema, depois a que existe em todo Mac.

- **Um arquivo estragado derrubava o programa.** Achado rodando o caminho inteiro com material de
  verdade, nao em teste de unidade: o ffprobe devolve a palavra `N/A` — e nao um erro — para
  arquivo truncado ou que nao e video, e `probe.dur` tentava virar isso em numero. O resultado era
  uma parada com mensagem em ingles e um monte de linha de codigo na tela de quem nao programa.
  Agora vira 0.0, o dossie marca o arquivo como ilegivel, e a pessoa le "nao deu para abrir, mande
  de novo".

- **`no_original` e `no_filme` nao sao o par que os nomes sugerem.** Cai nessa na propria
  conferencia: passei um instante do filme para `no_original`, que espera instante da cena, e a
  volta devolveu **26,0s onde o certo era 20,0s** — um numero plausivel, sem erro nenhum. Entrou
  `do_filme()`, que desconta o comeco da cena, e um teste que falha se os dois pares passarem a dar
  o mesmo resultado.

### A decisao de desenho que sustenta o paralelismo

Bandit e Bingo correm juntos, mas o Bingo **so mede**. A propriedade que torna isso seguro esta
escrita como teste (`test_medir_duas_vezes_da_o_mesmo_resultado`): nada no dossie depende de
decisao, entao as mesmas contas dao o mesmo resultado antes ou depois do Bandit. Cortar ou acelerar
nessa fase jogaria fora material que o roteiro ainda pode pedir — e foi o desenho original pedido,
recusado por isso.

O mesmo raciocinio vale para o que ja estava no motor: area util, contraste e pano verde sao
propriedades de ESPACO e saem sempre do arquivo original. Tempo e outra coisa.

---

## 2026-08-28 — a skill fechada

O `SKILL.md`, os quatro agentes, o perfil, e o que veio embutido das outras skills. 299 testes.

### Decisoes

- **Os limites nao sao repetidos, sao apontados.** `referencias/limites.md` manda ler
  `motor/limites.py`, que e onde as regras moram com soma de verificacao. Repetir o texto criaria
  duas fontes de verdade, e a soma so vigia uma delas.
- **O arquivo de estilos descreve, nao repete valor.** Cor e fonte moram em `motor/estilos.py`; o
  arquivo que a Chili le so diz como cada ficha parece e quando serve. Um teste recusa codigo de
  cor e nome de fonte no arquivo, para os dois nao sairem de sincronia no primeiro ajuste.
- **A varredura de jargao virou teste.** "Sem termo tecnico" e a instrucao mais facil de escrever e
  a mais facil de esquecer. O teste varre o `SKILL.md`, as referencias, o laudo, a folha e a
  mensagem de erro do contrato. A excecao — o termo passa se a frase explicar ali mesmo — pula 5%
  das frases, e nenhuma delas tem jargao, entao nao esta escondendo nada.
- **A limpeza de dado pessoal foi menor do que o desenho previa.** Medido nas quatro skills
  incorporadas: `audio-speed` e `audio-silence-cut` nao tem nenhum; no `deslopar` e no carrossel o
  que aparece e credito de autoria, que fica. O perfil preenchido do autor mora em `~/.claude/`,
  fora da pasta da skill, entao nunca seria copiado — o que entra e um modelo vazio.

### Duas falhas que so apareceram tentando usar

- **`python3 -m motor cenas.json saida.mp4` nao roda.** A skill mora em `~/.claude/skills/` e a
  gravacao da pessoa mora em outro lugar; sem `PYTHONPATH` o Python nao acha o motor. O comando
  estava escrito assim no `SKILL.md` e no arquivo do Bingo. Agora um teste roda o comando de uma
  pasta estranha, e outro guarda o texto da documentacao para o comando errado nao voltar.
- **O entregavel "o mesmo video sem legenda" nao existia.** O `SKILL.md` prometia, mas o motor
  sobrescrevia o arquivo e a versao sem legenda so vivia na pasta temporaria, que e descartada.

### Uma coisa que o plano errou e o subagente pegou

O contrato que escrevi no plano nao documentava a velocidade por cena, que o motor le
(`cenas.py`, `float(bruto.get("velocidade", velocidade))`). Campo que o motor le e a documentacao
nao explica e campo que nenhum agente vai usar.

---

## 2026-08-28 — laudo completo e folha de aprovacao

O motor esta fechado: entra `cenas.json` e gravacao, sai o filme legendado, o laudo do que foi
medido, e a folha que a pessoa marca. 227 testes.

### O laudo

Tres medicoes novas, cada uma ligada a um erro que aconteceu e que ninguem viu no olho: emenda que
decepa palavra, legenda sob a interface do aplicativo, e material de apoio repetindo em loop.

- **Emenda medida por energia, nao por transcricao.** Transcrever cada corte custaria um modelo de
  2,9GB por emenda e responderia de forma indireta.
- **A referencia e a FALA, nao o silencio — e isso custou uma correcao.** A primeira versao usava o
  percentil 10 do envelope como "nivel do silencio". Funciona em clipe de teste; falha no caso real.
  Num talking head bem cortado quase nao sobra silencio, entao esse percentil E fala: medido, um
  filme de duas cenas coladas devolveu "silencio" a -0,8 dB e nenhuma emenda suja era detectada. A
  fala, ao contrario, sempre existe num video de alguem falando. Emenda limpa fica 41 dB abaixo da
  fala; emenda que corta palavra, de 0 a 3 dB. Margem em 15.
- **Repeticao avisa e nao reprova.** Repetir pode ser deliberado.

### Duas medicoes que estavam calibradas contra numero que nao existe

- **O clipe de teste mentia sobre nivel.** O silencio de `clipe_fala` era zero DIGITAL, o que poe o
  piso em -120 dB e cria uma distancia de 120 dB entre fala e silencio — distancia que nao existe em
  gravacao nenhuma. Qualquer limiar ate 120 "passava" no teste sem medir coisa alguma. O fixture
  ganhou `ruido_dB`, e uma sala silenciosa fica por volta de -50 dB.
- **O limite da faixa segura nao pegaria o erro que o motivou.** A legenda na base 1500 caiu sob a
  interface do aplicativo, e por isso virou 1375. Mas 1500 termina em y=1501, e o limite escrito era
  1560. Foi para 1400, logo acima do unico valor que sabemos bom.

### A folha

- **O template mora no Python.** O custo real do projeto de origem nao foi o tamanho do arquivo: foi
  o modelo reescrever 50 KB de HTML a cada rodada. Agora ele produz so a lista de itens.
- **O decidido sai da folha.** Medido: folha de 10 itens com 6.561 bytes; depois de decidir 7, a
  folha seguinte tem 3.866. O que nao encolhe e a estrutura fixa (CSS e JS, ~2.700 bytes).
- **A armadilha do estado foi eliminada, nao documentada.** Antes havia dois trechos parecidos com
  `<script id="dados">` no mesmo arquivo — o bloco de verdade e a mesma string dentro do JavaScript
  que regenera a pagina — e quem lesse o segundo apagava o feedback. Agora os marcadores sao
  montados por concatenacao, aparecem uma vez so, e o leitor falha alto se achar mais de um.
- **`</script>` dentro do texto quebrava a pagina**, nos dois lados: no Python que gera e no
  JavaScript que republica. Os dois escapam `<` agora.
- **Miniatura, nunca video.** Video embutido levou a folha do projeto de origem a 5 MB.

### Uma armadilha da maquina, nao do codigo

Este Mac guarda o bytecode do Python em `~/Library/Caches/com.apple.python`, fora do projeto, e
invalida o cache comparando data **e tamanho** do arquivo. Trocar `1400` por `1560` — mesmo numero
de caracteres, no mesmo segundo — nao invalida nada, e o Python roda o codigo velho sem avisar. Isso
apareceu justamente numa verificacao do tipo "quebra o codigo e ve o teste falhar", que e onde mais
machuca: o resultado da verificacao vira ficcao. Toda verificacao desse tipo passou a rodar com
`PYTHONDONTWRITEBYTECODE=1`.

---

## 2026-08-28 — arte e legenda

Sete fichas de estilo, letreiro por cena, e legenda queimada nas quatro posicoes medidas.
176 testes. O motor esta completo: entra `cenas.json` e gravacao, sai o filme legendado.

### Decisoes

- **A fonte e um problema de distribuicao, nao de gosto.** A do projeto de origem e licenciada e
  mora na maquina do autor. Cada ficha lista candidatas em ordem e cai numa fonte do sistema. Sem
  isso a skill quebra na maquina de outra pessoa.
- **Texto vetorial, nunca modelo de imagem.** Modelo de imagem erra acento em portugues.
- **Base 1375 em tela cheia.** A 1500 caia sob a interface do aplicativo. A posicao centralizada do
  split usa a mesma base, para a legenda nao saltar na virada de cena.
- **A legenda some sob letreiro grande**, senao a mesma frase aparece duas vezes, uma grande e uma
  miuda. O mapa de cenas registra a janela do letreiro em tempo de filme; a legenda consulta.
- **`entra` e `dura` do letreiro contam na cena JA PRONTA**, depois do corte de silencio e da
  velocidade. Nao ha como ser diferente — as duas etapas mudam a escala do tempo de forma nao
  linear. Quem preenche o contrato tira o instante da transcricao do filme montado.
- **Transcricao injetavel.** `montar(..., transcrever=...)` existe porque, sem isso, testar a
  fiacao da legenda exigia baixar um modelo de 2,9GB e ter fala humana num clipe de bipe. Com a
  costura, toda a fiacao e testada de forma deterministica, e `tests/conftest.py` faz qualquer
  teste que caia na transcricao de verdade falhar alto em vez de travar a suite baixando modelo.

### Defeitos que so apareceram medindo

- **`-shortest` no overlay comia quadros.** Com letreiro, o video perdia de 2 a 5 quadros enquanto
  o audio ficava inteiro. A folga ia de 0,057s a 0,157s, sem relacao com o tamanho da cena — a cena
  mais LONGA era a pior, o que derruba a hipotese obvia de arredondamento. Num filme de dez cenas
  com letreiro isso passa de um segundo de descompasso entre boca e som. Trocado por
  `eof_action=pass`: quando a imagem acaba, os quadros da base seguem passando. Depois da troca a
  diferenca video/audio ficou constante em -0,023s, identica a de um filme sem letreiro nenhum.
- **A guarda contra correcao errada estava no lado errado.** O codigo recusava corrigir palavra
  curta da FALA. Medindo, as tres trocas erradas do teste vinham todas do ALVO curto: "te" bate
  0,80 contra "ter", "que" bate 0,857 contra "quem", "Nao" bate 0,80 contra "no". Filtrando o alvo,
  nenhuma palavra da fala passa de 0,29. A guarda mudou de lado, o que preserva a correcao de nome
  proprio de quatro letras (Nike, Ford, Java) que a outra solucao teria perdido em silencio.
- **Palavra sem espaco maior que a largura era cortada sem aviso.** Um token de 40 caracteres monta
  caixa de 1248px num quadro de 1080. O Pillow corta o que sai do canvas sem erro nenhum, e o bbox
  do PNG nunca denuncia — nao pode ser maior que o proprio PNG. Por isso o teste olha a MARGEM, nao
  o tamanho. A quebra caractere a caractere ja existia no letreiro; virou funcao comum aos dois.
- **Um teste media no lugar errado.** O brilho medio de uma regiao cancela contorno preto contra
  preenchimento amarelo (+82 contra -123 de luma), e o recorte chutado cobria 26% da tinta. Recorte
  chutado dava 15; recorte tirado do bbox do proprio PNG deu 72. Todo teste de "apareceu na tela"
  passou a derivar o recorte da peca e comparar pixel a pixel.

---

## 2026-08-28 — motor do nucleo pronto

Le um `cenas.json` e devolve o filme montado: corte de silencio pelas pontas, compressao de
pausa interna, velocidade por cena, split com ancora de recorte, trilha com abaixamento sob a
voz, e laudo de qualidade em portugues. 77 testes, ~60s de suite porque monta video de verdade.

Provado com material real do `conteudo/agentes-ginsu`: 3 gravacoes, 2 b-rolls e trilha viraram
17,8s de filme em 54s de processamento, sem uma linha de ffmpeg escrita a mao.

### Decisoes

- **Material de teste gerado por ffmpeg**, nao gravacao real. O valor esperado de cada teste
  fica conhecido e nenhum video pessoal entra no repositorio.
- **Nove modulos pequenos** em vez de um script grande. So `tratamentos.py` e `montar.py`
  geram video; o resto so mede ou valida.
- **O `cenas.json` e o contrato.** Os agentes escrevem, o motor le.
- **A ancora de recorte** existe porque a janela de cima do split e deitada (1080x807) e
  material vertical perde 58% da altura.

### Um bug que quase passou, e como

O `alimiter` tem `level=true` por padrao. A opcao NAO normaliza para 0 dB como o nome sugere:
soma um ganho fixo de +1.5 dB, compensando o valor do `limit`. O plano esqueceu o
`level=disabled` que o projeto de origem usava, e o pico do filme ia para -0.0 dB em vez de -1.5.

Ele passou por tres redes: os tres testes do plano, dois testes extras escritos pelo subagente,
e a primeira versao do teste de correcao. **So apareceu ao rodar com gravacao e trilha reais.**

A causa de o teste nao pegar: material sintetico baixo. Medido, um tom a -5.5 dB da o mesmo
resultado nas duas versoes; so material perto do teto separa. O teste final carrega uma
verificacao propria que se recusa a rodar se a fonte estiver baixa demais.

Licao para os proximos planos: **teste de audio precisa de fonte no nivel de producao**, e todo
teste de guarda deve ser provado quebrando o codigo de proposito.

### Cobertura por armadilha

| armadilha | teste que guarda |
|---|---|
| `-ss` depois do `-i` | tom em posicao conhecida, medido na saida |
| dessync progressivo | 15 cenas, erro constante em vez de crescente |
| ancora do split ignorada | material metade vermelho metade azul, pixel comparado |
| sidechain invertido | inversao de proposito faz o teste falhar |
| limitador desligado | fonte no nivel de producao |
| compressao comendo fala | conta os trechos de fala que sobreviveram |

---

## 2026-08-28 — inicio

Projeto criado.
