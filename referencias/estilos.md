# Como o texto aparece: fonte, cor e efeito

O texto do vídeo tem duas partes, e cada uma escolhe em separado:

- a **legenda**, que é pequena, corrida, e acompanha tudo o que a pessoa fala
- o **letreiro**, que é a frase grande que aparece na tela em alguns momentos

Para cada uma vão três escolhas: a **fonte**, a **paleta** e o **efeito**.

## A fonte da legenda — três

Legenda é texto pequeno, lido de relance enquanto a pessoa fala. Por isso as
três são de leitura, e nenhuma é de chamar atenção.

| chave | como parece |
|---|---|
| `sem serifa` | Letra limpa, sem os pezinhos. A mais neutra das três. |
| `serifa` | Letra com pezinhos, como livro. Fica mais calma e séria. |
| `monoespaço` | Todas as letras ocupam a mesma largura, como máquina de escrever. Puxa para o técnico. |

## A fonte do letreiro — cinco

Letreiro é para ser visto, não lido com calma. As cinco são de chamar atenção.

| chave | como parece |
|---|---|
| `estreita` | Muito alta e apertada. Cabe frase grande sem diminuir a letra. |
| `estreita leve` | Alta e apertada como a outra, mas com o traço mais fino. |
| `pesada` | Grossa e larga, sem serifa. A que mais ocupa espaço. |
| `revista` | Serifa moderna, com traço grosso e fino bem diferentes. Ar de capa de revista. |
| `editorial` | Serifa mais macia, menos dura que a de revista. |

## A paleta — cinco, e valem para as duas

| chave | como parece |
|---|---|
| `branco e preto` | Letra branca com contorno preto, ou caixa branca com letra preta. É o que quase todo vídeo usa, e funciona sobre qualquer imagem. |
| `amarelo` | Amarelo forte com contorno preto. A que mais para o dedo de quem rola a tela. |
| `preto e branco` | O contrário da primeira: letra preta com contorno branco, ou caixa preta com letra branca. Mais sóbrio. |
| `verde` | Verde claro sobre contorno escuro. Puxa para tecnologia. |
| `rosa` | Rosa forte com contorno escuro. Criativo, com pegada de arte impressa. |

**Cada paleta tem duas metades**, e por um motivo prático: a cor que se lê bem
com contorno não é a mesma que se lê bem dentro de uma caixa. Amarelo com
contorno preto funciona sobre vídeo; amarelo dentro de caixa amarela sumiria.
O motor troca sozinho conforme o efeito escolhido.

## O efeito — dois, e valem para as duas

| chave | o que acontece |
|---|---|
| `contorno` | A letra ganha um traço escuro em volta, como legenda de televisão. A imagem do vídeo aparece atrás do texto. |
| `caixa` | A letra fica dentro de um retângulo cheio. Tapa a imagem naquele pedaço, e é o que se lê melhor sobre fundo bagunçado. |

**São só esses dois porque são os dois que sobrevivem a imagem em movimento.**
Sombra suave, brilho e degradê somem assim que o fundo muda de cor — e o fundo
aqui é o rosto de alguém se mexendo.

## Como a pessoa escolhe

Ela não compara as trinta combinações de uma vez: isso não é escolher, é
adivinhar. A folha mostra **um eixo por vez** — as três fontes com a mesma cor e
o mesmo efeito, depois as cinco cores com a mesma fonte, depois os dois efeitos.
Cada tela muda uma coisa só. Quem gera isso é `motor/previa.py`.

Cor exata, nome de arquivo de fonte e tamanho moram em `motor/estilos.py`.
