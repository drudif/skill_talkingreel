"""A folha de aprovacao: HTML gerado em Python, nunca escrito pelo modelo.

POR QUE O TEMPLATE MORA AQUI. No projeto de origem o custo real nao foi o
tamanho do arquivo -- foi o modelo reescrever 50 KB de HTML a cada rodada. Com
o template no codigo, o modelo produz por rodada so a lista de itens.

O ESTADO FICA ENTRE MARCADORES QUE APARECEM UMA VEZ SO. A pagina se republica
sozinha quando a pessoa decide, e para reler o agente precisa achar o bloco de
dados. No projeto de origem havia DOIS trechos parecidos no mesmo arquivo -- o
bloco de verdade e a mesma string escrita dentro do JavaScript que regenera a
pagina -- e quem lesse o segundo apagava o feedback. Aqui o JavaScript monta os
marcadores por concatenacao e nunca os escreve inteiros."""
import html as _html
import json
import re
from pathlib import Path

INI = "/*E-INI*/"
FIM = "/*E-FIM*/"

# Duas aprovacoes, nao tres fases. Cada folha a mais e uma rodada a mais de
# espera de quem so quer o video pronto -- e a primeira decide tudo o que
# precisa ser decidido antes de montar.
FASES = {"primeira": "O que fica, como fica e como soa",
         "segunda": "O filme montado"}

_CSS = """*{box-sizing:border-box;margin:0}
body{font:16px/1.5 system-ui,sans-serif;background:#fff;color:#111;
padding:24px 20px 60px;max-width:760px;margin:auto}
h1{font-size:20px;margin-bottom:2px}
p.sub{color:#666;font-size:14px;margin-bottom:28px}
section{margin:0 0 34px}
h2{font-size:13px;letter-spacing:.09em;text-transform:uppercase;
font-weight:700;padding-bottom:6px;border-bottom:2px solid #111;margin-bottom:4px}
p.como{color:#555;font-size:14px;margin:8px 0 14px}
/* escolher um: cartao grande, sem campo de observacao */
.esc{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));
gap:12px}
.esc label{display:block;border:2px solid #e3e3e3;border-radius:6px;
padding:8px;cursor:pointer}
.esc label:has(input:checked){border-color:#111;background:#f6f6f6}
.esc img{width:100%;height:auto;border-radius:3px;display:block;margin-bottom:6px}
.esc .t{font-weight:600;font-size:14px}
.esc .f{font-size:13px;color:#555;margin-top:2px}
.esc audio{width:100%;height:34px;margin-top:6px;display:block}
/* o filme e vertical: sem teto de altura, 1920 de altura joga a decisao para
   fora da tela e a pessoa aprova sem ter visto o fim */
video{display:block;width:100%;max-width:270px;max-height:60vh;
border-radius:4px;margin:8px 0;background:#000}
.esc input{margin-right:6px}
/* aprovar ou reprovar: linha com miniatura pequena */
.i{border-top:1px solid #e5e5e5;padding:14px 0;display:flex;gap:12px}
.i img{width:74px;height:auto;border-radius:2px;flex:none}
.c{flex:1;min-width:0}
.t{font-weight:600;font-size:15px}
.f{font-size:14px;margin:2px 0 6px}
.d{color:#777;font-size:13px;margin-bottom:8px}
button{font:inherit;font-size:13px;font-weight:600;letter-spacing:.04em;
padding:6px 14px;margin-right:6px;border:1px solid #ccc;background:#fff;
border-radius:3px;cursor:pointer}
button[data-d=aprovado][aria-pressed=true]{background:#0a7d33;color:#fff;
border-color:#0a7d33}
button[data-d=reprovado][aria-pressed=true]{background:#b3261e;color:#fff;
border-color:#b3261e}
input.nota{font:inherit;font-size:14px;padding:5px 8px;border:1px solid #ddd;
border-radius:3px;width:100%;margin-top:8px}
textarea#geral{font:inherit;font-size:15px;padding:9px 11px;border:1px solid #ccc;
border-radius:4px;width:100%;resize:vertical;background:#fff;color:#111}
.fim{margin-top:22px;color:#666;font-size:14px}
.barra{position:sticky;bottom:0;background:#fff;border-top:1px solid #ddd;
padding:12px 0;margin-top:28px;display:flex;align-items:center;gap:14px}
#enviar{background:#111;color:#fff;border-color:#111;padding:10px 22px;
font-size:14px}
#enviar:disabled{background:#eee;color:#999;border-color:#ddd;cursor:default}
#placar{color:#666;font-size:13px}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]) body
{background:#111;color:#eee}
:root:not([data-theme=light]) .barra{background:#111;border-color:#333}
:root:not([data-theme=light]) #enviar{background:#eee;color:#111;
border-color:#eee}
:root:not([data-theme=light]) #enviar:disabled{background:#222;color:#666;
border-color:#333}
:root:not([data-theme=light]) h2{border-color:#eee}
:root:not([data-theme=light]) p.como{color:#aaa}
:root:not([data-theme=light]) .i{border-color:#333}
:root:not([data-theme=light]) textarea#geral{background:#1a1a1a;color:#eee;
border-color:#444}
:root:not([data-theme=light]) .esc label{border-color:#333}
:root:not([data-theme=light]) .esc label:has(input:checked)
{border-color:#eee;background:#1c1c1c}
:root:not([data-theme=light]) button{background:#1c1c1c;color:#eee;
border-color:#444}
:root:not([data-theme=light]) input.nota{background:#1c1c1c;color:#eee;
border-color:#444}}"""

