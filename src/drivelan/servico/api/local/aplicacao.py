"""Aplicação aiohttp do canal local: identidade do cliente, formato de erro e rotas (FSD 23.8).

A camada `api/` valida a entrada, identifica quem chama e delega; ela não decide regras de
negócio (FSD 5.4). Toda resposta de erro segue o formato da seção 23.6, e o usuário nunca recebe
pilha, caminhos internos ou mensagens técnicas (FSD 19.1.4).
"""

import functools
import json
import sys
import weakref
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TextIO

from aiohttp import web

from drivelan.comum.protocolo import (
    LIMITE_JSON_BYTES,
    PREFIXO_LOCAL,
    CodigoErro,
    ErroProtocolo,
    mensagem_erro_interno,
    mensagem_ou_generica,
)
from drivelan.servico.log_erros import LogErros, origem_de
from drivelan.servico.plataforma import (
    CHAVE_IDENTIDADE,
    IdentidadeCliente,
    IdentidadeIndisponivel,
)

ORIGEM_LOG = origem_de(__name__)

Manipulador = Callable[[web.Request], Awaitable[web.StreamResponse]]


@dataclass(slots=True)
class DependenciasCanal:
    """O que as rotas do canal local precisam do restante do serviço."""

    log: LogErros
    pronto: Callable[[], bool]
    """Se todas as etapas da inicialização terminaram (FSD 6.1)."""
    diagnostico: TextIO | None = None
    """Só no modo `--console`: recebe uma linha por conexão identificada (nunca vai para o log)."""
    conexoes_eventos: "RegistroEventos" = field(default_factory=lambda: RegistroEventos())


class RegistroEventos:
    """WebSockets de eventos locais abertos, por usuário do SO (base para as Fases 7 e 23)."""

    def __init__(self) -> None:
        self._abertos: dict[web.WebSocketResponse, IdentidadeCliente] = {}

    def adicionar(self, ws: web.WebSocketResponse, identidade: IdentidadeCliente) -> None:
        self._abertos[ws] = identidade

    def remover(self, ws: web.WebSocketResponse) -> None:
        self._abertos.pop(ws, None)

    def do_usuario(self, usuario_so: str) -> list[web.WebSocketResponse]:
        return [ws for ws, ident in self._abertos.items() if ident.usuario_so == usuario_so]

    def __len__(self) -> int:
        return len(self._abertos)

    async def fechar_todos(self) -> None:
        for ws in list(self._abertos):
            await ws.close()
        self._abertos.clear()


CHAVE_DEPENDENCIAS = web.AppKey("dependencias", DependenciasCanal)
CHAVE_IDENTIDADE_PEDIDO = web.RequestKey("identidade", IdentidadeCliente)
"""Chave do `request` com a `IdentidadeCliente` de quem fez o pedido."""


class ErroRota(Exception):
    """Levantada por uma rota para responder com um erro do protocolo (FSD 23.6)."""

    def __init__(self, erro: ErroProtocolo) -> None:
        super().__init__(erro.codigo.value)
        self.erro = erro

    @classmethod
    def de_codigo(cls, codigo: CodigoErro, **dados: Any) -> "ErroRota":
        return cls(ErroProtocolo(codigo, mensagem_ou_generica(codigo), dados))


_JSON_UTF8 = functools.partial(json.dumps, ensure_ascii=False)


def responder_json(dados: object, status: int = 200) -> web.Response:
    """Resposta JSON em UTF-8, sem escapar os acentos (FSD 23.1)."""
    return web.json_response(dados, status=status, dumps=_JSON_UTF8)


def resposta_erro(erro: ErroProtocolo) -> web.Response:
    return responder_json(erro.para_json(), status=erro.status_http)


def identidade_do_pedido(pedido: web.Request) -> IdentidadeCliente:
    """Identidade já verificada pelo middleware."""
    try:
        return pedido[CHAVE_IDENTIDADE_PEDIDO]
    except KeyError:
        raise RuntimeError("pedido sem identidade: o middleware não foi aplicado") from None


