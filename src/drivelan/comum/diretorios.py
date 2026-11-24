"""Pastas do sistema por plataforma (FSD 5.6) e pasta de dados de desenvolvimento (FSD 4.1).

As funções `montar_*` são puras: recebem o sistema, as variáveis de ambiente e a classe de
caminho, o que permite testar os caminhos do Windows no Linux (com `PureWindowsPath`).
`diretorios_servico` e `diretorios_usuario` são os atalhos para o sistema atual.
"""

import hashlib
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePath


class SistemaOperacional(StrEnum):
    """Sistemas suportados na v1 (FSD 3.1)."""

    WINDOWS = "windows"
    LINUX = "linux"


def sistema_atual() -> SistemaOperacional:
    """Sistema em que o processo está rodando."""
    return SistemaOperacional.WINDOWS if sys.platform == "win32" else SistemaOperacional.LINUX


# Valores fixos da seção 5.6.
PROGRAMDATA_PADRAO = r"C:\ProgramData"
PIPE_PRODUCAO = r"\\.\pipe\drivelan-servico"
SOCKET_PRODUCAO = "/run/drivelan/local.sock"
NOME_BANCO = "drivelan.db"
NOME_CONFIGURACAO = "drivelan.toml"

# Limite prático do caminho de um socket Unix (sun_path tem 108 bytes, contando o NUL final).
LIMITE_CAMINHO_SOCKET = 100


@dataclass(frozen=True, slots=True)
class DiretoriosServico[C: PurePath]:
    """Locais usados pelo `drivelan-service` (FSD 5.6)."""

    dados: C
    certificado: C
    banco: C
    configuracao: C
    logs: C
    canal_local: str
    """Caminho do socket Unix (Linux) ou nome do named pipe (Windows)."""


@dataclass(frozen=True, slots=True)
class DiretoriosUsuario[C: PurePath]:
    """Pasta de dados do usuário do SO, usada só pelo app (FSD 5.6)."""

    base: C
    edicao: C
    pendentes: C
    temp: C
    log_contingencia: C


def _hash_curto(caminho: PurePath) -> str:
    """12 caracteres hexadecimais que identificam uma pasta de desenvolvimento."""
    return hashlib.sha256(str(caminho).encode("utf-8")).hexdigest()[:12]


def _canal_local_desenvolvimento[C: PurePath](
    classe: type[C], sistema: SistemaOperacional, ambiente: Mapping[str, str], base: C
) -> str:
    """Canal local exclusivo de uma instância de desenvolvimento."""
    if sistema is SistemaOperacional.WINDOWS:
        return rf"\\.\pipe\drivelan-servico-dev-{_hash_curto(base)}"
    socket = str(base / "local.sock")
    if len(socket.encode("utf-8")) <= LIMITE_CAMINHO_SOCKET:
        return socket
    # Caminho longo demais para AF_UNIX: usa a pasta de execução privada do usuário.
    execucao = ambiente.get("XDG_RUNTIME_DIR")
    if execucao:
        return str(classe(execucao) / f"drivelan-dev-{_hash_curto(base)}.sock")
    return socket


def montar_diretorios_servico[C: PurePath](
    classe: type[C],
    sistema: SistemaOperacional,
    ambiente: Mapping[str, str],
    dados_dev: C | None = None,
) -> DiretoriosServico[C]:
    """Monta os locais do serviço; com `dados_dev`, tudo fica dentro dessa pasta (FSD 4.1)."""
    if dados_dev is not None:
        return DiretoriosServico(
            dados=dados_dev,
            certificado=dados_dev / "certificado",
            banco=dados_dev / NOME_BANCO,
            configuracao=dados_dev / "config" / NOME_CONFIGURACAO,
            logs=dados_dev / "logs",
            canal_local=_canal_local_desenvolvimento(classe, sistema, ambiente, dados_dev),
        )
    if sistema is SistemaOperacional.WINDOWS:
        raiz = classe(ambiente.get("PROGRAMDATA") or PROGRAMDATA_PADRAO) / "DriveLan"
        dados = raiz / "dados"
        return DiretoriosServico(
            dados=dados,
            certificado=dados / "certificado",
            banco=dados / NOME_BANCO,
            configuracao=raiz / "config" / NOME_CONFIGURACAO,
            logs=raiz / "logs",
            canal_local=PIPE_PRODUCAO,
        )
    dados = classe("/var/lib/drivelan")
    return DiretoriosServico(
        dados=dados,
        certificado=dados / "certificado",
        banco=dados / NOME_BANCO,
        configuracao=classe("/etc/drivelan") / NOME_CONFIGURACAO,
        logs=classe("/var/log/drivelan"),
        canal_local=SOCKET_PRODUCAO,
    )


def montar_diretorios_usuario[C: PurePath](
    classe: type[C],
    sistema: SistemaOperacional,
    ambiente: Mapping[str, str],
    home: C,
) -> DiretoriosUsuario[C]:
    """Monta a pasta de dados do usuário do SO (FSD 5.6)."""
    if sistema is SistemaOperacional.WINDOWS:
        local = ambiente.get("LOCALAPPDATA")
        base = (classe(local) if local else home / "AppData" / "Local") / "DriveLan"
    else:
        base = home / ".local" / "share" / "drivelan"
    return DiretoriosUsuario(
        base=base,
        edicao=base / "edicao",
        pendentes=base / "pendentes",
        temp=base / "temp",
        log_contingencia=base / "log-contingencia",
    )


def diretorios_servico(dados_dev: Path | None = None) -> DiretoriosServico[Path]:
    """Locais do serviço no sistema atual (`dados_dev` = opção `--dados`)."""
    base = dados_dev.resolve() if dados_dev is not None else None
    return montar_diretorios_servico(Path, sistema_atual(), os.environ, base)


def diretorios_usuario() -> DiretoriosUsuario[Path]:
    """Pasta de dados do usuário do SO atual."""
    return montar_diretorios_usuario(Path, sistema_atual(), os.environ, Path.home())


def criar_diretorio_privado(caminho: Path) -> None:
    """Cria a pasta (e as pastas-pai), acessível só ao dono (modo 0700 no POSIX, FSD 5.6).

    No Windows, as ACLs restritas das pastas do sistema são aplicadas pelo instalador (Fase 27).
    """
    caminho.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name == "posix":
        caminho.chmod(0o700)