_JS = """const E=JSON.parse(document.getElementById('dados').textContent
.replace('/*E-'+'INI*/','').replace('/*E-'+'FIM*/',''));
const CHAVE='folha-'+(E.fase||'x');
let sujo=false,enviando=false;
try{const g=localStorage.getItem(CHAVE);if(g){const j=JSON.parse(g);
const v=(j&&j.v)?j.v:j;if(j&&j.p)sujo=true;
if(j&&typeof j.g==='string')E.geral=j.g;
E.itens.forEach(it=>{const a=v[it.id];if(a){it.decisao=a.decisao;it.nota=a.nota||''}})}}catch(e){}
function achar(id){return E.itens.find(x=>x.id===id)}
function contar(){return E.itens.filter(x=>x.decisao).length}
function pinta(){E.itens.forEach(it=>{
document.querySelectorAll('[data-id="'+CSS.escape(it.id)+'"]').forEach(el=>{
if(el.tagName==='BUTTON'&&el.dataset.d)el.setAttribute('aria-pressed',
String(el.dataset.d===it.decisao));
else if(el.type==='radio')el.checked=(it.decisao==='escolhido');
else if(el.classList&&el.classList.contains('nota'))el.value=it.nota||''})});
const g=document.getElementById('geral');
if(g&&g.value!==(E.geral||''))g.value=E.geral||'';
const b=document.getElementById('enviar'),c=document.getElementById('placar');
if(c)c.textContent=contar()+' de '+E.itens.length+' respondidos'
+(sujo?' — falta enviar':'');
if(b){b.disabled=enviando||!sujo;
b.textContent=enviando?'ENVIANDO...':(sujo?'ENVIAR RESPOSTAS'
:(contar()?'TUDO ENVIADO':'NADA PARA ENVIAR AINDA'))}}
function salva(){try{const v={};E.itens.forEach(it=>{
if(it.decisao||it.nota)v[it.id]={decisao:it.decisao,nota:it.nota}});
localStorage.setItem(CHAVE,JSON.stringify({p:sujo,v:v,g:E.geral||''}))}catch(e){}pinta()}
function guarda(){sujo=true;salva()}
pinta();
function enviar(){if(enviando||!sujo)return;enviando=true;pinta();
const a=document.documentElement.outerHTML.replace(
new RegExp('(/\\\\*E-'+'INI\\\\*/)[\\\\s\\\\S]*?(/\\\\*E-'+'FIM\\\\*/)'),
(m,i,f)=>i+JSON.stringify(E).replace(/</g,'\\u003c')+f);
claude.use('artifact').then(a2=>{
if(!a2){enviando=false;pinta();return}
return a2.publish('<!doctype html>'+a).then(()=>{
sujo=false;enviando=false;salva()})}).catch(()=>{enviando=false;pinta()})}
document.addEventListener('click',ev=>{
if(ev.target.id==='enviar'){enviar();return}
const b=ev.target.closest('button[data-d]');
if(!b)return;const it=achar(b.dataset.id);
it.decisao=it.decisao===b.dataset.d?null:b.dataset.d;guarda()});
document.addEventListener('input',ev=>{
if(ev.target.id==='geral'){E.geral=ev.target.value;guarda()}});
document.addEventListener('change',ev=>{const el=ev.target;
if(el.type==='radio'){
E.itens.forEach(x=>{if(x.grupo===el.name)x.decisao=null});
achar(el.dataset.id).decisao='escolhido';guarda();return}
if(el.classList&&el.classList.contains('nota')){
achar(el.dataset.id).nota=el.value;guarda()}});
addEventListener('beforeunload',ev=>{if(sujo){ev.preventDefault();ev.returnValue=''}});"""


