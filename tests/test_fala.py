from motor import fala
from tests import fixtures


def test_acha_o_inicio_da_fala(tmp_path):
    # tom de 1.0s comecando em 1.20s, dentro de um clipe de 3s
    c = fixtures.clipe_fala(tmp_path / "a.mov", falas=[(1.20, 1.0)], total=3.0)
    ini, _ = fala.bordas(c)
    assert abs(ini - 1.20) < 0.12


def test_acha_o_fim_da_fala(tmp_path):
    c = fixtures.clipe_fala(tmp_path / "b.mov", falas=[(0.5, 1.0)], total=3.0)
    _, fim = fala.bordas(c)
    assert abs(fim - 1.50) < 0.40      # o respiro de saida adiciona folga


def test_pausa_interna_e_encontrada(tmp_path):
    # duas falas com 0.8s de silencio entre elas: e pausa
    c = fixtures.clipe_fala(tmp_path / "c.mov", falas=[(0.3, 0.6), (1.7, 0.6)], total=3.0)
    pausas = fala.pausas_internas(c, 0.0, 3.0)
    assert len(pausas) == 1
    ini, fim = pausas[0]
    assert 0.8 < ini < 1.1
    assert 1.6 < fim < 1.9


def test_pausa_curta_nao_conta(tmp_path):
    # 0.15s entre as falas, abaixo do limite de 0.22s
    c = fixtures.clipe_fala(tmp_path / "d.mov", falas=[(0.3, 0.6), (1.05, 0.6)], total=2.5)
    assert fala.pausas_internas(c, 0.0, 2.5) == []


def test_teto_encurta_o_fim(tmp_path):
    c = fixtures.clipe_fala(tmp_path / "e.mov", falas=[(0.5, 2.0)], total=3.5)
    ini, fim = fala.bordas_com_teto(c, teto=1.0)
    assert abs(fim - (ini + 1.0)) < 0.01


def test_inicio_da_fala_em_varias_posicoes(tmp_path):
    """bordas() nao pode estar certo so num ponto: testa varios inicios e
    confere que o resultado acompanha cada um. bordas subtrai RESPIRO_IN
    (0.06s) do inicio detectado do tom, entao o esperado e start - 0.06,
    com piso em 0.0. Tolerancia de 0.12s: a mesma da resolucao do
    envelope (passo de 10 ms) mais folga do ataque do tom sintetico."""
    inicios = [0.10, 0.45, 1.00, 1.75, 2.60]
    tabela = []
    for start in inicios:
        c = fixtures.clipe_fala(tmp_path / f"v_{start}.mov", falas=[(start, 0.5)], total=3.5)
        ini, _ = fala.bordas(c)
        esperado = max(0.0, start - 0.06)
        tabela.append((start, esperado, ini))
        assert abs(ini - esperado) < 0.12, tabela


def test_clipe_mudo_nao_quebra_e_nao_inventa_fala(tmp_path):
    """clipe_mudo nao tem nem trilha de audio. bordas() nao pode explodir, e o
    resultado sensato e cobrir o arquivo inteiro (nao ha fala pra recortar)."""
    c = fixtures.clipe_mudo(tmp_path / "mudo.mp4", total=2.0)
    ini, fim = fala.bordas(c)
    assert ini == 0.0
    assert abs(fim - 2.0) < 0.05


def test_duas_pausas_internas_em_ordem(tmp_path):
    """Tres falas, duas pausas longas entre elas: as duas tem que aparecer, em
    ordem crescente e sem se sobrepor."""
    c = fixtures.clipe_fala(
        tmp_path / "tres.mov",
        falas=[(0.2, 0.4), (1.2, 0.4), (2.4, 0.4)],
        total=4.0)
    pausas = fala.pausas_internas(c, 0.0, 4.0)
    assert len(pausas) == 2
    (a_ini, a_fim), (b_ini, b_fim) = pausas
    assert a_ini < a_fim <= b_ini < b_fim


def _comandos_de(monkeypatch, modulo):
    """Captura os comandos de ffmpeg que uma funcao dispara, sem rodar nada."""
    import subprocess as sp
    vistos = []
    real = sp.run

    def espiao(args, *a, **k):
        if args and args[0] in ("ffmpeg", "ffprobe"):
            vistos.append(list(args))
        return real(args, *a, **k)

    monkeypatch.setattr(modulo.subprocess, "run", espiao)
    return vistos


def test_medir_audio_nao_manda_decodificar_video(tmp_path, monkeypatch):
    """O defeito que isto impede: sem `-vn`, o ffmpeg decodifica o video
    inteiro so para jogar fora, e o custo passa a ser do tamanho da IMAGEM.

    MEDIDO num arquivo de celular de 4K com 4,7 minutos: 48,2 segundos sem
    `-vn` contra 0,3 segundo com ele, e a mesma resposta -- 66 pausas. Aqui a
    verificacao e do COMANDO, e nao do tempo: com clipe pequeno a diferenca
    encolhe para 3x, que nao sustenta um limite estavel; a propriedade que
    importa e nao pedir o video, e essa da para conferir sempre."""
    c = fixtures.clipe_fala(tmp_path / "v.mov", falas=[(0.3, 1.0)], total=2.0)
    vistos = _comandos_de(monkeypatch, fala)

    fala.envelope(c)
    fala.pausas_internas(c, 0.0, 2.0)

    assert vistos, "nenhum comando foi disparado"
    for cmd in vistos:
        assert "-vn" in cmd, (
            "um comando de analise de audio nao tem -vn e vai decodificar o "
            f"video a toa: {' '.join(str(x) for x in cmd)[:160]}")


def test_o_corte_do_audio_vem_antes_da_entrada(tmp_path, monkeypatch):
    """`-ss` depois do `-i` vira opcao de saida: o ffmpeg decodifica tudo desde
    o comeco e so entao descarta. Num arquivo longo isso e a diferenca entre
    instantaneo e minutos."""
    c = fixtures.clipe_fala(tmp_path / "w.mov", falas=[(0.3, 1.0)], total=3.0)
    vistos = _comandos_de(monkeypatch, fala)
    fala.envelope(c, de=1.0, ate=2.0)

    for cmd in vistos:
        if "-ss" in cmd:
            assert cmd.index("-ss") < cmd.index("-i"), (
                "o -ss ficou depois do -i e virou opcao de saida")
