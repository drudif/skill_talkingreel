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
try{const g=localStorage.getItem(CHAVE);if(g){const v=JSON.parse(g);
E.itens.forEach(it=>{const a=v[it.id];if(a){it.decisao=a.decisao;it.nota=a.nota||''}})}}catch(e){}
let sujo=false,enviando=false;
function achar(id){return E.itens.find(x=>x.id===id)}
function contar(){return E.itens.filter(x=>x.decisao).length}
function pinta(){E.itens.forEach(it=>{
document.querySelectorAll('[data-id="'+CSS.escape(it.id)+'"]').forEach(el=>{
if(el.tagName==='BUTTON'&&el.dataset.d)el.setAttribute('aria-pressed',
String(el.dataset.d===it.decisao));
else if(el.type==='radio')el.checked=(it.decisao==='escolhido');
else if(el.classList&&el.classList.contains('nota'))el.value=it.nota||''})});
const b=document.getElementById('enviar'),c=document.getElementById('placar');
if(c)c.textContent=contar()+' de '+E.itens.length+' respondidos'
+(sujo?' — falta enviar':'');
if(b){b.disabled=enviando||!sujo;
b.textContent=enviando?'ENVIANDO...':(sujo?'ENVIAR RESPOSTAS':'ENVIADO')}}
function guarda(){sujo=true;try{const v={};E.itens.forEach(it=>{
if(it.decisao||it.nota)v[it.id]={decisao:it.decisao,nota:it.nota}});
localStorage.setItem(CHAVE,JSON.stringify(v))}catch(e){}pinta()}
pinta();
function enviar(){if(enviando||!sujo)return;enviando=true;pinta();
const a=document.documentElement.outerHTML.replace(
new RegExp('(/\\\\*E-'+'INI\\\\*/)[\\\\s\\\\S]*?(/\\\\*E-'+'FIM\\\\*/)'),
(m,i,f)=>i+JSON.stringify(E).replace(/</g,'\\u003c')+f);
claude.use('artifact').then(a2=>{
if(!a2){enviando=false;pinta();return}
return a2.publish('<!doctype html>'+a).then(()=>{
sujo=false;enviando=false;pinta()})}).catch(()=>{enviando=false;pinta()})}
document.addEventListener('click',ev=>{
if(ev.target.id==='enviar'){enviar();return}
const b=ev.target.closest('button[data-d]');
if(!b)return;const it=achar(b.dataset.id);
it.decisao=it.decisao===b.dataset.d?null:b.dataset.d;guarda()});
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
    return (f'<label>{img}'
            f'<input type="radio" name="{_e(grupo)}" data-id="{_e(i["id"])}">'
            f'<span class="t">{_e(i["titulo"])}</span>'
            f'<div class="f">{_e(i.get("fato", ""))}</div>{som}</label>')


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
    return (f'<div class="i">{img}<div class="c">'
            f'<div class="t">{_e(i["titulo"])}</div>'
            f'<div class="f">{_e(i.get("fato", ""))}</div>{det}{som}'
            f'<button data-id="{_e(i["id"])}" data-d="aprovado" '
            f'aria-pressed="false">APROVADO</button>'
            f'<button data-id="{_e(i["id"])}" data-d="reprovado" '
            f'aria-pressed="false">REPROVADO</button>'
            f'<input class="nota" data-id="{_e(i["id"])}" '
            f'placeholder="por que, se quiser dizer">'
            f'</div></div>')


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

    estado = {"fase": fase,
              "itens": [{"id": i["id"], "titulo": i.get("titulo", ""),
                         "grupo": (b.get("id") or "grupo")
                                  if b.get("tipo") == "escolha" else None,
                         "decisao": None, "nota": ""}
                        for i, b in todos]}
    corpo = ("".join(_secao(b) for b in secoes if b["itens"]) if todos else
             '<p class="fim">Nada para decidir por aqui.</p>')
    doc = (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>{_e(FASES[fase])}</title><style>{_CSS}</style></head><body>'
           f'<h1>{_e(FASES[fase])}</h1>'
           f'<p class="sub">Escolha onde a folha pede para escolher, e marque '
           f'APROVADO ou REPROVADO no resto. Quando terminar tudo, aperte '
           f'ENVIAR RESPOSTAS no pé da página.</p>'
           f'{corpo}'
           f'<div class="barra"><button id="enviar" disabled>ENVIADO</button>'
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

    Quem nao foi decidido nao entra: continua pendente e volta na proxima."""
    from motor import registro
    novas = {i["id"]: {"decisao": i["decisao"], "nota": i.get("nota", "")}
             for i in estado.get("itens", [])
             if i.get("decisao") in ("aprovado", "reprovado", "escolhido")}
    return registro.anotar(caminho_registro, novas) if novas else \
        registro.carregar(caminho_registro)
