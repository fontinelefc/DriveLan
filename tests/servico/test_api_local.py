"""Testes do canal local do serviço: identidade, formato de erro 23.6, estado e eventos."""

import asyncio
import io
import json
import os
import re
import sys
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import aiohttp
import pytest
import pytest_asyncio
from aiohttp import web

from drivelan.comum.canal_local import ClienteCanalLocal, ErroCanalLocal, url_local
from drivelan.comum.protocolo import (
    LIMITE_JSON_BYTES,
    PREFIXO_LOCAL,
    CodigoErro,
    mensagem_generica,
)
from drivelan.servico.api.local.aplicacao import (
    DependenciasCanal,
    criar_aplicacao,
    identidade_do_pedido,
    ler_corpo_json,
    responder_json,
)
from drivelan.servico.api.local.servidor import CanalEmUso, CanalLocal
from drivelan.servico.log_erros import LogErros
from drivelan.servico.plataforma import IdentidadeIndisponivel

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="socket Unix (Linux)")


@dataclass
class Ambiente:
    endereco: str
    dependencias: DependenciasCanal
    diagnostico: io.StringIO
    pasta_logs: Path
    canal: CanalLocal
    estado: dict[str, bool]

    def texto_do_log(self) -> str:
        return "".join(p.read_text(encoding="utf-8") for p in self.pasta_logs.rglob("*.log"))


async def _rota_com_falha(_pedido: web.Request) -> web.Response:
    raise RuntimeError("detalhe interno /var/lib/drivelan")


async def _rota_eco(pedido: web.Request) -> web.Response:
    return responder_json(
        {"corpo": await ler_corpo_json(pedido), "uid": identidade_do_pedido(pedido).usuario_so}
    )


def _montar(pasta: Path, *, com_diagnostico: bool = True) -> tuple[Ambiente, web.Application]:
    estado = {"pronto": False}
    diagnostico = io.StringIO()
    dependencias = DependenciasCanal(
        log=LogErros(pasta / "logs", saida_erro=io.StringIO()),
        pronto=lambda: estado["pronto"],
        diagnostico=diagnostico if com_diagnostico else None,
    )
    aplicacao = criar_aplicacao(dependencias)
    aplicacao.router.add_get(f"{PREFIXO_LOCAL}/teste/falha", _rota_com_falha)
    aplicacao.router.add_post(f"{PREFIXO_LOCAL}/teste/eco", _rota_eco)
    endereco = str(pasta / "local.sock")
    canal = CanalLocal(endereco, aplicacao, dependencias.log, producao=False)
    return Ambiente(endereco, dependencias, diagnostico, pasta / "logs", canal, estado), aplicacao


@pytest_asyncio.fixture
async def ambiente(pasta_curta: Path) -> AsyncIterator[Ambiente]:
    amb, _ = _montar(pasta_curta)
    await amb.canal.iniciar()
    try:
        yield amb
    finally:
        await amb.canal.parar()


def _sessao(endereco: str) -> aiohttp.ClientSession:
    return aiohttp.ClientSession(connector=aiohttp.UnixConnector(endereco))


@pytest.mark.asyncio
async def test_estado_informa_versao_host_e_pronto(ambiente: Ambiente) -> None:
    async with ClienteCanalLocal(ambiente.endereco) as cliente:
        estado = await cliente.obter_estado()
        assert estado.versao_protocolo == 1
        assert estado.host
        assert estado.versao
        assert estado.pronto is False
        ambiente.estado["pronto"] = True
        assert (await cliente.obter_estado()).pronto is True


@pytest.mark.asyncio
async def test_json_em_utf8_sem_escapes(ambiente: Ambiente) -> None:
    async with _sessao(ambiente.endereco) as sessao, sessao.get(url_local("inexistente")) as r:
        texto = await r.text()
    assert "Não foi possível" in texto
    assert r.content_type == "application/json"


@pytest.mark.asyncio
async def test_rota_inexistente_no_formato_23_6(ambiente: Ambiente) -> None:
    async with ClienteCanalLocal(ambiente.endereco) as cliente:
        with pytest.raises(ErroCanalLocal) as erro:
            await cliente.pedir_json("GET", "nao-existe")
    assert erro.value.status == 404
    assert erro.value.erro is not None
    assert erro.value.erro.codigo is CodigoErro.NAO_ENCONTRADO
    assert erro.value.erro.mensagem == mensagem_generica()


@pytest.mark.asyncio
async def test_metodo_nao_permitido_e_requisicao_invalida(ambiente: Ambiente) -> None:
    async with ClienteCanalLocal(ambiente.endereco) as cliente:
        with pytest.raises(ErroCanalLocal) as erro:
            await cliente.pedir_json("DELETE", "estado")
    assert erro.value.status == 400
    assert erro.value.erro is not None
    assert erro.value.erro.codigo is CodigoErro.REQUISICAO_INVALIDA


