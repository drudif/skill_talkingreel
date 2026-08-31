# As trilhas que vêm com a skill

Quatro faixas, para a Chili escolher uma quando a pessoa não mandou música própria.

**Ainda não estão aqui.** Ponha os quatro arquivos nesta pasta, em `.mp3` ou `.m4a`, com estes
nomes — a Chili procura por eles e `tests/test_trilhas.py` confere:

| arquivo | quando serve |
|---|---|
| `calma.mp3` | conversa, opinião, relato — a música fica atrás e não disputa |
| `tensao.mp3` | quando o assunto tem virada, problema, alerta |
| `animada.mp3` | humor, novidade, convite — ritmo para a frente |
| `neutra.mp3` | conteúdo técnico ou institucional, onde a música é só base |

## O que a skill faz com elas

A música entra abaixo da voz e **abaixa sozinha quando a pessoa fala**. Quem cuida disso é
`motor/trilha.py`, e o volume já está calibrado — não é preciso preparar a faixa de nenhum jeito
especial.

Faixa mais curta que o vídeo repete até o fim. Faixa mais longa é cortada.

## Direitos

Ponha aqui só música que possa ser publicada em vídeo no Instagram e no TikTok. Faixa com direito
autoral fechado derruba o vídeo, e o problema aparece depois de publicar, não aqui.
