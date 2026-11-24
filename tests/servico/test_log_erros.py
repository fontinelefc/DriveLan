"""Testes do log de erros (FSD 19.1): formato, rotação, contingência, segredos e retenção."""

import io
import os
import re
import stat
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from drivelan.comum.protocolo import mensagem_erro_interno
from drivelan.servico.log_erros import (
    LIMITE_BUFFER_CONTINGENCIA,
    VALOR_OMITIDO,
    LogErros,
    NivelLog,
    aplicar_retencao,
    caminho_do_dia,
    data_limite_retencao,
    formatar_evento,
    gerar_codigo_log,
    origem_de,
)

BRASILIA = timezone(timedelta(hours=-3))
POSIX = os.name == "posix"


class Relogios:
    """Relógio de parede e monotônico controlados pelo teste."""

    def __init__(self, inicio: datetime) -> None:
        self.agora = inicio
        self.monotonico = 1000.0

    def parede(self) -> datetime:
        return self.agora

    def mono(self) -> float:
        return self.monotonico

    def avancar(self, segundos: float) -> None:
        self.agora += timedelta(seconds=segundos)
        self.monotonico += segundos


@pytest.fixture
def relogios() -> Relogios:
    return Relogios(datetime(2026, 11, 12, 10, 15, 3, 120000, tzinfo=BRASILIA))


def _criar_log(pasta: Path, relogios: Relogios, saida: io.StringIO | None = None) -> LogErros:
    return LogErros(
        pasta,
        relogio=relogios.parede,
        relogio_monotonico=relogios.mono,
        saida_erro=saida if saida is not None else io.StringIO(),
    )


def _ler(pasta: Path, dia: date) -> str:
    return caminho_do_dia(pasta, dia).read_text(encoding="utf-8")


# ---------------------------------------------------------------- formato e local


def test_caminho_do_dia_segue_ano_mes() -> None:
    caminho = caminho_do_dia(Path("/var/log/drivelan"), date(2026, 11, 12))
    assert caminho == Path("/var/log/drivelan/2026-11/2026-11-12.log")


def test_linha_no_formato_da_secao_19_1_2(tmp_path: Path, relogios: Relogios) -> None:
    log = _criar_log(tmp_path, relogios)
    log.erro(
        "servico.rede.anuncio_mdns", "Falha no anúncio mDNS", {"placa": "eth0", "tentativa": 3}
    )
    assert _ler(tmp_path, date(2026, 11, 12)) == (
        "2026-11-12T10:15:03.120-03:00 | ERRO | servico.rede.anuncio_mdns | "
        "Falha no anúncio mDNS | placa=eth0 tentativa=3\n"
    )


def test_sem_contexto_omite_o_campo() -> None:
    momento = datetime(2026, 1, 2, 3, 4, 5, tzinfo=BRASILIA)
    texto = formatar_evento(momento, NivelLog.CRITICO, "servico", "Banco corrompido")
    assert texto == "2026-01-02T03:04:05.000-03:00 | CRITICO | servico | Banco corrompido"


def test_momento_sem_fuso_e_recusado() -> None:
    with pytest.raises(ValueError, match="fuso"):
        formatar_evento(datetime(2026, 1, 1), NivelLog.ERRO, "servico", "x")


def test_niveis_do_fsd() -> None:
    assert [nivel.value for nivel in NivelLog] == ["ERRO", "CRITICO", "AVISO"]


def test_aviso_e_critico(tmp_path: Path, relogios: Relogios) -> None:
    log = _criar_log(tmp_path, relogios)
    log.aviso("servico.configuracao", "Valor inválido para rede.porta")
    log.critico("servico", "Falha impeditiva")
    linhas = _ler(tmp_path, date(2026, 11, 12)).splitlines()
    assert " | AVISO | servico.configuracao | " in linhas[0]
    assert " | CRITICO | servico | " in linhas[1]


def test_pilha_indentada(tmp_path: Path, relogios: Relogios) -> None:
    log = _criar_log(tmp_path, relogios)
    try:
        raise RuntimeError("falha de teste")
    except RuntimeError as erro:
        log.erro("servico", "Exceção não tratada", excecao=erro)
    linhas = _ler(tmp_path, date(2026, 11, 12)).splitlines()
    assert linhas[0].endswith("| ERRO | servico | Exceção não tratada")
    assert len(linhas) > 2
    assert all(linha.startswith("    ") for linha in linhas[1:])
    assert linhas[1].strip() == "Traceback (most recent call last):"
    assert linhas[-1].strip() == "RuntimeError: falha de teste"


