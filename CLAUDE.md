# skill_talkingreel — a skill "talking reel: done"

Pega um video de talking head do usuario e devolve um vertical montado, com ritmo, arte e legenda
queimada, pronto pra Instagram e TikTok. Python + ffmpeg + mlx-whisper + Pillow; legenda e letreiro
sao texto vetorial, nunca imagem de IA.
**Estado: completa — motor, laudo, folha, SKILL.md e os quatro agentes.**

> Este arquivo passa das 40 linhas de proposito, com aval do Drudi. Quase toda linha da secao de
> armadilhas custou uma rodada de erro num video de verdade, e o modo de falhar de quase todas e
> silencioso: o video sai errado sem ninguem ver. Aqui o teto vale menos que o prejuizo.

## Comandos
- `PYTHONPATH=<esta pasta> python3 -m motor cenas.json saida.mp4`, de dentro da pasta do
  trabalho — monta e imprime o laudo. **Sem o PYTHONPATH o Python nao acha o motor.**
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest` — 299 testes, ~5min. `TESTE_LENTO=1` liga o unico
  que roda o modelo de transcricao; `GRAVACOES_REAIS=<pasta>` aponta as gravacoes de verdade.

## Convencoes
- **Quatro agentes**: Bluey (principal e QA), Bandit (roteiro), Chili (arte e som), Bingo (montagem).
  Nenhum escreve comando de video nem HTML — preenchem `cenas.json` e uma lista de itens, e o
  motor executa. Toda a calibragem mora no codigo medido, nao no prompt.
- **O material do usuario entra como esta.** Gerar imagem ou video por IA so se ele pedir.
- **Tres fases**: estrutura, arte e trilha, corte. O aprovado ou descartado SAI da folha. Trilha
  aprovada ANTES da montagem; efeito sonoro entra DURANTE.
- **Linguagem**: quem usa nao entende de montagem nem de audio. Sem termo tecnico solto — se for
  inevitavel, explicar na mesma frase. Sem metafora. Checklist enxuto e esperar resposta.
  `tests/test_linguagem.py` varre isso e reprova.
- **Recusa dura**: texto normativo em `motor/limites.py`, com soma de verificacao e salvaguarda
  contra remocao silenciosa. Quem para e o Bluey, antes da folha.
- **A folha e gerada em Python, nunca escrita pelo modelo.** O custo do projeto de origem foi
  reescrever 50 KB de HTML por rodada; agora o modelo produz so a lista de itens.

## Armadilhas de ffmpeg
- `-ss` vai ANTES do `-i`. Depois vira opcao de saida e o corte escorrega pro arquivo seguinte.
- **`-shortest` no overlay come quadros de video e deixa o audio inteiro**: 0,06 a 0,16s de
  descompasso por cena, pior na cena LONGA. Quem segura e `eof_action=pass`.
- **No concat de imagens a ultima entrada duplicada herda a duracao da anterior.** Sem `-t` na
  duracao total a faixa de legenda infla — medido, 6s viraram 10,3s — e o filme sai curto.
- Antes do concat filter, normalizar `scale=1080:1920` por segmento: alguma etapa devolve 1918.
- **Audio: PCM nos segmentos, AAC so no final, `-ar 48000` em tudo, e concat FILTER.** As tres
  coisas juntas resolvem o dessync progressivo; qualquer uma sozinha nao resolve.
- `alimiter` tem `level=true` por padrao, que soma +1,5 dB DEPOIS de limitar. Sem `level=disabled`
  o pico sai em 0 dB. So aparece com material perto do teto — tom baixo passa nas duas versoes.
- Em `sidechaincompress`, a musica e comprimida e a voz e o gatilho. Invertido, renderiza sem erro.

## Armadilhas de medicao
- **Nivel de audio se mede contra a FALA do proprio filme, nunca contra o silencio**: num talking
  head bem cortado o percentil de baixo do envelope JA E fala — medido, deu -0,8 dB.
- **Clipe sintetico sem ruido mente sobre nivel**: o silencio e zero digital, o piso vira -120 dB
  e qualquer limiar ate 120 "passa" sem medir nada. Usar `clipe_fala(..., ruido_dB=-50)`.
- **Brilho medio cancela sinal.** Contorno preto contra preenchimento amarelo da +82 e -123 de
  luma, que se anulam. Comparar pixel a pixel, num recorte tirado do bbox da propria peca — recorte
  chutado, quatro vezes maior que a tinta, baixou a diferenca de 72 para 15.
- **Limiar so vale se foi provado dos dois lados.** Cada um tem um teste que falha quando ele sobe
  demais e outro quando desce demais. Sem isso o numero e chute com aparencia de medida.

## Armadilhas do dominio
- A transcricao diz QUAL e a palavra; a energia do audio diz ONDE cortar. Oclusiva (p t k b d g)
  tem silencio DENTRO da palavra — cortar no primeiro silencio depois de "tudo" decepa o "do".
- **O roteiro so conserta nome proprio, e o alvo precisa de 4+ letras.** Alvo curto bate 0,80
  contra qualquer palavra da fala: numa rodada sairam 19 correcoes, todas erradas.
- **`entra`/`dura` do letreiro contam na cena JA PRONTA**, depois do corte de silencio e da
  velocidade. Ler o instante da gravacao crua poe o letreiro no lugar errado, com erro crescente.
- **Palavra sem espaco maior que a largura** (link, hashtag colada) monta caixa maior que o quadro
  e o Pillow corta a tinta em silencio — usar `arte.quebra_forcando_largura`.
- **Transcrever e a etapa cara** (modelo de 2,9GB). `legenda: false` pula ela inteira;
  `montar(..., transcrever=...)` injeta uma falsa; `tests/conftest.py` faz a suite falhar alto se
  algum teste cair na transcricao de verdade.
- Fonte licenciada nao pode ser exigida: `estilos.fonte()` cai numa fonte do sistema.
- As gravacoes chegam 1920x1080 com o vertical dentro (barra preta nos lados). `probe.area_util`
  detecta e cropa, mas **so funciona no arquivo ORIGINAL**: o corte de fala pode devolver menos de
  1s, e ai a deteccao nao le quadro nenhum e devolve None, que quem chama entende como "ja esta
  vertical, nao mexe". Enquadramento e propriedade de espaco, nao de tempo.

## Armadilhas da maquina
- **Este Mac guarda o bytecode do Python FORA do projeto** (`~/Library/Caches/com.apple.python`) e
  invalida por data + TAMANHO. Trocar um numero por outro do mesmo tamanho no mesmo segundo faz o
  Python rodar codigo velho calado. Verificacao do tipo "quebra e ve falhar" exige
  `PYTHONDONTWRITEBYTECODE=1`, senao o resultado da verificacao e ficcao.
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
  programa como o usuario roda: a referencia de nivel da emenda (que so quebra quando o filme e
  quase todo fala) e o comando da documentacao, que nao acha o motor de outra pasta.

Mais armadilhas medidas, com o numero e a rodada de erro de cada uma: `docs/DIARIO.md`
Desenho: `docs/superpowers/specs/2026-08-28-skill-video-talking-head-design.md`
