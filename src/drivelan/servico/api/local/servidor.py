"""Servidor do canal local: socket Unix (Linux) ou named pipe próprio (Windows), FSD 15.5.

Nos dois sistemas, as conexões são atendidas pelo servidor HTTP de baixo nível do aiohttp
(`aiohttp.web.Server`, obtido do `AppRunner`), que não depende do tipo de transporte. O canal
local nunca usa TCP (FSD 15.5.1).
"""

import asyncio
import sys
from pathlib import Path
from typing import Any

from aiohttp import web

from drivelan.servico.log_erros import LogErros
from drivelan.servico.plataforma import CanalEmUso

__all__ = ["CanalEmUso", "CanalLocal"]

TEMPO_ENCERRAMENTO = 5.0
"""Segundos para as conexões abertas terminarem ao parar o serviço."""


class CanalLocal:
    """Liga e desliga o canal local para uma aplicação aiohttp."""

    def __init__(
        self, endereco: str, aplicacao: web.Application, log: LogErros, *, producao: bool
    ) -> None:
        self._endereco = endereco
        self._aplicacao = aplicacao
        self._log = log
        self._producao = producao
        self._runner: web.AppRunner | None = None
        self._servidor: Any = None
        self._ativo = False

    @property
    def endereco(self) -> str:
        return self._endereco

    async def iniciar(self) -> None:
        runner = web.AppRunner(
            self._aplicacao,
            handle_signals=False,
            access_log=None,
            shutdown_timeout=TEMPO_ENCERRAMENTO,
        )
        await runner.setup()
        fabrica = runner.server
        if fabrica is None:
            raise RuntimeError("AppRunner sem servidor após setup")
        try:
            if sys.platform == "win32":
                from drivelan.servico.plataforma.windows_pipe import ServidorPipe

                servidor = ServidorPipe(self._endereco, fabrica, self._log)
                servidor.iniciar()
                self._servidor = servidor
            else:
                self._servidor = await self._iniciar_socket(fabrica)
        except BaseException:
            await runner.cleanup()
            raise
        self._runner = runner
        self._ativo = True

    async def _iniciar_socket(self, fabrica: web.Server) -> asyncio.Server:
        from drivelan.servico.plataforma import linux

        caminho = Path(self._endereco)
        linux.preparar_caminho_socket(caminho, producao=self._producao)
        servidor = await asyncio.get_running_loop().create_unix_server(fabrica, str(caminho))
        linux.ajustar_permissoes_socket(caminho, producao=self._producao)
        return servidor

    async def parar(self) -> None:
        """Para de aceitar conexões, fecha as abertas e remove o socket. Idempotente."""
        if not self._ativo:
            return
        self._ativo = False
        if sys.platform == "win32":
            await self._servidor.parar()
        else:
            self._servidor.close()
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
        if sys.platform != "win32":
            await self._servidor.wait_closed()
            Path(self._endereco).unlink(missing_ok=True)
        self._servidor = None
