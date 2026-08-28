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

LUFS = -14                      # normalizacao. As gravacoes chegam por volta de -36 dB
TETO_DB = -1.5                  # teto do limitador, para a voz nao estourar

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
LEG_TOPO_LETREIRO = 1300        # letreiro com tinta abaixo disto tapa a legenda

SEGURO_TOPO = 180        # acima disto o aplicativo desenha a propria interface
SEGURO_BASE = 1560       # abaixo disto idem. A legenda a 1500 caia sob ela
