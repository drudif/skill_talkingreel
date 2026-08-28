"""Rede de protecao da suite.

Transcrever de verdade baixa um modelo de ~3GB e leva minutos. Nenhum teste
deve cair nisso por acidente — se cair, o teste tem de FALHAR alto, e nao
travar a suite baixando modelo. Quem quer transcricao de verdade usa a marca
LENTO e liga com TESTE_LENTO=1, ou injeta a propria funcao em `montar`."""
import os

import pytest

from motor import legenda


@pytest.fixture(autouse=True)
def sem_transcricao_de_verdade(monkeypatch, request):
    if os.environ.get("TESTE_LENTO") == "1":
        return

    def _explode(*_a, **_k):
        raise AssertionError(
            "este teste chamou a transcricao de verdade. Ou passe "
            '"legenda": False no arquivo de cenas, ou injete uma funcao em '
            "montar(..., transcrever=...). Rodar o modelo na suite baixa "
            "3GB e leva minutos.")

    monkeypatch.setattr(legenda, "transcrever", _explode)
