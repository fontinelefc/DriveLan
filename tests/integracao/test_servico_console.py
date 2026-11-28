"""O `drivelan-service` real, em subprocessos: console, duas instâncias, SIGTERM e `--migrar`."""

import asyncio
import os
import signal
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from drivelan.comum.canal_local import ClienteCanalLocal, ServicoIndisponivel
from drivelan.comum.diretorios import diretorios_servico

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="sinais e socket Unix (Linux)")

TEMPO_LIMITE = 20.0


def _iniciar(dados: Path) -> subprocess.Popen[str]:
    return subprocess.Popen(  # noqa: S603 — comando fixo do próprio projeto
        [sys.executable, "-m", "drivelan.servico", "--console", "--dados", str(dados)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


async def _esperar_pronto(endereco: str) -> bool:
    fim = asyncio.get_running_loop().time() + TEMPO_LIMITE
    while asyncio.get_running_loop().time() < fim:
        try:
            async with ClienteCanalLocal(endereco, tempo_limite=2) as cliente:
                if (await cliente.obter_estado()).pronto:
                    return True
        except ServicoIndisponivel:
            pass
        await asyncio.sleep(0.1)
    return False


def _encerrar(processo: subprocess.Popen[str]) -> tuple[int, str]:
    processo.send_signal(signal.SIGTERM)
    saida, _ = processo.communicate(timeout=TEMPO_LIMITE)
    return processo.returncode, saida


@pytest.fixture
def processos() -> Iterator[list[subprocess.Popen[str]]]:
    lista: list[subprocess.Popen[str]] = []
    yield lista
    for processo in lista:
        if processo.poll() is None:
            processo.kill()
            processo.communicate()


@pytest.mark.asyncio
async def test_console_sobe_responde_e_encerra_com_sigterm(
    pasta_curta: Path, processos: list[subprocess.Popen[str]]
) -> None:
    dados = pasta_curta / "a"
    diretorios = diretorios_servico(dados)
    processos.append(_iniciar(dados))
    assert await _esperar_pronto(diretorios.canal_local)
    assert diretorios.banco.exists() and diretorios.configuracao.exists()
    codigo, saida = _encerrar(processos[0])
    assert codigo == 0, saida
    assert "canal local em" in saida and "pronto." in saida
    assert f"usuario_so={os.getuid()}" in saida
    assert not Path(diretorios.canal_local).exists()


@pytest.mark.asyncio
async def test_duas_instancias_com_dados_e_portas_diferentes(
    pasta_curta: Path, processos: list[subprocess.Popen[str]]
) -> None:
    enderecos = []
    for nome, porta in (("dono", 47830), ("cliente", 47831)):
        dados = pasta_curta / nome
        diretorios = diretorios_servico(dados)
        diretorios.configuracao.parent.mkdir(parents=True)
        diretorios.configuracao.write_text(f"[rede]\nporta = {porta}\n", encoding="utf-8")
        processos.append(_iniciar(dados))
        enderecos.append(diretorios.canal_local)
    assert enderecos[0] != enderecos[1]
    for endereco in enderecos:
        assert await _esperar_pronto(endereco)
    for processo in processos:
        codigo, saida = _encerrar(processo)
        assert codigo == 0, saida


def test_migrar_com_dados_cria_o_banco_e_sai(pasta_curta: Path) -> None:
    dados = pasta_curta / "m"
    resultado = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "drivelan.servico", "--migrar", "--dados", str(dados)],
        capture_output=True,
        text=True,
        timeout=TEMPO_LIMITE,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert "banco atualizado" in resultado.stdout
    assert diretorios_servico(dados).banco.exists()


@pytest.mark.skipif(os.name == "posix" and os.geteuid() == 0, reason="rodando como root")
def test_migrar_em_producao_exige_root() -> None:
    from drivelan.servico.__main__ import SAIDA_SEM_PRIVILEGIO, main

    assert main(["--migrar"]) == SAIDA_SEM_PRIVILEGIO