def test_quebras_de_linha_e_barras_sao_escapadas(tmp_path: Path, relogios: Relogios) -> None:
    log = _criar_log(tmp_path, relogios)
    log.erro("servico", "linha1\nFALSO | CRITICO", {"nome": "a\r\nb|c"})
    conteudo = _ler(tmp_path, date(2026, 11, 12))
    assert conteudo.count("\n") == 1
    assert "linha1\\nFALSO \\| CRITICO" in conteudo
    assert "nome=a\\r\\nb\\|c" in conteudo


def test_valor_com_espaco_fica_entre_aspas(tmp_path: Path, relogios: Relogios) -> None:
    log = _criar_log(tmp_path, relogios)
    log.erro("servico", "x", {"motivo": 'disco "cheio" agora', "vazio": ""})
    assert 'motivo="disco \\"cheio\\" agora" vazio=""' in _ler(tmp_path, date(2026, 11, 12))


def test_origem_de_remove_o_prefixo_do_pacote() -> None:
    assert origem_de("drivelan.servico.rede.anuncio_mdns") == "servico.rede.anuncio_mdns"
    assert origem_de("app") == "app"


def test_texto_em_utf8(tmp_path: Path, relogios: Relogios) -> None:
    log = _criar_log(tmp_path, relogios)
    log.erro("servico", "Não há permissão — ação", {"pasta": "Relatórios"})
    bruto = caminho_do_dia(tmp_path, date(2026, 11, 12)).read_bytes()
    assert "Não há permissão — ação".encode() in bruto
    assert "pasta=Relatórios".encode() in bruto


# ---------------------------------------------------------------- rotação diária


def test_rotacao_diaria_e_mensal(tmp_path: Path, relogios: Relogios) -> None:
    relogios.agora = datetime(2026, 11, 30, 23, 59, 59, tzinfo=BRASILIA)
    log = _criar_log(tmp_path, relogios)
    log.erro("servico", "antes da meia-noite")
    relogios.avancar(2)
    log.erro("servico", "depois da meia-noite")
    assert "antes da meia-noite" in _ler(tmp_path, date(2026, 11, 30))
    assert "depois da meia-noite" in _ler(tmp_path, date(2026, 12, 1))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["2026-11", "2026-12"]


def test_eventos_do_mesmo_dia_sao_acrescentados(tmp_path: Path, relogios: Relogios) -> None:
    log = _criar_log(tmp_path, relogios)
    for numero in range(3):
        log.erro("servico", f"evento {numero}")
    linhas = _ler(tmp_path, date(2026, 11, 12)).splitlines()
    assert [linha.rsplit("| ", 1)[1] for linha in linhas] == ["evento 0", "evento 1", "evento 2"]


def test_pasta_removida_e_recriada(tmp_path: Path, relogios: Relogios) -> None:
    pasta = tmp_path / "logs"
    log = _criar_log(pasta, relogios)
    log.erro("servico", "primeiro")
    caminho_do_dia(pasta, date(2026, 11, 12)).unlink()
    caminho_do_dia(pasta, date(2026, 11, 12)).parent.rmdir()
    pasta.rmdir()
    log.erro("servico", "segundo")
    assert "segundo" in _ler(pasta, date(2026, 11, 12))


