# As trilhas que vêm com a skill

Ponha aqui as músicas que a Chili pode propor quando a pessoa não mandar uma própria.

**O nome do arquivo não importa.** Pode ser o nome que veio do site onde você baixou, com carimbo
de data e tudo — a skill lê qualquer `.mp3`, `.m4a`, `.wav`, `.aac` ou `.flac` que estiver nesta
pasta, e limpa o carimbo sozinha ao mostrar o nome.

O que ela ignora: arquivo que não é áudio, arquivo que não abre, e faixa com menos de 5 segundos
— um efeito sonoro solto na pasta não pode virar opção de trilha.

## Como a Chili escolhe sem ouvir

Ela não ouve. Então a skill **mede** cada faixa e mostra as opções da mais parada para a mais
agitada, com a duração de cada uma. Isso, mais o nome que você deu ao arquivo, é o que ela tem
para decidir — e é o que aparece na folha para a pessoa aprovar.

Para ver o que a skill está entendendo das suas faixas:

```bash
python3 -c "from motor import trilha; print(trilha.em_portugues(trilha.disponiveis()))"
```

Se o nome do arquivo não disser nada sobre a música, renomeie para algo que diga. É o único
rótulo que existe.

## O que a skill faz com a faixa escolhida

A música entra abaixo da voz e **abaixa sozinha quando a pessoa fala**. O volume já está
calibrado — não é preciso preparar a faixa de nenhum jeito especial.

Faixa mais curta que o vídeo **repete** até o fim, e a folha avisa quantas vezes antes de a pessoa
escolher. Faixa mais longa é cortada.

## Direitos

Ponha aqui só música que possa ser publicada em vídeo no Instagram e no TikTok. Faixa com direito
autoral fechado derruba o vídeo, e o problema aparece depois de publicar, não aqui.
