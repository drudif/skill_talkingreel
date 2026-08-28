# Diario — skill_talkingreel

Historico de decisoes. Nao e carregado em toda sessao — lido sob demanda, pode crescer.
Entrada nova no topo, com data.

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
