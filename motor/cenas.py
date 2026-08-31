"""O contrato entre os agentes e o motor. Os agentes escrevem este arquivo;
o motor le. Nenhum agente escreve comando de video."""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from motor import config, estilos

# Onde a legenda pode ficar quando a tela esta dividida em duas. Em tela
# cheia ela e sempre centralizada, entao "cheia" nao e escolha de ninguem.
LEGENDA_NO_SPLIT = ("esquerda", "direita", "centro")

TRATAMENTOS = ("cheia", "split")


class CenasInvalidas(Exception):
    """O arquivo de cenas nao pode ser usado. A mensagem diz o que corrigir."""


@dataclass
class Topo:
    arquivo: Path
    ancora: float = 0.0        # 0.0 topo, 0.5 centro, 1.0 base


@dataclass
class Letreiro:
    """`de` e `ate` sao segundos do arquivo ORIGINAL da cena -- o instante em
    que a pessoa fala aquilo na gravacao crua. Quem converte para o tempo do
    filme montado e `motor/tempo.py`, e so ele."""
    texto: str
    de: float = 0.0
    ate: Optional[float] = None
    base: Optional[int] = None
    box: bool = False


@dataclass
class Cena:
    """`de` e `ate` recortam o trecho do arquivo original que vira esta cena.
    E o que permite tirar varias cenas do mesmo take, e escolher a melhor
    tomada de uma frase que a pessoa repetiu. Sem eles, a cena e o arquivo
    inteiro."""
    n: int
    trat: str
    arquivo: Path
    velocidade: float
    de: Optional[float] = None
    ate: Optional[float] = None
    teto: Optional[float] = None
    topo: Optional["Topo"] = None
    letreiro: Optional[Letreiro] = None
    fundo: Optional[str] = None      # so funciona com pano verde de verdade


