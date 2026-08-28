# skill_talkingreel

A skill **talking reel: done**. Pega um video de talking head gravado pelo usuario e devolve um
vertical montado, com ritmo, arte e legenda queimada, pronto pra Instagram e TikTok.
**Estado: motor do nucleo pronto — cena cheia, split com ancora, ritmo, trilha, laudo.
Falta arte, legenda, folha e os agentes.**

## Stack
Python + ffmpeg (motor de montagem) · mlx-whisper (transcricao com timestamp por palavra) ·
Pillow + fonte da casa (legenda e letreiro sao texto vetorial) · artefato HTML (folha de aprovacao).

## Comandos
- `python3 -m motor <cenas.json> <saida.mp4>` — monta o filme e imprime o laudo
- `.venv/bin/pytest` — 77 testes do motor (~60s, monta video de verdade)

## Convencoes
- **Quatro agentes**: Bluey (principal e QA), Bandit (roteiro), Chili (arte e som), Bingo (montagem).
- **Os agentes nao escrevem comando de video.** Eles preenchem uma lista de cenas; um script fixo
  executa. Toda a calibragem mora no script, nao no prompt.
- **O material do usuario entra como esta.** Gerar imagem ou video por IA so acontece se ele pedir.
- **Tres fases de aprovacao**: estrutura, arte e trilha, corte. Uma folha por fase, e o que foi
  aprovado ou descartado SAI da folha.
- **Linguagem**: quem usa nao entende de montagem, edicao ou audio. Sem termo tecnico; se for
  inevitavel, explicar em uma frase. Sem metafora. Sem verborragia. Fechar com checklist enxuto
  e esperar resposta.
- A trilha e aprovada ANTES da montagem; o efeito sonoro entra DURANTE.
- **Recusa dura**: a skill nao produz, monta, legenda nem embala material com exploracao
  sexual de menores, apologia de violencia, misoginia, racismo ou discurso de odio. Vale
  para a gravacao do proprio usuario e para o que a skill gera. Quem para e o Bluey, antes
  da folha. **Nao limpa em silencio** — diz o que achou e onde, em uma frase, sem sermao.
  Nao vira classificador automatico: sem score, sem lista de palavras. Material ambiguo
  (ironia, citacao critica, relato de vitima) nao e alvo — na duvida, pergunta.

## Armadilhas
- **O que faz o video funcionar e calibragem, nao conhecimento.** Cada constante do desenho custou
  uma rodada de erro no `conteudo/agentes-ginsu`. Nao "simplificar" numero medido.
- `-ss` vai ANTES do `-i`. Depois do `-i` ele vira opcao de saida e o corte escorrega pro arquivo
  seguinte.
- A transcricao diz QUAL e a palavra; a energia do audio diz ONDE cortar. Oclusiva (p t k b d g)
  tem silencio DENTRO da palavra — cortar no primeiro silencio depois de "tudo" decepa o "do".
- MiniMax H3 com referencia de video NAO edita, regenera. Seedance 2.5 em `video_edit` edita.
- O `alimiter` tem `level=true` por padrao, e essa opcao soma +1.5 dB DEPOIS de limitar,
  desfazendo o trabalho. Sem `level=disabled` o pico final sai em 0 dB. So aparece com
  material perto do teto — tom baixo passa nas duas versoes.

Desenho completo: `docs/superpowers/specs/2026-08-28-skill-video-talking-head-design.md`
Historico de decisoes: `docs/DIARIO.md`