@pytest.mark.skipif(not POSIX, reason="modos POSIX")
def test_permissoes_restritas(tmp_path: Path, relogios: Relogios) -> None:
    pasta = tmp_path / "logs"
    log = _criar_log(pasta, relogios)
    log.erro("servico", "x")
    arquivo = caminho_do_dia(pasta, date(2026, 11, 12))
    assert stat.S_IMODE(arquivo.stat().st_mode) == 0o600
    assert stat.S_IMODE(arquivo.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(pasta.stat().st_mode) == 0o700


def test_uso_simultaneo_por_threads(tmp_path: Path) -> None:
    log = LogErros(tmp_path, saida_erro=io.StringIO())

    def gravar(numero: int) -> None:
        for indice in range(50):
            log.erro("servico", "evento", {"thread": numero, "indice": indice})

    threads = [threading.Thread(target=gravar, args=(numero,)) for numero in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    linhas = [
        linha
        for arquivo in tmp_path.rglob("*.log")
        for linha in arquivo.read_text(encoding="utf-8").splitlines()
    ]
    assert len(linhas) == 400
    padrao = re.compile(r"^\S+ \| ERRO \| servico \| evento \| thread=\d indice=\d+$")
    assert all(padrao.match(linha) for linha in linhas)


# ---------------------------------------------------------------- ligar e desligar


def test_desligado_nao_grava_nada(tmp_path: Path, relogios: Relogios) -> None:
    pasta = tmp_path / "logs"
    log = LogErros(pasta, ativo=False, relogio=relogios.parede, saida_erro=io.StringIO())
    log.erro("servico", "não deve aparecer")
    assert not pasta.exists()


def test_religar_volta_a_gravar(tmp_path: Path, relogios: Relogios) -> None:
    log = _criar_log(tmp_path, relogios)
    log.definir_ativo(False)
    log.erro("servico", "ignorado")
    log.definir_ativo(True)
    log.erro("servico", "gravado")
    conteudo = _ler(tmp_path, date(2026, 11, 12))
    assert "gravado" in conteudo
    assert "ignorado" not in conteudo


# ---------------------------------------------------------------- código curto (FSD 19.1.4)


def test_codigo_log_tem_8_hexadecimais_maiusculos() -> None:
    codigos = {gerar_codigo_log() for _ in range(200)}
    assert all(re.fullmatch(r"[0-9A-F]{8}", codigo) for codigo in codigos)
    assert len(codigos) > 190  # aleatório


def test_erro_inesperado_grava_e_devolve_o_codigo(tmp_path: Path, relogios: Relogios) -> None:
    log = _criar_log(tmp_path, relogios)
    try:
        raise ValueError("detalhe técnico")
    except ValueError as erro:
        codigo = log.erro_inesperado("servico.api.local", erro, {"rota": "/local/v1/estado"})
    conteudo = _ler(tmp_path, date(2026, 11, 12))
    assert f"| Erro inesperado | codigo={codigo} rota=/local/v1/estado\n" in conteudo
    assert "ValueError: detalhe técnico" in conteudo
    mensagem = mensagem_erro_interno(codigo)
    assert mensagem.endswith(f"Código: {codigo}")
    assert "detalhe técnico" not in mensagem


def test_erro_inesperado_com_log_desligado_ainda_devolve_codigo(tmp_path: Path) -> None:
    log = LogErros(tmp_path / "logs", ativo=False, saida_erro=io.StringIO())
    assert re.fullmatch(r"[0-9A-F]{8}", log.erro_inesperado("servico", RuntimeError()))
    assert not (tmp_path / "logs").exists()


# ---------------------------------------------------------------- segredos (FSD 24.5)


@pytest.mark.parametrize(
    "chave",
    ["pin", "PIN_pasta", "token", "token_sessao", "chave", "chave_seguranca", "senha", "sessao",
     "conteudo_arquivo", "segredo"],
)  # fmt: skip
def test_valores_de_chaves_sensiveis_sao_omitidos(
    tmp_path: Path, relogios: Relogios, chave: str
) -> None:
    log = _criar_log(tmp_path, relogios)
    log.erro("servico", "x", {chave: "123456-segredo"})
    conteudo = _ler(tmp_path, date(2026, 11, 12))
    assert "123456-segredo" not in conteudo
    assert f"{chave}={VALOR_OMITIDO}" in conteudo


def test_pilha_nao_inclui_variaveis_locais(tmp_path: Path, relogios: Relogios) -> None:
    log = _criar_log(tmp_path, relogios)

    def funcao_com_segredo() -> None:
        pin_digitado = "987654"
        raise RuntimeError("falhou" if pin_digitado else "vazio")

    try:
        funcao_com_segredo()
    except RuntimeError as erro:
        log.erro("servico", "x", excecao=erro)
    assert "987654" not in _ler(tmp_path, date(2026, 11, 12))


# ---------------------------------------------------------------- contingência (FSD 19.1.5)


def _bloquear(pasta: Path) -> None:
    """Faz a gravação falhar: um arquivo comum ocupa o lugar da pasta de logs."""
    pasta.write_text("não é uma pasta", encoding="utf-8")


def _desbloquear(pasta: Path) -> None:
    pasta.unlink()


def test_falha_de_gravacao_nao_levanta_e_vai_para_stderr(
    tmp_path: Path, relogios: Relogios
) -> None:
    pasta = tmp_path / "logs"
    _bloquear(pasta)
    saida = io.StringIO()
    log = _criar_log(pasta, relogios, saida)
    log.erro("servico", "evento durante a falha")
    estado = log.estado_contingencia()
    assert estado.em_contingencia
    assert estado.falha_desde == relogios.agora
    assert len(estado.eventos) == 1
    assert "evento durante a falha" in estado.eventos[0]
    assert "evento durante a falha" in saida.getvalue()


def test_saida_de_erro_padrao_e_usada_por_padrao(
    tmp_path: Path, relogios: Relogios, capsys: pytest.CaptureFixture[str]
) -> None:
    pasta = tmp_path / "logs"
    _bloquear(pasta)
    log = LogErros(pasta, relogio=relogios.parede, relogio_monotonico=relogios.mono)
    log.erro("servico", "vai para o journald")
    assert "vai para o journald" in capsys.readouterr().err


def test_buffer_guarda_so_os_ultimos_500(tmp_path: Path, relogios: Relogios) -> None:
    pasta = tmp_path / "logs"
    _bloquear(pasta)
    log = _criar_log(pasta, relogios)
    for numero in range(LIMITE_BUFFER_CONTINGENCIA + 20):
        log.erro("servico", f"evento {numero}")
    eventos = log.estado_contingencia().eventos
    assert len(eventos) == LIMITE_BUFFER_CONTINGENCIA
    assert eventos[0].endswith("evento 20")
    assert eventos[-1].endswith(f"evento {LIMITE_BUFFER_CONTINGENCIA + 19}")


def test_nao_tenta_de_novo_antes_de_60_segundos(tmp_path: Path, relogios: Relogios) -> None:
    pasta = tmp_path / "logs"
    _bloquear(pasta)
    log = _criar_log(pasta, relogios)
    log.erro("servico", "primeiro")
    _desbloquear(pasta)
    relogios.avancar(59)
    log.erro("servico", "segundo")
    assert not pasta.exists()
    assert len(log.estado_contingencia().eventos) == 2


def test_despeja_o_buffer_em_ordem_depois_de_60_segundos(
    tmp_path: Path, relogios: Relogios
) -> None:
    pasta = tmp_path / "logs"
    _bloquear(pasta)
    log = _criar_log(pasta, relogios)
    log.erro("servico", "primeiro")
    log.erro("servico", "segundo")
    _desbloquear(pasta)
    relogios.avancar(60)
    log.erro("servico", "terceiro")
    linhas = _ler(pasta, date(2026, 11, 12)).splitlines()
    assert [linha.rsplit("| ", 1)[1] for linha in linhas] == ["primeiro", "segundo", "terceiro"]
    estado = log.estado_contingencia()
    assert not estado.em_contingencia
    assert estado.eventos == []


def test_tentar_novamente_pelo_agendador(tmp_path: Path, relogios: Relogios) -> None:
    pasta = tmp_path / "logs"
    _bloquear(pasta)
    log = _criar_log(pasta, relogios)
    log.erro("servico", "guardado")
    assert log.tentar_novamente() is False
    _desbloquear(pasta)
    assert log.tentar_novamente() is True
    assert "guardado" in _ler(pasta, date(2026, 11, 12))
    assert log.tentar_novamente() is True  # sem contingência, nada a fazer


def test_despejo_grava_cada_evento_no_arquivo_do_seu_dia(
    tmp_path: Path, relogios: Relogios
) -> None:
    pasta = tmp_path / "logs"
    relogios.agora = datetime(2026, 11, 30, 23, 59, 30, tzinfo=BRASILIA)
    _bloquear(pasta)
    log = _criar_log(pasta, relogios)
    log.erro("servico", "de novembro")
    relogios.avancar(60)
    _desbloquear(pasta)
    log.erro("servico", "de dezembro")
    assert "de novembro" in _ler(pasta, date(2026, 11, 30))
    assert "de dezembro" in _ler(pasta, date(2026, 12, 1))
    assert "de dezembro" not in _ler(pasta, date(2026, 11, 30))


def test_desligar_descarta_a_contingencia(tmp_path: Path, relogios: Relogios) -> None:
    pasta = tmp_path / "logs"
    _bloquear(pasta)
    log = _criar_log(pasta, relogios)
    log.erro("servico", "x")
    log.definir_ativo(False)
    assert not log.estado_contingencia().em_contingencia


# ---------------------------------------------------------------- retenção (FSD 19.1.6)


@pytest.mark.parametrize(
    ("hoje", "limite"),
    [
        (date(2026, 11, 24), date(2026, 8, 24)),
        (date(2026, 1, 15), date(2025, 10, 15)),
        (date(2026, 5, 31), date(2026, 2, 28)),
        (date(2028, 5, 31), date(2028, 2, 29)),  # ano bissexto
        (date(2026, 3, 31), date(2025, 12, 31)),
    ],
)
def test_data_limite_de_3_meses(hoje: date, limite: date) -> None:
    assert data_limite_retencao(hoje) == limite


def _criar_arquivo_log(pasta: Path, dia: date) -> Path:
    caminho = caminho_do_dia(pasta, dia)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text("x\n", encoding="utf-8")
    return caminho


def test_retencao_apaga_so_o_que_e_anterior_a_3_meses(tmp_path: Path) -> None:
    hoje = date(2026, 11, 24)
    antigo = _criar_arquivo_log(tmp_path, date(2026, 8, 23))
    limite = _criar_arquivo_log(tmp_path, date(2026, 8, 24))
    recente = _criar_arquivo_log(tmp_path, date(2026, 11, 24))
    muito_antigo = _criar_arquivo_log(tmp_path, date(2025, 1, 1))
    assert aplicar_retencao(tmp_path, hoje) == 2
    assert not antigo.exists()
    assert not muito_antigo.exists()
    assert limite.exists()
    assert recente.exists()


def test_retencao_remove_pastas_de_mes_vazias(tmp_path: Path) -> None:
    _criar_arquivo_log(tmp_path, date(2026, 7, 1))
    _criar_arquivo_log(tmp_path, date(2026, 7, 2))
    (tmp_path / "2026-06").mkdir()
    aplicar_retencao(tmp_path, date(2026, 11, 24))
    assert not (tmp_path / "2026-07").exists()
    assert not (tmp_path / "2026-06").exists()


def test_retencao_preserva_arquivos_fora_do_padrao(tmp_path: Path) -> None:
    pasta_mes = tmp_path / "2026-01"
    pasta_mes.mkdir()
    estranhos = [
        pasta_mes / "anotacoes.txt",
        pasta_mes / "2026-02-01.log",  # dia de outro mês na pasta errada
        pasta_mes / "2026-01-32.log",  # data impossível
        tmp_path / "outro.log",
    ]
    for arquivo in estranhos:
        arquivo.write_text("x", encoding="utf-8")
    (tmp_path / "outra-pasta").mkdir()
    aplicar_retencao(tmp_path, date(2026, 11, 24))
    assert all(arquivo.exists() for arquivo in estranhos)
    assert (tmp_path / "outra-pasta").exists()


def test_retencao_com_pasta_inexistente(tmp_path: Path) -> None:
    assert aplicar_retencao(tmp_path / "nao-existe", date(2026, 11, 24)) == 0


def test_falha_no_meio_do_despejo_nao_duplica_linhas(tmp_path: Path, relogios: Relogios) -> None:
    pasta = tmp_path / "logs"
    relogios.agora = datetime(2026, 11, 30, 23, 59, 30, tzinfo=BRASILIA)
    _bloquear(pasta)
    log = _criar_log(pasta, relogios)
    log.erro("servico", "de novembro")
    relogios.avancar(60)
    log.erro("servico", "de dezembro")  # ainda bloqueado: os dois ficam no buffer
    _desbloquear(pasta)
    # O mês de dezembro falha (um arquivo ocupa o lugar da pasta do mês).
    (pasta / "2026-12").parent.mkdir()
    (pasta / "2026-12").write_text("bloqueio", encoding="utf-8")
    assert log.tentar_novamente() is False
    assert log.estado_contingencia().eventos[0].endswith("de dezembro")
    (pasta / "2026-12").unlink()
    assert log.tentar_novamente() is True
    assert _ler(pasta, date(2026, 11, 30)).count("de novembro") == 1
    assert _ler(pasta, date(2026, 12, 1)).count("de dezembro") == 1
