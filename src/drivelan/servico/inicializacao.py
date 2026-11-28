"""Ordem de partida e ciclo de vida do serviço (FSD 5.3 e 6.1).

Ordem da seção 6.1:

1. log de erros;
2. leitura da configuração (padrões se ausente ou inválida);
3. abertura do banco e execução das migrations;
4. certificado e identidade da instalação (Fase 11);
5. encerramentos vencidos durante o desligamento (Fase 20);
6. recálculo do espaço ocupado em segundo plano (Fase 13);
7. servidor TLS na porta configurada (Fase 11);
8. canal local;
9. anúncio mDNS e resposta a broadcast (Fase 12);
10. agendador.

Falha numa etapa é registrada no log. Quando ela é impeditiva (banco, canal em uso...), o serviço
tenta de novo a cada 30 segundos, sem encerrar. As etapas ainda não construídas aparecem na lista
sem efeito, para manter a ordem visível.
"""

import asyncio
import contextlib
import sys
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from drivelan.comum.diretorios import DiretoriosServico, diretorios_servico
from drivelan.servico.api.local.aplicacao import DependenciasCanal, criar_aplicacao
from drivelan.servico.api.local.servidor import CanalLocal
from drivelan.servico.configuracao import Configuracao, MonitorConfiguracao
from drivelan.servico.dados.banco import BancoDados
from drivelan.servico.log_erros import LogErros, origem_de
from drivelan.servico.tarefas.agendador import Agendador
from drivelan.servico.tarefas.basicas import registrar_tarefas_basicas

ORIGEM_LOG = origem_de(__name__)

INTERVALO_NOVA_TENTATIVA = 30.0
"""Segundos entre as tentativas de uma etapa impeditiva (FSD 6.1)."""

THREADS_DISCO = 4
"""Tamanho do pool de threads para operações de disco (FSD 5.3)."""


@dataclass(frozen=True, slots=True)
class OpcoesServico:
    """Opções de linha de comando que afetam a execução."""

    console: bool = False
    """Primeiro plano com o log também no terminal (FSD 4.1)."""
    dados_dev: Path | None = None
    """Pasta de dados alternativa de desenvolvimento (`--dados`)."""


@dataclass(frozen=True, slots=True)
class Etapa:
    numero: int
    nome: str
    executar: Callable[[], Awaitable[None]] | None
    """`None` = etapa de uma fase futura, sem efeito por enquanto."""
    impeditiva: bool = False


