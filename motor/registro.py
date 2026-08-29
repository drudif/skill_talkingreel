"""O que ja foi decidido, em disco.

E isto que faz a folha encolher: cada folha carrega SO o pendente. No projeto
de origem as pecas se acumulavam e a pagina chegou a 15 itens de uma vez."""
import json
from pathlib import Path

DECISOES = (None, "aprovado", "descartado")


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
                "descartado, ou nada ainda.")
    dados = carregar(caminho)
    dados.update(novas)
    gravar(caminho, dados)
    return dados


def pendentes(itens, caminho):
    """Os itens que ainda nao foram nem aprovados nem descartados."""
    dados = carregar(caminho)
    return [i for i in itens
            if dados.get(i["id"], {}).get("decisao") not in
            ("aprovado", "descartado")]
