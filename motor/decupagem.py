"""O Bandit conferindo a propria decupagem, antes de entregar.

O QUE ISTO EXISTE PARA PEGAR. Numa rodada com material real, quatro defeitos de
montagem passaram pela decupagem e so foram notados assistindo ao video pronto:
um trecho terminava no meio da palavra "Ou"; dois trechos seguidos comecavam com
"Mas,"; outros dois repetiam a muleta "como voce pode ver"; e um comecava com um
"E" solto.

Os quatro estavam na TRANSCRICAO, e dava para acha-los sem assistir a nada. E o
que este modulo faz.

E CONFERENCIA, NAO CORRECAO. Nada aqui muda a decupagem: cada achado diz onde
esta e o que ha de errado, e quem decide e o Bandit -- as vezes a repeticao e
proposital, e o comeco solto e o jeito da pessoa falar.
"""
import difflib
import re
from collections import defaultdict

# Palavras que sozinhas nao comecam nem terminam frase. Nao e lista de palavra
# proibida: e lista de palavra que, na BORDA de um trecho, quase sempre quer
# dizer que o corte pegou a frase pela metade.
# So conjuncao e preposicao: sao as que, sozinhas na borda de um trecho, quase
# sempre querem dizer que o corte pegou a frase pela metade.
#
# ARTIGO E ADVERBIO FICARAM DE FORA, e por medida: com "um", "uma", "só", "já",
# "como" e "quando" na lista, a conferencia acusava frases perfeitamente
# inteiras -- "Uma coisa que aprendi", "Como você pode ver", "Já falei disso".
# Lista grande demais vira ruido, e ruido faz quem le parar de olhar.
#
# COM ACENTO, tambem de proposito: "é" e verbo e "e" e conjuncao; "dá" e verbo e
# "da" e preposicao. Sem acento, "Dá uma olhada" e "é muito fácil" eram acusados
# de comecar pela metade -- dois falsos alarmes na primeira vez que isto rodou.
SOLTAS = {
    "e", "ou", "mas", "que", "porque", "então", "aí", "pois", "portanto",
    "de", "da", "do", "no", "na", "em", "com", "para", "pra", "por", "sobre",
}

MULETA = 3            # tamanho da repeticao que conta como muleta, em palavras
CURTO = 1.2           # trecho abaixo disto nao da tempo de ouvir
PARECIDO = 0.72       # semelhanca acima da qual dois trechos dizem a mesma
                      # coisa. E o caso que o Bandit existe para resolver: a
                      # pessoa repetiu a frase e as duas tomadas ficaram.


def _limpo(palavra):
    """So minuscula e sem pontuacao. O ACENTO FICA: e ele que separa "é" de
    "e" e "dá" de "da"."""
    return re.sub(r"[^\wÀ-ÿ]", "", palavra.lower())


def fala_de(palavras, de, ate):
    """As palavras que caem entre dois instantes da gravacao.

    Entra toda palavra que ENCOSTA no intervalo: o corte quase sempre cai no
    meio de uma, e exigir que ela comece depois faria a primeira sumir da
    conferencia -- justamente a que pode estar partida."""
    return [w for w in palavras if w["f"] > de and w["t"] < ate]


