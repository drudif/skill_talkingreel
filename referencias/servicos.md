# Editar o video com IA — medido, nao suposto

**So entra em jogo se a pessoa pedir.** O padrao e o material dela entrar como esta, sem passar
por nenhum destes servicos.

| tarefa | servico | resultado medido |
|---|---|---|
| editar o proprio video | Seedance 2.5, modo de edicao | muda entre 7,5 e 19,7 numa escala de 255 — a variacao normal de uma cor entre dois quadros vizinhos. Edita de verdade. |
| trocar a boca no proprio video | Veed Sync 2.0, no Magnific | 23 de mudanca na boca, 2 no resto do quadro |
| **nao use para editar** | MiniMax H3 com referencia de video | 13 a 99 de mudanca no quadro inteiro: **regenera** o rosto da pessoa em vez de so editar, e desloca o audio em 0,95 segundo |
| **nao aceita video** | Kling 3.0 | so recebe uma imagem inicial, nao um video |

A escala de 255 mede o quanto a cor de cada ponto da imagem mudou de um quadro para o outro: 0 e
nada, 255 e o maximo. Numero baixo quer dizer que so o pedido foi alterado; numero alto quer dizer
que o servico refez a imagem quase inteira.

Toda troca de imagem por um destes servicos passa por um teste antes de entrar no video final: o
motor compara o resultado com a gravacao original e informa a diferenca. Quem decide com esse
numero e o Bluey, nao a impressao de quem so olhou.

## Armadilhas de pedido, ja pagas

- **Marcacao de tempo so e obedecida se for dita das duas formas: em segundos e em porcentagem do
  video.** "Aos 2 segundos" sozinho e ignorado; "aos 2 segundos, que e 40% do video" funciona.
- **O gerador de imagem corta os pes da pessoa** se o pedido nao disser que ela ocupa 55% da
  altura do quadro.
- Para o servico nao mudar o que ja existe na imagem, o pedido precisa dizer isso com forca:
  **incluir** uma coisa nova, nunca **refazer** a imagem inteira.

## Para trilha e efeito sonoro

| servico | musica | efeito sonoro | limpar a voz |
|---|---|---|---|
| Magnific | sim | sim | sim |
| Higgsfield | sim | sim | nao |
| ElevenLabs direto | sim | — | — |

Para efeito sonoro gratuito, o Freesound e a opcao solida. Para musica gratuita, os bancos livres
tem pouco acervo e uma regra de credito que muda de faixa para faixa — nao contar com eles para um
trabalho serio.
