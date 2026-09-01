"""O que a pessoa mandou, e o que e cada coisa.

O PROBLEMA QUE ISTO RESOLVE. A pessoa larga os arquivos numa pasta e diz "esta
tudo ai". Quem le precisa descobrir sozinho qual e a gravacao dela falando, qual
e material para entrar junto, e qual e musica -- e errar isso monta o video com
o arquivo errado no lugar errado.

Adivinhar pelo conteudo e caro e falivel: exigiria abrir cada arquivo e olhar.
Pedir NOME e barato e nao erra. Entao a skill pede, com exemplo, e esta funcao
le o que voltou.

A REGRA DOS NOMES, que a skill mostra a pessoa:

    principal.mov          a gravacao de voce falando
    principal2.mov         se houver mais de uma gravacao sua
    complementar1.mp4      o que entra junto, na ordem em que deve aparecer
    complementar2.jpg      imagem tambem vale
    trilha.mp3             sua musica, se voce tiver uma

Arquivo com nome fora da regra nao e adivinhado nem descartado em silencio: ele
volta na lista de `nao_reconhecidos`, para quem chamou perguntar.
"""
import re
from pathlib import Path

VIDEO = (".mov", ".mp4", ".m4v", ".avi", ".mkv")
IMAGEM = (".jpg", ".jpeg", ".png", ".heic", ".webp")
AUDIO = (".mp3", ".m4a", ".wav", ".aac", ".flac")
TEXTO = (".md", ".txt", ".rtf", ".text")

_PRINCIPAL = re.compile(r"^principal\s*(\d*)$", re.I)
_COMPLEMENTAR = re.compile(r"^complementar\s*(\d*)$", re.I)
_TRILHA = re.compile(r"^trilha\s*(\d*)$", re.I)
_ROTEIRO = re.compile(r"^roteiro\s*(\d*)$", re.I)


def _ordem(nome, padrao):
    m = padrao.match(nome)
    return int(m.group(1)) if m and m.group(1) else 0


def ler(pasta):
    """Separa o que ha na pasta em principal, complementar, trilha e o resto.

    Devolve um dicionario com quatro listas de caminhos. As duas primeiras vem
    em ordem de numero: `complementar2` depois de `complementar1`, que e a
    ordem em que a pessoa quer que aparecam."""
    pasta = Path(pasta)
    achado = {"principal": [], "complementar": [], "trilha": [], "roteiro": [],
              "nao_reconhecidos": []}
    if not pasta.is_dir():
        return achado

    for caminho in sorted(pasta.iterdir()):
        if caminho.name.startswith(".") or caminho.is_dir():
            continue
        ext = caminho.suffix.lower()
        nome = caminho.stem
        if _PRINCIPAL.match(nome) and ext in VIDEO:
            achado["principal"].append(caminho)
        elif _COMPLEMENTAR.match(nome) and ext in VIDEO + IMAGEM:
            achado["complementar"].append(caminho)
        elif _TRILHA.match(nome) and ext in AUDIO:
            achado["trilha"].append(caminho)
        elif _ROTEIRO.match(nome) and ext in TEXTO:
            achado["roteiro"].append(caminho)
        elif ext in VIDEO + IMAGEM + AUDIO + TEXTO:
            achado["nao_reconhecidos"].append(caminho)

    achado["principal"].sort(key=lambda p: _ordem(p.stem, _PRINCIPAL))
    achado["complementar"].sort(key=lambda p: _ordem(p.stem, _COMPLEMENTAR))
    return achado


COMO_NOMEAR = """Renomeie os arquivos assim, e eu não erro nenhum:

  principal.mov       o vídeo de você falando para a câmera
  principal2.mov      se você gravou em mais de um arquivo
  complementar1.mp4   o que entra junto, na ordem em que deve aparecer
  complementar2.jpg   imagem também vale
  trilha.mp3          sua música, se você tiver uma

A extensão do arquivo não muda — só o nome antes do ponto."""


def em_portugues(achado, pasta=None):
    """O que foi reconhecido, e o que fazer com o resto. Para a pessoa ler."""
    linhas = []
    if achado["principal"]:
        nomes = ", ".join(p.name for p in achado["principal"])
        linhas.append(f"Gravação de você falando: {nomes}.")
    else:
        linhas.append(
            "Não achei a gravação de você falando para a câmera, que é a única "
            "coisa que eu não consigo dispensar.")
    if achado["complementar"]:
        nomes = ", ".join(p.name for p in achado["complementar"])
        linhas.append(f"Entra junto, nesta ordem: {nomes}.")
    if achado["trilha"]:
        linhas.append(f"Sua música: {achado['trilha'][0].name}.")
    if achado["roteiro"]:
        linhas.append(f"Seu roteiro: {achado['roteiro'][0].name}.")
    elif achado["principal"]:
        # a ausencia do roteiro NAO passa em silencio: quem escreveu um
        # raramente pensa em anexa-lo, e descobrir isso depois da decupagem
        # pronta joga fora a etapa mais cara do trabalho.
        linhas.append(
            "Não achei roteiro nenhum. Se você escreveu o que ia falar, ou uma "
            "lista do que quer que fique no vídeo, me manda — evita eu escolher "
            "os trechos por conta e você ter de recusar depois. Se não tem, "
            "tudo bem: eu escolho e você aprova.")
    if achado["nao_reconhecidos"]:
        nomes = ", ".join(p.name for p in achado["nao_reconhecidos"])
        linhas.append(
            f"Não sei o que fazer com estes: {nomes}. Eles não entram no vídeo "
            "enquanto não tiverem um nome que eu reconheça.")
    if achado["nao_reconhecidos"] or not achado["principal"]:
        linhas.append("")
        linhas.append(COMO_NOMEAR)
    return "\n".join(linhas)


def sugerir_renomeacao(pasta):
    """Para cada arquivo de nome estranho, o nome que ele deveria ter.

    Devolve [(caminho_atual, nome_sugerido)]. NAO renomeia nada: mexer no
    arquivo da pessoa sem ela mandar e a forma mais rapida de perder material.
    A sugestao serve para a skill mostrar o comando pronto e ela decidir."""
    achado = ler(pasta)
    soltos = achado["nao_reconhecidos"]
    if not soltos:
        return []

    # o maior video vira o principal quando ainda nao ha um: gravacao de alguem
    # falando por minutos e sempre maior que um material de apoio de segundos
    videos = [p for p in soltos if p.suffix.lower() in VIDEO]
    sugestoes, n_comp = [], len(achado["complementar"])
    principal = None
    if not achado["principal"] and videos:
        principal = max(videos, key=lambda p: p.stat().st_size)
        sugestoes.append((principal, f"principal{principal.suffix.lower()}"))

    for caminho in soltos:
        if caminho is principal:
            continue
        ext = caminho.suffix.lower()
        if ext in TEXTO:
            sugestoes.append((caminho, f"roteiro{ext}"))
        elif ext in AUDIO:
            sugestoes.append((caminho, f"trilha{ext}"))
        else:
            n_comp += 1
            sugestoes.append((caminho, f"complementar{n_comp}{ext}"))
    return sugestoes
