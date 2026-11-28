"""Identidade do cliente do named pipe e privilégios (Windows, FSD 15.5).

O registro como serviço do Windows (LocalSystem) e o firewall são da Fase 27.
"""

import sys

assert sys.platform == "win32"  # noqa: S101 — o mypy só analisa este módulo no Windows

import ctypes

import pywintypes
import win32api
import win32con
import win32security

from drivelan.servico.plataforma import IdentidadeIndisponivel

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def sid_do_processo(pid: int) -> str:
    """SID (texto `S-1-5-...`) do usuário dono do token do processo."""
    try:
        processo = win32api.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        try:
            token = win32security.OpenProcessToken(processo, win32con.TOKEN_QUERY)
            try:
                sid, _atributos = win32security.GetTokenInformation(token, win32security.TokenUser)
                return str(win32security.ConvertSidToStringSid(sid))
            finally:
                token.Close()
        finally:
            processo.Close()
    except pywintypes.error as erro:
        raise IdentidadeIndisponivel(f"SID do processo {pid} indisponível") from erro


def eh_administrador() -> bool:
    """Comandos protegidos exigem administrador do SO (FSD 24.8)."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False
