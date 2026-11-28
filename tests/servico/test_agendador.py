"""Testes do agendador e das tarefas básicas (FSD 5.3, 6.1, 19.1.3, 19.1.5, 19.1.6)."""

import asyncio
import io
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from drivelan.servico.configuracao import Configuracao, MonitorConfiguracao
from drivelan.servico.log_erros import LogErros, caminho_do_dia
from drivelan.servico.tarefas.agendador import Agendador, proxima_execucao_diaria
from drivelan.servico.tarefas.basicas import registrar_tarefas_basicas

BRASILIA = timezone(timedelta(hours=-3))


def _log(pasta: Path) -> LogErros:
    return LogErros(pasta / "logs", saida_erro=io.StringIO())


def _texto_log(pasta: Path) -> str:
    return "".join(p.read_text(encoding="utf-8") for p in (pasta / "logs").rglob("*.log"))


class TempoSimulado:
    """Relógio e `dormir` falsos: dormir avança o relógio; após o limite, dorme para sempre."""

    def __init__(self, inicio: datetime, limite: timedelta) -> None:
        self.agora = inicio
        self._fim = inicio + limite

    def relogio(self) -> datetime:
        return self.agora

    async def dormir(self, segundos: float) -> None:
        if self.agora >= self._fim:
            await asyncio.Event().wait()
        self.agora += timedelta(seconds=segundos)
        await asyncio.sleep(0)


async def _esperar(condicao: object, tempo: float = 2.0) -> None:
    fim = asyncio.get_running_loop().time() + tempo
    while not condicao() and asyncio.get_running_loop().time() < fim:  # type: ignore[operator]
        await asyncio.sleep(0.01)


@pytest.mark.parametrize(
    ("agora", "esperado"),
    [
        (datetime(2026, 11, 27, 2, 59, tzinfo=BRASILIA), datetime(2026, 11, 27, 3, 0)),
        (datetime(2026, 11, 27, 3, 0, tzinfo=BRASILIA), datetime(2026, 11, 28, 3, 0)),
        (datetime(2026, 11, 27, 15, 0, tzinfo=BRASILIA), datetime(2026, 11, 28, 3, 0)),
        (datetime(2026, 12, 31, 23, 0, tzinfo=BRASILIA), datetime(2027, 1, 1, 3, 0)),
    ],
)
def test_proxima_execucao_diaria(agora: datetime, esperado: datetime) -> None:
    assert proxima_execucao_diaria(agora, 3, 0) == esperado.replace(tzinfo=BRASILIA)


def test_valores_invalidos(tmp_path: Path) -> None:
    agendador = Agendador(_log(tmp_path))
    with pytest.raises(ValueError):
        agendador.a_cada("x", 0, lambda: None)
    with pytest.raises(ValueError):
        agendador.diariamente("x", 24, 0, lambda: None)


@pytest.mark.asyncio
async def test_tarefa_periodica_roda_varias_vezes_em_thread_de_disco(tmp_path: Path) -> None:
    threads: list[str] = []
    agendador = Agendador(_log(tmp_path))
    agendador.a_cada("contar", 0.01, lambda: threads.append(threading.current_thread().name))
    agendador.iniciar()
    await _esperar(lambda: len(threads) >= 3)
    await agendador.parar()
    assert len(threads) >= 3
    assert threading.main_thread().name not in threads


@pytest.mark.asyncio
async def test_corrotina_roda_no_laco(tmp_path: Path) -> None:
    chamadas: list[int] = []

    async def tarefa() -> None:
        chamadas.append(1)

    agendador = Agendador(_log(tmp_path))
    agendador.a_cada("async", 0.01, tarefa)
    agendador.iniciar()
    await _esperar(lambda: len(chamadas) >= 2)
    await agendador.parar()
    assert len(chamadas) >= 2


@pytest.mark.asyncio
async def test_falha_vai_para_o_log_e_nao_para_o_agendador(tmp_path: Path) -> None:
    chamadas: list[int] = []

    def falha() -> None:
        chamadas.append(1)
        raise OSError("disco")

    agendador = Agendador(_log(tmp_path))
    agendador.a_cada("falha", 0.01, falha)
    agendador.iniciar()
    await _esperar(lambda: len(chamadas) >= 3)
    await agendador.parar()
    assert len(chamadas) >= 3
    texto = _texto_log(tmp_path)
    assert "Falha na tarefa periódica" in texto and "tarefa=falha" in texto


