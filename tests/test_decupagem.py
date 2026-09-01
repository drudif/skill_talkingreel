"""A conferencia que o Bandit roda antes de entregar o roteiro.

POR QUE ELA EXISTE. Numa rodada com material real, quatro defeitos passaram pela
decupagem e so foram notados assistindo ao video: um trecho terminando no meio da
palavra "Ou", dois trechos seguidos comecando com "Mas,", dois repetindo a muleta
"como voce pode ver", e um comecando com um "E" solto. Os quatro estavam na
transcricao o tempo todo.
"""
from motor import decupagem


def _p(palavra, t, f):
    return {"p": palavra, "t": t, "f": f}


def _frase(texto, inicio=0.0, passo=0.4):
    """Uma transcricao falsa, com uma palavra a cada `passo` segundos."""
    return [_p(w, inicio + i * passo, inicio + (i + 1) * passo - 0.02)
            for i, w in enumerate(texto.split())]


def _tipos(achados):
    return [a["tipo"] for a in achados]


# --- corte partindo palavra --------------------------------------------------

def test_corte_de_saida_no_meio_da_palavra(tmp_path):
    """O caso real: o trecho terminava dentro do "Ou"."""
    p = _frase("da uma olhada nesse trecho Ou seja quase nada")
    # "Ou" e a sexta palavra: comeca em 2.0 e acaba em 2.38
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0, "ate": 2.2}]
    achados = decupagem.conferir(cenas, p)
    assert "palavra partida" in _tipos(achados)
    assert "Ou" in achados[0]["o_que"]
    assert "2.0" in achados[0]["conserto"] or "2.38" in achados[0]["conserto"]


def test_corte_de_entrada_no_meio_da_palavra():
    p = _frase("uma frase qualquer para cortar")
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.2, "ate": 2.0}]
    assert "palavra partida" in _tipos(decupagem.conferir(cenas, p))


def test_corte_encostado_na_palavra_nao_acusa():
    """Cortar exatamente onde a palavra acaba e o certo, e nao pode virar
    achado -- senao nao ha corte que passe."""
    p = _frase("uma frase qualquer para cortar")
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0, "ate": 1.2}]
    assert "palavra partida" not in _tipos(decupagem.conferir(cenas, p))


# --- borda solta -------------------------------------------------------------

def test_trecho_que_comeca_em_conjuncao():
    """Os casos reais: "E como você pode ver" e "Mas, o que uma ferramenta"."""
    p = _frase("Mas o que uma ferramenta consegue fazer")
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0, "ate": 2.8}]
    achados = decupagem.conferir(cenas, p)
    assert "borda solta" in _tipos(achados)


def test_o_acento_separa_verbo_de_conjuncao():
    """Falso alarme da primeira versao: comparando sem acento, "é muito fácil"
    e "Dá uma olhada" eram acusados de comecar pela metade. "é" e verbo e "e"
    e conjuncao; "dá" e verbo e "da" e preposicao."""
    for texto in ("é muito fácil de driblar", "Dá uma olhada nisso"):
        p = _frase(texto)
        cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0,
                  "ate": len(texto.split()) * 0.4}]
        assert "borda solta" not in _tipos(decupagem.conferir(cenas, p)), (
            f'"{texto}" foi acusado, e comeca com verbo')


def test_trecho_que_termina_em_conjuncao():
    p = _frase("ele nao gerava o video mas")
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0, "ate": 2.4}]
    achados = decupagem.conferir(cenas, p)
    assert any(a["tipo"] == "borda solta" and "termina" in a["o_que"]
               for a in achados)


# --- muleta ------------------------------------------------------------------

def test_muleta_repetida_entre_trechos():
    """O caso real: "como você pode ver" em dois trechos."""
    p = (_frase("como você pode ver ele cria coisas", 0.0)
         + _frase("como você pode ver é fácil driblar", 10.0))
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0, "ate": 2.8},
             {"n": 2, "arquivo": "a.mov", "de": 10.0, "ate": 12.8}]
    achados = decupagem.conferir(cenas, p)
    assert "muleta repetida" in _tipos(achados)
    assert any("como você pode" in a["o_que"] for a in achados)


