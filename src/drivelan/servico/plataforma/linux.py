"""Identidade do cliente do socket Unix, preparação do socket e privilégios (Linux, FSD 15.5).

O registro como unidade systemd e o firewall são da Fase 27.
"""

import errno
import os
import socket
import stat
import struct
from pathlib import Path

from drivelan.servico.plataforma import (
    CanalEmUso,
    IdentidadeCliente,
    IdentidadeIndisponivel,
    horario_criacao_processo,
)

_FORMATO_UCRED = "3i"
"""`struct ucred` do Linux: pid, uid e gid (inteiros de 32 bits)."""

MODO_PASTA_PRODUCAO = 0o755
"""`/run/drivelan`: só root grava; usuários locais precisam atravessar a pasta para conectar."""

MODO_SOCKET_PRODUCAO = 0o666
"""Usuários locais conectam; a proteção vem da identidade (SO_PEERCRED) e da sessão (FSD 5.6)."""

MODO_SOCKET_DESENVOLVIMENTO = 0o600
"""Em desenvolvimento, só o próprio usuário que roda o serviço."""


def identidade_do_socket(conexao: socket.socket) -> IdentidadeCliente:
    """Lê UID e PID do processo do outro lado com `SO_PEERCRED` (FSD 15.5)."""
    try:
        dados = conexao.getsockopt(
            socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize(_FORMATO_UCRED)
        )
    except OSError as erro:
        raise IdentidadeIndisponivel("SO_PEERCRED indisponível") from erro
    pid, uid, _gid = struct.unpack(_FORMATO_UCRED, dados)
    if pid <= 0:
        raise IdentidadeIndisponivel("PID do cliente desconhecido")
    return IdentidadeCliente(str(uid), pid, horario_criacao_processo(pid))


def _ha_servidor_respondendo(caminho: Path) -> bool:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as teste:
        teste.settimeout(1.0)
        try:
            teste.connect(str(caminho))
        except OSError as erro:
            if erro.errno in (errno.ECONNREFUSED, errno.ENOENT):
                return False
            raise
        return True


def preparar_caminho_socket(caminho: Path, *, producao: bool) -> None:
    """Deixa o caminho do socket pronto para `bind`.

    Cria a pasta (0755 em produção, como `/run/drivelan`; em desenvolvimento ela já é a pasta de
    dados privada ou `$XDG_RUNTIME_DIR`). Um socket antigo, sem ninguém atendendo, é removido. Se
    outro processo responde nele, levanta `CanalEmUso`. Um arquivo que não é socket nunca é
    apagado.
    """
    pasta = caminho.parent
    if producao:
        pasta.mkdir(mode=MODO_PASTA_PRODUCAO, parents=True, exist_ok=True)
        pasta.chmod(MODO_PASTA_PRODUCAO)
    else:
        pasta.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        estado = caminho.lstat()
    except FileNotFoundError:
        return
    if not stat.S_ISSOCK(estado.st_mode):
        raise CanalEmUso(f"{caminho} existe e não é um socket")
    if _ha_servidor_respondendo(caminho):
        raise CanalEmUso(f"outro processo atende em {caminho}")
    caminho.unlink()


def ajustar_permissoes_socket(caminho: Path, *, producao: bool) -> None:
    """Aplica o modo do socket depois do `bind`."""
    caminho.chmod(MODO_SOCKET_PRODUCAO if producao else MODO_SOCKET_DESENVOLVIMENTO)


def eh_administrador() -> bool:
    """Comandos protegidos exigem root (FSD 24.8)."""
    return os.geteuid() == 0
