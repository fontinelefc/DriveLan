"""Testes da ordem de inicialização e do ciclo de vida do serviço (FSD 6.1)."""

import asyncio
import io
import sys
from pathlib import Path
from typing import Any

import pytest

from drivelan.comum.canal_local import ClienteCanalLocal
from drivelan.comum.diretorios import diretorios_servico
from drivelan.servico.dados.banco import BancoDados
from drivelan.servico.dados.migracoes import FalhaMigracao
from drivelan.servico.inicializacao import OpcoesServico, Servico

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="socket Unix (Linux)")


def _servico(pasta: Path, *, console: bool = False, intervalo: float = 0.02) -> Servico:
    return Servico(
        OpcoesServico(console=console, dados_dev=pasta),
        terminal=io.StringIO(),
        intervalo_nova_tentativa=intervalo,
    )


def _texto_log(pasta: Path) -> str:
    return "".join(p.read_text(encoding="utf-8") for p in (pasta / "logs").rglob("*.log"))


async def _esperar(condicao: Any, tempo: float = 5.0) -> None:
    fim = asyncio.get_running_loop().time() + tempo
    while not condicao() and asyncio.get_running_loop().time() < fim:
        await asyncio.sleep(0.01)


def test_ordem_das_etapas_da_secao_6_1(pasta_curta: Path) -> None:
    etapas = _servico(pasta_curta).etapas()
    assert [e.numero for e in etapas] == list(range(1, 11))
    sem_efeito = [e.numero for e in etapas if e.executar is None]
    assert sem_efeito == [4, 5, 6, 7, 9]  # fases 11, 20, 13, 11 e 12
    assert [e.numero for e in etapas if e.impeditiva] == [3, 8]


@pytest.mark.asyncio
async def test_partida_completa_e_fechamento(pasta_curta: Path) -> None:
    servico = _servico(pasta_curta)
    try:
        assert await servico.iniciar() is True
        assert servico.etapas_concluidas == [1, 2, 3, 8, 10]
        assert servico.pronto
        assert servico.diretorios.banco.exists()
        assert servico.diretorios.configuracao.exists()
        async with ClienteCanalLocal(servico.diretorios.canal_local) as cliente:
            assert (await cliente.obter_estado()).pronto is True
        assert servico.agendador is not None
        assert "retencao-logs" in servico.agendador.nomes
    finally:
        await servico.fechar()
    assert not servico.pronto
    assert not Path(servico.diretorios.canal_local).exists()
    await servico.fechar()  # idempotente


@pytest.mark.asyncio
async def test_executar_ate_pedir_parada(pasta_curta: Path) -> None:
    servico = _servico(pasta_curta, console=True)
    tarefa = asyncio.create_task(servico.executar())
    await _esperar(lambda: servico.pronto)
    assert servico.pronto
    servico.pedir_parada()
    await asyncio.wait_for(tarefa, 5)
    terminal = servico._terminal.getvalue()  # type: ignore[attr-defined]
    assert "canal local em" in terminal and "pronto." in terminal


@pytest.mark.asyncio
async def test_canal_em_uso_tenta_de_novo_ate_liberar(pasta_curta: Path) -> None:
    primeiro = _servico(pasta_curta)
    assert await primeiro.iniciar()
    segundo = _servico(pasta_curta)
    tarefa = asyncio.create_task(segundo.iniciar())
    try:
        await _esperar(lambda: _texto_log(pasta_curta).count("Falha impeditiva") >= 2)
        assert not segundo.pronto
        assert 8 not in segundo.etapas_concluidas
        await primeiro.fechar()
        assert await asyncio.wait_for(tarefa, 5) is True
        assert segundo.pronto
    finally:
        await primeiro.fechar()
        await segundo.fechar()
    texto = _texto_log(pasta_curta)
    assert "etapa=8" in texto and "CanalEmUso" in texto


@pytest.mark.asyncio
async def test_falha_no_banco_tenta_de_novo(
    pasta_curta: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = BancoDados.abrir
    tentativas: list[int] = []

    def abrir_com_falha(caminho: Path, log: Any, *, migrar: bool = True) -> BancoDados:
        tentativas.append(1)
        if len(tentativas) < 3:
            raise FalhaMigracao(1)
        return original(caminho, log, migrar=migrar)

    monkeypatch.setattr(BancoDados, "abrir", staticmethod(abrir_com_falha))
    servico = _servico(pasta_curta)
    try:
        assert await servico.iniciar()
    finally:
        await servico.fechar()
    assert len(tentativas) == 3
    texto = _texto_log(pasta_curta)
    assert texto.count("Falha impeditiva na inicialização") == 2 and "etapa=3" in texto


@pytest.mark.asyncio
async def test_parada_durante_nova_tentativa(
    pasta_curta: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def sempre_falha(*_args: Any, **_kwargs: Any) -> BancoDados:
        raise FalhaMigracao(1)

    monkeypatch.setattr(BancoDados, "abrir", staticmethod(sempre_falha))
    servico = _servico(pasta_curta, intervalo=30.0)
    tarefa = asyncio.create_task(servico.iniciar())
    await _esperar(lambda: "Falha impeditiva" in _texto_log(pasta_curta))
    servico.pedir_parada()  # interrompe a espera de 30 s
    assert await asyncio.wait_for(tarefa, 2) is False
    assert not servico.pronto
    await servico.fechar()


@pytest.mark.asyncio
async def test_configuracao_ilegivel_nao_impede_a_partida(pasta_curta: Path) -> None:
    configuracao = diretorios_servico(pasta_curta).configuracao
    configuracao.parent.mkdir(parents=True)
    configuracao.write_text("isto não é [toml", encoding="utf-8")
    servico = _servico(pasta_curta)
    try:
        assert await servico.iniciar()
    finally:
        await servico.fechar()
    assert configuracao.read_text(encoding="utf-8") == "isto não é [toml"
    assert "| AVISO |" in _texto_log(pasta_curta)


@pytest.mark.asyncio
async def test_porta_da_configuracao_e_lida(pasta_curta: Path) -> None:
    configuracao = diretorios_servico(pasta_curta).configuracao
    configuracao.parent.mkdir(parents=True)
    configuracao.write_text("[rede]\nporta = 47821\n", encoding="utf-8")
    servico = _servico(pasta_curta)
    try:
        assert await servico.iniciar()
        assert servico.configuracao.rede_porta == 47821
    finally:
        await servico.fechar()


@pytest.mark.asyncio
async def test_console_espelha_o_log_no_terminal(pasta_curta: Path) -> None:
    servico = _servico(pasta_curta, console=True)
    try:
        assert await servico.iniciar()
        assert servico.log is not None
        servico.log.erro("teste", "Erro de teste")
    finally:
        await servico.fechar()
    assert "Erro de teste" in servico._terminal.getvalue()  # type: ignore[attr-defined]
