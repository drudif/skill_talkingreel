import json
import re

import pytest

from motor import folha


def _itens(n=2):
    return [{"id": f"i{k}", "titulo": f"Item {k}",
             "fato": f"Fato medido numero {k}."} for k in range(n)]


def test_gera_um_documento_completo(tmp_path):
    p = folha.escrever(_itens(), "primeira", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "</html>" in html


def test_cada_item_aparece_uma_vez(tmp_path):
    p = folha.escrever(_itens(3), "primeira", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    for k in range(3):
        assert html.count(f"Fato medido numero {k}.") == 1


def test_o_estado_esta_entre_os_marcadores_uma_vez_so(tmp_path):
    """A armadilha do projeto de origem: dois blocos parecidos no mesmo
    arquivo, e quem lesse o segundo apagava o feedback da pessoa."""
    p = folha.escrever(_itens(), "primeira", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    assert html.count(folha.INI) == 1, "o marcador de inicio aparece mais de uma vez"
    assert html.count(folha.FIM) == 1, "o marcador de fim aparece mais de uma vez"


def test_o_estado_e_json_valido_e_traz_os_itens(tmp_path):
    p = folha.escrever(_itens(2), "segunda", tmp_path / "f.html")
    estado = folha.ler(p)
    assert estado["fase"] == "segunda"
    assert [i["id"] for i in estado["itens"]] == ["i0", "i1"]
    assert all(i["decisao"] is None for i in estado["itens"])


def test_ler_devolve_as_decisoes_que_a_pessoa_tomou(tmp_path):
    p = folha.escrever(_itens(2), "primeira", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    estado = folha.ler(p)
    estado["itens"][0]["decisao"] = "aprovado"
    estado["itens"][1]["decisao"] = "reprovado"
    estado["itens"][1]["nota"] = "esse trecho nao"
    novo = html.replace(
        html[html.index(folha.INI):html.index(folha.FIM) + len(folha.FIM)],
        folha.INI + json.dumps(estado, ensure_ascii=False) + folha.FIM)
    (tmp_path / "g.html").write_text(novo, encoding="utf-8")
    lido = folha.ler(tmp_path / "g.html")
    assert lido["itens"][0]["decisao"] == "aprovado"
    assert lido["itens"][1]["nota"] == "esse trecho nao"


def test_texto_com_html_dentro_nao_quebra_a_pagina(tmp_path):
    itens = [{"id": "x", "titulo": "<script>alert(1)</script>",
              "fato": 'aspas " e < e &'}]
    p = folha.escrever(itens, "primeira", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert folha.ler(p)["itens"][0]["titulo"] == "<script>alert(1)</script>"


def test_folha_sem_item_nenhum_diz_isso(tmp_path):
    p = folha.escrever([], "segunda", tmp_path / "f.html")
    assert "nada" in p.read_text(encoding="utf-8").lower()


def test_id_repetido_e_recusado(tmp_path):
    itens = [{"id": "a", "titulo": "A", "fato": "."},
             {"id": "a", "titulo": "B", "fato": "."}]
    with pytest.raises(ValueError, match="repetid"):
        folha.escrever(itens, "primeira", tmp_path / "f.html")


def test_item_sem_id_e_recusado(tmp_path):
    with pytest.raises(ValueError, match="id"):
        folha.escrever([{"titulo": "A", "fato": "."}], "primeira",
                       tmp_path / "f.html")


def test_a_pagina_e_pequena(tmp_path):
    """O custo de token de uma pagina grande e real: no projeto de origem o
    modelo reescrevia 50 KB de HTML a cada rodada."""
    p = folha.escrever(_itens(5), "primeira", tmp_path / "f.html")
    assert len(p.read_bytes()) < 12_000, (
        f"a folha de 5 itens saiu com {len(p.read_bytes())} bytes")


def test_a_folha_seguinte_carrega_so_o_pendente(tmp_path):
    from motor import registro
    itens = [{"id": f"i{k}", "titulo": f"Item {k}", "fato": "."}
             for k in range(5)]
    reg = tmp_path / "registro.json"

    p1 = folha.publicar(itens, "primeira", tmp_path / "f1.html", reg)
    assert len(folha.ler(p1)["itens"]) == 5

    # a pessoa decide tres e a pagina se republica
    estado = folha.ler(p1)
    for k, d in ((0, "aprovado"), (1, "reprovado"), (2, "aprovado")):
        estado["itens"][k]["decisao"] = d
    folha.recolher(estado, reg)

    p2 = folha.publicar(itens, "primeira", tmp_path / "f2.html", reg)
    assert [i["id"] for i in folha.ler(p2)["itens"]] == ["i3", "i4"]


def test_recolher_guarda_a_nota_junto(tmp_path):
    from motor import registro
    reg = tmp_path / "r.json"
    folha.recolher({"fase": "segunda", "itens": [
        {"id": "a", "decisao": "reprovado", "nota": "muito rapido"}]}, reg)
    assert registro.carregar(reg)["a"]["nota"] == "muito rapido"


def test_recolher_ignora_quem_nao_decidiu(tmp_path):
    from motor import registro
    reg = tmp_path / "r.json"
    folha.recolher({"fase": "segunda", "itens": [
        {"id": "a", "decisao": None, "nota": ""}]}, reg)
    assert registro.carregar(reg) == {}


def test_tudo_decidido_da_uma_folha_vazia(tmp_path):
    reg = tmp_path / "r.json"
    itens = [{"id": "a", "titulo": "A", "fato": "."}]
    folha.recolher({"fase": "segunda", "itens": [
        {"id": "a", "decisao": "aprovado", "nota": ""}]}, reg)
    p = folha.publicar(itens, "segunda", tmp_path / "f.html", reg)
    assert folha.ler(p)["itens"] == []
    assert "nada" in p.read_text(encoding="utf-8").lower()


def test_nota_com_fecha_script_nao_quebra_a_pagina_republicada(tmp_path):
    """A pessoa escreve `</script>` numa observacao. Sem escapar, o navegador
    fecha a tag do bloco de dados ali e a pagina republicada nasce quebrada:
    o estado some e ela perde tudo que decidiu.

    O Python ja escapa quando GERA a folha; este teste cobre o outro lado, o
    JavaScript que a pagina roda quando se republica."""
    import json
    import re
    import subprocess

    p = folha.escrever([{"id": "a", "titulo": "A", "fato": "."}],
                       "primeira", tmp_path / "f.html")
    html = p.read_text(encoding="utf-8")
    js = re.findall(r"<script>([\s\S]*?)</script>", html)[-1]

    programa = f"""
const E = {{"fase":"primeira","itens":[
  {{"id":"a","titulo":"A","decisao":"aprovado","nota":"olha o </script> aqui"}}]}};
const saida = {json.dumps(html)}.replace(
  new RegExp('(/\\\\*E-'+'INI\\\\*/)[\\\\s\\\\S]*?(/\\\\*E-'+'FIM\\\\*/)'),
  (m,i,f)=>i+JSON.stringify(E).replace(/</g,'\\\\u003c')+f);
process.stdout.write(saida);
"""
    r = subprocess.run(["node", "-e", programa], capture_output=True, text=True)
    if r.returncode != 0:
        import pytest
        pytest.skip(f"node nao rodou aqui: {r.stderr[:120]}")

    novo = tmp_path / "g.html"
    novo.write_text(r.stdout, encoding="utf-8")
    bloco = r.stdout[r.stdout.index(folha.INI):r.stdout.index(folha.FIM)]
    assert "</script>" not in bloco, (
        "o `</script>` foi para dentro do bloco de dados e fecha a tag cedo")
    assert folha.ler(novo)["itens"][0]["nota"] == "olha o </script> aqui", (
        "o texto nao sobreviveu a ida e volta")
    assert js.count("JSON.stringify(E).replace") == 1, (
        "o JavaScript da pagina voltou a serializar sem escapar")


# ---------------------------------------------------------------------------
# Secoes, escolha unica, e as palavras dos botoes
#
# A folha antiga era uma lista corrida de coisas de natureza diferente --
# estilo, musica, corte -- todas com os mesmos dois botoes. Quem lia nao sabia
# se estava escolhendo entre opcoes ou aprovando uma a uma.
# ---------------------------------------------------------------------------

def _secoes():
    return [
        {"id": "estilo", "titulo": "ESTILO DE LETTERING E LEGENDAS",
         "instrucao": "Veja os estilos disponiveis e escolha um.",
         "tipo": "escolha",
         "itens": [{"id": "e1", "titulo": "terminal", "fato": "escuro"},
                   {"id": "e2", "titulo": "brutalista", "fato": "amarelo"}]},
        {"id": "trechos", "titulo": "TRECHOS ESCOLHIDOS",
         "instrucao": "Marque cada um.", "tipo": "decisao",
         "itens": [{"id": "t1", "titulo": "Trecho 1", "fato": "."}]},
    ]


def test_os_botoes_dizem_aprovado_e_reprovado(tmp_path):
    """'Pode ir' e 'tira' deixam margem: a folha e o registro do que foi
    combinado, e cada lado lembra de um jeito."""
    t = folha.escrever(_secoes(), "primeira",
                       tmp_path / "f.html").read_text(encoding="utf-8")
    assert ">APROVADO<" in t and ">REPROVADO<" in t
    for informal in ("Pode ir", "Tira<", "descartado"):
        assert informal not in t, f"a folha ainda diz '{informal}'"


def test_a_secao_traz_titulo_e_instrucao(tmp_path):
    t = folha.escrever(_secoes(), "primeira",
                       tmp_path / "f.html").read_text(encoding="utf-8")
    assert "ESTILO DE LETTERING E LEGENDAS" in t
    assert "Veja os estilos disponiveis e escolha um." in t
    assert t.count("<section>") == 2


def test_escolha_unica_usa_radio_e_nao_tem_observacao(tmp_path):
    """Oferecer aprovar/reprovar em cada um dos sete estilos convida a aprovar
    tres, e nao ha o que fazer com isso."""
    t = folha.escrever(_secoes(), "primeira",
                       tmp_path / "f.html").read_text(encoding="utf-8")
    assert 'type="radio"' in t
    assert t.count('name="estilo"') == 2, (
        "os dois estilos precisam do mesmo nome de grupo para um desmarcar o "
        "outro")
    # o campo de observacao existe na secao de decisao, e so nela
    assert t.count('class="nota"') == 1


def test_o_grupo_da_escolha_vai_para_o_estado(tmp_path):
    """E o que o JavaScript usa para desmarcar os irmaos, e o que diz depois,
    na leitura, que aquele item era de escolha."""
    p = folha.escrever(_secoes(), "primeira", tmp_path / "f.html")
    estado = folha.ler(p)
    por_id = {i["id"]: i for i in estado["itens"]}
    assert por_id["e1"]["grupo"] == "estilo"
    assert por_id["t1"]["grupo"] is None


def test_a_escolha_e_recolhida_como_decisao(tmp_path):
    from motor import registro
    reg = tmp_path / "r.json"
    estado = {"fase": "primeira", "itens": [
        {"id": "e2", "decisao": "escolhido", "nota": ""},
        {"id": "t1", "decisao": "reprovado", "nota": "ficou longo"}]}
    folha.recolher(estado, reg)
    guardado = registro.carregar(reg)
    assert guardado["e2"]["decisao"] == "escolhido"
    assert guardado["t1"]["nota"] == "ficou longo"


def test_secao_que_ficou_vazia_nao_aparece(tmp_path):
    """Titulo sozinho, sem nada embaixo, faz a pessoa procurar o que nao
    existe."""
    reg = tmp_path / "r.json"
    folha.recolher({"fase": "primeira", "itens": [
        {"id": "e1", "decisao": "escolhido"},
        {"id": "e2", "decisao": "reprovado"}]}, reg)
    t = folha.publicar(_secoes(), "primeira", tmp_path / "f.html",
                       reg).read_text(encoding="utf-8")
    assert "ESTILO DE LETTERING E LEGENDAS" not in t
    assert "TRECHOS ESCOLHIDOS" in t


def test_lista_simples_de_itens_ainda_funciona(tmp_path):
    """Quem chama do jeito antigo recebe um bloco de decisao, e nao um erro."""
    t = folha.escrever(_itens(2), "primeira",
                       tmp_path / "f.html").read_text(encoding="utf-8")
    assert ">APROVADO<" in t and "<section>" in t


def test_tipo_de_secao_desconhecido_e_erro(tmp_path):
    with pytest.raises(ValueError, match="escolha"):
        folha.escrever([{"id": "x", "titulo": "X", "tipo": "votacao",
                         "itens": _itens(1)}], "primeira", tmp_path / "f.html")


# ---------------------------------------------------------------------------
# A folha so envia quando a pessoa manda
# ---------------------------------------------------------------------------

def test_a_folha_so_publica_no_botao_de_enviar(tmp_path):
    """Antes a folha se republicava a cada clique. Isso enche quem espera de
    aviso a cada marcacao, gasta uma versao por clique, e abre a porta para
    duas publicacoes se atropelarem enquanto a pessoa ainda esta decidindo."""
    t = folha.escrever(_secoes(), "primeira",
                       tmp_path / "f.html").read_text(encoding="utf-8")
    assert 'id="enviar"' in t
    # a publicacao mora dentro da funcao enviar(), e nao no tratador de clique
    assert "function enviar()" in t
    corpo_do_clique = t[t.index("addEventListener('click'"):]
    assert "publish(" not in corpo_do_clique, (
        "o clique ainda publica direto; deveria so guardar e esperar o envio")


def test_o_botao_comeca_desligado_e_a_folha_conta_o_que_falta(tmp_path):
    t = folha.escrever(_secoes(), "primeira",
                       tmp_path / "f.html").read_text(encoding="utf-8")
    assert '<button id="enviar" disabled>' in t
    assert 'id="placar"' in t
    assert "respondidos" in t


def test_a_folha_guarda_o_que_foi_marcado_antes_de_enviar(tmp_path):
    """Se a pessoa fechar a aba sem querer no meio, ou o navegador recarregar,
    o que ela ja marcou nao pode sumir."""
    t = folha.escrever(_secoes(), "primeira",
                       tmp_path / "f.html").read_text(encoding="utf-8")
    assert "localStorage.setItem" in t and "localStorage.getItem" in t
    assert "beforeunload" in t, (
        "sair com resposta nao enviada deveria avisar")


def test_o_estado_gravado_na_pagina_comeca_vazio(tmp_path):
    """O que a pessoa marca so entra no arquivo quando ela envia. Antes disso a
    folha publicada continua sendo a que foi mandada para ela."""
    p = folha.escrever(_secoes(), "primeira", tmp_path / "f.html")
    estado = folha.ler(p)
    assert all(i["decisao"] is None for i in estado["itens"])
    assert all(i["nota"] == "" for i in estado["itens"])


def test_escolher_um_resolve_o_bloco_inteiro(tmp_path):
    """Achado com material real: a pessoa escolheu um dos sete estilos, e a
    folha seguinte trouxe os outros seis de volta. Eles nao ficaram pendentes
    -- ficaram para tras -- e ve-los de novo faz ela achar que falta marcar
    mais alguma coisa ali."""
    reg = tmp_path / "r.json"
    folha.recolher({"fase": "primeira",
                    "itens": [{"id": "e2", "decisao": "escolhido"}]}, reg)
    t = folha.publicar(_secoes(), "primeira", tmp_path / "f.html",
                       reg).read_text(encoding="utf-8")
    assert "ESTILO DE LETTERING E LEGENDAS" not in t, (
        "o bloco de escolha voltou depois de a pessoa ja ter escolhido")
    assert "TRECHOS ESCOLHIDOS" in t, "o resto da folha sumiu junto"


def test_bloco_de_escolha_sem_escolha_continua_inteiro(tmp_path):
    """O contrario do teste acima: enquanto ninguem escolheu, os sete ficam --
    inclusive os que foram reprovados um a um, que numa escolha nao querem
    dizer nada."""
    reg = tmp_path / "r.json"
    folha.recolher({"fase": "primeira",
                    "itens": [{"id": "t1", "decisao": "aprovado"}]}, reg)
    t = folha.publicar(_secoes(), "primeira", tmp_path / "f.html",
                       reg).read_text(encoding="utf-8")
    assert "ESTILO DE LETTERING E LEGENDAS" in t
    assert "TRECHOS ESCOLHIDOS" not in t


# --- embutir imagem e som ----------------------------------------------------

def _jpg(caminho, larg=1080, alt=1920):
    from PIL import Image
    Image.new("RGB", (larg, alt), (30, 90, 160)).save(caminho)
    return caminho


def test_a_folha_publicada_nao_alcanca_o_disco(tmp_path):
    """O modo de falhar que isto evita e silencioso: `src="foto.jpg"` abre
    certo na maquina de quem escreveu e nao aparece na tela de quem decide."""
    arq = _jpg(tmp_path / "previa.jpg")
    uri = folha.embutir(arq, largura=folha.LARGURA_PREVIA)
    assert uri.startswith("data:image/jpeg;base64,")
    caminho = folha.escrever(
        [{"id": "e", "titulo": "ESTILO", "tipo": "escolha",
          "itens": [{"id": "a", "titulo": "Amarelo", "miniatura": uri}]}],
        "primeira", tmp_path / "f.html")
    html = caminho.read_text()
    assert "previa.jpg" not in html, "sobrou caminho de disco na folha"
    assert "data:image/jpeg;base64," in html


def test_encolher_e_o_que_faz_a_folha_caber(tmp_path):
    """22 previas de 1080x1920 somam 5,2 MB no disco e 6,9 MB em base64. So
    elas ja passariam de metade do teto."""
    arq = _jpg(tmp_path / "grande.jpg")
    inteira = folha.embutir(arq)
    reduzida = folha.embutir(arq, largura=folha.LARGURA_PREVIA)
    assert len(reduzida) < len(inteira) / 2


def test_encolher_nao_estica_imagem_pequena(tmp_path):
    import base64
    from io import BytesIO

    from PIL import Image
    arq = _jpg(tmp_path / "pequena.jpg", 200, 300)
    uri = folha.embutir(arq, largura=folha.LARGURA_PREVIA)
    im = Image.open(BytesIO(base64.b64decode(uri.split(",", 1)[1])))
    assert im.size == (200, 300)


def test_a_amostra_de_musica_e_curta(tmp_path):
    """A trilha inteira de um dos arquivos reais tem 5,5 MB. Embutir tres
    assim estouraria o teto sozinho, e ninguem precisa da musica inteira para
    reconhece-la."""
    import subprocess
    som = tmp_path / "trilha.mp3"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=90",
                    str(som)], check=True)
    uri = folha.embutir(som, segundos=25)
    assert uri.startswith("data:audio/mpeg;base64,")
    assert len(uri) < len(som.read_bytes()) * 0.6


def test_cabe_avisa_antes_de_publicar(tmp_path):
    caminho = folha.escrever([{"id": "x", "titulo": "T", "fato": "f"}],
                             "primeira", tmp_path / "f.html")
    tamanho, passa = folha.cabe(caminho)
    assert passa and 0 < tamanho < folha.TETO_FOLHA


def test_o_botao_nao_diz_enviado_antes_de_haver_resposta(tmp_path):
    """Ele nascia escrito ENVIADO e desligado. Quem abre a folha le que ja
    enviou alguma coisa, sem ter respondido nada."""
    html = folha.escrever([{"id": "x", "titulo": "T", "fato": "f"}],
                          "primeira", tmp_path / "f.html").read_text()
    botao = html.split('id="enviar"')[1].split("</button>")[0]
    assert "ENVIADO" not in botao
    assert "NADA PARA ENVIAR" in botao


def test_o_aviso_de_falta_enviar_sobrevive_a_recarga(tmp_path):
    """O que foi marcado fica no navegador, mas o `falta enviar` se perdia:
    ao voltar, a folha dizia TUDO ENVIADO com nada enviado."""
    js = folha.escrever([{"id": "x", "titulo": "T", "fato": "f"}],
                        "primeira", tmp_path / "f.html").read_text()
    assert "if(j&&j.p)sujo=true" in js, "a recarga nao recupera o pendente"
    assert "{p:sujo,v:v}" in js, "o pendente nao e gravado junto"


def test_embutir_som_nao_suja_a_pasta_do_usuario(tmp_path):
    """A primeira versao gravava a amostra ao lado do arquivo, e largou tres
    `.amostra-*.mp3` no meio das musicas de quem usa a skill."""
    import subprocess
    som = tmp_path / "trilha.mp3"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=30",
                    str(som)], check=True)
    folha.embutir(som, segundos=5)
    assert [a.name for a in tmp_path.iterdir()] == ["trilha.mp3"]


def test_a_segunda_folha_mostra_o_filme_dentro_dela(tmp_path):
    """A segunda aprovacao existe para a pessoa ASSISTIR. Sem campo de video
    ela receberia um link para um arquivo no disco de quem montou -- que na
    tela dela nao abre."""
    import subprocess
    filme = tmp_path / "f.mp4"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=navy:s=270x480:r=30:d=2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(filme)],
                   check=True)
    uri = folha.embutir(filme)
    assert uri.startswith("data:video/mp4;base64,")
    html = folha.escrever(
        [{"id": "filme", "titulo": "O vídeo montado", "fato": "assista",
          "video": uri}], "segunda", tmp_path / "s.html").read_text()
    assert "<video" in html and "controls" in html
    assert "f.mp4" not in html, "sobrou caminho de disco em vez do filme"


def test_o_filme_da_folha_vai_em_baixa(tmp_path):
    """O arquivo de entrega de 54 segundos tem 76 MB; em base64 passaria de
    100 MB, sete vezes o teto da pagina."""
    import subprocess
    filme = tmp_path / "g.mp4"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=2",
                    "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p",
                    str(filme)], check=True)
    uri = folha.embutir(filme)
    assert len(uri) < filme.stat().st_size, (
        "o filme entrou na folha do tamanho que veio")