def _e(s):
    return _html.escape(str(s), quote=True)


def _json_no_script(estado):
    """JSON.dumps do estado, seguro para morar dentro de um `<script>`.

    json.dumps nao escapa `<`, entao um titulo ou nota com `</script>` dentro
    fecharia a tag `<script id="dados">` na leitura do navegador -- o HTML
    quebraria antes do JS rodar. `\\u003c` e JSON valido e json.loads devolve
    o `<` de volta; so protege contra a tag fechar cedo demais."""
    return json.dumps(estado, ensure_ascii=False).replace("<", "\\u003c")


def _cartao(i, grupo):
    """Um item de ESCOLHA: cartao grande, com radio, sem campo de observacao.

    Escolher entre sete estilos nao e a mesma decisao que aprovar um corte. Ali
    a pessoa compara e pega um; oferecer aprovar/reprovar em cada um convida a
    aprovar tres, e nao ha o que fazer com isso. O radio deixa a regra visivel:
    marcar um desmarca o outro."""
    img = (f'<img src="{_e(i["miniatura"])}" alt="">' if i.get("miniatura")
           else "")
    som = (f'<audio controls preload="none" src="{_e(i["audio"])}"></audio>'
           if i.get("audio") else "")
    filme = (f'<video controls playsinline preload="metadata" '
             f'src="{_e(i["video"])}"></video>' if i.get("video") else "")
    return (f'<label>{img}'
            f'<input type="radio" name="{_e(grupo)}" data-id="{_e(i["id"])}">'
            f'<span class="t">{_e(i["titulo"])}</span>'
            f'<div class="f">{_e(i.get("fato", ""))}</div>{filme}{som}</label>')


def _linha(i):
    """Um item de DECISAO: aprovar ou reprovar, com espaco para o porque.

    APROVADO e REPROVADO, e nao 'pode ir' e 'tira': a folha e o registro do que
    foi combinado, e palavra informal deixa margem para os dois lados lembrarem
    coisas diferentes."""
    img = (f'<img src="{_e(i["miniatura"])}" alt="">' if i.get("miniatura")
           else "")
    det = f'<div class="d">{_e(i["detalhe"])}</div>' if i.get("detalhe") else ""
    # `preload="none"`: com varias faixas na pagina, deixar o navegador carregar
    # todas de uma vez trava a folha no celular.
    som = (f'<audio class="s" controls preload="none" '
           f'src="{_e(i["audio"])}"></audio>' if i.get("audio") else "")
    filme = (f'<video class="v" controls playsinline preload="metadata" '
             f'src="{_e(i["video"])}"></video>' if i.get("video") else "")
    return (f'<div class="i">{img}<div class="c">'
            f'<div class="t">{_e(i["titulo"])}</div>'
            f'<div class="f">{_e(i.get("fato", ""))}</div>{det}{filme}{som}'
            f'<button data-id="{_e(i["id"])}" data-d="aprovado" '
            f'aria-pressed="false">APROVADO</button>'
            f'<button data-id="{_e(i["id"])}" data-d="reprovado" '
            f'aria-pressed="false">REPROVADO</button>'
            f'<input class="nota" data-id="{_e(i["id"])}" '
            f'placeholder="por que, se quiser dizer">'
            f'</div></div>')


