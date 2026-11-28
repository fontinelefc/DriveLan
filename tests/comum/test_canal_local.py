"""Testes do cliente do canal local (`comum/canal_local.py`, FSD 23.8)."""

import shutil
import sys
import tempfile
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import aiohttp
import pytest
import pytest_asyncio
from aiohttp import web

from drivelan.comum.canal_local import (
    URL_BASE,
    ClienteCanalLocal,
    ErroCanalLocal,
    EstadoServico,
    ServicoIndisponivel,
    criar_conector,
    url_local,
)
from drivelan.comum.protocolo import CodigoErro, ErroProtocolo

somente_linux = pytest.mark.skipif(sys.platform == "win32", reason="socket Unix (Linux)")


@pytest.fixture
def pasta_curta() -> Iterator[Path]:
    caminho = Path(tempfile.mkdtemp(prefix="dl-"))
    try:
        yield caminho
    finally:
        shutil.rmtree(caminho, ignore_errors=True)


def test_url_local() -> None:
    assert url_local("estado") == f"{URL_BASE}/local/v1/estado"
    assert url_local("/eventos") == f"{URL_BASE}/local/v1/eventos"


@pytest.mark.asyncio
@somente_linux
async def test_conector_do_linux_e_unix() -> None:
    conector = criar_conector("qualquer.sock")
    try:
        assert isinstance(conector, aiohttp.UnixConnector)
    finally:
        await conector.close()


def test_estado_de_json() -> None:
    dados = {"versao": "1.0", "versao_protocolo": 1, "host": "pc", "pronto": True}
    assert EstadoServico.de_json(dados) == EstadoServico("1.0", 1, "pc", True)


@pytest.mark.parametrize(
    "dados",
    [
        [],
        {"versao": "1.0", "versao_protocolo": True, "host": "pc", "pronto": True},
        {"versao": "1.0", "versao_protocolo": 1, "host": "pc", "pronto": "sim"},
        {"versao_protocolo": 1, "host": "pc", "pronto": True},
    ],
)
def test_estado_fora_do_formato(dados: object) -> None:
    with pytest.raises(ValueError):
        EstadoServico.de_json(dados)


@pytest.mark.asyncio
async def test_uso_fora_do_contexto() -> None:
    with pytest.raises(RuntimeError):
        await ClienteCanalLocal("x.sock").obter_estado()


@pytest.mark.asyncio
@somente_linux
async def test_servico_ausente(pasta_curta: Path) -> None:
    async with ClienteCanalLocal(str(pasta_curta / "nada.sock")) as cliente:
        with pytest.raises(ServicoIndisponivel):
            await cliente.obter_estado()
        with pytest.raises(ServicoIndisponivel):
            await cliente.abrir_eventos()


async def _erro(_pedido: web.Request) -> web.Response:
    erro = ErroProtocolo(CodigoErro.ACESSO_NEGADO, "Você não tem permissão para esta ação.")
    return web.json_response(erro.para_json(), status=403)


async def _texto(_pedido: web.Request) -> web.Response:
    return web.Response(text="quebrado", status=502)


async def _estado_ruim(_pedido: web.Request) -> web.Response:
    return web.json_response({"versao": 1})


@pytest_asyncio.fixture
async def servidor_falso(pasta_curta: Path) -> AsyncIterator[str]:
    aplicacao = web.Application()
    aplicacao.router.add_get("/local/v1/erro", _erro)
    aplicacao.router.add_get("/local/v1/texto", _texto)
    aplicacao.router.add_get("/local/v1/estado", _estado_ruim)
    runner = web.AppRunner(aplicacao)
    await runner.setup()
    caminho = str(pasta_curta / "s.sock")
    await web.UnixSite(runner, caminho).start()
    try:
        yield caminho
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
@somente_linux
async def test_erro_do_servico_no_formato_23_6(servidor_falso: str) -> None:
    async with ClienteCanalLocal(servidor_falso) as cliente:
        with pytest.raises(ErroCanalLocal) as erro:
            await cliente.pedir_json("GET", "erro")
    assert erro.value.status == 403
    assert erro.value.erro is not None
    assert erro.value.erro.codigo is CodigoErro.ACESSO_NEGADO


@pytest.mark.asyncio
@somente_linux
async def test_erro_fora_do_formato(servidor_falso: str) -> None:
    async with ClienteCanalLocal(servidor_falso) as cliente:
        with pytest.raises(ErroCanalLocal) as erro:
            await cliente.pedir_json("GET", "texto")
        assert erro.value.status == 502
        assert erro.value.erro is None
        with pytest.raises(ErroCanalLocal):
            await cliente.obter_estado()
        with pytest.raises(ErroCanalLocal) as ws:
            await cliente.abrir_eventos()
        assert ws.value.status == 404
