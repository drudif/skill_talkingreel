"""Constantes calibradas. Cada numero aqui custou uma rodada de erro no projeto
`conteudo/agentes-ginsu`. Nao "arredondar" nem "simplificar" sem medir de novo."""

W, H, FPS = 1080, 1920, 30      # vertical de Reels/TikTok

DIVISORIA = 807                 # linha do split, medida no pixel. A janela de cima
                                # fica 1080x807 (deitada); a de baixo, 1080x1113
SPLIT_TETO = 380                # quanto do teto sai no crop da janela de baixo.
                                # Sem isso o rosto nao cabe na janela

VELOCIDADE = 1.15               # padrao dos talking heads

RESPIRO_IN = 0.06               # folga antes da primeira palavra
RESPIRO_OUT = 0.32              # folga depois da ultima. Maior que a entrada porque
                                # a cauda da palavra decai devagar e colar corta o som

PAUSA_MAX = 0.22                # silencio interno acima disso e comprimido
PAUSA_FICA = 0.10               # para este tamanho

DB_PAUSA = -45                  # limiar para achar pausa interna. A -34 dB a cauda
                                # da palavra era lida como silencio e sumia
DB_ENVELOPE = -32               # limiar do envelope de energia nas pontas

# --- contraste da imagem ---
CONTRASTE_BASE = 1.08    # o realce que TODO material recebe, de sempre.
CONTRASTE_ALVO = 165     # para onde levar a imagem lavada. MEDIDO em seis
                         # gravacoes reais de talking head: a faixa de brilho
                         # que elas ocupam ficou entre 163,7 e 165,7 nas seis,
                         # nenhuma com pixel estourado. O alvo e onde o material
                         # BEM gravado ja vive, nao um numero escolhido.
CONTRASTE_LAVADO = 143   # abaixo desta faixa a imagem e corrigida. DERIVADO do
                         # alvo: 165/1,15 = 143, e 1,15 e o menor esticamento
                         # que se nota. Provado pelo outro lado: material que ja
                         # esta em 163,5 perde 0,47% dos pixels no estouro com
                         # esticamento de so 1,15 -- entao o limiar nao pode
                         # chegar perto do alvo.
CONTRASTE_MAX = 1.8      # teto do esticamento. ESTIMATIVA, nao medicao: acima
                         # disto o que cresce e o granulado da imagem, e material
                         # que precisaria de mais tem problema de gravacao, nao
                         # de acabamento. Quem tem de saber disso e a pessoa.

# --- fundo verde ---
VERDE_DA_MOLDURA = 0.40  # a partir desta fracao da BORDA do quadro em verde, o
                         # motor aceita trocar o fundo. MEDIDO dos dois lados:
                         # pano de fundo de verdade deu 85% com a pessoa no meio
                         # e 58% no enquadramento mais apertado; camiseta verde,
                         # planta no canto e imagem colorida qualquer ficaram
                         # todas em 12 a 13%. O limiar fica no meio dessa
                         # distancia, longe dos dois grupos.

VERDE_TOLERANCIA = 0.11  # quanto o corte do pano verde aceita de variacao de
                         # tom. MEDIDO dos dois lados, com um pano de luz
                         # irregular e uma figura na frente: de 0,04 a 0,18 o
                         # corte sai exato -- todo o pano vai embora e a figura
                         # fica inteira. Em 0,02 sobra pano (7 pontos do quadro
                         # por trocar); em 0,20 a figura comeca a ser comida e
                         # em 0,28 ela some por completo. 0,11 e o meio dessa
                         # janela.
VERDE_BORDA = 0.08       # suavizacao do contorno recortado

# --- o estalo de abertura ---
#
# CRASH ZOOM OUT, e nao um zoom que passeia: a imagem entra 2,4 vezes maior e
# desaba para o tamanho normal em pouco mais de um quarto de segundo. A curva e
# ao CUBO -- quase toda a viagem acontece nos tres primeiros quadros, e e isso
# que da o soco. Curva suave viraria movimento de camera, que e outra coisa.
#
# SEM CLARAO BRANCO. O que sustenta o efeito e a imagem se desmontando: canais
# fora de registro, croma deslocado e grao. Somar luz por cima disso lava tudo
# e some com o pouco que ha para ver.
ABERTURA_DUR = 0.30      # o crash inteiro. ESTIMATIVA: e o tempo em que o dedo
                         # de quem rola a tela ainda esta decidindo. Passou
                         # disso, o mesmo efeito atrapalha em vez de segurar.
ABERTURA_FORCA = 1.0     # multiplica tudo. 0 desliga.
ABERTURA_ZOOM = 1.40     # quanto a imagem entra maior: 1,40 = 2,4 vezes

