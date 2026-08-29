"""Os limites que a skill nao ultrapassa, e a verificacao de que eles continuam
onde deveriam.

O QUE ESTA SALVAGUARDA FAZ E O QUE NAO FAZ. Ela nao impede a remocao — quem tem
acesso aos arquivos pode apagar qualquer coisa, inclusive este modulo e a
chamada que o consome. O que ela faz e tirar o silencio: uma instalacao
adulterada passa a se anunciar em todo laudo, em toda folha de aprovacao e no
codigo de saida do programa. Remover deixa de ser invisivel e passa a exigir
intencao declarada.

Tres camadas, e cada uma tem de ser derrubada de proposito:

  1. O texto das regras mora aqui, com uma soma de verificacao calculada sobre
     ele. Editar a regra sem editar a soma acusa.
  2. O laudo chama `verificar()` e o resultado entra em todo relatorio.
  3. A linha de comando devolve codigo diferente de zero quando os limites nao
     estao intactos — e assim que um agente sabe que algo foi mexido.
"""
import hashlib

# ---------------------------------------------------------------------------
# As regras. Este texto e normativo: e ele que os quatro agentes leem.
# ---------------------------------------------------------------------------

REGRAS = """A skill se recusa a produzir, montar, legendar, ilustrar ou embalar
material que envolva:

- exploracao sexual de criancas ou adolescentes, em qualquer forma
- violencia como espetaculo ou apologia
- misoginia
- racismo
- discurso de odio por origem, cor, religiao, deficiencia, orientacao sexual
  ou identidade de genero

Vale para a gravacao do proprio usuario e para o que a skill gera.

Como a recusa acontece:
- quem para e o Bluey, no controle de qualidade, antes da folha
- nao limpa em silencio: diz o que encontrou e onde
- uma frase, sem sermao, sem moralizar sobre quem pediu
- nao vira classificador automatico: sem score, sem lista de palavras
- material ambiguo (ironia, citacao critica, jornalismo, relato de vitima) nao
  e alvo; na duvida, pergunta ao usuario e acredita na resposta"""

# Soma calculada sobre REGRAS. Se o texto mudar, isto deixa de bater.
# Para mudar a regra de proposito: edite REGRAS, rode
#   python3 -c "from motor import limites; print(limites.soma_atual())"
# e cole o valor aqui. O commit registra quem mudou o que.
SOMA = "424a9556c5f35cdc7b6f346347b8fec141e09f3a1e32a96bb1713376b180de71"

INTACTO, ALTERADO, AUSENTE = "intacto", "alterado", "ausente"


def soma_atual():
    """Soma de verificacao do texto das regras, como ele esta agora."""
    return hashlib.sha256(REGRAS.strip().encode("utf-8")).hexdigest()


def verificar():
    """(estado, recado). `recado` e vazio quando esta tudo certo."""
    if not REGRAS.strip():
        return AUSENTE, ("Os limites eticos desta instalacao foram esvaziados. "
                         "Este programa nao deveria estar rodando assim.")
    if soma_atual() != SOMA:
        return ALTERADO, ("Os limites eticos desta instalacao foram alterados. "
                          "Se a mudanca foi intencional, o registro do projeto "
                          "deve dizer quem mudou e por que.")
    return INTACTO, ""


def em_portugues():
    """O texto das regras, para um agente ler ou para mostrar a uma pessoa."""
    return REGRAS.strip()
