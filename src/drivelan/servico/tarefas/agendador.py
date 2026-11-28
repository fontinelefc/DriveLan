"""Agendador interno das tarefas periódicas (FSD 5.3 e 6.1).

Há dois tipos de tarefa: a que roda **a cada N segundos** e a que roda **diariamente** num horário
local (por exemplo, 03:00), opcionalmente também na inicialização. Funções síncronas rodam no pool
de threads de disco (`asyncio.to_thread`); corrotinas rodam no laço principal. A falha de uma
execução é registrada no log (FSD 19.1.1, "Falhas de tarefas periódicas") e não interrompe o
agendador nem as outras tarefas.
"""

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from drivelan.servico.log_erros import LogErros, origem_de

ORIGEM_LOG = origem_de(__name__)

FuncaoTarefa = Callable[[], object] | Callable[[], Awaitable[object]]

ESPERA_MAXIMA = 60.0
"""A espera pela próxima execução diária é feita em trechos de até 60 s, para acompanhar
mudanças do relógio (horário de verão, suspensão do computador)."""


def _hora_local() -> datetime:
    return datetime.now().astimezone()


def proxima_execucao_diaria(agora: datetime, hora: int, minuto: int) -> datetime:
    """Próximo instante `hora:minuto` (no fuso de `agora`) estritamente depois de `agora`."""
    alvo = datetime.combine(agora.date(), time(hora, minuto), tzinfo=agora.tzinfo)
    if alvo <= agora:
        alvo = datetime.combine(agora.date() + timedelta(days=1), time(hora, minuto), agora.tzinfo)
    return alvo


@dataclass(frozen=True, slots=True)
class _Periodica:
    nome: str
    intervalo: float
    funcao: FuncaoTarefa


@dataclass(frozen=True, slots=True)
class _Diaria:
    nome: str
    hora: int
    minuto: int
    funcao: FuncaoTarefa
    na_inicializacao: bool


class Agendador:
    """Executa as tarefas registradas até `parar()`."""

    def __init__(
        self,
        log: LogErros,
        *,
        relogio: Callable[[], datetime] = _hora_local,
        dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._log = log
        self._relogio = relogio
        self._dormir = dormir
        self._tarefas: list[_Periodica | _Diaria] = []
        self._em_execucao: list[asyncio.Task[None]] = []

    @property
    def nomes(self) -> list[str]:
        return [tarefa.nome for tarefa in self._tarefas]

    def a_cada(self, nome: str, segundos: float, funcao: FuncaoTarefa) -> None:
        """Roda `funcao` a cada `segundos`; a primeira execução vem após o primeiro intervalo."""
        if segundos <= 0:
            raise ValueError("o intervalo precisa ser positivo")
        self._tarefas.append(_Periodica(nome, segundos, funcao))

    def diariamente(
        self,
        nome: str,
        hora: int,
        minuto: int,
        funcao: FuncaoTarefa,
        *,
        na_inicializacao: bool = True,
    ) -> None:
        """Roda `funcao` todos os dias em `hora:minuto` (horário local) e, se pedido, ao iniciar."""
        time(hora, minuto)  # valida a faixa
        self._tarefas.append(_Diaria(nome, hora, minuto, funcao, na_inicializacao))

    def iniciar(self) -> None:
        if self._em_execucao:
            return
        for tarefa in self._tarefas:
            corrotina = (
                self._laco_periodico(tarefa)
                if isinstance(tarefa, _Periodica)
                else self._laco_diario(tarefa)
            )
            self._em_execucao.append(
                asyncio.get_running_loop().create_task(corrotina, name=f"tarefa-{tarefa.nome}")
            )

    async def parar(self) -> None:
        """Cancela todas as tarefas e espera que terminem. Idempotente."""
        tarefas, self._em_execucao = self._em_execucao, []
        for tarefa in tarefas:
            tarefa.cancel()
        await asyncio.gather(*tarefas, return_exceptions=True)

    async def executar_agora(self, nome: str, funcao: FuncaoTarefa) -> None:
        """Executa uma vez, registrando a falha no log em vez de propagá-la."""
        try:
            if inspect.iscoroutinefunction(funcao):
                await funcao()
            else:
                await asyncio.to_thread(funcao)
        except asyncio.CancelledError:
            raise
        except Exception as erro:
            self._log.erro(ORIGEM_LOG, "Falha na tarefa periódica", {"tarefa": nome}, erro)

    async def _laco_periodico(self, tarefa: _Periodica) -> None:
        while True:
            await self._dormir(tarefa.intervalo)
            await self.executar_agora(tarefa.nome, tarefa.funcao)

    async def _laco_diario(self, tarefa: _Diaria) -> None:
        if tarefa.na_inicializacao:
            await self.executar_agora(tarefa.nome, tarefa.funcao)
        while True:
            alvo = proxima_execucao_diaria(self._relogio(), tarefa.hora, tarefa.minuto)
            while (restante := (alvo - self._relogio()).total_seconds()) > 0:
                await self._dormir(min(restante, ESPERA_MAXIMA))
            await self.executar_agora(tarefa.nome, tarefa.funcao)