class Servico:
    """Contexto do serviço: cria os componentes na ordem da seção 6.1 e os fecha ao parar."""

    def __init__(
        self,
        opcoes: OpcoesServico,
        *,
        diretorios: DiretoriosServico[Path] | None = None,
        terminal: TextIO | None = None,
        intervalo_nova_tentativa: float = INTERVALO_NOVA_TENTATIVA,
    ) -> None:
        self.opcoes = opcoes
        self.diretorios = diretorios or diretorios_servico(opcoes.dados_dev)
        self._terminal = terminal if terminal is not None else sys.stderr
        self._intervalo = intervalo_nova_tentativa
        self._parada = asyncio.Event()
        self.log: LogErros | None = None
        self.monitor: MonitorConfiguracao | None = None
        self.configuracao = Configuracao()
        self.banco: BancoDados | None = None
        self.canal: CanalLocal | None = None
        self.agendador: Agendador | None = None
        self.pool: ThreadPoolExecutor | None = None
        self.pronto = False
        self.etapas_concluidas: list[int] = []

    # ------------------------------------------------------------ ciclo de vida

    def pedir_parada(self) -> None:
        self._parada.set()

    async def executar(self) -> None:
        """Inicia todas as etapas e roda até `pedir_parada()`. Sempre fecha o que abriu."""
        try:
            if await self.iniciar():
                self._escrever_terminal("drivelan-service: pronto.")
                await self._parada.wait()
        finally:
            await self.fechar()

    async def iniciar(self) -> bool:
        """Executa as etapas em ordem. Devolve `False` se a parada foi pedida no meio."""
        self.pool = ThreadPoolExecutor(THREADS_DISCO, thread_name_prefix="drivelan-disco")
        asyncio.get_running_loop().set_default_executor(self.pool)
        for etapa in self.etapas():
            if etapa.executar is None:
                continue
            if not await self._executar_etapa(etapa):
                return False
            self.etapas_concluidas.append(etapa.numero)
        self.pronto = True
        return True

    async def fechar(self) -> None:
        """Fecha na ordem inversa: agendador, canal, banco. Pode ser chamado mais de uma vez."""
        self.pronto = False
        if self.agendador is not None:
            await self.agendador.parar()
            self.agendador = None
        if self.canal is not None:
            await self.canal.parar()
            self.canal = None
        if self.banco is not None:
            banco, self.banco = self.banco, None
            await asyncio.to_thread(banco.fechar)

    # ------------------------------------------------------------ etapas

    def etapas(self) -> list[Etapa]:
        return [
            Etapa(1, "log de erros", self._iniciar_log),
            Etapa(2, "configuração", self._carregar_configuracao),
            Etapa(3, "banco e migrations", self._abrir_banco, impeditiva=True),
            Etapa(4, "certificado e identidade", None),  # Fase 11
            Etapa(5, "encerramentos vencidos", None),  # Fase 20
            Etapa(6, "recálculo do espaço ocupado", None),  # Fase 13
            Etapa(7, "servidor TLS", None),  # Fase 11
            Etapa(8, "canal local", self._iniciar_canal, impeditiva=True),
            Etapa(9, "anúncio mDNS e broadcast", None),  # Fase 12
            Etapa(10, "agendador", self._iniciar_agendador),
        ]

    async def _executar_etapa(self, etapa: Etapa) -> bool:
        executar = etapa.executar
        if executar is None:
            return True
        while not self._parada.is_set():
            try:
                await executar()
                return True
            except Exception as erro:
                if not etapa.impeditiva:
                    self._log_obrigatorio().erro(
                        ORIGEM_LOG,
                        "Falha numa etapa da inicialização; o serviço continua",
                        {"etapa": etapa.numero, "nome": etapa.nome},
                        erro,
                    )
                    return True
                self._log_obrigatorio().erro(
                    ORIGEM_LOG,
                    "Falha impeditiva na inicialização; nova tentativa em 30 segundos",
                    {"etapa": etapa.numero, "nome": etapa.nome},
                    erro,
                )
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._parada.wait(), timeout=self._intervalo)
        return False

    async def _iniciar_log(self) -> None:
        self.log = LogErros(
            self.diretorios.logs, espelho=self._terminal if self.opcoes.console else None
        )

    async def _carregar_configuracao(self) -> None:
        self.monitor = MonitorConfiguracao(self.diretorios.configuracao, self._log_obrigatorio())
        self.configuracao = await asyncio.to_thread(self.monitor.carregar)

    async def _abrir_banco(self) -> None:
        self.banco = await asyncio.to_thread(
            BancoDados.abrir, self.diretorios.banco, self._log_obrigatorio()
        )

    async def _iniciar_canal(self) -> None:
        dependencias = DependenciasCanal(
            log=self._log_obrigatorio(),
            pronto=lambda: self.pronto,
            diagnostico=self._terminal if self.opcoes.console else None,
        )
        canal = CanalLocal(
            self.diretorios.canal_local,
            criar_aplicacao(dependencias),
            self._log_obrigatorio(),
            producao=self.opcoes.dados_dev is None,
        )
        await canal.iniciar()
        self.canal = canal
        self._escrever_terminal(f"drivelan-service: canal local em {canal.endereco}")

    async def _iniciar_agendador(self) -> None:
        if self.monitor is None:
            raise RuntimeError("a configuração é carregada antes do agendador")
        agendador = Agendador(self._log_obrigatorio())
        registrar_tarefas_basicas(
            agendador, self._log_obrigatorio(), self.monitor, self._aplicar_configuracao
        )
        agendador.iniciar()
        self.agendador = agendador

    def _aplicar_configuracao(self, nova: Configuracao) -> None:
        # Chamado na thread de disco; a troca da referência é atômica. Porta e placa novas passam
        # a valer nas fases da rede (10 a 12).
        self.configuracao = nova

    # ------------------------------------------------------------ auxiliares

    def _log_obrigatorio(self) -> LogErros:
        if self.log is None:
            raise RuntimeError("o log é a primeira etapa da inicialização")
        return self.log

    def _escrever_terminal(self, texto: str) -> None:
        if not self.opcoes.console:
            return
        try:
            self._terminal.write(texto + "\n")
            self._terminal.flush()
        except (OSError, ValueError):
            pass


async def executar_servico(opcoes: OpcoesServico) -> int:
    """Roda o serviço até `SIGTERM`/`SIGINT` (Linux) ou Ctrl+C (Windows, pelo `asyncio.run`)."""
    servico = Servico(opcoes)
    if sys.platform != "win32":
        import signal

        laco = asyncio.get_running_loop()
        for sinal in (signal.SIGTERM, signal.SIGINT):
            laco.add_signal_handler(sinal, servico.pedir_parada)
    await servico.executar()
    return 0