def conferir(cenas, palavras, alvo_segundos=None, velocidade=1.15):
    """Os problemas da decupagem, em ordem de gravidade.

    `cenas` e a lista que o Bandit escreveu: cada uma com `n`, `arquivo`, `de`
    e `ate`. `palavras` e a transcricao, ja com as trocas de nome aplicadas.
    """
    achados = []
    falas, limpos = {}, {}
    for c in cenas:
        de, ate = c.get("de", 0.0), c.get("ate", 1e9)
        ws = fala_de(palavras, de, ate)
        falas[c["n"]] = ws
        limpos[c["n"]] = [_limpo(w["p"]) for w in ws]

        # 1. o corte caiu dentro de uma palavra
        for w in palavras:
            if w["t"] < de < w["f"]:
                achados.append({
                    "tipo": "palavra partida", "cena": c["n"],
                    "o_que": f'a entrada corta a palavra "{w["p"]}" ao meio',
                    "conserto": f'comece em {w["f"]:.2f} ou em {w["t"]:.2f}'})
            if w["t"] < ate < w["f"]:
                achados.append({
                    "tipo": "palavra partida", "cena": c["n"],
                    "o_que": f'a saida corta a palavra "{w["p"]}" ao meio',
                    "conserto": f'termine em {w["t"]:.2f} ou em {w["f"]:.2f}'})

        if not ws:
            achados.append({"tipo": "trecho mudo", "cena": c["n"],
                            "o_que": "nao ha fala nenhuma neste trecho",
                            "conserto": "confira os instantes"})
            continue

        # 2. comeca ou termina numa palavra que nao se sustenta sozinha
        if limpos[c["n"]][0] in SOLTAS:
            achados.append({
                "tipo": "borda solta", "cena": c["n"],
                "o_que": f'comeca em "{ws[0]["p"]}", que sozinho nao abre frase',
                "conserto": f'comece em {ws[0]["f"]:.2f}, na palavra seguinte'})
        if limpos[c["n"]][-1] in SOLTAS:
            achados.append({
                "tipo": "borda solta", "cena": c["n"],
                "o_que": f'termina em "{ws[-1]["p"]}", com a frase pela metade',
                "conserto": f'termine em {ws[-1]["t"]:.2f}, antes dela'})

        # 3. trecho curto demais para ouvir
        dur = (ate if ate < 1e9 else ws[-1]["f"]) - de
        if dur < CURTO:
            achados.append({
                "tipo": "trecho curto", "cena": c["n"],
                "o_que": f"tem {dur:.1f} segundos, e nao da tempo de ouvir",
                "conserto": "junte ao trecho vizinho ou tire"})

    # 4. a mesma muleta em mais de um trecho
    onde = defaultdict(set)
    for n, ws in limpos.items():
        for i in range(len(ws) - MULETA + 1):
            onde[" ".join(ws[i:i + MULETA])].add(n)
    for frase, ns in sorted(onde.items()):
        if len(ns) > 1 and frase.strip():
            achados.append({
                "tipo": "muleta repetida", "cena": min(ns),
                "o_que": f'"{frase}" aparece nas cenas {sorted(ns)}',
                "conserto": "tire de todas menos de uma"})

    # 5. dois trechos dizendo a mesma coisa
    ns = sorted(falas)
    for i, a in enumerate(ns):
        for b in ns[i + 1:]:
            ta, tb = " ".join(limpos[a]), " ".join(limpos[b])
            if not ta or not tb:
                continue
            s = difflib.SequenceMatcher(None, ta, tb).ratio()
            if s >= PARECIDO:
                achados.append({
                    "tipo": "tomada repetida", "cena": a,
                    "o_que": f"as cenas {a} e {b} dizem quase a mesma coisa "
                             f"({s:.0%} igual)",
                    "conserto": "fique com uma das duas"})

    # 6. dois trechos do mesmo arquivo que se cruzam no tempo
    por_arquivo = defaultdict(list)
    for c in cenas:
        por_arquivo[c.get("arquivo")].append(c)
    for arquivo, lista in por_arquivo.items():
        for i, a in enumerate(lista):
            for b in lista[i + 1:]:
                a0, a1 = a.get("de", 0.0), a.get("ate", 1e9)
                b0, b1 = b.get("de", 0.0), b.get("ate", 1e9)
                if a0 < b1 and b0 < a1:
                    achados.append({
                        "tipo": "trechos sobrepostos", "cena": a["n"],
                        "o_que": f"as cenas {a['n']} e {b['n']} pegam o mesmo "
                                 f"pedaco de {arquivo}",
                        "conserto": "a fala vai aparecer duas vezes"})

    # 7. quanto o filme deve dar, comparado ao que a pessoa pediu
    if alvo_segundos:
        bruto = sum((c.get("ate", 0) - c.get("de", 0)) for c in cenas
                    if c.get("ate"))
        # o corte de pausa e a velocidade encolhem o bruto; o quanto depende do
        # material, e 0,8 e a folga que sobrou nas rodadas medidas
        previsto = bruto * 0.8 / velocidade
        if previsto > alvo_segundos * 1.15:
            achados.append({
                "tipo": "longo demais", "cena": None,
                "o_que": f"deve dar por volta de {previsto:.0f} segundos, e "
                         f"voce pediu {alvo_segundos:.0f}",
                "conserto": "tire mais algum trecho"})

    ordem = ["palavra partida", "trecho mudo", "trechos sobrepostos",
             "tomada repetida", "borda solta", "muleta repetida",
             "trecho curto", "longo demais"]
    return sorted(achados, key=lambda a: (ordem.index(a["tipo"]),
                                          a["cena"] or 0))


def em_portugues(achados):
    """Os achados em frases, para o Bandit ler e decidir."""
    if not achados:
        return ("A decupagem passou: todo trecho comeca e termina em palavra "
                "inteira, ninguem repete o que o outro ja disse, e nao ha "
                "muleta aparecendo duas vezes.")
    linhas = [f"{len(achados)} coisa(s) para olhar antes de entregar:"]
    for a in achados:
        onde = f"cena {a['cena']}: " if a["cena"] else ""
        linhas.append(f"- {onde}{a['o_que']} — {a['conserto']}")
    return "\n".join(linhas)
