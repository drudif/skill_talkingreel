# skill_talkingreel

A skill **talking reel: done**: pega um video de talking head gravado pelo usuario e devolve um
vertical montado, com ritmo, arte e legenda queimada, pronto pra Instagram e TikTok. Python +
ffmpeg + mlx-whisper + Pillow — legenda e letreiro sao texto vetorial, nunca imagem de IA.
**Estado: motor pronto — montagem, arte e legenda. Falta a folha de aprovacao e os agentes.**

## Comandos
- `python3 -m motor <cenas.json> <saida.mp4>` — monta o filme e imprime o laudo
- `.venv/bin/pytest` — 176 testes, ~2min. `TESTE_LENTO=1` liga o unico que roda o modelo

## Convencoes
- **Quatro agentes**: Bluey (principal e QA), Bandit (roteiro), Chili (arte e som), Bingo (montagem).
  Nenhum deles escreve comando de video — preenchem um `cenas.json` e o motor executa.
- **O material do usuario entra como esta.** Gerar imagem ou video por IA so se ele pedir.
- **Tres fases**: estrutura, arte e trilha, corte. O aprovado ou descartado SAI da folha. Trilha
  aprovada ANTES da montagem; efeito sonoro entra DURANTE.
- **Linguagem**: sem termo tecnico solto, sem metafora. Checklist enxuto e esperar resposta.
- **Recusa dura**: texto normativo em `motor/limites.py`, com salvaguarda contra remocao silenciosa.

## Armadilhas
- **Calibragem, nao conhecimento.** Cada constante custou uma rodada de erro no `agentes-ginsu`;
  nao "simplificar" numero medido. E `-ss` vai ANTES do `-i`, senao o corte escorrega de arquivo.
- **`-shortest` no overlay come quadros e deixa o audio inteiro**: 0,06 a 0,16s por cena, pior na
  cena longa. Quem segura e `eof_action=pass`.
- **No concat de imagens a ultima entrada duplicada herda a duracao da anterior.** Sem `-t` a faixa
  de legenda infla (6s viraram 10,3s) e o filme sai curto.
- A transcricao diz QUAL e a palavra; a energia diz ONDE cortar. Oclusiva (p t k b d g) tem silencio
  DENTRO da palavra — cortar no primeiro silencio depois de "tudo" decepa o "do". E o roteiro so
  conserta nome proprio, com alvo de 4+ letras: alvo curto bate 0,80 contra qualquer palavra e
  numa rodada sairam 19 correcoes, todas erradas.
- **`entra`/`dura` do letreiro contam na cena JA PRONTA**, depois do corte e da velocidade.
- **Palavra sem espaco maior que a largura** faz caixa maior que o quadro e o Pillow corta em
  silencio — usar `arte.quebra_forcando_largura`.
- **Transcrever e a etapa cara** (2,9GB). `legenda: false` pula; `montar(..., transcrever=...)`
  injeta uma falsa; `tests/conftest.py` faz a suite falhar se cair nela sem querer.
- `alimiter` tem `level=true` por padrao, que soma +1,5 dB DEPOIS de limitar — sem `level=disabled`
  o pico sai em 0 dB. Fonte licenciada nao pode ser exigida: `estilos.fonte()` cai numa do sistema.

Desenho: `docs/superpowers/specs/2026-08-28-skill-video-talking-head-design.md` · Diario: `docs/DIARIO.md`
