"""A skill vai morar em `~/.claude/skills/`, e a gravacao da pessoa em outro
lugar qualquer. O comando escrito na documentacao tem de funcionar DALI.

Isto e teste porque ja falhou: `python3 -m motor cenas.json saida.mp4`, como
estava escrito no SKILL.md, nao acha o motor quando a pasta de trabalho e outra
— que e o caso normal. So aparece rodando de verdade de fora do projeto."""
import json
import re
import subprocess
import sys
from pathlib import Path

from tests import fixtures

RAIZ = Path(__file__).resolve().parent.parent


def _trabalho(tmp_path):
    (tmp_path / "gravacoes").mkdir(parents=True, exist_ok=True)
    fixtures.clipe_fala(tmp_path / "gravacoes" / "t.mov",
                        falas=[(0.3, 1.5)], total=2.0)
    p = tmp_path / "cenas.json"
    p.write_text(json.dumps({"velocidade": 1.0, "legenda": False, "cenas": [
        {"n": 1, "trat": "cheia", "arquivo": "gravacoes/t.mov"}]}),
        encoding="utf-8")
    return p


def test_o_motor_roda_de_outra_pasta_com_pythonpath(tmp_path):
    _trabalho(tmp_path)
    r = subprocess.run([sys.executable, "-m", "motor", "cenas.json", "f.mp4"],
                       cwd=tmp_path, env={"PYTHONPATH": str(RAIZ),
                                          "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"},
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]
    assert (tmp_path / "f.mp4").exists()


def test_sem_pythonpath_o_motor_nao_e_encontrado(tmp_path):
    """O outro lado da moeda: se isto passar a funcionar sozinho, a instrucao
    do PYTHONPATH virou ruido e pode sair."""
    _trabalho(tmp_path)
    r = subprocess.run([sys.executable, "-m", "motor", "cenas.json", "f.mp4"],
                       cwd=tmp_path,
                       env={"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"},
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "No module named motor" in r.stderr


def test_a_documentacao_manda_usar_pythonpath():
    """Se o comando na documentacao voltar a ser o que nao funciona, isto
    acusa antes de a pessoa descobrir sozinha."""
    for arq in ("SKILL.md", "referencias/agentes/bingo.md"):
        texto = (RAIZ / arq).read_text(encoding="utf-8")
        comandos = re.findall(r"python3 -m motor[^\n`]*", texto)
        assert comandos, f"{arq} nao mostra o comando de montar"
        for c in comandos:
            i = texto.index(c)
            assert "PYTHONPATH" in texto[max(0, i - 120):i], (
                f"{arq} mostra `{c}` sem o PYTHONPATH antes")


def test_o_requirements_lista_o_que_o_motor_importa():
    req = (RAIZ / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "pillow" in req, "falta Pillow, que desenha todo o texto"
    assert "mlx-whisper" in req, "falta mlx-whisper, que transcreve"
    assert "ffmpeg" in req, "o requirements tem de avisar que o ffmpeg e a parte"
