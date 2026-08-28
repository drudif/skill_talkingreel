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

FASES = {"estrutura": "O que fica do que voce falou",
         "arte": "Estilo, letreiros e trilha",
         "corte": "O filme montado"}

_CSS = """*{box-sizing:border-box;margin:0}
body{font:16px/1.5 system-ui,sans-serif;background:#fff;color:#111;
padding:24px;max-width:720px;margin:auto}
h1{font-size:19px;margin-bottom:2px}
p.sub{color:#666;font-size:14px;margin-bottom:20px}
.i{border-top:1px solid #e5e5e5;padding:14px 0;display:flex;gap:12px}
.i img{width:80px;height:auto;border-radius:2px;flex:none}
.c{flex:1;min-width:0}
.t{font-weight:600;font-size:15px}
.f{font-size:14px;margin:2px 0 8px}
.d{color:#777;font-size:13px;margin-bottom:8px}
button{font:inherit;font-size:14px;padding:5px 12px;margin-right:6px;
border:1px solid #ccc;background:#fff;border-radius:3px;cursor:pointer}
button[aria-pressed=true]{background:#111;color:#fff;border-color:#111}
input{font:inherit;font-size:14px;padding:5px 8px;border:1px solid #ddd;
border-radius:3px;width:100%;margin-top:6px}
.fim{margin-top:22px;color:#666;font-size:14px}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]) body
{background:#111;color:#eee}
:root:not([data-theme=light]) .i{border-color:#333}
:root:not([data-theme=light]) button{background:#1c1c1c;color:#eee;
border-color:#444}
:root:not([data-theme=light]) button[aria-pressed=true]{background:#eee;
color:#111}
:root:not([data-theme=light]) input{background:#1c1c1c;color:#eee;
border-color:#444}}"""

_JS = """const E=JSON.parse(document.getElementById('dados').textContent
.replace('/*E-'+'INI*/','').replace('/*E-'+'FIM*/',''));
function pinta(){E.itens.forEach(it=>{
document.querySelectorAll('[data-id="'+CSS.escape(it.id)+'"]').forEach(el=>{
if(el.tagName==='BUTTON')el.setAttribute('aria-pressed',
String(el.dataset.d===it.decisao));else el.value=it.nota||''})})}
pinta();
function p(){const a=document.documentElement.outerHTML.replace(
new RegExp('(/\\\\*E-'+'INI\\\\*/)[\\\\s\\\\S]*?(/\\\\*E-'+'FIM\\\\*/)'),
(m,i,f)=>i+JSON.stringify(E)+f);
claude.use('artifact').then(a2=>a2&&a2.publish('<!doctype html>'+a)).catch(()=>{})}
document.addEventListener('click',ev=>{const b=ev.target.closest('button');
if(!b)return;const it=E.itens.find(x=>x.id===b.dataset.id);
it.decisao=it.decisao===b.dataset.d?null:b.dataset.d;pinta();p()});
document.addEventListener('change',ev=>{if(ev.target.tagName!=='INPUT')return;
E.itens.find(x=>x.id===ev.target.dataset.id).nota=ev.target.value;p()});"""


def _e(s):
    return _html.escape(str(s), quote=True)


def _json_no_script(estado):
    """JSON.dumps do estado, seguro para morar dentro de um `<script>`.

    json.dumps nao escapa `<`, entao um titulo ou nota com `</script>` dentro
    fecharia a tag `<script id="dados">` na leitura do navegador -- o HTML
    quebraria antes do JS rodar. `\\u003c` e JSON valido e json.loads devolve
    o `<` de volta; so protege contra a tag fechar cedo demais."""
    return json.dumps(estado, ensure_ascii=False).replace("<", "\\u003c")


def _linha(i):
    img = (f'<img src="{_e(i["miniatura"])}" alt="">' if i.get("miniatura")
           else "")
    det = f'<div class="d">{_e(i["detalhe"])}</div>' if i.get("detalhe") else ""
    return (f'<div class="i">{img}<div class="c">'
            f'<div class="t">{_e(i["titulo"])}</div>'
            f'<div class="f">{_e(i.get("fato", ""))}</div>{det}'
            f'<button data-id="{_e(i["id"])}" data-d="aprovado" '
            f'aria-pressed="false">Pode ir</button>'
            f'<button data-id="{_e(i["id"])}" data-d="descartado" '
            f'aria-pressed="false">Tira</button>'
            f'<input data-id="{_e(i["id"])}" placeholder="uma observacao, se '
            f'quiser">'
            f'</div></div>')


def escrever(itens, fase, destino):
    """Grava a folha em `destino` e devolve o caminho."""
    if fase not in FASES:
        raise ValueError(f"fase '{fase}' nao existe. Use uma de: "
                         + ", ".join(FASES))
    vistos = set()
    for i in itens:
        if not i.get("id"):
            raise ValueError("todo item precisa de um 'id'")
        if i["id"] in vistos:
            raise ValueError(f"o id '{i['id']}' esta repetido")
        vistos.add(i["id"])

    estado = {"fase": fase,
              "itens": [{"id": i["id"], "titulo": i.get("titulo", ""),
                         "decisao": None, "nota": ""} for i in itens]}
    corpo = ("".join(_linha(i) for i in itens) if itens else
             '<p class="fim">Nada para decidir por aqui.</p>')
    doc = (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>{_e(FASES[fase])}</title><style>{_CSS}</style></head><body>'
           f'<h1>{_e(FASES[fase])}</h1>'
           f'<p class="sub">Marque o que pode ir e o que sai. '
           f'Fecha a aba quando terminar.</p>'
           f'{corpo}'
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
