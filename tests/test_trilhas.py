"""As trilhas que vem com a skill.

As quatro faixas NAO entram no repositorio -- e musica, e quem instala poe a
sua. Entao estes testes se dividem em dois: os que valem sempre, sobre a lista
e sobre nao prometer o que nao existe, e os que so rodam quando as faixas
estiverem na pasta.
"""
import pytest

from motor import trilha


def test_a_lista_tem_quatro_faixas_e_diz_para_que_serve_cada_uma():
    """A Chili escolhe olhando esta descricao. Uma faixa sem descricao e uma
    faixa que ela vai escolher no chute."""
    assert len(trilha.PRONTAS) == 4
    for nome, quando in trilha.PRONTAS.items():
        assert len(quando) > 20, f"a faixa '{nome}' nao diz quando serve"


def test_pasta_vazia_nao_promete_faixa_nenhuma(tmp_path):
    """O modo de falhar que isto evita: a Chili poe no `cenas.json` o caminho
    de uma faixa que nao existe, e a montagem quebra depois de todo o trabalho
    feito."""
    assert trilha.disponiveis(tmp_path) == {}


def test_so_devolve_o_que_esta_no_disco(tmp_path):
    (tmp_path / "calma.mp3").write_bytes(b"")
    achadas = trilha.disponiveis(tmp_path)
    assert set(achadas) == {"calma"}
    assert achadas["calma"].exists()


def test_aceita_os_formatos_de_audio_que_o_motor_le(tmp_path):
    (tmp_path / "tensao.m4a").write_bytes(b"")
    assert "tensao" in trilha.disponiveis(tmp_path)


def test_arquivo_com_nome_fora_da_lista_e_ignorado(tmp_path):
    """A lista e fechada de proposito: a Chili escolhe entre quatro, e um
    arquivo solto na pasta viraria uma quinta opcao sem descricao nenhuma."""
    (tmp_path / "minha-musica.mp3").write_bytes(b"")
    assert trilha.disponiveis(tmp_path) == {}


def test_o_leia_me_da_pasta_lista_as_mesmas_quatro():
    """Duas listas em lugares diferentes viram duas listas diferentes."""
    texto = (trilha.pasta() / "LEIA-ME.md").read_text(encoding="utf-8")
    for nome in trilha.PRONTAS:
        assert nome in texto, f"o LEIA-ME nao cita a faixa '{nome}'"


@pytest.mark.skipif(not trilha.disponiveis(),
                    reason="as quatro trilhas ainda nao foram postas em "
                           "assets/trilhas/ -- ver o LEIA-ME de la")
def test_as_faixas_instaladas_tocam_de_verdade():
    """So roda quando as faixas existirem. Um arquivo com o nome certo e sem
    audio dentro passaria por todos os outros testes e quebraria na montagem."""
    from motor import probe
    for nome, caminho in trilha.disponiveis().items():
        assert probe.dur(caminho) > 5.0, (
            f"a faixa '{nome}' tem menos de 5 segundos ou nao e audio")