async def ler_corpo_json(pedido: web.Request) -> dict[str, Any]:
    """Lê um corpo JSON (objeto) de até 64 KB (FSD 24.9) ou levanta `requisicao_invalida`."""
    if pedido.content_length is not None and pedido.content_length > LIMITE_JSON_BYTES:
        raise ErroRota.de_codigo(CodigoErro.REQUISICAO_INVALIDA)
    try:
        bruto = await pedido.read()
    except web.HTTPRequestEntityTooLarge:
        raise ErroRota.de_codigo(CodigoErro.REQUISICAO_INVALIDA) from None
    try:
        objeto = json.loads(bruto.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ErroRota.de_codigo(CodigoErro.REQUISICAO_INVALIDA) from None
    if not isinstance(objeto, dict):
        raise ErroRota.de_codigo(CodigoErro.REQUISICAO_INVALIDA)
    return objeto


# ---------------------------------------------------------------- identidade (FSD 15.5)


def _calcular_identidade(transporte: Any) -> IdentidadeCliente:
    identidade = transporte.get_extra_info(CHAVE_IDENTIDADE)
    if isinstance(identidade, IdentidadeCliente):
        return identidade  # servidor do pipe (Windows): lida antes de aceitar pedidos
    if sys.platform == "win32":
        raise IdentidadeIndisponivel("conexão sem identidade")
    from drivelan.servico.plataforma.linux import identidade_do_socket

    conexao = transporte.get_extra_info("socket")
    if conexao is None:
        raise IdentidadeIndisponivel("conexão sem socket")
    return identidade_do_socket(conexao)


def _middleware_identidade(dependencias: DependenciasCanal) -> Any:
    """Identifica o usuário do SO e o PID uma vez por conexão, antes de qualquer rota."""
    cache: weakref.WeakKeyDictionary[Any, IdentidadeCliente] = weakref.WeakKeyDictionary()

    @web.middleware
    async def identificar(pedido: web.Request, handler: Manipulador) -> web.StreamResponse:
        transporte = pedido.transport
        identidade = cache.get(transporte) if transporte is not None else None
        if identidade is None:
            try:
                if transporte is None:
                    raise IdentidadeIndisponivel("conexão já fechada")
                identidade = _calcular_identidade(transporte)
            except IdentidadeIndisponivel as erro:
                dependencias.log.erro(
                    ORIGEM_LOG, "Cliente do canal local sem identidade", excecao=erro
                )
                resposta = resposta_erro(ErroRota.de_codigo(CodigoErro.ACESSO_NEGADO).erro)
                resposta.force_close()
                return resposta
            cache[transporte] = identidade
            _escrever_diagnostico(dependencias.diagnostico, identidade)
        pedido[CHAVE_IDENTIDADE_PEDIDO] = identidade
        return await handler(pedido)

    return identificar


def _escrever_diagnostico(saida: TextIO | None, identidade: IdentidadeCliente) -> None:
    if saida is None:
        return
    try:
        saida.write(
            "drivelan-service: conexão local aceita | "
            f"usuario_so={identidade.usuario_so} pid={identidade.pid}\n"
        )
        saida.flush()
    except (OSError, ValueError):
        pass


# ---------------------------------------------------------------- erros (FSD 23.6)


def _codigo_do_status(status: int) -> CodigoErro:
    """Erros HTTP gerados pelo próprio aiohttp (rota inexistente, método, corpo grande)."""
    return CodigoErro.NAO_ENCONTRADO if status == 404 else CodigoErro.REQUISICAO_INVALIDA


def _middleware_erros(dependencias: DependenciasCanal) -> Any:
    @web.middleware
    async def tratar_erros(pedido: web.Request, handler: Manipulador) -> web.StreamResponse:
        try:
            return await handler(pedido)
        except ErroRota as erro:
            return resposta_erro(erro.erro)
        except web.HTTPException as erro:
            if erro.status < 400:
                raise
            return resposta_erro(ErroRota.de_codigo(_codigo_do_status(erro.status)).erro)
        except Exception as erro:
            codigo_log = dependencias.log.erro_inesperado(
                ORIGEM_LOG, erro, {"rota": pedido.path, "metodo": pedido.method}
            )
            return resposta_erro(
                ErroProtocolo(
                    CodigoErro.ERRO_INTERNO,
                    mensagem_erro_interno(codigo_log),
                    {"codigo_log": codigo_log},
                )
            )

    return tratar_erros


# ---------------------------------------------------------------- montagem


def criar_aplicacao(dependencias: DependenciasCanal) -> web.Application:
    """Aplicação com as rotas do canal local implementadas até esta fase (FSD 23.8)."""
    from drivelan.servico.api.local import estado, eventos

    aplicacao = web.Application(
        client_max_size=LIMITE_JSON_BYTES,
        # A identidade vem antes de tudo; o tratamento de erros envolve as rotas.
        middlewares=[_middleware_identidade(dependencias), _middleware_erros(dependencias)],
    )
    aplicacao[CHAVE_DEPENDENCIAS] = dependencias
    aplicacao.router.add_get(f"{PREFIXO_LOCAL}/estado", estado.obter_estado)
    aplicacao.router.add_get(f"{PREFIXO_LOCAL}/eventos", eventos.abrir_eventos)

    async def _fechar_eventos(_aplicacao: web.Application) -> None:
        await dependencias.conexoes_eventos.fechar_todos()

    aplicacao.on_shutdown.append(_fechar_eventos)
    return aplicacao
