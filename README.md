# talking reel: done

Uma skill de Claude Code. Pega um vídeo em que alguém fala para a câmera e devolve um vertical
montado para Instagram e TikTok: pausas cortadas, letreiro, legenda queimada e trilha.

Quem usa não precisa entender de montagem. A skill pergunta o mínimo, mostra o que decidiu numa
página de aprovação, e espera a resposta antes de seguir.

## O que ela precisa

- **ffmpeg** — `brew install ffmpeg`
- **Python 3.9 ou mais novo**, com `pip install -r requirements.txt`

A transcrição baixa um modelo de cerca de 2,9 GB no primeiro uso. Só acontece quando a legenda
está ligada.

## Como instalar

```bash
git clone git@github.com:drudif/skill_talkingreel.git ~/.claude/skills/talking-reel-done
pip install -r ~/.claude/skills/talking-reel-done/requirements.txt
```

Depois é só pedir, em qualquer sessão: *"transforma esse vídeo num Reel"*.

## O motor, sozinho

O motor de montagem funciona sem a skill. De dentro da pasta do trabalho:

```bash
PYTHONPATH=~/.claude/skills/talking-reel-done python3 -m motor cenas.json saida.mp4
```

O formato do `cenas.json` está em [referencias/contrato.md](referencias/contrato.md).

## Como isto foi feito

Cada número dentro do motor custou uma rodada de erro num vídeo de verdade. O histórico está em
[docs/DIARIO.md](docs/DIARIO.md), e as armadilhas que mais custaram estão no
[CLAUDE.md](CLAUDE.md).

Os testes montam vídeo de verdade, não conferem chamadas de função:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest
```

## Origem do que veio de fora

Ver [CREDITOS.md](CREDITOS.md).