@pytest.mark.asyncio
async def test_erro_inesperado_vira_erro_interno_com_codigo(ambiente: Ambiente) -> None:
    async with _sessao(ambiente.endereco) as sessao, sessao.get(url_local("teste/falha")) as r:
        status, corpo = r.status, await r.text()
    assert status == 500
    erro = json.loads(corpo)["erro"]
    assert erro["codigo"] == "erro_interno"
    codigo = erro["dados"]["codigo_log"]
    assert re.fullmatch(r"[0-9A-F]{8}", codigo)
    assert f"Código: {codigo}" in erro["mensagem"]
    # Nada técnico chega ao usuário; o detalhe fica só no log (FSD 19.1.4).
    assert "Traceback" not in corpo and "/var/lib" not in corpo and "RuntimeError" not in corpo
    log = ambiente.texto_do_log()
    assert f"codigo={codigo}" in log and "RuntimeError" in log


@pytest.mark.asyncio
async def test_corpo_json_valido(ambiente: Ambiente) -> None:
    async with ClienteCanalLocal(ambiente.endereco) as cliente:
        resposta = await cliente.pedir_json("POST", "teste/eco", json={"a": "ação"})
    assert resposta == {"corpo": {"a": "ação"}, "uid": str(os.getuid())}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "corpo",
    [b"{nao e json", b"[1, 2]", b"\xff\xfe", b'{"x": "' + b"a" * LIMITE_JSON_BYTES + b'"}'],
    ids=["malformado", "nao-objeto", "nao-utf8", "maior-que-64kb"],
)
async def test_corpo_invalido_e_requisicao_invalida(ambiente: Ambiente, corpo: bytes) -> None:
    async with ClienteCanalLocal(ambiente.endereco) as cliente:
        with pytest.raises(ErroCanalLocal) as erro:
            await cliente.pedir_json("POST", "teste/eco", data=corpo)
    assert erro.value.status == 400
    assert erro.value.erro is not None
    assert erro.value.erro.codigo is CodigoErro.REQUISICAO_INVALIDA


@pytest.mark.asyncio
async def test_websocket_de_eventos_abre_e_responde_ping(ambiente: Ambiente) -> None:
    registro = ambiente.dependencias.conexoes_eventos
    async with ClienteCanalLocal(ambiente.endereco) as cliente:
        ws = await cliente.abrir_eventos()
        await ws.ping()
        await ws.send_str("ignorado")
        assert len(registro) == 1
        assert len(registro.do_usuario(str(os.getuid()))) == 1
        assert registro.do_usuario("outro") == []
        await ws.close()
    for _ in range(50):
        if len(registro) == 0:
            break
        await asyncio.sleep(0.01)
    assert len(registro) == 0


@pytest.mark.asyncio
async def test_parar_fecha_websockets_abertos(pasta_curta: Path) -> None:
    amb, _ = _montar(pasta_curta)
    await amb.canal.iniciar()
    async with ClienteCanalLocal(amb.endereco) as cliente:
        ws = await cliente.abrir_eventos()
        await amb.canal.parar()
        mensagem = await ws.receive(timeout=5)
        assert mensagem.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED)
    assert not Path(amb.endereco).exists()
    await amb.canal.parar()  # idempotente


@pytest.mark.asyncio
async def test_diagnostico_uma_linha_por_conexao(ambiente: Ambiente) -> None:
    async with ClienteCanalLocal(ambiente.endereco) as cliente:
        await cliente.obter_estado()
        await cliente.obter_estado()  # mesma conexão (pool): não repete a linha
    linhas = ambiente.diagnostico.getvalue().splitlines()
    assert linhas == [
        f"drivelan-service: conexão local aceita | usuario_so={os.getuid()} pid={os.getpid()}"
    ]
    assert "conexão local aceita" not in ambiente.texto_do_log()


@pytest.mark.asyncio
async def test_sem_console_nao_ha_diagnostico(pasta_curta: Path) -> None:
    amb, _ = _montar(pasta_curta, com_diagnostico=False)
    await amb.canal.iniciar()
    try:
        async with ClienteCanalLocal(amb.endereco) as cliente:
            await cliente.obter_estado()
    finally:
        await amb.canal.parar()
    assert amb.diagnostico.getvalue() == ""


@pytest.mark.asyncio
async def test_cliente_sem_identidade_e_recusado(
    ambiente: Ambiente, monkeypatch: pytest.MonkeyPatch
) -> None:
    from drivelan.servico.plataforma import linux

    def _falhar(_conexao: object) -> object:
        raise IdentidadeIndisponivel("teste")

    monkeypatch.setattr(linux, "identidade_do_socket", _falhar)
    async with ClienteCanalLocal(ambiente.endereco) as cliente:
        with pytest.raises(ErroCanalLocal) as erro:
            await cliente.obter_estado()
    assert erro.value.status == 403
    assert erro.value.erro is not None
    assert erro.value.erro.codigo is CodigoErro.ACESSO_NEGADO
    assert "Cliente do canal local sem identidade" in ambiente.texto_do_log()


@pytest.mark.asyncio
async def test_segunda_instancia_no_mesmo_endereco_e_recusada(
    ambiente: Ambiente, pasta_curta: Path
) -> None:
    outro, _ = _montar(pasta_curta)
    with pytest.raises(CanalEmUso):
        await outro.canal.iniciar()
    # A primeira continua atendendo.
    async with ClienteCanalLocal(ambiente.endereco) as cliente:
        await cliente.obter_estado()


def test_identidade_ausente_e_erro_de_programacao() -> None:
    from aiohttp.test_utils import make_mocked_request

    with pytest.raises(RuntimeError):
        identidade_do_pedido(make_mocked_request("GET", "/"))
