"""Coordenada unica de tempo: do arquivo original para o filme montado.

A REGRA DO PROJETO: todo instante que um agente escreve no `cenas.json` e
segundo do arquivo ORIGINAL, contado do comeco dele. Nenhum agente escreve
instante do filme pronto. So este modulo converte.

POR QUE. Entre a gravacao e o filme o tempo passa por duas transformacoes que
nao sao proporcionais:

  1. o corte das pausas internas REMOVE pedacos em lugares especificos -- uma
     pausa de 0,9s no meio da fala vira 0,10s, e tudo que vem depois anda para
     tras 0,8s;
  2. a velocidade DIVIDE o que sobrou.

Somar o instante da gravacao ao inicio da cena, que era o jeito antigo, erra
por mais quanto mais tarde estiver o instante -- e o erro cresce a cada pausa
comprimida. Foi o que punha letreiro no lugar errado.

A conversao aqui usa a MESMA lista de pedacos que o corte usa de verdade
(`marcas`). Se as duas divergirem, o letreiro entra na hora errada e nada
acusa: por isso ha uma fonte so, e `tratamentos.aperta` corta por ela.
"""
from dataclasses import dataclass, field
from typing import Optional

from motor import config

PISO_PEDACO = 0.05   # pedaco menor que isto nao vira arquivo: o ffmpeg devolve
                     # um trecho de um quadro so e o concat quebra


def marcas(ini, fim, pausas):
    """Os pedacos de fala que sobram da cena depois de comprimir as pausas.

    `ini` e `fim` sao as bordas da fala no arquivo original; `pausas` sao os
    silencios internos, em segundos RELATIVOS a `ini`, como
    `fala.pausas_internas` devolve.

    Devolve [(a, b)] tambem relativo a `ini`, ja sem os pedacos curtos demais
    para virar arquivo. Cada pausa some e deixa `config.PAUSA_FICA` no lugar.
    """
    if not pausas:
        return [(0.0, fim - ini)]
    saida, t = [], 0.0
    for a, b in pausas:
        saida.append((t, a + config.PAUSA_FICA))
        t = b
    saida.append((t, fim - ini))
    return [(a, b) for a, b in saida if b - a >= PISO_PEDACO]


@dataclass
class Mapa:
    """O mapa de tempo de UMA cena. Converte instante do original em instante
    do filme, e de volta.

    `dur` e a duracao REAL do segmento, medida com ffprobe depois de renderizar.
    Quando ela existe, a conversao e esticada para caber nela: fps, decimais de
    ffprobe e arredondamento de quadro fazem o que saiu diferir em algumas
    dezenas de milissegundos do que a conta previa, e sem esse ajuste o erro
    aparece todo no fim da cena, que e justamente onde os letreiros costumam
    estar.
    """
    ini: float
    fim: float
    marcas: list = field(default_factory=list)
    velocidade: float = 1.0
    offset: float = 0.0                 # onde a cena comeca no filme
    dur: Optional[float] = None         # duracao medida do segmento pronto
    n: Optional[int] = None

    @property
    def dur_teorica(self):
        """Quanto a cena deveria durar, pela conta."""
        return sum(b - a for a, b in self.marcas) / self.velocidade

    @property
    def ajuste(self):
        t = self.dur_teorica
        if not self.dur or t <= 0:
            return 1.0
        return self.dur / t

    def na_cena(self, s):
        """Instante `s` do arquivo original -> segundos desde o comeco desta
        cena ja pronta.

        Instante que caiu numa pausa cortada, ou fora das bordas da fala, volta
        na borda mais proxima: um letreiro ancorado no silencio aparece onde o
        silencio estava."""
        r = s - self.ini
        somado = 0.0
        for a, b in self.marcas:
            if r >= b:
                somado += b - a
            elif r > a:
                somado += r - a
                break
            else:
                break
        return somado / self.velocidade * self.ajuste

    def no_filme(self, s):
        """Instante `s` do arquivo original -> segundos desde o comeco do filme."""
        return self.offset + self.na_cena(s)

    def no_original(self, t):
        """O caminho de volta: segundos desde o comeco desta cena pronta ->
        instante do arquivo original. Serve para dizer de onde veio um pedaco
        do filme -- e para conferir a ida."""
        alvo = max(0.0, t) / self.ajuste * self.velocidade
        somado = 0.0
        for a, b in self.marcas:
            if somado + (b - a) >= alvo:
                return self.ini + a + (alvo - somado)
            somado += b - a
        return self.fim

    def do_filme(self, t):
        """O caminho de volta de `no_filme`: segundos desde o comeco do FILME
        -> instante do arquivo original. Use este quando o numero na mao veio do
        filme montado."""
        return self.no_original(t - self.offset)

    def como_registro(self):
        """A forma que vai para o `cenas-mapa.json`.

        `de` e `ate` sao da GRAVACAO; `ini` e `fim`, que quem chama acrescenta,
        sao do FILME. Os dois pares convivem no mesmo registro de proposito: e
        o que permite ir e voltar entre os dois tempos depois, sem remontar."""
        return {"de": round(self.ini, 3), "ate": round(self.fim, 3),
                "marcas": [[round(a, 3), round(b, 3)] for a, b in self.marcas],
                "velocidade": self.velocidade}


def de_registro(reg):
    """Reconstroi um Mapa a partir de uma entrada do `cenas-mapa.json`."""
    ini_filme = reg.get("ini", 0.0)
    fim_filme = reg.get("fim")
    return Mapa(ini=reg["de"], fim=reg["ate"],
                marcas=[tuple(x) for x in reg.get("marcas", [])],
                velocidade=reg.get("velocidade", 1.0),
                offset=ini_filme,
                dur=(fim_filme - ini_filme) if fim_filme is not None else None,
                n=reg.get("n"))
