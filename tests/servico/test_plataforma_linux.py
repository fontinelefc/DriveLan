"""Testes da identidade do cliente do socket Unix e da preparação do socket (FSD 15.5)."""

import os
import socket
import stat
import sys
from pathlib import Path

import pytest

from drivelan.servico.plataforma import (
    CanalEmUso,
    IdentidadeIndisponivel,
    horario_criacao_processo,
)

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="somente Linux")

if sys.platform != "win32":
    from drivelan.servico.plataforma import linux


def test_so_peercred_identifica_uid_e_pid() -> None:
    a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    with a, b:
        identidade = linux.identidade_do_socket(a)
    assert identidade.usuario_so == str(os.getuid())
    assert identidade.pid == os.getpid()
    assert identidade.processo_criado_em == horario_criacao_processo(os.getpid())


def test_socket_sem_credenciais_nao_tem_identidade() -> None:
    with (
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp,
        pytest.raises(IdentidadeIndisponivel),
    ):
        linux.identidade_do_socket(udp)


def test_processo_inexistente_nao_tem_identidade() -> None:
    with pytest.raises(IdentidadeIndisponivel):
        horario_criacao_processo(2**30)


def test_caminho_livre_fica_pronto(pasta_curta: Path) -> None:
    caminho = pasta_curta / "sub" / "local.sock"
    linux.preparar_caminho_socket(caminho, producao=False)
    assert caminho.parent.is_dir()
    assert stat.S_IMODE(caminho.parent.stat().st_mode) == 0o700


def test_pasta_de_producao_fica_com_0755(pasta_curta: Path) -> None:
    caminho = pasta_curta / "run" / "local.sock"
    linux.preparar_caminho_socket(caminho, producao=True)
    assert stat.S_IMODE(caminho.parent.stat().st_mode) == 0o755


def test_socket_abandonado_e_removido(pasta_curta: Path) -> None:
    caminho = pasta_curta / "local.sock"
    antigo = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    antigo.bind(str(caminho))
    antigo.close()  # o arquivo fica, mas ninguém atende
    linux.preparar_caminho_socket(caminho, producao=False)
    assert not caminho.exists()


def test_socket_em_uso_por_outro_processo(pasta_curta: Path) -> None:
    caminho = pasta_curta / "local.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as vivo:
        vivo.bind(str(caminho))
        vivo.listen()
        with pytest.raises(CanalEmUso):
            linux.preparar_caminho_socket(caminho, producao=False)
    assert caminho.exists()


def test_arquivo_comum_nunca_e_apagado(pasta_curta: Path) -> None:
    caminho = pasta_curta / "local.sock"
    caminho.write_text("não sou socket", encoding="utf-8")
    with pytest.raises(CanalEmUso):
        linux.preparar_caminho_socket(caminho, producao=False)
    assert caminho.read_text(encoding="utf-8") == "não sou socket"


@pytest.mark.parametrize(("producao", "modo"), [(False, 0o600), (True, 0o666)])
def test_modo_do_socket(pasta_curta: Path, producao: bool, modo: int) -> None:
    caminho = pasta_curta / "local.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as servidor:
        servidor.bind(str(caminho))
        linux.ajustar_permissoes_socket(caminho, producao=producao)
        assert stat.S_IMODE(caminho.stat().st_mode) == modo


def test_administrador_e_root() -> None:
    assert linux.eh_administrador() == (os.geteuid() == 0)