def test_muleta_dentro_do_mesmo_trecho_nao_conta():
    """Repetir dentro de uma frase e jeito de falar, e nao erro de corte."""
    p = _frase("eu acho que eu acho que sim")
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0, "ate": 3.2}]
    assert "muleta repetida" not in _tipos(decupagem.conferir(cenas, p))


# --- tomada repetida ---------------------------------------------------------

def test_duas_tomadas_da_mesma_frase():
    """O caso que o Bandit existe para resolver: a pessoa repetiu a frase e as
    duas tomadas ficaram no corte."""
    p = (_frase("o que ele tem de bom ele tem de perigoso", 0.0)
         + _frase("o que ele tem de bom ele tem de perigoso", 20.0))
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0, "ate": 4.4},
             {"n": 2, "arquivo": "a.mov", "de": 20.0, "ate": 24.4}]
    achados = decupagem.conferir(cenas, p)
    assert "tomada repetida" in _tipos(achados)


def test_trechos_diferentes_nao_sao_acusados():
    p = (_frase("saiu o modelo mais poderoso de todos", 0.0)
         + _frase("comenta ai quero que eu te mando", 20.0))
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0, "ate": 2.8},
             {"n": 2, "arquivo": "a.mov", "de": 20.0, "ate": 22.8}]
    assert "tomada repetida" not in _tipos(decupagem.conferir(cenas, p))


# --- sobreposicao e trecho vazio ---------------------------------------------

def test_dois_trechos_que_pegam_o_mesmo_pedaco():
    """A fala apareceria duas vezes no video."""
    p = _frase("uma frase bem comprida para dar espaco aqui")
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0, "ate": 2.0},
             {"n": 2, "arquivo": "a.mov", "de": 1.5, "ate": 3.2}]
    assert "trechos sobrepostos" in _tipos(decupagem.conferir(cenas, p))


def test_mesmo_intervalo_em_arquivos_diferentes_nao_acusa():
    p = _frase("uma frase qualquer")
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0, "ate": 1.0},
             {"n": 2, "arquivo": "b.mov", "de": 0.0, "ate": 1.0}]
    assert "trechos sobrepostos" not in _tipos(decupagem.conferir(cenas, p))


def test_trecho_sem_fala_nenhuma():
    p = _frase("a fala esta toda aqui no comeco")
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 60.0, "ate": 64.0}]
    assert "trecho mudo" in _tipos(decupagem.conferir(cenas, p))


def test_trecho_curto_demais():
    p = _frase("uma frase")
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0, "ate": 0.5}]
    assert "trecho curto" in _tipos(decupagem.conferir(cenas, p))


# --- duracao alvo ------------------------------------------------------------

def test_avisa_quando_passa_muito_do_que_a_pessoa_pediu():
    p = _frase("palavra " * 200, passo=0.4)
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0, "ate": 80.0}]
    achados = decupagem.conferir(cenas, p, alvo_segundos=30)
    assert "longo demais" in _tipos(achados)


def test_dentro_do_alvo_nao_avisa():
    p = _frase("palavra " * 60, passo=0.4)
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0, "ate": 24.0}]
    assert "longo demais" not in _tipos(
        decupagem.conferir(cenas, p, alvo_segundos=30))


# --- o texto -----------------------------------------------------------------

def test_decupagem_limpa_diz_que_passou():
    p = _frase("uma frase inteira que comeca e termina bem")
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0, "ate": 3.2}]
    texto = decupagem.em_portugues(decupagem.conferir(cenas, p))
    assert "passou" in texto.lower()


def test_cada_achado_diz_o_que_fazer():
    """Achado sem conserto e reclamacao. O Bandit precisa saber para onde
    mover o corte."""
    p = _frase("Mas o que uma ferramenta consegue fazer")
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0, "ate": 2.8}]
    for a in decupagem.conferir(cenas, p):
        assert a["conserto"], f"o achado '{a['tipo']}' nao diz o que fazer"


