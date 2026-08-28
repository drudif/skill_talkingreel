"""O contrato entre os agentes e o motor. Os agentes escrevem este arquivo;
o motor le. Nenhum agente escreve comando de video."""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from motor import config, estilos

TRATAMENTOS = ("cheia", "split")


class CenasInvalidas(Exception):
    """O arquivo de cenas nao pode ser usado. A mensagem diz o que corrigir."""


@dataclass
class Topo:
    arquivo: Path
    ancora: float = 0.0        # 0.0 topo, 0.5 centro, 1.0 base


@dataclass
class Letreiro:
    texto: str
    entra: float = 0.0
    dura: Optional[float] = None
    base: Optional[int] = None
    box: bool = False


@dataclass
class Cena:
    n: int
    trat: str
    arquivo: Path
    velocidade: float
    teto: Optional[float] = None
    topo: Optional["Topo"] = None
    letreiro: Optional[Letreiro] = None


@dataclass
class Producao:
    raiz: Path
    velocidade: float
    trilha: Optional[Path]
    cenas: list = field(default_factory=list)
    estilo: str = estilos.PADRAO
    legenda: bool = True


def _caminho(raiz, rel, onde):
    """Resolve e valida um caminho relativo. Lanca CenasInvalidas se nao existir."""
    p = (raiz / rel).resolve()
    if not p.exists():
        raise CenasInvalidas(f"cena {onde}: o arquivo {rel} nao existe")
    return p


def carregar(caminho):
    """Carrega e valida o arquivo de cenas JSON.

    Retorna Producao com estrutura validada e caminhos resolvidos.
    Lanca CenasInvalidas se algo estiver errado; a mensagem diz o que corrigir.
    """
    caminho = Path(caminho)
    raiz = caminho.parent

    # Ler JSON
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise CenasInvalidas(
            f"o arquivo de cenas nao e um JSON valido: {e}") from e

    # Velocidade geral (padrao em config.VELOCIDADE)
    velocidade = float(dados.get("velocidade", config.VELOCIDADE))

    # Estilo visual (uma das fichas de motor/estilos.py; padrao brutalista)
    estilo = dados.get("estilo", estilos.PADRAO)
    if estilo not in estilos.ESTILOS:
        raise CenasInvalidas(
            f"nao conheco o estilo '{estilo}'. Os que existem sao: "
            + ", ".join(sorted(estilos.ESTILOS)))
    legenda = bool(dados.get("legenda", True))

    # Trilha sonora (opcional)
    trilha = dados.get("trilha")

    # Lista de cenas
    lista = dados.get("cenas") or []
    if not lista:
        raise CenasInvalidas("o arquivo de cenas nao tem nenhuma cena")

    vistos, montadas = set(), []
    for bruto in lista:
        # Numero da cena
        n = bruto.get("n")
        if n is None:
            raise CenasInvalidas("ha uma cena sem numero (campo 'n')")
        if n in vistos:
            raise CenasInvalidas(f"cena {n}: numero repetido")
        vistos.add(n)

        # Tratamento
        trat = bruto.get("trat")
        if trat not in TRATAMENTOS:
            raise CenasInvalidas(
                f"cena {n}: tratamento '{trat}' desconhecido. "
                f"Use um destes: {', '.join(TRATAMENTOS)}")

        # Arquivo do talking head
        arquivo = bruto.get("arquivo")
        if not arquivo:
            raise CenasInvalidas(f"cena {n}: falta o campo 'arquivo'")

        # Topo (split screen)
        topo = None
        if trat == "split":
            bruto_topo = bruto.get("topo")
            if not bruto_topo or not bruto_topo.get("arquivo"):
                raise CenasInvalidas(
                    f"cena {n}: split precisa do campo 'topo' com um arquivo")
            ancora = float(bruto_topo.get("ancora", 0.0))
            if not 0.0 <= ancora <= 1.0:
                raise CenasInvalidas(
                    f"cena {n}: 'ancora' deve estar entre 0.0 e 1.0, veio {ancora}")
            topo = Topo(
                arquivo=_caminho(raiz, bruto_topo["arquivo"], n),
                ancora=ancora)

        # Letreiro (opcional)
        letreiro = None
        bruto_letreiro = bruto.get("letreiro")
        if bruto_letreiro:
            if not bruto_letreiro.get("texto"):
                raise CenasInvalidas(
                    f"cena {n}: o letreiro precisa do campo 'texto'")
            entra = float(bruto_letreiro.get("entra", 0.0))
            if entra < 0:
                raise CenasInvalidas(
                    f"cena {n}: 'entra' do letreiro nao pode ser negativo")
            letreiro = Letreiro(
                texto=bruto_letreiro["texto"],
                entra=entra,
                dura=bruto_letreiro.get("dura"),
                base=bruto_letreiro.get("base"),
                box=bool(bruto_letreiro.get("box", False)))

        # Montar cena validada
        montadas.append(Cena(
            n=n,
            trat=trat,
            arquivo=_caminho(raiz, arquivo, n),
            velocidade=float(bruto.get("velocidade", velocidade)),
            teto=bruto.get("teto"),
            topo=topo,
            letreiro=letreiro))

    return Producao(
        raiz=raiz,
        velocidade=velocidade,
        trilha=_caminho(raiz, trilha, "trilha") if trilha else None,
        cenas=montadas,
        estilo=estilo,
        legenda=legenda)
