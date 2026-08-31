"""O que ja foi decidido, em disco.

E isto que faz a folha encolher: cada folha carrega SO o pendente. No projeto
de origem as pecas se acumulavam e a pagina chegou a 15 itens de uma vez."""
import json
from pathlib import Path

# As mesmas palavras que aparecem na folha, e nao sinonimos delas: a folha e o
# registro do que foi combinado, e traduzir a decisao no meio do caminho e como
# se perde a diferenca entre o que a pessoa marcou e o que ficou anotado.
# `escolhido` e a decisao de um bloco de escolha unica -- so um item do bloco
# recebe.
DECISOES = (None, "aprovado", "reprovado", "escolhido")


class RegistroIlegivel(Exception):
    """O arquivo de registro existe mas nao da para ler."""


def carregar(caminho):
    caminho = Path(caminho)
    if not caminho.exists():
        return {}
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RegistroIlegivel(
            f"o registro em {caminho} esta corrompido e nao da para ler: {e}. "
            "Apague o arquivo para comecar de novo, ou conserte o JSON.")


def gravar(caminho, dados):
    Path(caminho).write_text(
        json.dumps(dados, indent=1, ensure_ascii=False), encoding="utf-8")


def anotar(caminho, novas):
    """Junta decisoes novas as que ja existiam, sem apagar as antigas."""
    for chave, d in novas.items():
        if d.get("decisao") not in DECISOES:
            raise ValueError(
                f"'{d.get('decisao')}' nao e uma decisao. So existe aprovado, "
                "reprovado, escolhido, ou nada ainda.")
    dados = carregar(caminho)
    dados.update(novas)
    gravar(caminho, dados)
    return dados


def pendentes(itens, caminho):
    """Os itens que ainda nao foram decididos."""
    dados = carregar(caminho)
    return [i for i in itens
            if dados.get(i["id"], {}).get("decisao") not in
            ("aprovado", "reprovado", "escolhido")]
