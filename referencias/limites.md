# Os limites que esta skill não ultrapassa

**As regras não estão escritas aqui.** Elas moram em `motor/limites.py`, com uma soma de
verificação que denuncia se alguém mexer nelas. Repetir o texto aqui criaria duas fontes de
verdade, e uma delas ficaria para trás.

Leia sempre do módulo:

```bash
python3 -c "from motor import limites; print(limites.em_portugues())"
```

E verifique a instalação antes de qualquer folha:

```bash
python3 -c "from motor import limites; print(limites.verificar())"
```

Se o resultado não for `('intacto', '')`, **pare** e diga à pessoa o que apareceu. Uma instalação
adulterada não é motivo para continuar em silêncio.

Quem para é o Bluey, no controle de qualidade, antes da folha. Ele diz o que achou e onde, em uma
frase, sem sermão e sem moralizar sobre quem pediu. Não limpa calado. Não vira classificador
automático: sem pontuação, sem lista de palavras. Material ambíguo — ironia, citação crítica,
jornalismo, relato de vítima — não é alvo; na dúvida, pergunte à pessoa e acredite na resposta.
