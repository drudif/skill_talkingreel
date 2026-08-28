# Diario — skill_talkingreel

Historico de decisoes. Nao e carregado em toda sessao — lido sob demanda, pode crescer.
Entrada nova no topo, com data.

---

## 2026-08-28 — motor do nucleo pronto

Le um `cenas.json` e devolve o filme montado: corte de silencio pelas pontas, compressao de
pausa interna, velocidade por cena, split com ancora de recorte, trilha com abaixamento sob a
voz, e laudo de qualidade em portugues. 77 testes, ~60s de suite porque monta video de verdade.

Provado com material real do `conteudo/agentes-ginsu`: 3 gravacoes, 2 b-rolls e trilha viraram
17,8s de filme em 54s de processamento, sem uma linha de ffmpeg escrita a mao.

### Decisoes

- **Material de teste gerado por ffmpeg**, nao gravacao real. O valor esperado de cada teste
  fica conhecido e nenhum video pessoal entra no repositorio.
- **Nove modulos pequenos** em vez de um script grande. So `tratamentos.py` e `montar.py`
  geram video; o resto so mede ou valida.
- **O `cenas.json` e o contrato.** Os agentes escrevem, o motor le.
- **A ancora de recorte** existe porque a janela de cima do split e deitada (1080x807) e
  material vertical perde 58% da altura.

### Um bug que quase passou, e como

O `alimiter` tem `level=true` por padrao. A opcao NAO normaliza para 0 dB como o nome sugere:
soma um ganho fixo de +1.5 dB, compensando o valor do `limit`. O plano esqueceu o
`level=disabled` que o projeto de origem usava, e o pico do filme ia para -0.0 dB em vez de -1.5.

Ele passou por tres redes: os tres testes do plano, dois testes extras escritos pelo subagente,
e a primeira versao do teste de correcao. **So apareceu ao rodar com gravacao e trilha reais.**

A causa de o teste nao pegar: material sintetico baixo. Medido, um tom a -5.5 dB da o mesmo
resultado nas duas versoes; so material perto do teto separa. O teste final carrega uma
verificacao propria que se recusa a rodar se a fonte estiver baixa demais.

Licao para os proximos planos: **teste de audio precisa de fonte no nivel de producao**, e todo
teste de guarda deve ser provado quebrando o codigo de proposito.

### Cobertura por armadilha

| armadilha | teste que guarda |
|---|---|
| `-ss` depois do `-i` | tom em posicao conhecida, medido na saida |
| dessync progressivo | 15 cenas, erro constante em vez de crescente |
| ancora do split ignorada | material metade vermelho metade azul, pixel comparado |
| sidechain invertido | inversao de proposito faz o teste falhar |
| limitador desligado | fonte no nivel de producao |
| compressao comendo fala | conta os trechos de fala que sobreviveram |

---

## 2026-08-28 — inicio

Projeto criado.
