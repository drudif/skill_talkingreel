"""Quem usa esta skill nao entende de montagem, edicao ou audio.

Isto varre o texto que a PESSOA le. Termo tecnico so passa se estiver explicado
na mesma frase — a explicacao tem de estar ali, nao num arquivo ao lado.

"Sem termo tecnico" e a instrucao mais facil de escrever e a mais facil de
esquecer. Um teste transforma a instrucao em coisa verificavel."""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

# Palavras que nao dizem nada para quem nunca editou video. Nao e uma lista de
# palavras proibidas: e uma lista de palavras que exigem explicacao na hora.
JARGAO = ["codec", "bitrate", "container", "keyframe", "timeline", "render",
          "encode", "muxer", "demuxer", "sample rate", "loudness", "lufs",
          "buffer", "pipeline", "commit", "hash", "checksum", "regex",
          "stdout", "b-roll", "crossfade", "chroma", "alpha", "overlay"]

# Metaforas batidas. O usuario pediu por escrito: nada de figura de linguagem.
BATIDAS = ["a cereja do bolo", "o pulo do gato", "na veia", "de bandeja",
           "colocar a mao na massa", "por a mao na massa", "tirar do papel",
           "virada de chave", "nao e so", "não é só", "muito mais do que",
           "ponta do iceberg", "carro-chefe", "chave de ouro"]

# O que esta entre crases e codigo: nome de campo, comando, caminho de arquivo.
# Ali o termo tecnico e legitimo — e o nome da coisa, nao conversa.
_CODIGO = re.compile(r"```.*?```|`[^`]*`", re.S)
# Tabela de referencia tecnica tambem nao e conversa com a pessoa.
_EXPLICA = ("quer dizer", "que e", "que é", "ou seja", "isto e", "isto é",
            "significa", "chamado", "chamada")


def _conversa(caminho):
    """So o texto que a pessoa le como frase, sem o codigo."""
    return _CODIGO.sub(" ", caminho.read_text(encoding="utf-8"))


def _arquivos():
    yield RAIZ / "SKILL.md"
    yield from sorted((RAIZ / "referencias").glob("**/*.md"))


IDS = [p.name for p in _arquivos()]


@pytest.mark.parametrize("caminho", list(_arquivos()), ids=IDS)
def test_sem_jargao_sem_explicacao(caminho):
    achados = []
    for frase in re.split(r"(?<=[.!?:])\s+|\n\n", _conversa(caminho)):
        baixo = frase.lower()
        if any(x in baixo for x in _EXPLICA):
            continue
        for termo in JARGAO:
            if termo in baixo:
                achados.append((termo, " ".join(frase.split())[:90]))
    assert not achados, (
        f"{caminho.name} usa termo tecnico sem explicar na mesma frase:\n"
        + "\n".join(f"  '{t}' em: {f}" for t, f in achados))


@pytest.mark.parametrize("caminho", list(_arquivos()), ids=IDS)
def test_sem_metafora_batida(caminho):
    baixo = _conversa(caminho).lower()
    achadas = [b for b in BATIDAS if b in baixo]
    assert not achadas, f"{caminho.name} usa figura de linguagem: {achadas}"


def test_o_laudo_fala_a_lingua_da_pessoa():
    """O laudo e o texto que a pessoa mais le: sai a cada montagem."""
    from motor import laudo
    r = {"duracao": 42.0, "cenas": 3, "ok": False,
         "problemas": ["a imagem e o som terminam em momentos diferentes: "
                       "0.42 segundo de diferenca",
                       "na emenda aos 12.4 segundos ainda ha som de fala: o "
                       "corte pode ter comido um pedaco de palavra"],
         "repeticao": [{"n": 2, "vezes": 30, "material_s": 2.4, "cena_s": 70.9}]}
    texto = laudo.em_portugues(r).lower()
    for termo in JARGAO:
        assert termo not in texto, f"o laudo vazou o termo '{termo}'"
    for b in BATIDAS:
        assert b not in texto, f"o laudo usa figura de linguagem: '{b}'"


def test_a_folha_fala_a_lingua_da_pessoa(tmp_path):
    """A folha e a outra coisa que a pessoa le. O texto fixo dela — titulo dos
    botoes, cabecalho — nao pode ter jargao."""
    from motor import folha
    p = folha.escrever([], "primeira", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    visivel = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", html)
    visivel = re.sub(r"<[^>]+>", " ", visivel).lower()
    for termo in JARGAO:
        assert termo not in visivel, f"a folha vazou o termo '{termo}'"


def test_o_erro_de_contrato_diz_o_que_consertar(tmp_path):
    """Quando a pessoa ve um erro, ele tem de dizer o que fazer, nao so o que
    esta errado."""
    import json

    from motor import cenas
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"estilo": "roxo-neon", "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "x.mov"}]}), encoding="utf-8")
    try:
        cenas.carregar(p)
        raise AssertionError("deveria ter recusado o estilo inexistente")
    except cenas.CenasInvalidas as e:
        msg = str(e)
        assert "brutalista" in msg, "o erro nao diz quais estilos existem"
        for termo in JARGAO:
            assert termo not in msg.lower(), f"o erro vazou '{termo}'"
