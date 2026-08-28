"""Uso: python3 -m motor <cenas.json> <saida.mp4>

Le o arquivo de cenas, monta o filme e imprime um laudo em portugues. Se algo
der errado, a mensagem diz o que corrigir e o codigo de saida vem diferente
de zero -- e assim que um agente sabe que precisa agir de novo."""
import sys

from motor import cenas, laudo, montar


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip())
        return 2
    try:
        filme = montar.montar(argv[1], argv[2])
    except cenas.CenasInvalidas as e:
        print(f"O arquivo de cenas tem um problema: {e}")
        return 1
    except RuntimeError as e:
        print(f"Nao consegui montar o filme: {e}")
        return 1
    print(laudo.em_portugues(laudo.rodar(filme, argv[1])))
    print(f"pronto: {filme}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
