"""Tarefas periódicas que já existem nesta fase (FSD 6.1, 19.1.3, 19.1.5 e 19.1.6).

As demais tarefas da seção 6.1 (encerramentos vencidos, travas sem sinal, lixeira, auditoria,
espaço ocupado e `PRAGMA optimize`) são registradas aqui pelas fases que as implementam.
"""

from collections.abc import Callable
from datetime import date

from drivelan.servico.configuracao import Configuracao, MonitorConfiguracao
from drivelan.servico.log_erros import LogErros, aplicar_retencao
from drivelan.servico.tarefas.agendador import Agendador

INTERVALO_CONFIGURACAO = 60.0
"""Verificação da data de modificação do `drivelan.toml` (FSD 19.1.3)."""

INTERVALO_CONTINGENCIA = 60.0
"""Nova tentativa de gravar o log em arquivo (FSD 19.1.5)."""

HORA_TAREFAS_DIARIAS = (3, 0)
"""As tarefas diárias rodam às 03:00 e na inicialização (FSD 6.1)."""


def registrar_tarefas_basicas(
    agendador: Agendador,
    log: LogErros,
    monitor: MonitorConfiguracao,
    ao_mudar_configuracao: Callable[[Configuracao], None],
    *,
    hoje: Callable[[], date] = date.today,
) -> None:
    def verificar_configuracao() -> None:
        nova = monitor.verificar()
        if nova is not None:
            ao_mudar_configuracao(nova)

    def reter_logs() -> None:
        aplicar_retencao(log.pasta, hoje())

    agendador.a_cada("configuracao", INTERVALO_CONFIGURACAO, verificar_configuracao)
    agendador.a_cada("log-contingencia", INTERVALO_CONTINGENCIA, log.tentar_novamente)
    hora, minuto = HORA_TAREFAS_DIARIAS
    agendador.diariamente("retencao-logs", hora, minuto, reter_logs)
