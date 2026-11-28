"""Critério de saída da seção 15.5.1 (Windows): pipe próprio, SID e PID, recusa de rede.

Sem variáveis de ambiente, o teste sobe o serviço **no próprio processo** (mesmo usuário dos dois
lados) e confere a identificação, o HTTP, o WebSocket e a recusa pelo caminho de rede.

Com `DRIVELAN_TESTE_PIPE_DADOS=<pasta>` (a mesma `--dados` do serviço externo), os mesmos testes
rodam contra um serviço já em execução — por exemplo, como LocalSystem numa tarefa agendada. Rode
como usuário comum com `-s` para ver o SID e o PID deste processo e comparar com a linha
"conexão local aceita" que o serviço escreveu na saída do `--console`.
"""

import io
import os
import sys
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import pytest
import pytest_asyncio

from drivelan.comum.canal_local import ClienteCanalLocal
from drivelan.comum.diretorios import diretorios_servico

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="somente Windows")

VARIAVEL_EXTERNO = "DRIVELAN_TESTE_PIPE_DADOS"


@dataclass
class Alvo:
    endereco: str
    terminal: io.StringIO | None
    """Saída do `--console` (só quando o serviço roda neste processo)."""


def _sid_deste_processo() -> str:
    from drivelan.servico.plataforma.windows import sid_do_processo

    return sid_do_processo(os.getpid())


@pytest_asyncio.fixture
async def alvo(tmp_path: Path) -> AsyncIterator[Alvo]:
    externo = os.environ.get(VARIAVEL_EXTERNO)
    if externo:
        print(f"\nSID deste processo: {_sid_deste_processo()} | PID: {os.getpid()}")
        yield Alvo(diretorios_servico(Path(externo)).canal_local, None)
        return
    from drivelan.servico.inicializacao import OpcoesServico, Servico

    terminal = io.StringIO()
    servico = Servico(OpcoesServico(console=True, dados_dev=tmp_path), terminal=terminal)
    try:
        assert await servico.iniciar()
        yield Alvo(servico.diretorios.canal_local, terminal)
    finally:
        await servico.fechar()


@pytest.mark.asyncio
async def test_http_pelo_pipe(alvo: Alvo) -> None:
    async with ClienteCanalLocal(alvo.endereco) as cliente:
        estado = await cliente.obter_estado()
    assert estado.pronto and estado.versao_protocolo == 1


@pytest.mark.asyncio
async def test_websocket_pelo_pipe(alvo: Alvo) -> None:
    async with ClienteCanalLocal(alvo.endereco) as cliente:
        ws = await cliente.abrir_eventos()
        await ws.ping()
        await ws.close()


@pytest.mark.asyncio
async def test_sid_e_pid_identificados(alvo: Alvo) -> None:
    async with ClienteCanalLocal(alvo.endereco) as cliente:
        await cliente.obter_estado()
    if alvo.terminal is None:
        pytest.skip("serviço externo: confira a linha 'conexão local aceita' na saída dele")
    esperado = f"usuario_so={_sid_deste_processo()} pid={os.getpid()}"
    assert esperado in alvo.terminal.getvalue()


@pytest.mark.asyncio
async def test_caminho_de_rede_e_recusado(alvo: Alvo) -> None:
    # `\\localhost\pipe\...` passa pelo redirecionador SMB, como um cliente de outro computador:
    # PIPE_REJECT_REMOTE_CLIENTS e a negação a usuários de rede (NU) precisam recusar.
    nome = alvo.endereco.rsplit("\\", 1)[-1]
    with pytest.raises(OSError), open(rf"\\localhost\pipe\{nome}", "r+b"):
        pass


@pytest.mark.asyncio
async def test_segunda_instancia_do_pipe_e_recusada(alvo: Alvo) -> None:
    from drivelan.servico.plataforma import CanalEmUso
    from drivelan.servico.plataforma.windows_pipe import criar_instancia

    with pytest.raises(CanalEmUso):
        criar_instancia(alvo.endereco, primeira=True)
