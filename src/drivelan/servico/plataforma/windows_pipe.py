"""Servidor próprio do named pipe do canal local (Windows, FSD 15.5.1).

O `NamedPipeSite` do aiohttp usa o pipe do `asyncio`, que é criado com flags e descritor de
segurança fixos: não recusa clientes remotos nem dá escrita a usuários comuns. Por isso o serviço
cria cada instância do pipe por conta própria:

- `PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED` (mais `FILE_FLAG_FIRST_PIPE_INSTANCE` na primeira,
  para que nenhum outro processo ocupe o nome antes do serviço);
- `PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS`, instâncias
  ilimitadas e sempre uma instância aguardando conexão;
- descritor de segurança explícito `DESCRITOR_SDDL`.

Ao conectar, o PID (`GetNamedPipeClientProcessId`) e o SID do token do processo são lidos **antes**
de qualquer pedido; sem identidade, a instância é fechada. A instância conectada vira um transporte
do proactor do `asyncio` (E/S sobreposta com IOCP) e é atendida pelo `aiohttp.web.Server`, que não
depende de socket.

Atenção: `loop._proactor.accept_pipe` e `loop._make_duplex_pipe_transport` são APIs internas do
`asyncio` (as mesmas usadas pelo `PipeServer` da biblioteca padrão), estáveis no Python 3.12 fixado
pelo projeto. Se deixarem de funcionar, a alternativa prevista no FSD é uma ponte com uma thread
por conexão.
"""

import sys

assert sys.platform == "win32"  # noqa: S101 — o mypy só analisa este módulo no Windows

import asyncio
import contextlib
from asyncio import windows_utils
from collections.abc import Callable
from typing import Any

import pywintypes
import win32file
import win32pipe
import win32security

from drivelan.servico.log_erros import LogErros, origem_de
from drivelan.servico.plataforma import (
    CHAVE_IDENTIDADE,
    CanalEmUso,
    IdentidadeCliente,
    IdentidadeIndisponivel,
    horario_criacao_processo,
)
from drivelan.servico.plataforma.windows import sid_do_processo

ORIGEM_LOG = origem_de(__name__)

DESCRITOR_SDDL = "D:P(D;;GA;;;NU)(A;;GA;;;SY)(A;;GA;;;BA)(A;;GRGW;;;IU)"
"""Nega usuários de rede; controle total para SYSTEM e administradores; leitura e escrita para
usuários interativos (FSD 15.5.1)."""

PIPE_REJECT_REMOTE_CLIENTS = 0x00000008
FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000
TAMANHO_BUFFER = 64 * 1024
_ERRO_ACESSO_NEGADO = 5
_ERRO_PIPE_OCUPADO = 231


def _atributos_seguranca() -> Any:
    atributos = win32security.SECURITY_ATTRIBUTES()
    atributos.SECURITY_DESCRIPTOR = (
        win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
            DESCRITOR_SDDL, win32security.SDDL_REVISION_1
        )
    )
    atributos.bInheritHandle = False
    return atributos


def criar_instancia(nome: str, *, primeira: bool) -> windows_utils.PipeHandle:
    """Cria uma instância do pipe com as flags e o descritor da seção 15.5.1."""
    modo_abertura = win32pipe.PIPE_ACCESS_DUPLEX | win32file.FILE_FLAG_OVERLAPPED
    if primeira:
        modo_abertura |= FILE_FLAG_FIRST_PIPE_INSTANCE
    modo_pipe = (
        win32pipe.PIPE_TYPE_BYTE
        | win32pipe.PIPE_READMODE_BYTE
        | win32pipe.PIPE_WAIT
        | PIPE_REJECT_REMOTE_CLIENTS
    )
    try:
        identificador = win32pipe.CreateNamedPipe(
            nome,
            modo_abertura,
            modo_pipe,
            win32pipe.PIPE_UNLIMITED_INSTANCES,
            TAMANHO_BUFFER,
            TAMANHO_BUFFER,
            0,
            _atributos_seguranca(),
        )
    except pywintypes.error as erro:
        if erro.winerror in (_ERRO_ACESSO_NEGADO, _ERRO_PIPE_OCUPADO):
            raise CanalEmUso(f"o pipe {nome} já está em uso") from erro
        raise
    return windows_utils.PipeHandle(identificador.Detach())


def identidade_do_pipe(pipe: windows_utils.PipeHandle) -> IdentidadeCliente:
    """PID do cliente conectado, SID do token do processo e horário de criação."""
    try:
        pid = int(win32pipe.GetNamedPipeClientProcessId(pipe.fileno()))
    except pywintypes.error as erro:
        raise IdentidadeIndisponivel("PID do cliente do pipe indisponível") from erro
    if pid <= 0:
        raise IdentidadeIndisponivel("PID do cliente desconhecido")
    return IdentidadeCliente(sid_do_processo(pid), pid, horario_criacao_processo(pid))


class ServidorPipe:
    """Aceita conexões no pipe e entrega cada uma a um protocolo `asyncio` novo."""

    def __init__(
        self,
        nome: str,
        fabrica_protocolo: Callable[[], asyncio.Protocol],
        log: LogErros,
    ) -> None:
        self._nome = nome
        self._fabrica = fabrica_protocolo
        self._log = log
        self._pendente: windows_utils.PipeHandle | None = None
        self._tarefa: asyncio.Task[None] | None = None
        self._transportes: set[asyncio.BaseTransport] = set()

    @property
    def nome(self) -> str:
        return self._nome

    def iniciar(self) -> None:
        """Cria a primeira instância (falha já aqui se o nome estiver em uso) e começa a aceitar."""
        self._pendente = criar_instancia(self._nome, primeira=True)
        self._tarefa = asyncio.get_running_loop().create_task(
            self._aceitar_em_laco(), name="drivelan-canal-pipe"
        )

    async def _aceitar_em_laco(self) -> None:
        laco: Any = asyncio.get_running_loop()
        while True:
            atual = self._pendente
            if atual is None:
                return
            try:
                await laco._proactor.accept_pipe(atual)
            except asyncio.CancelledError:
                raise
            except OSError as erro:
                # Cliente desistiu antes de concluir a conexão: descarta a instância e segue.
                atual.close()
                self._pendente = criar_instancia(self._nome, primeira=False)
                self._log.erro(ORIGEM_LOG, "Falha ao aceitar conexão no pipe", excecao=erro)
                continue
            # Antes de atender esta conexão, já deixa outra instância aguardando.
            self._pendente = criar_instancia(self._nome, primeira=False)
            self._atender(laco, atual)

    def _atender(self, laco: Any, pipe: windows_utils.PipeHandle) -> None:
        try:
            identidade = identidade_do_pipe(pipe)
        except IdentidadeIndisponivel as erro:
            self._log.erro(ORIGEM_LOG, "Cliente do canal local sem identidade", excecao=erro)
            pipe.close()
            return
        protocolo = self._fabrica()
        transporte = laco._make_duplex_pipe_transport(
            pipe, protocolo, extra={CHAVE_IDENTIDADE: identidade, "addr": self._nome}
        )
        self._transportes = {t for t in self._transportes if not t.is_closing()}
        self._transportes.add(transporte)

    async def parar(self) -> None:
        """Para de aceitar, fecha as conexões abertas e a instância pendente."""
        if self._tarefa is not None:
            self._tarefa.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._tarefa
            self._tarefa = None
        for transporte in list(self._transportes):
            transporte.close()
        self._transportes.clear()
        if self._pendente is not None:
            self._pendente.close()
            self._pendente = None
