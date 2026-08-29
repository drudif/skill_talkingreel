# O contrato: o arquivo `cenas.json`

Este arquivo é a única coisa que os agentes escrevem. O motor lê e executa.

## Exemplo completo

```json
{
  "velocidade": 1.15,
  "estilo": "brutalista",
  "legenda": true,
  "legenda_split": "esquerda",
  "proprios": ["Ginsu", "Anthropic"],
  "trilha": "audio/trilha.mp3",
  "cenas": [
    {"n": 1, "trat": "cheia", "arquivo": "gravacoes/take-01.mov", "teto": 6.0,
     "letreiro": {"texto": "COMENTA QUERO", "entra": 1.1, "dura": 1.8,
                  "base": 1400, "box": false}},
    {"n": 2, "trat": "split", "arquivo": "gravacoes/take-02.mov",
     "topo": {"arquivo": "broll/faca.mp4", "ancora": 0.3}}
  ]
}
```

## Os campos da produção

| campo | precisa? | o que é |
|---|---|---|
| `velocidade` | não | quanto o filme acelera. 1.15 é o padrão, e não se nota |
| `estilo` | não | uma das sete fichas. Padrão `brutalista` |
| `legenda` | não | queimar a legenda no fim. Padrão `true`. **Desligar pula a transcrição inteira**, que é a etapa mais demorada |
| `legenda_split` | não | onde a legenda fica quando a tela está dividida em duas: `esquerda`, `direita` ou `centro`. Padrão `esquerda` |
| `proprios` | não | nomes que a transcrição costuma errar, escritos do jeito certo. **Só nome próprio, e só com 4 letras ou mais** |
| `trilha` | não | a música de fundo. Ela abaixa sozinha quando a pessoa fala. Sem este campo, o filme sai sem música |
| `cenas` | sim | a lista de cenas, em ordem |

## Os campos de cada cena

| campo | precisa? | o que é |
|---|---|---|
| `n` | sim | o número da cena |
| `trat` | sim | `cheia` (só a pessoa) ou `split` (material extra em cima, pessoa embaixo) |
| `arquivo` | sim | a gravação, relativa à pasta do `cenas.json` |
| `velocidade` | não | troca a velocidade só nesta cena. Sem este campo, vale a velocidade geral da produção |
| `teto` | não | limite de duração, em segundos, para essa cena |
| `topo` | só no split | `{"arquivo": ..., "ancora": 0.0 a 1.0}`. A âncora escolhe que parte da imagem fica visível: 0 é o topo, 1 é o pé |
| `letreiro` | não | texto grande sobre a imagem |

## O letreiro

| campo | precisa? | o que é |
|---|---|---|
| `texto` | sim | o que aparece escrito |
| `entra` | não | quando aparece. Padrão 0 |
| `dura` | não | quanto tempo fica. Sem isso, fica até o fim da cena |
| `base` | não | onde o texto se apoia na altura da tela |
| `box` | não | caixa sólida atrás do texto. Padrão sem caixa |

**A armadilha do tempo do letreiro.** `entra` e `dura` contam na cena já pronta — depois do corte
de silêncio e depois da velocidade. Não são o instante da gravação crua: as duas etapas mudam a
escala do tempo, e não de forma proporcional. O jeito certo de achar o número certo: monte o filme
uma vez, olhe o `cenas-mapa.json` que sai junto, e some `entra` ao `ini` daquela cena.
