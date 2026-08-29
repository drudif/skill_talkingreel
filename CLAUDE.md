# skill_talkingreel — a skill "talking reel: done"

Pega um video de talking head do usuario e devolve um vertical montado, com ritmo, arte e legenda
queimada, pronto pra Instagram e TikTok. Python + ffmpeg + mlx-whisper + Pillow; legenda e letreiro
sao texto vetorial, nunca imagem de IA.
**Estado: completa — motor, laudo, folha, SKILL.md e os quatro agentes.**

## Comandos
- `PYTHONPATH=<esta pasta> python3 -m motor cenas.json saida.mp4`, de dentro da pasta do
  trabalho — monta e imprime o laudo. **Sem o PYTHONPATH o Python nao acha o motor.**
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest` — 285 testes, ~5min

## Convencoes
- **Quatro agentes**: Bluey (principal e QA), Bandit (roteiro), Chili (arte e som), Bingo (montagem).
  Nenhum escreve comando de video nem HTML — preenchem `cenas.json` e uma lista de itens.
- **O material do usuario entra como esta.** Gerar imagem ou video por IA so se ele pedir.
- **Tres fases**: estrutura, arte e trilha, corte. O aprovado ou descartado SAI da folha. Trilha
  aprovada ANTES da montagem; efeito sonoro entra DURANTE.
- **Linguagem**: sem termo tecnico solto, sem metafora. Checklist enxuto e esperar resposta.
  **Recusa dura**: texto normativo em `motor/limites.py`, com salvaguarda contra remocao.

## Armadilhas
- **Calibragem, nao conhecimento.** Cada constante custou uma rodada de erro no `agentes-ginsu`; nao
  "simplificar" numero medido. `-ss` vai ANTES do `-i`, senao o corte escorrega de arquivo.
- **`-shortest` no overlay come quadros e deixa o audio inteiro** (0,06 a 0,16s por cena, pior na
  longa): usar `eof_action=pass`. E no concat de imagens a ultima entrada duplicada herda a duracao
  da anterior — sem `-t` a faixa de legenda infla e o filme sai curto.
- **Nivel de audio se mede contra a FALA do proprio filme, nunca contra o silencio**: num talking
  head bem cortado o percentil de baixo do envelope JA E fala. E clipe sintetico sem ruido mente —
  silencio de zero digital poe o piso em -120 dB e qualquer limiar "passa" sem medir nada; usar
  `clipe_fala(..., ruido_dB=-50)`.
- A transcricao diz QUAL e a palavra; a energia diz ONDE cortar. Oclusiva (p t k b d g) tem silencio
  DENTRO da palavra — cortar no primeiro silencio depois de "tudo" decepa o "do". E o roteiro so
  conserta nome proprio, com alvo de 4+ letras: alvo curto bate 0,80 contra qualquer palavra, e
  numa rodada sairam 19 correcoes, todas erradas.
- **`entra`/`dura` do letreiro contam na cena JA PRONTA**, depois do corte e da velocidade. E palavra
  sem espaco maior que a largura faz caixa maior que o quadro, cortada em silencio pelo Pillow —
  usar `arte.quebra_forcando_largura`.
- **Verificar quebrando o codigo exige `PYTHONDONTWRITEBYTECODE=1`** neste Mac: o bytecode fica fora
  do projeto e invalida por data + TAMANHO, entao trocar um numero por outro do mesmo tamanho roda
  o codigo velho calado (o porque, medido, esta no diario).
- **Transcrever e a etapa cara** (2,9GB): `legenda: false` pula, `montar(..., transcrever=...)`
  injeta uma falsa, e `tests/conftest.py` faz a suite falhar se cair nela sem querer.

Mais armadilhas medidas: `docs/DIARIO.md` · Desenho: `docs/superpowers/specs/2026-08-28-skill-video-talking-head-design.md`
