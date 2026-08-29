# Corte rapido, fora das tres fases

**Isto e avulso — nao faz parte das tres fases da skill.** Use so quando a pessoa pedir exatamente
isto, e nada mais: so acelerar, ou so tirar os silencios, sem montar o video, sem legenda, sem
escolher estilo.

**As tres fases nao usam estes comandos.** Dentro delas, o motor corta o silencio olhando a
energia do audio — o volume em cada instante — e ainda comprime as pausas que sobram no meio da
propria fala. Isso da um corte melhor do que so detectar silencio. **Rodar um destes comandos
antes das tres fases atrapalha**: tira a margem que o motor precisa para achar onde a fala comeca
e onde termina, e o resultado final sai com palavras cortadas nas pontas.

## Acelerar sem mudar a voz

Deixa o video mais rapido sem deixar a voz da pessoa aguda ou de desenho animado.

```bash
ffmpeg -i entrada.mp4 -filter:v "setpts=PTS/1.5" -filter:a "atempo=1.5" saida.mp4
```

O numero `1.5` e a velocidade: 1.5 quer dizer 50% mais rapido. Os dois numeros do comando — o da
imagem e o do som — tem de ser sempre o mesmo, senao a boca da pessoa se descola da voz.

Este comando so aceita um numero entre 0.5 e 2.0 de cada vez. Para ir mais rapido que isso, repete
o pedaco do som mais de uma vez, multiplicando os numeros. Por exemplo, para triplicar a
velocidade: `atempo=2.0,atempo=1.5` — porque 2.0 vezes 1.5 da 3.0. O pedaco da imagem
(`setpts=PTS/3.0`) muda direto, sem precisar repetir.

## Tirar so os silencios

Encontra os trechos sem fala para depois cortar cada um e juntar o que sobrou, com uma pausa curta
no lugar de cada silencio.

```bash
ffmpeg -i entrada.mp4 -af "silencedetect=noise=-30dB:d=0.3" -f null -
```

Este comando so aponta onde estao os silencios — cortar cada pedaco e juntar de novo e um passo
separado. E ele erra pelas bordas: como decide olhando so o volume de cada instante, deixa uma
sobra de silencio grudada no comeco e no fim de cada corte. E exatamente por isso que o motor, nas
tres fases, usa o outro metodo, o de cima: ele olha a energia da fala inteira, nao um limite fixo
de volume.