@pytest.mark.asyncio
async def test_diaria_roda_na_inicializacao_e_as_tres(tmp_path: Path) -> None:
    tempo = TempoSimulado(datetime(2026, 11, 27, 2, 58, tzinfo=BRASILIA), timedelta(hours=36))
    horarios: list[datetime] = []
    agendador = Agendador(_log(tmp_path), relogio=tempo.relogio, dormir=tempo.dormir)
    agendador.diariamente("diaria", 3, 0, lambda: horarios.append(tempo.agora))
    agendador.iniciar()
    await _esperar(lambda: len(horarios) >= 3)
    await asyncio.sleep(0.05)
    await agendador.parar()
    assert [h.strftime("%d %H:%M") for h in horarios] == ["27 02:58", "27 03:00", "28 03:00"]


@pytest.mark.asyncio
async def test_diaria_sem_execucao_na_inicializacao(tmp_path: Path) -> None:
    tempo = TempoSimulado(datetime(2026, 11, 27, 4, 0, tzinfo=BRASILIA), timedelta(hours=2))
    horarios: list[datetime] = []
    agendador = Agendador(_log(tmp_path), relogio=tempo.relogio, dormir=tempo.dormir)
    agendador.diariamente("d", 3, 0, lambda: horarios.append(tempo.agora), na_inicializacao=False)
    agendador.iniciar()
    await asyncio.sleep(0.1)
    await agendador.parar()
    assert horarios == []


@pytest.mark.asyncio
async def test_parar_e_idempotente(tmp_path: Path) -> None:
    agendador = Agendador(_log(tmp_path))
    agendador.a_cada("x", 10, lambda: None)
    agendador.iniciar()
    agendador.iniciar()  # não duplica
    await agendador.parar()
    await agendador.parar()


# ---------------------------------------------------------------- tarefas básicas


@pytest.mark.asyncio
async def test_tarefas_basicas_registradas(tmp_path: Path) -> None:
    log = _log(tmp_path)
    monitor = MonitorConfiguracao(tmp_path / "drivelan.toml", log)
    agendador = Agendador(log)
    registrar_tarefas_basicas(agendador, log, monitor, lambda _c: None)
    assert agendador.nomes == ["configuracao", "log-contingencia", "retencao-logs"]


@pytest.mark.asyncio
async def test_retencao_dos_logs_roda_na_inicializacao(tmp_path: Path) -> None:
    log = _log(tmp_path)
    antigo = caminho_do_dia(log.pasta, date(2026, 1, 10))
    recente = caminho_do_dia(log.pasta, date(2026, 11, 1))
    for arquivo in (antigo, recente):
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text("x\n", encoding="utf-8")
    monitor = MonitorConfiguracao(tmp_path / "drivelan.toml", log)
    agendador = Agendador(log)
    registrar_tarefas_basicas(
        agendador, log, monitor, lambda _c: None, hoje=lambda: date(2026, 11, 27)
    )
    agendador.iniciar()
    await _esperar(lambda: not antigo.exists())
    await agendador.parar()
    assert not antigo.exists() and recente.exists()


@pytest.mark.asyncio
async def test_mudanca_na_configuracao_e_aplicada(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import drivelan.servico.tarefas.basicas as basicas

    monkeypatch.setattr(basicas, "INTERVALO_CONFIGURACAO", 0.01)
    caminho = tmp_path / "drivelan.toml"
    log = _log(tmp_path)
    monitor = MonitorConfiguracao(caminho, log, intervalo=0)
    monitor.carregar()
    recebidas: list[Configuracao] = []
    agendador = Agendador(log)
    registrar_tarefas_basicas(agendador, log, monitor, recebidas.append)
    agendador.iniciar()
    caminho.write_text("[rede]\nporta = 47900\n", encoding="utf-8")
    await _esperar(lambda: bool(recebidas))
    await agendador.parar()
    assert recebidas[-1].rede_porta == 47900
