# skill_talkingreel — a skill "talking reel: done"

Pega um ou mais videos de talking head do usuario e devolve um vertical montado, com ritmo, arte e
legenda queimada, pronto pra Instagram e TikTok. Python + ffmpeg + mlx-whisper + Pillow; legenda e
letreiro sao texto vetorial, nunca imagem de IA.
**Estado: completa — motor, laudo, folha, SKILL.md e os quatro agentes.**

> Este arquivo passa das 40 linhas de proposito, com aval do Drudi. Quase toda linha da secao de
> armadilhas custou uma rodada de erro num video de verdade, e o modo de falhar de quase todas e
> silencioso: o video sai errado sem ninguem ver. Aqui o teto vale menos que o prejuizo.

## Comandos
- `PYTHONPATH=<esta pasta> python3 -m motor cenas.json saida.mp4`, de dentro da pasta do
  trabalho — monta e imprime o laudo. **Sem o PYTHONPATH o Python nao acha o motor.**
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest` — 408 testes, ~9min. Eles montam video de verdade,
  nao conferem chamada de funcao. `TESTE_LENTO=1` liga o unico que roda o modelo de transcricao;
  `GRAVACOES_REAIS=<pasta>` aponta as gravacoes de verdade.

## A regra do tempo — le isto antes de mexer em qualquer instante
**Todo instante que um agente escreve no `cenas.json` e segundo do arquivo ORIGINAL.** Onde a cena
comeca e acaba, quando um letreiro entra e sai. Nenhum agente faz conta; quem converte e
`motor/tempo.py`, e so ele.

Entre a gravacao e o filme o tempo encolhe duas vezes, e nao proporcionalmente: o corte das pausas
REMOVE pedacos em lugares especificos, e a velocidade DIVIDE o que sobra. Medido no filme
renderizado: um letreiro ancorado em 4,5s da gravacao cai em 2,658s do filme; somando o instante
cru — o jeito antigo — ele iria para 4,240s, 1,58s de erro. O erro cresce a cada pausa cortada.

`tempo.marcas()` e fonte UNICA: `tratamentos.aperta` corta por ela e `Mapa` converte por ela. Se as
duas divergirem, o letreiro entra fora de hora e nada acusa.

## Convencoes
- **Quatro agentes**: Bluey (supervisor e QA), Bandit (decupa e escreve o roteiro), Chili (estilo,
  letreiro e trilha), Bingo (mede e monta). Nenhum escreve comando de video nem HTML — preenchem
  `cenas.json` e uma lista de itens, e o motor executa.
- **Bandit e Bingo correm em paralelo.** O Bandit ouve; o Bingo MEDE (`motor/dossie.py`). O Bingo
  **nao corta nem acelera** nessa fase: medir da o mesmo resultado antes ou depois do Bandit,
  cortar jogaria fora material que o roteiro ainda pode pedir. `tests/test_dossie.py` guarda isso.
- **Duas aprovacoes**, nao tres fases: a primeira decide estrutura, estilo, letreiro e trilha; a
  segunda ve o filme leve montado. Trilha aprovada ANTES da montagem.
- **O material do usuario entra como esta.** Gerar imagem ou video por IA so se ele pedir.
- **Linguagem**: quem usa nao entende de montagem nem de audio. Sem termo tecnico solto.
  `tests/test_linguagem.py` varre isso e reprova. A lista de jargao inclui `chroma`, `overlay` e
  `b-roll` — nos .md de referencia, escreva "pano verde" e "material complementar".
- **Recusa dura**: texto normativo em `motor/limites.py`, com soma de verificacao. Quem para e o
  Bluey, antes da folha.
- **O visual e composto, nao escolhido de uma lista fechada.** Fonte + paleta + efeito, uma vez
  para a legenda e outra para o letreiro. As sete fichas fechadas sairam: elas nao deixavam a
  pessoa gostar da letra de uma e da cor de outra, que foi o que apareceu no uso.
- **A folha mostra UM EIXO POR VEZ.** As tres fontes com a mesma cor e o mesmo efeito, depois as
  cinco cores com a mesma fonte. Comparar as trinta combinacoes de uma vez nao e escolher, e
  adivinhar — e a folha estaria pedindo uma decisao que ninguem consegue tomar olhando.
- **Cada paleta tem QUATRO cores**, nao duas: a da letra e a do contorno, mais a da caixa e a da
  letra dentro dela. Amarelo com contorno preto se le sobre video; amarelo dentro de caixa amarela
  sumiria. `estilos.compor()` pega a certa conforme o efeito.
- **A folha e gerada em Python, nunca escrita pelo modelo.** O custo do projeto de origem foi
  reescrever 50 KB de HTML por rodada; agora o modelo produz so a lista de itens.
- **A folha tem SECOES, e duas naturezas de item.** `tipo: "escolha"` e cartao grande com radio,
  sem campo de observacao — escolher entre sete estilos nao e aprovar sete coisas, e oferecer
  aprovar/reprovar em cada um convida a aprovar tres. `tipo: "decisao"` e APROVADO/REPROVADO com
  espaco para o porque. **As palavras sao essas**, e as mesmas que o `registro.py` guarda: a folha
  e o registro do que foi combinado, e sinonimo deixa cada lado lembrando de um jeito.
- **A folha so publica no botao de ENVIAR.** Publicar a cada clique gasta uma versao por marcacao,
  enche quem espera de aviso — chegaram 13 de uma vez — e deixa duas publicacoes se atropelarem
  enquanto a pessoa ainda decide. O que ela marca fica no navegador ate ela mandar.
- **Escolher um resolve o bloco de escolha inteiro.** Os outros nao ficaram pendentes, ficaram
  para tras; traze-los de volta na folha seguinte faz a pessoa procurar o que nao existe.
- **Item reprovado volta com id NOVO.** A proposta nova e outra coisa a decidir; reusar o id faz
  o registro achar que ja foi respondida.

## Armadilhas de ffmpeg
- `-ss` vai ANTES do `-i`. Depois vira opcao de saida e o corte escorrega pro arquivo seguinte.
- **`-shortest` no overlay come quadros de video e deixa o audio inteiro**: 0,06 a 0,16s de
  descompasso por cena. Quem segura e `eof_action=pass`. Vale para `com_overlay`,
  `com_peca_animada` e `trocar_fundo` — nos tres a duracao e fixada por fora.
- **No concat de imagens a ultima entrada duplicada herda a duracao da anterior.** Sem `-t` na
  duracao total a faixa de legenda infla — medido, 6s viraram 10,3s.
- Antes do concat filter, normalizar `scale=1080:1920` por segmento: alguma etapa devolve 1918.
- **Audio: PCM nos segmentos, AAC so no final, `-ar 48000` em tudo, e concat FILTER.** As tres
  coisas juntas resolvem o dessync progressivo; qualquer uma sozinha nao resolve.
- `alimiter` tem `level=true` por padrao, que soma +1,5 dB DEPOIS de limitar. Sem `level=disabled`
  o pico sai em 0 dB.
- **O AAC acrescenta ~0,3 dB depois do limitador.** MEDIDO com gravacao e trilha reais: o mix sai
  do `alimiter` em -1,5 dB cravado e o mesmo audio em AAC mede -1,2 dB. E do formato, nao do
  motor. Por isso `TETO_DB = -1.5` nao e folga arbitraria — e a margem que absorve isso. Um teste
  que meca so a saida de `trilha.aplicar` (que e PCM) nao pega isto.
- Em `sidechaincompress`, a musica e comprimida e a voz e o gatilho. Invertido, renderiza sem erro.
- **O letreiro tem UMA entrada: a frase se monta palavra a palavra.** Houve sete por um tempo, e a
  escolha entre elas nao mudava nada que importasse. Duas armadilhas, as duas vistas no video
  pronto:
  - Cada pedaco e desenhado uma vez e **repetido pelos quadros que couberem**. Sem isso a entrada
    dura um quadro por palavra: numa frase de tres, um decimo de segundo, e a frase inteira aparece
    antes de dar para ver a primeira.
  - O pedaco NAO e uma frase nova: e a frase INTEIRA com N palavras visiveis (`ate_palavra`).
    Desenhar "FÁCIL" como texto proprio recalcula quebra de linha, largura e caixa — e a cada
    palavra tudo saltava de tamanho e de lugar, inclusive mudando de uma para duas linhas no fim.
    A sonda da caixa usa sempre o texto completo.
- **Letreiro animado sai em `qtrle`.** E o unico formato deste ffmpeg que guarda transparencia;
  em h264 o letreiro entra dentro de um retangulo preto. O quadro parado depois da entrada e
  repetido por `tpad`, nao gerado pelo Pillow.

## Armadilhas de custo — todas achadas com um 4K de celular de 4,7 minutos
O material de teste sintetico e pequeno, e por isso NENHUMA destas aparece nele. Todas foram
medidas com o arquivo de verdade, e as tres primeiras deixavam a skill inutilizavel.

- **`-vn` em toda leitura de audio.** Sem ele o ffmpeg decodifica o video inteiro so para jogar
  fora, e o custo vira o do tamanho da IMAGEM. Medido: `silencedetect` levou **48,2s sem `-vn`
  contra 0,3s com ele**, mesma resposta. Roda uma vez por cena.
- **Quadro se busca, nao se filtra.** Pedir quadros espalhados com `fps=` obriga a decodificar
  tudo: **passou de 2 minutos** contra **6,9s** buscando um a um com `-ss` antes do `-i`.
- **O corte ja enquadra.** `aperta` guardava os pedacos na resolucao da camera para o passo
  seguinte escalar para 1080x1920. Medido em 3s de 4K: **6,7s e 8,6 MB** mantendo o tamanho,
  **2,4s e 2,8 MB** ja enquadrado. Quem passa `area` para `aperta` deve passar `""` adiante.
- **Rotacao nos metadados.** Celular grava em pe e guarda deitado, com uma marca de -90. O ffprobe
  devolve o tamanho GUARDADO; os filtros trabalham com o girado. `probe.dimensao` corrige — sem
  isso o dossie dizia "gravado deitado" para um video em pe, e a conta do encaixe do split saia
  trocada. Para criar arquivo de teste com a marca: `-display_rotation` ANTES do `-i`
  (`-metadata:s:v:0 rotate=` e ignorado em silencio por este ffmpeg).

- **A transcricao parte numero decimal**: "Seedance 2.5" sai como `Sidense`, `2` e `.5.`, e a peca
  `.5.` nao tem letra, entao a troca palavra a palavra a pula em silencio. Chave de `trocas` com
  espaco (`"2 .5"`) funde a sequencia.
- **Folha publicada nao alcanca o disco de quem a escreveu.** `src="foto.jpg"` abre certo aqui e
  nao aparece na tela da pessoa, sem erro: ela escolhe estilo sem ver estilo. `folha.embutir`
  encolhe e vira `data:` URI; `folha.cabe` avisa antes do teto de 16 MB.
- **O roteiro e procurado no material, e a falta dele vira pergunta.** `entrada.ler` acha
  `roteiro.md`/`.txt`; `em_portugues` diz que nao achou e pede. Quem escreveu um roteiro raramente
  pensa em anexa-lo, e descobrir isso depois da decupagem pronta joga fora a etapa mais cara.
- **O Bandit confere a propria decupagem** com `motor/decupagem.py`, antes de entregar. Ele acha na
  TRANSCRICAO o que so se notaria assistindo: corte no meio de palavra, trecho abrindo ou fechando
  em conjuncao, muleta repetida entre trechos, duas tomadas da mesma frase, trechos sobrepostos.
  Numa rodada real esses quatro tipos passaram e so apareceram no video pronto.

- **O painel de camera tem duas pecas, e cada uma falha em silencio.** A barra: com o audio ja
  normalizado a -14 LUFS a escala LOG satura (85 a 95% da barra nas cinco amostras do filme real,
  praticamente parada), e RMS linear anda mas entre 10 e 28%, fino demais para ver. PICO linear vai
  de 35 a 55% -- e o unico dos tres em que da para ver o som subir e descer. E ela e alimentada
  pelo filme ANTES da trilha: com o audio final, danca com a batida da musica no silencio da fala.
  A frase: a imagem tem DUAS repeticoes lado a lado e uma repeticao e sempre maior que a tela --
  com uma so, ou com uma repeticao menor que 1080, a frase some por um instante a cada volta.
  O painel entra DEPOIS da abertura: interface de camera nao desaba junto com o zoom da lente.
- **Dois efeitos de estalo, e a diferenca entre eles e o ponto.** `abertura` abre o video e pode
  ser violenta: crash zoom de 2,4x desabando em 0,30s, canais fora de registro, croma deslocado e
  grao alto. `glitch` marca virada de assunto no MEIO da fala, entao dura um terco disso e o zoom
  e um tranco de 1,06x. Em uma emenda a cada quatro, nunca na primeira — em todas vira tique, e na
  primeira se soma a abertura e vira borra.
- **Nenhum dos filtros de estalo aceita expressao de tempo** (`rgbashift`, `chromashift`, `noise`):
  so numero fixo mais `enable`. Por isso o decaimento vai em degraus de 2 a 3 quadros. So `scale`
  aceita, e por isso o zoom e continuo.
- **Nao ha clarao branco no estalo.** Existiu numa versao e saiu: somar luz sobre uma imagem que ja
  esta se desmontando lava tudo, e o pouco que ha para ver some.

## Armadilhas de medicao
- **Nivel de audio se mede contra a FALA do proprio filme, nunca contra o silencio**: num talking
  head bem cortado o percentil de baixo do envelope JA E fala — medido, deu -0,8 dB.
- **Clipe sintetico sem ruido mente sobre nivel**: usar `clipe_fala(..., ruido_dB=-50)`.
- **Medir efeito de imagem exige material feito para a medida.** As primeiras versoes dos testes
  do estalo mediam sobre `testsrc2` e sobre clipe cinza, e nao serviam: num padrao cheio de bordas
  o grao proprio da imagem e maior que o do efeito; reduzir o quadro para 64x64 antes de medir grao
  o apaga na media; e num clipe todo cinza o deslocamento de canais nao produz cor nenhuma. O que
  serve e um clipe de REFERENCIA — fundo liso escuro com um quadrado branco no meio — onde o zoom
  vira a largura do quadrado e o grao vira a variacao do fundo.
- **Brilho medio cancela sinal.** Vale para comparar pecas E para medir contraste: uma imagem meio
  preta e meio branca tem a mesma media que uma toda cinza. Comparar pixel a pixel, num recorte
  tirado do bbox da propria peca — recorte chutado, quatro vezes maior que a tinta, baixou a
  diferenca de 72 para 15.
- **Lista de palavra proibida cresce e vira ruido.** A conferencia de decupagem comecou com trinta
  palavras "soltas" e acusava frase inteira: "Uma coisa que aprendi", "Já falei disso", "Como você
  pode ver". Ficaram so conjuncao e preposicao. E o acento FICA na comparacao: sem ele, "é" vira
  "e" e "dá" vira "da", e dois verbos viravam conjuncao.
- **Limiar so vale se foi provado dos dois lados.** Cada um tem um teste que falha quando ele sobe
  demais e outro quando desce demais.
- **Contraste: o alvo sai do material bem gravado, nao de um numero bonito.** Seis gravacoes reais
  ocupam de 163,7 a 165,7 da escala de brilho, todas sem pixel estourado — dai o alvo 165.
  **Corrigir o que ja esta bom nao e neutro**: material em 163,5 perde 0,47% dos pixels no estouro
  com esticamento de so 1,15. Por isso o limiar de "lavado" e 143, com folga ate o alvo.
- **Pano verde se detecta na BORDA do quadro, nao no quadro inteiro.** Pela fracao do quadro, croma
  apertado (33%) quase encostava em camiseta verde (20%); pela borda, 58% contra 13% — fator
  quatro. A pessoa fica no meio, o pano aparece em volta.
- **A tolerancia do corte do pano tem janela estreita dos dois lados**: de 0,04 a 0,18 o corte sai
  exato; em 0,02 sobra pano (o fundo novo cobre 37% onde devia cobrir 67); em 0,20 a figura comeca
  a ser comida e em 0,28 some. Fixado em 0,11. **O palpite inicial de 0,20 estava errado** — so a
  medicao pegou.

- **A trilha nao tem rotulo, tem medida.** A primeira versao exigia quatro nomes fixos
  (`calma.mp3`, `tensao.mp3`...) e nenhuma das quatro faixas reais tinha esses nomes — exigir nome
  canonico obriga a renomear musica baixada, e o rotulo seria um dado que ninguem conferiu. Agora
  `trilha.disponiveis()` le qualquer audio da pasta, mede, e ordena da mais parada para a mais
  agitada. **`picos_por_minuto` nao e batida por minuto**: e quantas vezes a energia sobe acima da
  media. Serve para ORDENAR as faixas entre si, nao como andamento musical.

## Armadilhas do dominio
- A transcricao diz QUAL e a palavra; a energia do audio diz ONDE cortar. Oclusiva (p t k b d g)
  tem silencio DENTRO da palavra — cortar no primeiro silencio depois de "tudo" decepa o "do".
- **A correcao de nome proprio erra para os DOIS lados, e o limiar tem janela estreita.** Alvo
  precisa de 4+ letras: alvo curto bate contra qualquer palavra. E o LIMIAR tem de ficar entre
  0,59 e 0,88, medido: a 0,50 -- o valor que ele tinha -- "sabe" (0,500), "semanas" e "verdade"
  (0,533) viravam "Seedance" na legenda queimada; acima de 0,88, "Seedence" deixa de ser
  corrigido. Fixado em 0,73.
- **Erro FONETICO nao tem limiar que pegue.** A transcricao ouviu "Sidense" onde a pessoa disse
  "Seedance": as duas grafias batem **0,267**. Comparacao de letras nao serve para som. Para esses
  casos existe `pedidas`, a troca dita palavra por palavra — e e o unico jeito.
- **Palavra sem espaco maior que a largura** (link, hashtag colada) monta caixa maior que o quadro
  e o Pillow corta a tinta em silencio — usar `arte.quebra_forcando_largura`.
- **Transcrever e a etapa cara** (modelo de 2,9GB). `legenda: false` pula ela inteira;
  `montar(..., transcrever=...)` injeta uma falsa; `tests/conftest.py` faz a suite falhar alto se
  algum teste cair na transcricao de verdade.
- Fonte licenciada nao pode ser exigida: a lista de cada opcao termina numa fonte que existe em
  todo Mac.
- **A base do letreiro sai da METRICA da fonte, nao de `corpo * entrelinha`.** As duas coisas nao
  sao a mesma: entrelinha e o espaco ENTRE linhas. MEDIDO em corpo 104: a conta antiga reservava
  114px para toda fonte, e as cinco de display ocupam de 124 a 159 — com a mais alta o texto descia
  46px ABAIXO da base, que existe justamente para o letreiro nao cair sob a interface do
  aplicativo. Ficava latente enquanto todas as fichas usavam a mesma fonte. **Mas o
  contrario tambem custou caro**: por listarem todas a MESMA primeira candidata, e ela existir na
  maquina do autor, as sete fichas usavam duas fontes no total — "fonte" era um dos tres eixos que
  separam um estilo do outro, e o unico que nao separava nada. Agora cada ficha tem fonte propria
  de letreiro E de legenda, em `assets/fontes/`. Medido na gravacao real: o par de estilos mais
  parecido saiu de 20,8 para 37,0, e `terminal` contra `neubrutal` saiu de 20,8 para 57,5.
- As gravacoes chegam 1920x1080 com o vertical dentro (barra preta nos lados). `probe.area_util`
  detecta e cropa, mas **so funciona no arquivo ORIGINAL**: o corte de fala pode devolver menos de
  1s, e ai a deteccao nao le quadro nenhum e devolve None, que quem chama entende como "ja esta
  vertical, nao mexe". **A mesma regra vale para contraste e pano verde**: sao propriedades de
  ESPACO, medidas sempre no original.

## Armadilhas da maquina
- **Este Mac guarda o bytecode do Python FORA do projeto** (`~/Library/Caches/com.apple.python`) e
  invalida por data + TAMANHO. Trocar um numero por outro do mesmo tamanho no mesmo segundo faz o
  Python rodar codigo velho calado. Verificacao do tipo "quebra e ve falhar" exige
  `PYTHONDONTWRITEBYTECODE=1`, senao o resultado da verificacao e ficcao.
- **Este disco nao distingue maiuscula de minuscula.** `f.mp4` e `F.mp4` sao o MESMO arquivo: num
  teste, o segundo sobrescreveu o primeiro e a comparacao virou o arquivo contra ele mesmo, dando
  igual com o efeito funcionando. Nome de arquivo de teste precisa diferir por mais que a caixa.
- Este ffmpeg **nao tem `drawtext`, `subtitles` nem `ass`** — so `overlay`. Todo texto sobre imagem
  sai do Pillow. `timeout` nao existe neste zsh, e nao ha ImageMagick.

## Como trabalhar aqui
- **Calibragem, nao conhecimento.** Nao "simplificar" numero medido, e nao mudar constante para um
  teste passar. Se a constante estiver errada, medir de novo e mostrar o numero.
- **Clipe sintetico nao substitui gravacao real.** Tres defeitos so apareceram com material do
  usuario: o `alimiter` que nao segurava o teto, o recorte do split que pegava a faixa errada, e a
  `area_util` cega. `tests/test_laudo_real.py` roda contra as gravacoes de verdade e se pula
  sozinho quando elas nao existem.
- **Teste de unidade nao substitui o caminho inteiro.** Outros dois so apareceram rodando o
  programa como o usuario roda: a referencia de nivel da emenda e o comando da documentacao, que
  nao acha o motor de outra pasta.

Mais armadilhas medidas, com o numero e a rodada de erro de cada uma: `docs/DIARIO.md`
Desenho: `docs/superpowers/specs/2026-08-28-skill-video-talking-head-design.md`