def test_os_achados_vem_do_pior_para_o_menos_grave():
    """Palavra partida e erro; muleta repetida e escolha de conteudo."""
    p = (_frase("como você pode ver uma coisa qualquer", 0.0)
         + _frase("como você pode ver outra coisa aqui", 10.0))
    cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.1, "ate": 2.8},
             {"n": 2, "arquivo": "a.mov", "de": 10.0, "ate": 12.8}]
    tipos = _tipos(decupagem.conferir(cenas, p))
    assert tipos.index("palavra partida") < tipos.index("muleta repetida")


def test_artigo_e_adverbio_nao_sao_borda_solta():
    """Medida ao rodar a primeira versao: com "um", "uma", "só", "já" e "como"
    na lista, frases perfeitamente inteiras eram acusadas. Lista grande demais
    vira ruido, e ruido faz quem le parar de olhar."""
    for texto in ("Uma coisa que aprendi nisso tudo",
                  "Já falei disso outras vezes aqui",
                  "Como você pode ver isso funciona",
                  "Só que ninguém quis pagar nada"):
        p = _frase(texto)
        cenas = [{"n": 1, "arquivo": "a.mov", "de": 0.0,
                  "ate": len(texto.split()) * 0.4}]
        assert "borda solta" not in _tipos(decupagem.conferir(cenas, p)), (
            f'"{texto}" foi acusado, e e uma frase inteira')


def test_a_conferencia_acha_os_quatro_erros_da_rodada_real():
    """O teste que justifica o modulo. Estes sao os quatro defeitos que
    passaram pela decupagem numa rodada com material de verdade e so foram
    notados assistindo ao video pronto -- todos estavam na transcricao."""
    p = (_frase("Dá uma olhada nesse trecho que ele gerou Ou seja quase", 0.0)
         + _frase("Mas como você pode ver é muito fácil de driblar", 40.0)
         + _frase("Mas o que uma ferramenta com esse poder faz", 80.0)
         + _frase("E como você pode ver ele cria coisas boas", 120.0))
    cenas = [
        {"n": 5, "arquivo": "a.mov", "de": 0.0, "ate": 4.2},    # corta o "Ou"
        {"n": 7, "arquivo": "a.mov", "de": 40.0, "ate": 44.0},  # abre com "Mas"
        {"n": 8, "arquivo": "a.mov", "de": 80.0, "ate": 83.6},  # abre com "Mas"
        {"n": 3, "arquivo": "a.mov", "de": 120.0, "ate": 124.0},  # abre com "E"
    ]
    achados = decupagem.conferir(cenas, p)
    tipos = _tipos(achados)
    assert "palavra partida" in tipos, "nao achou o corte no meio do 'Ou'"
    assert tipos.count("borda solta") >= 3, (
        "nao achou os tres trechos que abrem com conjuncao")
    assert "muleta repetida" in tipos, (
        "nao achou 'como você pode ver' repetido em dois trechos")


# --- o roteiro como guia do corte --------------------------------------------
#
# Quando a pessoa escreveu o que ia falar, o corte deixa de ser escolha do
# agente: e procurar na gravacao o que ela ja tinha decidido dizer. A
# conferencia entao olha os DOIS lados -- o que o roteiro pede e nao entrou, e
# o que entrou sem estar no roteiro.

def _transcreve(*frases):
    """Uma transcricao falsa: cada frase vira palavras com 0,3s cada, separadas
    por um segundo de silencio. Devolve (palavras, cenas)."""
    palavras, cenas, t = [], [], 0.0
    for i, frase in enumerate(frases, 1):
        de = t
        for w in frase.split():
            palavras.append({"p": w, "t": round(t, 2), "f": round(t + 0.3, 2)})
            t += 0.3
        cenas.append({"n": i, "de": round(de, 2), "ate": round(t + 0.05, 2)})
        t += 1.0
    return palavras, cenas