@dataclass
class Producao:
    raiz: Path
    velocidade: float
    trilha: Optional[Path]
    cenas: list = field(default_factory=list)
    legenda_estilo: dict = field(default_factory=dict)
    letreiro_estilo: dict = field(default_factory=dict)
    legenda: bool = True
    legenda_split: str = "esquerda"
    proprios: list = field(default_factory=list)
    trocas: dict = field(default_factory=dict)
    contraste: object = True    # True mede e corrige; False deixa como veio;
                                # um numero forca aquele esticamento


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

    # Como o texto aparece: fonte, paleta e efeito, escolhidos em separado
    # para a legenda e para o letreiro. O que faltar vira o padrao.
    def _visual(campo, para):
        bruto = dados.get(campo) or {}
        if not isinstance(bruto, dict):
            raise CenasInvalidas(
                f"'{campo}' e um conjunto de escolhas, por exemplo "
                '{"fonte": "sem serifa", "paleta": "amarelo", '
                '"efeito": "contorno"}')
        for chave in bruto:
            if chave not in ("fonte", "paleta", "efeito"):
                raise CenasInvalidas(
                    f"'{campo}' nao tem o campo '{chave}'. Ele aceita fonte, "
                    "paleta e efeito")
        try:
            estilos.compor(bruto, para)
        except estilos.EstiloDesconhecido as e:
            raise CenasInvalidas(str(e)) from e
        return bruto

    legenda_estilo = _visual("legenda_estilo", "legenda")
    letreiro_estilo = _visual("letreiro_estilo", "letreiro")
    legenda = bool(dados.get("legenda", True))
    legenda_split = dados.get("legenda_split", "esquerda")
    if legenda_split not in LEGENDA_NO_SPLIT:
        raise CenasInvalidas(
            f"nao sei por a legenda em '{legenda_split}' quando a tela esta "
            "dividida. Use uma de: " + ", ".join(LEGENDA_NO_SPLIT))
    proprios = list(dados.get("proprios", []))
    if any(not isinstance(x, str) or not x.strip() for x in proprios):
        raise CenasInvalidas(
            "'proprios' e uma lista de nomes escritos do jeito certo, "
            "por exemplo [\"Ginsu\", \"Anthropic\"]")

    # Trocas ditadas palavra por palavra. E o UNICO jeito de consertar erro de
    # SOM na transcricao -- "sidense" nao se parece com "Seedance" quando se
    # comparam as letras, e nao ha limiar de semelhanca que pegue isso sem
    # trocar palavra comum da fala junto (ver motor/legenda.py).
    trocas = dados.get("trocas") or {}
    if not isinstance(trocas, dict):
        raise CenasInvalidas(
            "'trocas' e uma lista de trocas, do jeito que a transcricao "
            "escreveu para o jeito certo, por exemplo "
            "{\"sidense\": \"Seedance\"}")
    for errado, certo in trocas.items():
        if not isinstance(errado, str) or not isinstance(certo, str) \
                or not errado.strip() or not certo.strip():
            raise CenasInvalidas(
                f"a troca {errado!r} -> {certo!r} nao serve: os dois lados "
                "precisam ser texto")

    # Correcao de contraste: True mede cada gravacao e corrige a que estiver
    # lavada; False nao mexe; um numero forca o mesmo esticamento em todas.
    contraste = dados.get("contraste", True)
    if not isinstance(contraste, bool):
        try:
            contraste = float(contraste)
        except (TypeError, ValueError):
            raise CenasInvalidas(
                "'contraste' aceita true (mede e corrige o que estiver lavado), "
                "false (deixa a imagem como veio) ou um numero")
        if not 1.0 <= contraste <= config.CONTRASTE_MAX:
            raise CenasInvalidas(
                f"'contraste' com numero tem de ficar entre 1.0 e "
                f"{config.CONTRASTE_MAX}, veio {contraste}")

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

        # Recorte no arquivo original: de onde ate onde usar deste take
        de = bruto.get("de")
        ate = bruto.get("ate")
        if de is not None:
            de = float(de)
            if de < 0:
                raise CenasInvalidas(
                    f"cena {n}: 'de' e o segundo em que o trecho comeca na "
                    "gravacao, e nao pode ser negativo")
        if ate is not None:
            ate = float(ate)
            if de is not None and ate <= de:
                raise CenasInvalidas(
                    f"cena {n}: o trecho termina em {ate} e comeca em {de}. "
                    "O fim tem de vir depois do comeco")
            if de is None and ate <= 0:
                raise CenasInvalidas(
                    f"cena {n}: 'ate' e o segundo em que o trecho termina na "
                    "gravacao, e tem de ser maior que zero")

        # Trocar o fundo. So funciona se a pessoa gravou na frente de um pano
        # verde -- quem confere isso e a montagem, olhando a imagem.
        fundo = bruto.get("fundo")
        if fundo is not None:
            fundo = str(fundo)
            if fundo.startswith("#"):
                if len(fundo) != 7 or any(c not in "0123456789abcdefABCDEF"
                                          for c in fundo[1:]):
                    raise CenasInvalidas(
                        f"cena {n}: a cor de fundo '{fundo}' nao esta escrita "
                        "do jeito certo. Use seis digitos, como #101010")
            else:
                fundo = str(_caminho(raiz, fundo, n))

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
            if "entra" in bruto_letreiro or "dura" in bruto_letreiro:
                raise CenasInvalidas(
                    f"cena {n}: o letreiro agora usa 'de' e 'ate', que sao os "
                    "segundos da GRAVACAO em que o texto aparece e some. "
                    "'entra' e 'dura' contavam no video ja cortado e punham o "
                    "texto na hora errada")
            l_de = float(bruto_letreiro.get("de", 0.0))
            if l_de < 0:
                raise CenasInvalidas(
                    f"cena {n}: 'de' do letreiro e o segundo da gravacao em "
                    "que o texto aparece, e nao pode ser negativo")
            l_ate = bruto_letreiro.get("ate")
            if l_ate is not None:
                l_ate = float(l_ate)
                if l_ate <= l_de:
                    raise CenasInvalidas(
                        f"cena {n}: o letreiro some em {l_ate} e aparece em "
                        f"{l_de}. O fim tem de vir depois do comeco")
            # O letreiro marca uma frase que a pessoa fala DENTRO desta cena.
            # Fora do recorte ele nunca apareceria, e o silencio seria pior
            # que o erro: o video sai sem o texto e ninguem descobre por que.
            if de is not None and l_de < de:
                raise CenasInvalidas(
                    f"cena {n}: o letreiro aparece em {l_de} segundos, mas "
                    f"esta cena so comeca em {de}. Ele nunca apareceria")
            if ate is not None and l_de >= ate:
                raise CenasInvalidas(
                    f"cena {n}: o letreiro aparece em {l_de} segundos, mas "
                    f"esta cena termina em {ate}. Ele nunca apareceria")
            letreiro = Letreiro(
                texto=bruto_letreiro["texto"],
                de=l_de,
                ate=l_ate,
                base=bruto_letreiro.get("base"),
                box=bool(bruto_letreiro.get("box", False)))

        # Montar cena validada
        montadas.append(Cena(
            n=n,
            trat=trat,
            arquivo=_caminho(raiz, arquivo, n),
            velocidade=float(bruto.get("velocidade", velocidade)),
            de=de,
            ate=ate,
            teto=bruto.get("teto"),
            topo=topo,
            letreiro=letreiro,
            fundo=fundo))

    return Producao(
        raiz=raiz,
        velocidade=velocidade,
        trilha=_caminho(raiz, trilha, "trilha") if trilha else None,
        cenas=montadas,
        legenda_estilo=legenda_estilo,
        letreiro_estilo=letreiro_estilo,
        legenda_split=legenda_split,
        proprios=proprios,
        trocas={k.lower(): v for k, v in trocas.items()},
        legenda=legenda,
        contraste=contraste)