# O campo de observacao GERAL, em toda folha. Os campos de nota dos itens
# perguntam sobre aquele item; nao ha onde dizer "o corte aos 22 segundos
# engasga" ou "diminui a musica". Sem lugar para isso, ou a pessoa reprova um
# item so para ter onde escrever, ou a coisa se perde no meio da conversa.
#
# PEDIR O SEGUNDO NAO E FORMALIDADE: sem ele, achar um defeito de meio segundo
# num filme de 54 obriga a assistir tudo procurando, varias vezes.
_OBSERVACOES = (
    '<section><h2>OUTRA COISA QUE VOCÊ QUEIRA DIZER</h2>'
    '<p class="como">Este espaço é para o que não cabe nas perguntas acima. '
    '<b>Se você viu alguma coisa errada no vídeo</b> — um corte que engasga, '
    'uma palavra pela metade, um texto que entra fora de hora, a música alta '
    'demais —, escreva aqui <b>em que segundo do vídeo isso acontece</b>. '
    'Pode ser aproximado ("por volta de 0:22"). Sem o segundo eu tenho de '
    'assistir o vídeo inteiro procurando, e às vezes não acho. '
    'Também serve para pedido geral: mais rápido, mais curto, outro tom.</p>'
    '<textarea id="geral" rows="4" placeholder="ex: aos 0:22 a palavra sai '
    'cortada; e a música podia ser mais baixa"></textarea></section>')


def _observacoes():
    return _OBSERVACOES


def _secao(s):
    """Um bloco da folha: titulo em caixa alta, uma linha dizendo o que fazer,
    e os itens.

    O titulo e a instrucao nao sao enfeite. Sem eles a folha vira uma lista
    corrida de coisas diferentes -- estilo, musica, corte -- e quem le nao sabe
    se esta escolhendo entre opcoes ou aprovando uma a uma."""
    escolha = s.get("tipo") == "escolha"
    grupo = s.get("id") or "grupo"
    corpo = ("".join(_cartao(i, grupo) for i in s["itens"])
             if escolha else "".join(_linha(i) for i in s["itens"]))
    classe = ' class="esc"' if escolha else ""
    como = (f'<p class="como">{_e(s["instrucao"])}</p>'
            if s.get("instrucao") else "")
    return (f'<section><h2>{_e(s["titulo"])}</h2>{como}'
            f'<div{classe}>{corpo}</div></section>')



def escrever(secoes, fase, destino):
    """Grava a folha em `destino` e devolve o caminho.

    `secoes` e uma lista de blocos:

        {"id": "estilo",
         "titulo": "ESTILO DE LETTERING E LEGENDAS",
         "instrucao": "Veja os estilos disponiveis e escolha um.",
         "tipo": "escolha",          # ou "decisao"
         "itens": [{"id": ..., "titulo": ..., "fato": ...,
                    "miniatura": ..., "audio": ..., "detalhe": ...}]}

    `tipo` muda o que a pessoa pode fazer, e nao so a aparencia:
    **escolha** = um dos itens do bloco, com imagem grande e sem observacao;
    **decisao** = cada item aprovado ou reprovado, com espaco para o porque.

    Uma lista simples de itens tambem e aceita, e vira um bloco de decisao sem
    titulo -- e o que mantem de pe quem chama do jeito antigo."""
    if fase not in FASES:
        raise ValueError(f"fase '{fase}' nao existe. Use uma de: "
                         + ", ".join(FASES))
    if secoes and not isinstance(secoes[0], dict):
        raise ValueError("cada secao e um dicionario")
    if secoes and "itens" not in secoes[0]:
        secoes = [{"id": "geral", "titulo": FASES[fase], "tipo": "decisao",
                   "itens": list(secoes)}]

    vistos, todos = set(), []
    for bloco in secoes:
        if bloco.get("tipo", "decisao") not in ("escolha", "decisao"):
            raise ValueError(
                f"a secao '{bloco.get('titulo')}' tem tipo "
                f"'{bloco['tipo']}'. Use 'escolha' ou 'decisao'")
        for i in bloco["itens"]:
            if not i.get("id"):
                raise ValueError("todo item precisa de um 'id'")
            if i["id"] in vistos:
                raise ValueError(f"o id '{i['id']}' esta repetido")
            vistos.add(i["id"])
            todos.append((i, bloco))

    estado = {"fase": fase, "geral": "",
              "itens": [{"id": i["id"], "titulo": i.get("titulo", ""),
                         "grupo": (b.get("id") or "grupo")
                                  if b.get("tipo") == "escolha" else None,
                         "decisao": None, "nota": ""}
                        for i, b in todos]}
    corpo = ("".join(_secao(b) for b in secoes if b["itens"]) if todos else
             '<p class="fim">Nada para decidir por aqui.</p>')
    corpo += _observacoes()
    doc = (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>{_e(FASES[fase])}</title><style>{_CSS}</style></head><body>'
           f'<h1>{_e(FASES[fase])}</h1>'
           f'<p class="sub">Escolha onde a folha pede para escolher, e marque '
           f'APROVADO ou REPROVADO no resto. Quando terminar tudo, aperte '
           f'ENVIAR RESPOSTAS no pé da página.</p>'
           f'{corpo}'
           f'<div class="barra">'
           f'<button id="enviar" disabled>NADA PARA ENVIAR AINDA</button>'
           f'<span id="placar"></span></div>'
           f'<script id="dados" type="application/json">'
           f'{INI}{_json_no_script(estado)}{FIM}</script>'
           f'<script>{_JS}</script></body></html>')
    destino = Path(destino)
    destino.write_text(doc, encoding="utf-8")
    return destino