def _so(achados, tipo):
    return [a for a in achados if a["tipo"] == tipo]


def test_sem_roteiro_nada_disto_aparece(tmp_path):
    """A conferencia de sempre nao pode mudar de comportamento por causa de um
    campo que ninguem preencheu."""
    palavras, cenas = _transcreve("o modelo mais poderoso de geracao de video")
    achados = decupagem.conferir(cenas, palavras)
    assert not _so(achados, "fora do roteiro")
    assert not _so(achados, "faltou do roteiro")


def test_o_que_o_roteiro_pede_e_nao_foi_gravado_aparece():
    palavras, cenas = _transcreve(
        "o modelo mais poderoso de geracao de video saiu essa semana")
    roteiro = ("- o modelo mais poderoso de geracao de video\n"
               "- quanto custa a assinatura por mes e o que vem nela\n")
    faltou = _so(decupagem.conferir(cenas, palavras, roteiro=roteiro),
                    "faltou do roteiro")
    assert len(faltou) == 1
    assert "custa a assinatura" in faltou[0]["o_que"]


def test_trecho_que_nao_esta_no_roteiro_aparece():
    palavras, cenas = _transcreve(
        "o modelo mais poderoso de geracao de video saiu essa semana",
        "e eu comprei um cachorro amarelo no domingo de manha cedo")
    fora = _so(decupagem.conferir(
        cenas, palavras,
        roteiro="- o modelo mais poderoso de geracao de video\n"),
        "fora do roteiro")
    assert [a["cena"] for a in fora] == [2]


def test_o_limiar_aguenta_a_pessoa_falar_diferente_do_que_escreveu():
    """O piso da janela, medido nas seis frases que a pessoa refez na gravacao
    real: a versao mais distante de uma mesma ideia deu 0,416. Com um limiar
    acima disso, a conferencia acusaria de "fora do roteiro" um trecho que
    esta no roteiro -- e foi o que o chute inicial de 0,50 fez em tres dos seis
    pares."""
    palavras, cenas = _transcreve(
        "da uma olhada nesse trecho que ele gerou com esse prompt")
    achados = decupagem.conferir(
        cenas, palavras, roteiro="- da uma olhadinha nesse trecho que ele gerou\n")
    assert not _so(achados, "fora do roteiro"), (
        "a fala solta deixou de casar com a linha do roteiro")
    assert decupagem.DO_ROTEIRO < 0.416, (
        "o limiar subiu acima da paráfrase mais distante que foi medida")


def test_o_limiar_nao_deixa_casar_assunto_diferente():
    """O teto da janela: cinco pares de assuntos diferentes da mesma gravacao
    foram no maximo a 0,309. Abaixo disso o limiar comeca a dar por cumprida
    uma linha do roteiro que ninguem falou."""
    palavras, cenas = _transcreve(
        "ele ainda aceita ate cinquenta referencias segundo as fontes")
    achados = decupagem.conferir(
        cenas, palavras,
        roteiro="- o que uma ferramenta dessas faz nas maos erradas\n")
    assert _so(achados, "faltou do roteiro"), (
        "uma linha de outro assunto passou por cumprida")
    assert decupagem.DO_ROTEIRO > 0.309, (
        "o limiar desceu ate onde assuntos diferentes se confundem")


def test_marca_de_lista_e_titulo_nao_viram_fala():
    linhas = decupagem.linhas_do_roteiro(
        "# Roteiro do video\n\n"
        "- primeira coisa que eu falo\n"
        "2) segunda coisa que eu falo\n"
        "* terceira coisa que eu falo\n"
        "\n"
        "ok\n")
    assert linhas == ["Roteiro do video", "primeira coisa que eu falo",
                      "segunda coisa que eu falo", "terceira coisa que eu falo"]
    assert "ok" not in linhas, "linha de duas palavras nao e fala de roteiro"
