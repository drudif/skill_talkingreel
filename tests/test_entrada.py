"""A leitura do material por nome.

O PROBLEMA QUE ISTO RESOLVE. A pessoa larga os arquivos numa pasta e diz "esta
tudo ai". Adivinhar pelo conteudo qual e a gravacao dela, qual e material de
apoio e qual e musica seria caro e falivel; pedir NOME e barato e nao erra.

Numa rodada com material real esta leitura pegou de primeira um
`complememtar3.mp4` escrito com "m" -- que, sem ela, ficaria de fora do video
sem ninguem notar.
"""
from motor import entrada


def _com(tmp_path, *nomes):
    for n in nomes:
        (tmp_path / n).write_bytes(b"x")
    return tmp_path


def test_separa_cada_coisa_pelo_nome(tmp_path):
    d = _com(tmp_path, "principal.mov", "complementar1.mp4",
             "complementar2.jpg", "trilha.mp3", "roteiro.md")
    a = entrada.ler(d)
    assert [p.name for p in a["principal"]] == ["principal.mov"]
    assert [p.name for p in a["complementar"]] == ["complementar1.mp4",
                                                   "complementar2.jpg"]
    assert [p.name for p in a["trilha"]] == ["trilha.mp3"]
    assert [p.name for p in a["roteiro"]] == ["roteiro.md"]
    assert a["nao_reconhecidos"] == []


def test_os_complementares_vem_na_ordem_dos_numeros(tmp_path):
    """`complementar12` vem depois de `complementar2`, e nao entre 1 e 2: e a
    ordem em que a pessoa quer que eles aparecam."""
    d = _com(tmp_path, "complementar12.mov", "complementar2.mp4",
             "complementar1.mov")
    nomes = [p.name for p in entrada.ler(d)["complementar"]]
    assert nomes == ["complementar1.mov", "complementar2.mp4",
                     "complementar12.mov"]


def test_nome_fora_da_regra_nao_e_adivinhado_nem_sumido(tmp_path):
    """O caso real: `complememtar3.mp4`, com "m" no lugar do "n". Adivinhar
    seria arriscar por o arquivo errado no video; descartar em silencio o
    deixaria de fora sem ninguem notar."""
    d = _com(tmp_path, "principal.mov", "complememtar3.mp4")
    a = entrada.ler(d)
    assert [p.name for p in a["nao_reconhecidos"]] == ["complememtar3.mp4"]
    assert a["complementar"] == []
    texto = entrada.em_portugues(a)
    assert "complememtar3.mp4" in texto
    assert "nome que eu reconheça" in texto


def test_arquivo_que_nao_e_midia_nem_texto_e_ignorado(tmp_path):
    d = _com(tmp_path, "principal.mov", "notas.pdf", "planilha.xlsx")
    a = entrada.ler(d)
    assert a["nao_reconhecidos"] == []


def test_arquivo_escondido_e_pasta_nao_entram(tmp_path):
    (tmp_path / "sub").mkdir()
    d = _com(tmp_path, "principal.mov", ".DS_Store")
    assert entrada.ler(d)["nao_reconhecidos"] == []


# --- o roteiro ---------------------------------------------------------------

def test_a_falta_de_roteiro_nao_passa_em_silencio(tmp_path):
    """Quem escreveu um roteiro raramente pensa em anexa-lo, e descobrir isso
    depois da decupagem pronta joga fora a etapa mais cara do trabalho. Entao a
    ausencia dele e dita, e vira pergunta."""
    d = _com(tmp_path, "principal.mov")
    texto = entrada.em_portugues(entrada.ler(d))
    assert "não achei roteiro" in texto.lower()
    assert "me manda" in texto.lower(), "nao pede o roteiro"
    assert "se não tem, tudo bem" in texto.lower(), (
        "a falta de roteiro nao pode soar como erro: e o caso normal")


def test_com_roteiro_a_skill_nao_pergunta(tmp_path):
    d = _com(tmp_path, "principal.mov", "roteiro.txt")
    texto = entrada.em_portugues(entrada.ler(d))
    assert "roteiro.txt" in texto
    assert "não achei roteiro" not in texto.lower()


def test_sem_gravacao_nao_pergunta_pelo_roteiro(tmp_path):
    """Falta a unica coisa indispensavel. Pedir o roteiro junto misturaria o
    que trava o trabalho com o que so ajuda."""
    texto = entrada.em_portugues(entrada.ler(tmp_path))
    assert "não achei a gravação" in texto.lower()
    assert "não achei roteiro" not in texto.lower()


def test_texto_com_nome_estranho_vira_sugestao_de_roteiro(tmp_path):
    d = _com(tmp_path, "principal.mov", "minhas anotacoes.txt")
    sugestoes = {a.name: n for a, n in entrada.sugerir_renomeacao(d)}
    assert sugestoes["minhas anotacoes.txt"] == "roteiro.txt"


# --- a gravacao, que e a unica obrigatoria -----------------------------------

def test_sem_gravacao_a_skill_diz_que_nao_da_para_seguir(tmp_path):
    d = _com(tmp_path, "complementar1.mp4")
    texto = entrada.em_portugues(entrada.ler(d))
    assert "não consigo dispensar" in texto.lower()


def test_o_maior_video_solto_vira_o_principal(tmp_path):
    """Gravacao de alguem falando por minutos e sempre maior que um material de
    apoio de segundos. A sugestao NAO renomeia nada: mexer no arquivo da pessoa
    sem ela mandar e a forma mais rapida de perder material."""
    d = tmp_path
    (d / "IMG_9141.mov").write_bytes(b"x" * 5000)
    (d / "clipe.mp4").write_bytes(b"x" * 10)
    sugestoes = {a.name: n for a, n in entrada.sugerir_renomeacao(d)}
    assert sugestoes["IMG_9141.mov"] == "principal.mov"
    assert sugestoes["clipe.mp4"].startswith("complementar")
    assert (d / "IMG_9141.mov").exists(), "sugerir_renomeacao mexeu no arquivo"


def test_com_principal_ja_nomeado_o_resto_vira_complementar(tmp_path):
    d = tmp_path
    (d / "principal.mov").write_bytes(b"x" * 5000)
    (d / "outro.mov").write_bytes(b"x" * 9000)
    sugestoes = {a.name: n for a, n in entrada.sugerir_renomeacao(d)}
    assert sugestoes["outro.mov"] == "complementar1.mov"


def test_a_regra_de_nomes_aparece_quando_ha_o_que_corrigir(tmp_path):
    d = _com(tmp_path, "principal.mov", "coisa.mp4")
    texto = entrada.em_portugues(entrada.ler(d))
    assert "principal.mov" in texto and "complementar1.mp4" in texto
    assert "roteiro" in texto.lower()


def test_pasta_que_nao_existe_nao_quebra(tmp_path):
    a = entrada.ler(tmp_path / "nao-existe")
    assert a["principal"] == [] and a["nao_reconhecidos"] == []