def ler(caminho_ou_texto):
    """As decisoes que estao dentro da folha.

    Falha alto se achar mais de um bloco de estado -- e exatamente o erro que
    apagou o feedback da pessoa no projeto de origem."""
    p = Path(caminho_ou_texto) if not str(caminho_ou_texto).lstrip().startswith(
        "<") else None
    texto = p.read_text(encoding="utf-8") if p else str(caminho_ou_texto)
    if texto.count(INI) != 1 or texto.count(FIM) != 1:
        raise ValueError(
            f"esperava um bloco de estado, achei {texto.count(INI)} de inicio "
            f"e {texto.count(FIM)} de fim. Ler o bloco errado apaga o que a "
            "pessoa decidiu.")
    bruto = texto[texto.index(INI) + len(INI):texto.index(FIM)]
    return json.loads(bruto)


def publicar(secoes, fase, destino, caminho_registro):
    """A folha com SO o que falta decidir.

    Item ja decidido sai; secao que ficou sem item nenhum sai junto -- um
    titulo sozinho, sem nada embaixo, faz a pessoa procurar o que nao existe."""
    from motor import registro
    if secoes and isinstance(secoes[0], dict) and "itens" not in secoes[0]:
        return escrever(registro.pendentes(secoes, caminho_registro), fase,
                        destino)
    ja = registro.carregar(caminho_registro)
    podadas = []
    for bloco in secoes:
        # numa ESCOLHA, escolher um resolve o bloco inteiro: os outros nao
        # ficaram pendentes, ficaram para tras. Traze-los de volta faria a
        # pessoa achar que precisa marcar mais alguma coisa ali.
        if bloco.get("tipo") == "escolha" and any(
                ja.get(i["id"], {}).get("decisao") == "escolhido"
                for i in bloco["itens"]):
            continue
        restam = registro.pendentes(bloco["itens"], caminho_registro)
        if restam:
            podadas.append({**bloco, "itens": restam})
    return escrever(podadas, fase, destino)


def recolher(estado, caminho_registro):
    """Guarda no registro o que a pessoa decidiu nesta folha.

    Quem nao foi decidido nao entra: continua pendente e volta na proxima.

    A OBSERVACAO GERAL entra junto, sob a chave `_geral`. Ela nao e item e nao
    tem decisao: e o que a pessoa escreveu sobre o filme inteiro, e some se
    ficar so na tela. O sublinhado no comeco a mantem fora de `pendentes` --
    ela nunca fica pendente, porque nunca foi uma pergunta."""
    from motor import registro
    novas = {i["id"]: {"decisao": i["decisao"], "nota": i.get("nota", "")}
             for i in estado.get("itens", [])
             if i.get("decisao") in ("aprovado", "reprovado", "escolhido")}
    geral = (estado.get("geral") or "").strip()
    if geral:
        anterior = registro.carregar(caminho_registro).get("_geral", {})
        antigas = anterior.get("todas", []) if isinstance(anterior, dict) else []
        if geral not in antigas:
            antigas = antigas + [geral]
        novas["_geral"] = {"decisao": None, "nota": geral, "todas": antigas}
    return registro.anotar(caminho_registro, novas) if novas else \
        registro.carregar(caminho_registro)


