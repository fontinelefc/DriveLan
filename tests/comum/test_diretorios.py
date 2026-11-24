"""Testes dos diretórios por plataforma (FSD 5.6) e do modo de desenvolvimento (FSD 4.1)."""

import os
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from drivelan.comum.diretorios import (
    LIMITE_CAMINHO_SOCKET,
    SistemaOperacional,
    criar_diretorio_privado,
    diretorios_servico,
    diretorios_usuario,
    montar_diretorios_servico,
    montar_diretorios_usuario,
    sistema_atual,
)

WINDOWS = SistemaOperacional.WINDOWS
LINUX = SistemaOperacional.LINUX


def test_servico_linux() -> None:
    d = montar_diretorios_servico(PurePosixPath, LINUX, {})
    assert d.dados == PurePosixPath("/var/lib/drivelan")
    assert d.certificado == PurePosixPath("/var/lib/drivelan/certificado")
    assert d.banco == PurePosixPath("/var/lib/drivelan/drivelan.db")
    assert d.configuracao == PurePosixPath("/etc/drivelan/drivelan.toml")
    assert d.logs == PurePosixPath("/var/log/drivelan")
    assert d.canal_local == "/run/drivelan/local.sock"


def test_servico_windows() -> None:
    d = montar_diretorios_servico(PureWindowsPath, WINDOWS, {"PROGRAMDATA": r"C:\ProgramData"})
    assert str(d.dados) == r"C:\ProgramData\DriveLan\dados"
    assert str(d.certificado) == r"C:\ProgramData\DriveLan\dados\certificado"
    assert str(d.banco) == r"C:\ProgramData\DriveLan\dados\drivelan.db"
    assert str(d.configuracao) == r"C:\ProgramData\DriveLan\config\drivelan.toml"
    assert str(d.logs) == r"C:\ProgramData\DriveLan\logs"
    assert d.canal_local == r"\\.\pipe\drivelan-servico"


def test_servico_windows_sem_variavel_usa_padrao() -> None:
    d = montar_diretorios_servico(PureWindowsPath, WINDOWS, {})
    assert str(d.dados) == r"C:\ProgramData\DriveLan\dados"


def test_servico_windows_com_programdata_em_outra_unidade() -> None:
    d = montar_diretorios_servico(PureWindowsPath, WINDOWS, {"PROGRAMDATA": r"D:\PD"})
    assert str(d.logs) == r"D:\PD\DriveLan\logs"


def test_desenvolvimento_linux() -> None:
    base = PurePosixPath("/srv/dl/dono")
    d = montar_diretorios_servico(PurePosixPath, LINUX, {}, base)
    assert d.dados == base
    assert d.banco == base / "drivelan.db"
    assert d.certificado == base / "certificado"
    assert d.configuracao == base / "config" / "drivelan.toml"
    assert d.logs == base / "logs"
    assert d.canal_local == "/srv/dl/dono/local.sock"


def test_desenvolvimento_socket_longo_usa_pasta_de_execucao() -> None:
    base = PurePosixPath("/home/usuario/" + "p" * LIMITE_CAMINHO_SOCKET)
    d = montar_diretorios_servico(PurePosixPath, LINUX, {"XDG_RUNTIME_DIR": "/run/user/1000"}, base)
    assert d.canal_local.startswith("/run/user/1000/drivelan-dev-")
    assert d.canal_local.endswith(".sock")
    assert len(d.canal_local.encode()) <= LIMITE_CAMINHO_SOCKET


def test_desenvolvimento_socket_longo_sem_pasta_de_execucao() -> None:
    base = PurePosixPath("/home/usuario/" + "p" * LIMITE_CAMINHO_SOCKET)
    d = montar_diretorios_servico(PurePosixPath, LINUX, {}, base)
    assert d.canal_local == str(base / "local.sock")


def test_duas_instancias_de_desenvolvimento_nao_colidem() -> None:
    dono = PurePosixPath("/home/u/" + "d" * 120 + "/dono")
    cliente = PurePosixPath("/home/u/" + "d" * 120 + "/cliente")
    ambiente = {"XDG_RUNTIME_DIR": "/run/user/1000"}
    canal_dono = montar_diretorios_servico(PurePosixPath, LINUX, ambiente, dono).canal_local
    canal_cliente = montar_diretorios_servico(PurePosixPath, LINUX, ambiente, cliente).canal_local
    assert canal_dono != canal_cliente


def test_desenvolvimento_windows_usa_pipe_proprio() -> None:
    dono = montar_diretorios_servico(PureWindowsPath, WINDOWS, {}, PureWindowsPath(r"C:\dev\dono"))
    cliente = montar_diretorios_servico(
        PureWindowsPath, WINDOWS, {}, PureWindowsPath(r"C:\dev\cliente")
    )
    assert dono.canal_local.startswith(r"\\.\pipe\drivelan-servico-dev-")
    assert dono.canal_local != cliente.canal_local
    assert str(dono.configuracao) == r"C:\dev\dono\config\drivelan.toml"


def test_usuario_linux() -> None:
    d = montar_diretorios_usuario(PurePosixPath, LINUX, {}, PurePosixPath("/home/ana"))
    assert d.base == PurePosixPath("/home/ana/.local/share/drivelan")
    assert d.edicao == d.base / "edicao"
    assert d.pendentes == d.base / "pendentes"
    assert d.temp == d.base / "temp"
    assert d.log_contingencia == d.base / "log-contingencia"


def test_usuario_windows() -> None:
    ambiente = {"LOCALAPPDATA": r"C:\Users\ana\AppData\Local"}
    d = montar_diretorios_usuario(PureWindowsPath, WINDOWS, ambiente, PureWindowsPath(r"C:\x"))
    assert str(d.base) == r"C:\Users\ana\AppData\Local\DriveLan"
    assert str(d.log_contingencia) == r"C:\Users\ana\AppData\Local\DriveLan\log-contingencia"


def test_usuario_windows_sem_variavel() -> None:
    home = PureWindowsPath(r"C:\Users\ana")
    d = montar_diretorios_usuario(PureWindowsPath, WINDOWS, {}, home)
    assert str(d.base) == r"C:\Users\ana\AppData\Local\DriveLan"


def test_sistema_atual() -> None:
    esperado = WINDOWS if os.name == "nt" else LINUX
    assert sistema_atual() is esperado


def test_atalhos_do_sistema_atual(tmp_path: Path) -> None:
    d = diretorios_servico(tmp_path / "dono")
    assert isinstance(d.banco, Path)
    assert d.dados == (tmp_path / "dono").resolve()
    assert isinstance(diretorios_usuario().base, Path)


@pytest.mark.skipif(os.name != "posix", reason="modo 0700 é do POSIX")
def test_criar_diretorio_privado(tmp_path: Path) -> None:
    alvo = tmp_path / "a" / "b"
    criar_diretorio_privado(alvo)
    assert alvo.is_dir()
    assert stat.S_IMODE(alvo.stat().st_mode) == 0o700
    # Pasta já existente com permissão aberta volta a 0700.
    alvo.chmod(0o755)
    criar_diretorio_privado(alvo)
    assert stat.S_IMODE(alvo.stat().st_mode) == 0o700
