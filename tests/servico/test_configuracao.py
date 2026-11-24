"""Testes do `drivelan.toml` (FSD 20.2): padrões, validação, ilegível e gravação atômica."""

import io
import os
import stat
import tomllib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from drivelan.servico import configuracao as modulo
from drivelan.servico.configuracao import (
    MODELO_PADRAO,
    Configuracao,
    ConfiguracaoIlegivel,
    MonitorConfiguracao,
    carregar_configuracao,
    gravar_atomico,
    gravar_valores,
    registrar_avisos,
)
from drivelan.servico.log_erros import LogErros, caminho_do_dia

POSIX = os.name == "posix"
PADRAO = Configuracao(log_ativo=True, rede_interface="", rede_porta=47820)


@pytest.fixture
def caminho(tmp_path: Path) -> Path:
    return tmp_path / "config" / "drivelan.toml"


def _escrever(caminho: Path, texto: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")


# ---------------------------------------------------------------- padrões e criação


def test_padroes_da_secao_20_2() -> None:
    assert Configuracao() == PADRAO


def test_modelo_padrao_corresponde_aos_padroes() -> None:
    dados = tomllib.loads(MODELO_PADRAO)
    assert dados == {"log": {"ativo": True}, "rede": {"interface": "", "porta": 47820}}
    assert "senha" not in MODELO_PADRAO.casefold()


def test_arquivo_ausente_e_criado_com_os_padroes(caminho: Path) -> None:
    resultado = carregar_configuracao(caminho)
    assert resultado.criado
    assert resultado.legivel
    assert resultado.avisos == []
    assert resultado.configuracao == PADRAO
    assert caminho.read_text(encoding="utf-8") == MODELO_PADRAO


@pytest.mark.skipif(not POSIX, reason="modos POSIX")
def test_arquivo_criado_com_permissoes_restritas(caminho: Path) -> None:
    carregar_configuracao(caminho)
    assert stat.S_IMODE(caminho.stat().st_mode) == 0o600
    assert stat.S_IMODE(caminho.parent.stat().st_mode) == 0o700


def test_segunda_leitura_nao_recria(caminho: Path) -> None:
    carregar_configuracao(caminho)
    resultado = carregar_configuracao(caminho)
    assert not resultado.criado
    assert resultado.configuracao == PADRAO


def test_falha_ao_criar_usa_padroes_com_aviso(
    caminho: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def falhar(destino: Path, conteudo: bytes) -> None:
        raise PermissionError("sem permissão")

    monkeypatch.setattr(modulo, "gravar_atomico", falhar)
    resultado = carregar_configuracao(caminho)
    assert resultado.configuracao == PADRAO
    assert not resultado.criado
    assert len(resultado.avisos) == 1
    assert "Não foi possível criar" in resultado.avisos[0]
    assert "PermissionError" in resultado.avisos[0]
    assert not caminho.exists()


def test_caminho_impossivel_e_tratado_como_ilegivel(tmp_path: Path) -> None:
    bloqueio = tmp_path / "config"
    bloqueio.write_text("arquivo no lugar da pasta", encoding="utf-8")
    resultado = carregar_configuracao(bloqueio / "drivelan.toml")
    assert resultado.configuracao == PADRAO
    assert not resultado.legivel
    assert bloqueio.read_text(encoding="utf-8") == "arquivo no lugar da pasta"


def test_valores_validos_sao_lidos(caminho: Path) -> None:
    _escrever(caminho, '[log]\nativo = false\n[rede]\ninterface = "enp3s0"\nporta = 50000\n')
    resultado = carregar_configuracao(caminho)
    assert resultado.avisos == []
    assert resultado.configuracao == Configuracao(False, "enp3s0", 50000)


def test_secoes_ausentes_usam_padroes_sem_aviso(caminho: Path) -> None:
    _escrever(caminho, "")
    resultado = carregar_configuracao(caminho)
    assert resultado.configuracao == PADRAO
    assert resultado.avisos == []


def test_limites_da_porta_sao_aceitos(caminho: Path) -> None:
    for porta in (1024, 65535):
        _escrever(caminho, f"[rede]\nporta = {porta}\n")
        assert carregar_configuracao(caminho).configuracao.rede_porta == porta


# ---------------------------------------------------------------- valores inválidos


@pytest.mark.parametrize(
    ("texto", "chave"),
    [
        ("[rede]\nporta = 1023\n", "rede.porta"),
        ("[rede]\nporta = 65536\n", "rede.porta"),
        ("[rede]\nporta = 0\n", "rede.porta"),
        ("[rede]\nporta = -1\n", "rede.porta"),
        ("[rede]\nporta = true\n", "rede.porta"),
        ('[rede]\nporta = "47820"\n', "rede.porta"),
        ("[rede]\nporta = 47820.0\n", "rede.porta"),
        ("[log]\nativo = 1\n", "log.ativo"),
        ('[log]\nativo = "sim"\n', "log.ativo"),
        ("[rede]\ninterface = 3\n", "rede.interface"),
        ('[rede]\ninterface = ["eth0"]\n', "rede.interface"),
        ('[rede]\ninterface = "eth0\\n"\n', "rede.interface"),
    ],
)
def test_valor_invalido_usa_o_padrao_com_aviso(caminho: Path, texto: str, chave: str) -> None:
    _escrever(caminho, texto)
    original = caminho.read_bytes()
    resultado = carregar_configuracao(caminho)
    assert resultado.configuracao == PADRAO
    assert resultado.legivel
    assert len(resultado.avisos) == 1
    assert chave in resultado.avisos[0]
    assert "usando o padrão" in resultado.avisos[0]
    assert caminho.read_bytes() == original  # valor inválido não reescreve o arquivo


def test_um_valor_invalido_nao_afeta_os_outros(caminho: Path) -> None:
    _escrever(caminho, '[log]\nativo = false\n[rede]\ninterface = "wlan0"\nporta = 80\n')
    resultado = carregar_configuracao(caminho)
    assert resultado.configuracao == Configuracao(False, "wlan0", 47820)
    assert len(resultado.avisos) == 1


def test_secao_que_nao_e_tabela(caminho: Path) -> None:
    _escrever(caminho, 'rede = "x"\n[log]\nativo = false\n')
    resultado = carregar_configuracao(caminho)
    assert resultado.configuracao == Configuracao(False, "", 47820)
    assert "[rede]" in resultado.avisos[0]


def test_aviso_nao_repete_o_valor_invalido(caminho: Path) -> None:
    _escrever(caminho, '[rede]\ninterface = "\\u0007conteudo-arbitrario"\n')
    resultado = carregar_configuracao(caminho)
    assert "conteudo-arbitrario" not in resultado.avisos[0]


# ---------------------------------------------------------------- arquivo ilegível


@pytest.mark.parametrize(
    "bruto",
    [
        b"[log\nativo = true\n",  # sintaxe inválida
        b"[rede]\nporta = 47820\nporta = 1\n",  # chave repetida
        b'[rede]\ninterface = "\xff\xfe"\n',  # não é UTF-8
    ],
)
def test_arquivo_ilegivel_usa_padroes_e_nao_e_sobrescrito(caminho: Path, bruto: bytes) -> None:
    caminho.parent.mkdir(parents=True)
    caminho.write_bytes(bruto)
    resultado = carregar_configuracao(caminho)
    assert resultado.configuracao == PADRAO
    assert not resultado.legivel
    assert not resultado.criado
    assert "ilegível" in resultado.avisos[0]
    assert caminho.read_bytes() == bruto


def test_diretorio_no_lugar_do_arquivo_e_ilegivel(caminho: Path) -> None:
    caminho.mkdir(parents=True)
    resultado = carregar_configuracao(caminho)
    assert not resultado.legivel
    assert resultado.configuracao == PADRAO
    assert caminho.is_dir()


@pytest.mark.skipif(not POSIX or os.geteuid() == 0, reason="permissão POSIX sem root")
def test_sem_permissao_de_leitura_e_ilegivel(caminho: Path) -> None:
    _escrever(caminho, "[log]\nativo = false\n")
    caminho.chmod(0o000)
    try:
        resultado = carregar_configuracao(caminho)
    finally:
        caminho.chmod(0o600)
    assert not resultado.legivel
    assert resultado.configuracao == PADRAO
    assert caminho.read_text(encoding="utf-8") == "[log]\nativo = false\n"


# ---------------------------------------------------------------- gravação atômica


def test_gravar_valores_preserva_as_demais_chaves(caminho: Path) -> None:
    _escrever(
        caminho,
        '[log]\nativo = false\n[rede]\ninterface = ""\nporta = 50000\n'
        '[extra]\nlista = [1, 2]\n[rede.detalhe]\nx = "y"\n',
    )
    gravar_valores(caminho, {"rede": {"interface": "eth0"}})
    dados = tomllib.loads(caminho.read_text(encoding="utf-8"))
    assert dados == {
        "log": {"ativo": False},
        "rede": {"interface": "eth0", "porta": 50000, "detalhe": {"x": "y"}},
        "extra": {"lista": [1, 2]},
    }
    assert carregar_configuracao(caminho).configuracao == Configuracao(False, "eth0", 50000)


def test_gravar_valores_com_arquivo_ausente_parte_dos_padroes(caminho: Path) -> None:
    gravar_valores(caminho, {"rede": {"interface": "eth1"}})
    assert carregar_configuracao(caminho).configuracao == Configuracao(True, "eth1", 47820)


def test_gravar_valores_nao_sobrescreve_arquivo_ilegivel(caminho: Path) -> None:
    _escrever(caminho, "[rede\n")
    with pytest.raises(ConfiguracaoIlegivel):
        gravar_valores(caminho, {"rede": {"interface": "eth0"}})
    assert caminho.read_text(encoding="utf-8") == "[rede\n"


def test_falha_na_substituicao_mantem_o_original(
    caminho: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _escrever(caminho, "[log]\nativo = false\n")

    def falhar(origem: object, destino: object) -> None:
        raise OSError("disco cheio")

    monkeypatch.setattr(modulo.os, "replace", falhar)
    with pytest.raises(OSError, match="disco cheio"):
        gravar_valores(caminho, {"rede": {"interface": "eth0"}})
    assert caminho.read_text(encoding="utf-8") == "[log]\nativo = false\n"
    assert sorted(p.name for p in caminho.parent.iterdir()) == ["drivelan.toml"]


def test_falha_na_escrita_nao_deixa_temporario(
    caminho: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _escrever(caminho, "original")

    def falhar(descritor: int) -> None:
        raise OSError("falha de E/S")

    monkeypatch.setattr(modulo.os, "fsync", falhar)
    with pytest.raises(OSError):
        gravar_atomico(caminho, b"novo")
    assert caminho.read_text(encoding="utf-8") == "original"
    assert [p.name for p in caminho.parent.iterdir()] == ["drivelan.toml"]


@pytest.mark.skipif(not POSIX, reason="modos POSIX")
def test_gravacao_atomica_mantem_modo_restrito(caminho: Path) -> None:
    _escrever(caminho, "")
    caminho.chmod(0o644)
    gravar_atomico(caminho, b"[log]\nativo = true\n")
    assert stat.S_IMODE(caminho.stat().st_mode) == 0o600


# ---------------------------------------------------------------- avisos no log e recarga


class RelogioFalso:
    def __init__(self) -> None:
        self.valor = 100.0

    def __call__(self) -> float:
        return self.valor


HORA = datetime(2026, 11, 24, 9, 0, tzinfo=timezone(timedelta(hours=-3)))


def _log(tmp_path: Path) -> LogErros:
    return LogErros(tmp_path / "logs", relogio=lambda: HORA, saida_erro=io.StringIO())


def _conteudo_log(tmp_path: Path) -> str:
    arquivo = caminho_do_dia(tmp_path / "logs", date(2026, 11, 24))
    return arquivo.read_text(encoding="utf-8") if arquivo.exists() else ""


def test_registrar_avisos_usa_o_nivel_aviso(tmp_path: Path, caminho: Path) -> None:
    _escrever(caminho, "[rede]\nporta = 1\n")
    log = _log(tmp_path)
    registrar_avisos(log, carregar_configuracao(caminho))
    assert " | AVISO | servico.configuracao | Valor inválido para rede.porta" in _conteudo_log(
        tmp_path
    )


def test_monitor_carrega_e_aplica_log_ativo(tmp_path: Path, caminho: Path) -> None:
    _escrever(caminho, "[log]\nativo = false\n[rede]\nporta = 1\n")
    log = _log(tmp_path)
    monitor = MonitorConfiguracao(caminho, log, relogio=RelogioFalso())
    assert monitor.carregar() == Configuracao(False, "", 47820)
    assert not log.ativo
    assert _conteudo_log(tmp_path) == ""  # log desligado: nem o aviso é gravado


def test_monitor_so_verifica_a_cada_60_segundos(tmp_path: Path, caminho: Path) -> None:
    _escrever(caminho, "[log]\nativo = true\n")
    log = _log(tmp_path)
    relogio = RelogioFalso()
    monitor = MonitorConfiguracao(caminho, log, relogio=relogio)
    monitor.carregar()
    _escrever(caminho, "[log]\nativo = false\n# alterado\n")
    relogio.valor += 59
    assert monitor.verificar() is None
    assert log.ativo
    relogio.valor += 1
    nova = monitor.verificar()
    assert nova is not None
    assert nova.log_ativo is False
    assert not log.ativo


def test_monitor_sem_alteracao_nao_rele(
    tmp_path: Path, caminho: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _escrever(caminho, "[log]\nativo = true\n")
    relogio = RelogioFalso()
    monitor = MonitorConfiguracao(caminho, _log(tmp_path), relogio=relogio)
    monitor.carregar()
    chamadas: list[Path] = []
    monkeypatch.setattr(modulo, "carregar_configuracao", lambda c: chamadas.append(c))
    relogio.valor += 120
    assert monitor.verificar() is None
    assert chamadas == []


def test_monitor_religa_o_log_e_registra_avisos(tmp_path: Path, caminho: Path) -> None:
    _escrever(caminho, "[log]\nativo = false\n")
    log = _log(tmp_path)
    relogio = RelogioFalso()
    monitor = MonitorConfiguracao(caminho, log, relogio=relogio)
    monitor.carregar()
    _escrever(caminho, "[log]\nativo = true\n[rede]\nporta = 99999\n")
    relogio.valor += 60
    assert monitor.verificar() == PADRAO
    assert log.ativo
    assert "rede.porta" in _conteudo_log(tmp_path)


def test_monitor_com_arquivo_que_ficou_ilegivel(tmp_path: Path, caminho: Path) -> None:
    _escrever(caminho, "[log]\nativo = true\n")
    log = _log(tmp_path)
    relogio = RelogioFalso()
    monitor = MonitorConfiguracao(caminho, log, relogio=relogio)
    monitor.carregar()
    _escrever(caminho, "[log\n")
    relogio.valor += 60
    assert monitor.verificar() == PADRAO
    assert "ilegível" in _conteudo_log(tmp_path)
    assert caminho.read_text(encoding="utf-8") == "[log\n"
