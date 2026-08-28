# skill_talkingreel

A skill **talking reel: done**. Pega um video de talking head gravado pelo usuario e devolve um
vertical montado, com ritmo, arte e legenda queimada, pronto pra Instagram e TikTok.
**Estado: so o desenho existe. Nenhum codigo escrito ainda.**

## Stack
Python + ffmpeg (motor de montagem) · mlx-whisper (transcricao com timestamp por palavra) ·
Pillow + fonte da casa (legenda e letreiro sao texto vetorial) · artefato HTML (folha de aprovacao).

## Comandos
- ainda nao ha. O motor sai do plano de implementacao.

## Convencoes
- **Quatro agentes**: Bluey (principal e QA), Bandit (roteiro), Chili (arte e som), Bingo (montagem).
- **Os agentes nao escrevem comando de video.** Eles preenchem uma lista de cenas; um script fixo
  executa. Toda a calibragem mora no script, nao no prompt.
- **A skill nao reescreve fala.** A selecao e subtrativa: escolhe trechos e apaga outros.
- **O material do usuario entra como esta.** Gerar imagem ou video por IA so acontece se ele pedir.
- **Tres fases de aprovacao**: estrutura, arte e trilha, corte. Uma folha por fase, e o que foi
  aprovado ou descartado SAI da folha.
- **A folha mostra o fato medido, nao a opiniao do agente.** "A legenda aparece 0,2s depois da
  palavra", nao "ficou bom".
- **Linguagem**: quem usa nao entende de montagem, edicao ou audio. Sem termo tecnico; se for
  inevitavel, explicar em uma frase. Sem metafora. Sem verborragia. Fechar com checklist enxuto
  e esperar resposta.
- A trilha e aprovada ANTES da montagem; o efeito sonoro entra DURANTE.

## Armadilhas
- **O que faz o video funcionar e calibragem, nao conhecimento.** Cada constante do desenho custou
  uma rodada de erro no `conteudo/agentes-ginsu`. Nao "simplificar" numero medido.
- `-ss` vai ANTES do `-i`. Depois do `-i` ele vira opcao de saida e o corte escorrega pro arquivo
  seguinte.
- A transcricao diz QUAL e a palavra; a energia do audio diz ONDE cortar. Oclusiva (p t k b d g)
  tem silencio DENTRO da palavra — cortar no primeiro silencio depois de "tudo" decepa o "do".
- Audio sem compressao nos segmentos, comprimido so no final, taxa de amostragem igual em tudo, e
  juntar por filtro (nao por lista). As quatro coisas juntas resolvem o dessync; nenhuma sozinha.
- **A folha encarece pelo codigo da pagina, nao pelo peso do arquivo.** No projeto de origem eram
  50 KB reescritos a cada rodada.
- MiniMax H3 com referencia de video NAO edita, regenera. Seedance 2.5 em `video_edit` edita.

Desenho completo: `docs/superpowers/specs/2026-08-28-skill-video-talking-head-design.md`
Historico de decisoes: `docs/DIARIO.md`
