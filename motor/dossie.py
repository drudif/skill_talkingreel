"""O que se sabe de cada arquivo antes de montar qualquer coisa.

POR QUE ESTE MODULO EXISTE. Bandit e Bingo trabalham ao mesmo tempo. O Bandit
depende de ouvir o que foi dito, e isso demora; enquanto isso o Bingo nao pode
ficar parado -- mas tambem NAO pode cortar nem acelerar nada, porque o que fica
no filme ainda vai ser decidido.

O que ele pode fazer e o que esta aqui: MEDIR. Nada nesta pasta produz video, e
nada aqui depende de decisao nenhuma -- as mesmas contas dariam o mesmo
resultado antes ou depois do Bandit. Por isso rodar em paralelo e seguro.

E o resultado serve duas vezes: informa a folha de aprovacao (quanto tempo tem,
quanto e fala, o que esta lavado, o que tem pano verde) e adianta para a
montagem o que ela teria de medir de qualquer jeito.

REGRA QUE VALE PARA TUDO AQUI: as medidas saem do arquivo ORIGINAL. Area util,
contraste e pano verde sao propriedades de ESPACO, nao de tempo -- medi-las num
trecho ja cortado, que pode ter menos de um segundo, devolve resposta errada ou
resposta nenhuma.
"""
import json
from pathlib import Path

from motor import fala, imagem, probe


def de_um(caminho):
    """Tudo o que da para saber de um arquivo sem decidir nada sobre ele."""
    caminho = Path(caminho)
    dur = probe.dur(caminho)
    largura, altura = probe.dimensao(caminho)
    tem_som = probe.tem_audio(caminho)

    ficha = {
        "arquivo": str(caminho),
        "duracao": round(dur, 3),
        # arquivo truncado, vazio, ou que nao e video: o ffprobe nao acha
        # duracao nenhuma. Marcar aqui e o que permite avisar em portugues em
        # vez de deixar o erro estourar la na montagem, com o trabalho ja feito.
        "ilegivel": dur <= 0,
        "largura": largura,
        "altura": altura,
        "em_pe": altura > largura,
        "tem_som": tem_som,
        "contraste": round(imagem.contraste(caminho), 1),
        "esticamento": round(imagem.ganho(caminho), 3),
        "pano_verde": imagem.tem_fundo_verde(caminho),
    }

    if ficha["ilegivel"]:
        return ficha

    if tem_som:
        ini, fim = fala.bordas(caminho)
        pausas = fala.pausas_internas(caminho, ini, fim)
        ficha.update({
            "fala_de": round(ini, 3),
            "fala_ate": round(fim, 3),
            "fala_dura": round(fim - ini, 3),
            "pausas": [[round(a, 3), round(b, 3)] for a, b in pausas],
            "silencio_a_cortar": round(sum(b - a for a, b in pausas), 3),
        })
    return ficha


def de(arquivos, destino=None):
    """A ficha de cada arquivo. Grava em `destino` se pedido."""
    fichas = [de_um(a) for a in arquivos]
    if destino:
        Path(destino).write_text(
            json.dumps(fichas, indent=1, ensure_ascii=False), encoding="utf-8")
    return fichas


def em_portugues(fichas):
    """O dossie em frases, para a pessoa ler na folha.

    Sem termo tecnico: quem le nunca abriu um programa de edicao."""
    linhas = []
    for f in fichas:
        nome = Path(f["arquivo"]).name
        if f.get("ilegivel"):
            linhas.append(
                f"{nome}: nao deu para abrir. O arquivo pode estar incompleto, "
                "ou pode nao ser um video. Mande de novo.")
            continue
        partes = [f"{nome}: {f['duracao']:.0f} segundos"]
        if f.get("fala_dura") is not None:
            partes.append(f"{f['fala_dura']:.0f} segundos de fala")
            if f["silencio_a_cortar"] > 0.5:
                partes.append(
                    f"{f['silencio_a_cortar']:.0f} segundos de pausa para tirar")
        if not f["tem_som"]:
            partes.append("sem som")
        if not f["em_pe"]:
            partes.append("gravado deitado, vai ser cortado para caber em pe")
        if f["esticamento"] > 1.10:
            partes.append("imagem lavada, o programa corrige")
        if f["pano_verde"]:
            partes.append("gravado na frente de pano verde, da para trocar o fundo")
        linhas.append(", ".join(partes) + ".")
    return "\n".join(linhas)