# Os tres em DEGRAUS porque nenhum dos filtros aceita expressao de tempo -- so
# numero fixo mais `enable`. A 30 quadros por segundo cada faixa dura de 2 a 3
# quadros, e o olho le a sequencia como decaimento.
#
# (deslocamento horizontal, vertical, inicio, fim) -- o vertical so na primeira
# faixa, que e onde a imagem tem de parecer que rasgou.
ABERTURA_CANAIS = ((26, 8, 0.00, 0.06), (16, 4, 0.06, 0.12),
                   (8, 0, 0.12, 0.20), (3, 0, 0.20, 0.30))
# o croma anda por conta propria, e e o que da o borrao colorido por cima do
# deslocamento seco dos canais
ABERTURA_CROMA = ((14, 0.00, 0.08), (6, 0.08, 0.18))
# grao alto, temporal: muda a cada quadro, como chuvisco
ABERTURA_GRAO = ((48, 0.00, 0.08), (30, 0.08, 0.16),
                 (16, 0.16, 0.26), (7, 0.26, 0.36))


# --- o glitch das emendas ---
#
# A versao curta do estalo, para entrar de vez em quando no meio do filme. E
# outra coisa do que a abertura: ali o efeito ABRE o video; aqui ele marca uma
# virada de assunto. Mas nao e para ser discreto -- a primeira versao era, e
# passava despercebida. O que muda em relacao a abertura e a DURACAO e o
# tamanho do zoom, nao a violencia do glitch em si.
GLITCH_DUR = 0.22
GLITCH_FORCA = 1.0
GLITCH_ZOOM = 0.16       # contra 1,40 da abertura: um tranco, nao um mergulho
GLITCH_CANAIS = ((20, 6, 0.00, 0.06), (12, 3, 0.06, 0.12), (5, 0, 0.12, 0.18))
GLITCH_CROMA = ((12, 0.00, 0.06), (5, 0.06, 0.13))
GLITCH_GRAO = ((42, 0.00, 0.06), (26, 0.06, 0.13), (11, 0.13, 0.20))

# A CADENCIA E POR TEMPO, e nao por contagem de emendas: a cada 6 a 8 segundos,
# na emenda que cair mais perto. Contar emendas dava resultado irregular --
# quatro cenas curtas seguidas juntavam dois estalos, e uma cena longa deixava
# meio minuto sem nenhum.
GLITCH_MIN = 6.0         # nao repete antes disso
GLITCH_MAX = 8.0         # passando disso, pega a proxima emenda que houver

LUFS = -14 
LUFS = -14                      # normalizacao. As gravacoes chegam por volta de -36 dB
TETO_DB = -1.5           # teto do limitador, para a voz nao estourar. A margem
                         # ate 0 dB NAO e folga arbitraria: MEDIDO com gravacao
                         # e trilha reais, o limitador entrega -1,5 dB cravado e
                         # o mesmo audio em AAC — o formato do arquivo entregue —
                         # sai em -1,2 dB. O acrescimo e do formato, que
                         # reconstroi a onda de forma aproximada, e nao ha o que
                         # corrigir no limitador. Encostar este numero em zero
                         # faria o arquivo final passar de 0 dB e distorcer no
                         # aplicativo.

VOL_TRILHA = 0.34               # musica bem abaixo da voz
SR = 48000                      # taxa de amostragem, igual em TODA etapa. Misturar
                                # taxas foi uma das tres causas do dessync progressivo

LEG_CORPO = 54                  # corpo da legenda
LEG_ENTRELINHA = 1.16
LEG_PAD_X, LEG_PAD_Y = 24, 12   # respiro dentro da caixa
LEG_LARGURA_MAX = 840           # forca quebra antes de vazar
LEG_BASE = 1375                 # base em tela cheia. A 1500 caia sob a
                                 # interface do aplicativo
LEG_SPLIT_X = 60                # margem, na posicao alinhada a esquerda
LEG_SPLIT_TOPO = 827            # 20px abaixo da divisoria em 807
LEG_MIN_LETREIRO = 0.4   # tempo minimo que um letreiro fica na tela. ESTIMATIVA,
                         # nao medicao: e o piso de legibilidade, nao um numero
                         # tirado de um teste. Existe porque a conversao de tempo
                         # pode espremer um letreiro a quase nada quando ele foi
                         # ancorado numa pausa que o corte removeu -- e um texto
                         # que pisca por 0,1s some sem ninguem entender por que.

LEG_TOPO_LETREIRO = 1300        # letreiro com tinta abaixo disto tapa a legenda

SEGURO_TOPO = 180        # acima disto o aplicativo desenha a propria interface.
                         # ESTIMATIVA, nao medicao: nunca houve incidente no
                         # topo. Se aparecer um, e este numero que muda.
SEGURO_BASE = 1400       # MEDIDO por dois pontos: legenda com base 1375
                         # (tinta terminando em y=1376) funciona; base 1500
                         # (y=1501) caiu sob a interface do aplicativo e por
                         # isso virou 1375. O limite fica logo acima do unico
                         # valor que sabemos bom. Um limite em 1560 nao pegaria
                         # o proprio erro que motivou a mudanca.