def observacao(estado):
    """O que a pessoa escreveu no campo geral desta folha, ou string vazia.

    Vale ler ANTES dos itens: e ali que aparece o defeito que nenhuma pergunta
    cobria -- um corte que engasga, um texto fora de hora -- e e o unico lugar
    da folha onde ela pode apontar um segundo do filme."""
    return (estado.get("geral") or "").strip()


# Uma folha publicada nao alcanca o disco de quem a escreveu: `src="foto.jpg"`
# abre certo aqui e quebra na tela da pessoa, sem erro visivel -- a imagem
# simplesmente nao aparece, e ela escolhe estilo sem ver estilo nenhum. Por
# isso tudo vai embutido no HTML, e por isso ha um teto.
TETO_FOLHA = 15_000_000     # a pagina publicada e recusada acima de 16 MB
LARGURA_MINIATURA = 240     # a coluna da miniatura tem 74 px na tela
LARGURA_PREVIA = 460        # o cartao de escolha vai a 150-380 px
SEGUNDOS_AMOSTRA = 25       # o bastante para reconhecer a musica
QUALIDADE = 72              # medido: abaixo disto o contorno da letra suja


def embutir(caminho, largura=None, segundos=None):
    """O arquivo virado `data:` URI, para a folha funcionar publicada.

    `largura` encolhe a imagem antes; `segundos` corta o som e o passa a mono
    de 64 kbps. Sem encolher nao cabe: as 22 previas de estilo saem do motor em
    1080x1920 e somam 5,2 MB, que em base64 viram 6,9 MB -- so elas."""
    import base64
    import subprocess
    from pathlib import Path

    caminho = Path(caminho)
    ext = caminho.suffix.lower()
    if ext in (".mp4", ".mov", ".m4v", ".webm"):
        # o filme montado, para a pessoa assistir na propria folha. Vai SEMPRE
        # pela versao leve: o arquivo de entrega de 54 segundos tem 76 MB, e em
        # base64 passaria de 100 -- sozinho, sete vezes o teto da pagina.
        from motor import previa
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            leve = Path(td) / "leve.mp4"
            previa.em_baixa(caminho, leve)
            dados, tipo = leve.read_bytes(), "video/mp4"
    elif ext in (".mp3", ".m4a", ".wav", ".aac"):
        import tempfile
        # o temporario NAO vai na pasta do arquivo: ela e do usuario, e a
        # primeira rodada largou tres `.amostra-*.mp3` no meio das musicas dele
        with tempfile.TemporaryDirectory() as td:
            saida = Path(td) / "amostra.mp3"
            subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                 "-i", str(caminho), "-t", str(segundos or SEGUNDOS_AMOSTRA),
                 "-vn", "-ac", "1", "-b:a", "64k", str(saida)], check=True)
            dados, tipo = saida.read_bytes(), "audio/mpeg"
    else:
        from io import BytesIO

        from PIL import Image
        im = Image.open(caminho).convert("RGB")
        if largura and im.width > largura:
            alt = round(im.height * largura / im.width)
            im = im.resize((largura, alt), Image.LANCZOS)
        buf = BytesIO()
        im.save(buf, "JPEG", quality=QUALIDADE, optimize=True)
        dados, tipo = buf.getvalue(), "image/jpeg"
    return f"data:{tipo};base64," + base64.b64encode(dados).decode()


def cabe(destino):
    """O tamanho da folha e se ela passa do teto do que da para publicar."""
    from pathlib import Path
    n = Path(destino).stat().st_size
    return n, n <= TETO_FOLHA
