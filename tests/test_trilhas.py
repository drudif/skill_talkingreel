"""As trilhas que vem guardadas com a skill.

O desenho aqui mudou depois que as faixas de verdade chegaram: a primeira
versao exigia quatro nomes fixos (`calma.mp3`, `tensao.mp3`...) e nenhuma das
quatro faixas reais tinha esses nomes. Exigir nome canonico obriga quem instala
a renomear musica baixada, e o unico ganho seria um rotulo que ninguem conferiu.

O que substitui o rotulo e medida, e e o que estes testes protegem.
"""
import pytest

from motor import trilha


def _falso_audio(destino, segundos=8.0, freq=220):
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", str(segundos),
         "-i", f"sine=frequency={freq}:sample_rate=48000", str(destino)],
        check=True)
    return destino


# --- o que a pasta devolve ---

def test_pasta_vazia_nao_promete_faixa_nenhuma(tmp_path):
    """O modo de falhar que isto evita: a Chili poe no `cenas.json` o caminho
    de uma faixa que nao existe, e a montagem quebra depois de todo o trabalho
    feito."""
    assert trilha.disponiveis(tmp_path) == []


def test_aceita_qualquer_nome_de_arquivo(tmp_path):
    """A correcao que motivou a reescrita. As faixas reais chegaram com nomes
    de exportador, com carimbo de data e tudo."""
    _falso_audio(tmp_path / "Latino_Lo-fi_Dreams_2026-07-27T210721.mp3")
    achadas = trilha.disponiveis(tmp_path)
    assert len(achadas) == 1


def test_o_carimbo_de_data_sai_do_nome(tmp_path):
    """Quem le a folha nao tem o que fazer com a hora em que o arquivo foi
    baixado, e o carimbo empurra o nome de verdade para fora da linha."""
    _falso_audio(tmp_path / "Amor_e_Ritmo_2026-08-31T172951.mp3")
    assert trilha.disponiveis(tmp_path)[0]["nome"] == "Amor e Ritmo"


def test_arquivo_que_nao_e_audio_e_ignorado(tmp_path):
    (tmp_path / "LEIA-ME.md").write_text("isto nao e musica")
    (tmp_path / "capa.png").write_bytes(b"nem isto")
    assert trilha.disponiveis(tmp_path) == []


def test_arquivo_curto_demais_nao_e_trilha(tmp_path):
    """Um efeito sonoro de 2 segundos na pasta viraria uma opcao de trilha."""
    _falso_audio(tmp_path / "bip.mp3", segundos=2.0)
    _falso_audio(tmp_path / "musica.mp3", segundos=20.0)
    achadas = trilha.disponiveis(tmp_path)
    assert [f["nome"] for f in achadas] == ["musica"]


def test_arquivo_quebrado_nao_derruba_a_lista(tmp_path):
    _falso_audio(tmp_path / "boa.mp3", segundos=10.0)
    (tmp_path / "quebrada.mp3").write_bytes(b"isto nao abre")
    achadas = trilha.disponiveis(tmp_path)
    assert [f["nome"] for f in achadas] == ["boa"]


# --- a medida, que substitui o rotulo ---

def test_as_faixas_vem_da_mais_parada_para_a_mais_agitada(tmp_path):
    """A ordem E a informacao: sem rotulo, a Chili escolhe comparando as faixas
    entre si, e a ordem e o que torna a comparacao possivel."""
    import subprocess
    parada = tmp_path / "parada.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", "12",
                    "-i", "sine=frequency=110:sample_rate=48000", str(parada)],
                   check=True)
    agitada = tmp_path / "agitada.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", "12",
                    "-i", "sine=frequency=110:sample_rate=48000",
                    "-af", "tremolo=f=8:d=0.9", str(agitada)], check=True)
    nomes = [f["nome"] for f in trilha.disponiveis(tmp_path)]
    assert nomes == ["parada", "agitada"], (
        f"a ordem saiu {nomes}: a faixa que pulsa oito vezes por segundo "
        "deveria contar mais picos que um tom continuo")


def test_a_medida_traz_duracao_e_picos(tmp_path):
    _falso_audio(tmp_path / "m.mp3", segundos=15.0)
    f = trilha.disponiveis(tmp_path)[0]
    assert abs(f["duracao"] - 15.0) < 0.5
    assert "picos_por_minuto" in f and "energia" in f


# --- o texto que vai para a folha ---

def test_o_texto_da_folha_avisa_que_a_faixa_vai_repetir(tmp_path):
    """A pessoa precisa saber disso ANTES de escolher: uma faixa de 45 segundos
    debaixo de um video de tres minutos toca quatro vezes."""
    _falso_audio(tmp_path / "curta.mp3", segundos=10.0)
    texto = trilha.em_portugues(trilha.disponiveis(tmp_path),
                                duracao_do_filme=60).lower()
    assert "repetir" in texto


def test_o_texto_da_folha_nao_avisa_de_repeticao_a_toa(tmp_path):
    _falso_audio(tmp_path / "longa.mp3", segundos=60.0)
    texto = trilha.em_portugues(trilha.disponiveis(tmp_path),
                                duracao_do_filme=30).lower()
    assert "repetir" not in texto


def test_sem_trilha_nenhuma_o_texto_diz_o_que_fazer(tmp_path):
    texto = trilha.em_portugues(trilha.disponiveis(tmp_path)).lower()
    assert "sem musica" in texto or "mandar a musica" in texto


def test_o_texto_da_folha_nao_usa_termo_tecnico(tmp_path):
    _falso_audio(tmp_path / "x.mp3", segundos=20.0)
    texto = trilha.em_portugues(trilha.disponiveis(tmp_path), 40).lower()
    for termo in ("bpm", "rms", "envelope", "picos_por_minuto", "energia",
                  "codec", "bitrate"):
        assert termo not in texto, f"o texto da folha usa '{termo}'"


# --- as faixas de verdade, quando estiverem instaladas ---

@pytest.mark.skipif(not trilha.disponiveis(),
                    reason="nao ha trilha em assets/trilhas/ -- ver o LEIA-ME")
def test_as_faixas_instaladas_abrem_e_tem_duracao_de_musica():
    for f in trilha.disponiveis():
        assert f["duracao"] >= trilha.MIN_SEGUNDOS, (
            f"a faixa '{f['nome']}' tem {f['duracao']}s")
        assert not f.get("ilegivel")
