"""Cliente do canal local app ↔ serviço (FSD 15.5 e 23.8).

O canal local é HTTP/1.1 + WebSocket sobre socket Unix (Linux) ou named pipe (Windows); nunca TCP.
O endereço é o caminho do socket ou o nome do pipe (`DiretoriosServico.canal_local` ou a opção
`--servico-local` do app). Toda resposta de erro segue a seção 23.6 e vira `ErroCanalLocal`.
"""

import sys
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Self

import aiohttp

from drivelan.comum.protocolo import PREFIXO_LOCAL, ErroProtocolo

URL_BASE = "http://drivelan-local"
"""Host fictício: o conector decide o destino (socket ou pipe); o nome nunca é resolvido."""

TEMPO_LIMITE_PADRAO = 10.0
INTERVALO_PING = 30.0


def criar_conector(endereco: str) -> aiohttp.BaseConnector:
    """`UnixConnector` no Linux e `NamedPipeConnector` no Windows (FSD 15.5.1)."""
    if sys.platform == "win32":
        return aiohttp.NamedPipeConnector(endereco)
    return aiohttp.UnixConnector(endereco)


def url_local(rota: str) -> str:
    """URL de uma rota do canal local (`"estado"` → `http://drivelan-local/local/v1/estado`)."""
    return f"{URL_BASE}{PREFIXO_LOCAL}/{rota.lstrip('/')}"


class ErroCanalLocal(Exception):
    """Resposta de erro do serviço (`erro` traz o formato 23.6) ou resposta fora do formato."""

    def __init__(self, status: int, erro: ErroProtocolo | None) -> None:
        super().__init__(erro.codigo.value if erro else f"HTTP {status}")
        self.status = status
        self.erro = erro


class ServicoIndisponivel(Exception):
    """Não foi possível conectar ao serviço (tela "serviço indisponível", FSD 12.2)."""


@dataclass(frozen=True, slots=True)
class EstadoServico:
    """Resposta de `GET /local/v1/estado`."""

    versao: str
    versao_protocolo: int
    host: str
    pronto: bool

    @classmethod
    def de_json(cls, objeto: object) -> "EstadoServico":
        if not isinstance(objeto, dict):
            raise ValueError("estado deve ser um objeto JSON")
        versao, protocolo, host, pronto = (
            objeto.get("versao"),
            objeto.get("versao_protocolo"),
            objeto.get("host"),
            objeto.get("pronto"),
        )
        if not (
            isinstance(versao, str)
            and isinstance(protocolo, int)
            and not isinstance(protocolo, bool)
            and isinstance(host, str)
            and isinstance(pronto, bool)
        ):
            raise ValueError("estado fora do formato")
        return cls(versao, protocolo, host, pronto)


class ClienteCanalLocal:
    """Sessão HTTP do app com o serviço. Use com `async with`."""

    def __init__(self, endereco: str, *, tempo_limite: float = TEMPO_LIMITE_PADRAO) -> None:
        self._endereco = endereco
        self._tempo_limite = tempo_limite
        self._sessao: aiohttp.ClientSession | None = None

    @property
    def endereco(self) -> str:
        return self._endereco

    async def __aenter__(self) -> Self:
        self._sessao = aiohttp.ClientSession(
            connector=criar_conector(self._endereco),
            timeout=aiohttp.ClientTimeout(total=self._tempo_limite),
        )
        return self

    async def __aexit__(
        self,
        tipo: type[BaseException] | None,
        excecao: BaseException | None,
        rastro: TracebackType | None,
    ) -> None:
        await self.fechar()

    async def fechar(self) -> None:
        if self._sessao is not None:
            await self._sessao.close()
            self._sessao = None

    def _sessao_aberta(self) -> aiohttp.ClientSession:
        if self._sessao is None:
            raise RuntimeError("use o cliente dentro de `async with`")
        return self._sessao

    async def pedir_json(self, metodo: str, rota: str, **opcoes: Any) -> Any:
        """Faz o pedido e devolve o JSON; erros viram `ErroCanalLocal` ou `ServicoIndisponivel`."""
        try:
            async with self._sessao_aberta().request(metodo, url_local(rota), **opcoes) as resposta:
                try:
                    corpo = await resposta.json(content_type=None)
                except ValueError:
                    corpo = None
                if resposta.status >= 400:
                    raise ErroCanalLocal(resposta.status, _ler_erro(corpo))
                return corpo
        except (aiohttp.ClientConnectionError, OSError) as erro:
            raise ServicoIndisponivel(str(erro)) from erro

    async def obter_estado(self) -> EstadoServico:
        try:
            return EstadoServico.de_json(await self.pedir_json("GET", "estado"))
        except ValueError as erro:
            raise ErroCanalLocal(200, None) from erro

    async def abrir_eventos(self) -> aiohttp.ClientWebSocketResponse:
        """Abre o WebSocket de eventos (`GET /local/v1/eventos`), com ping a cada 30 s."""
        try:
            return await self._sessao_aberta().ws_connect(
                url_local("eventos"), heartbeat=INTERVALO_PING
            )
        except aiohttp.WSServerHandshakeError as erro:
            raise ErroCanalLocal(erro.status, None) from erro
        except (aiohttp.ClientConnectionError, OSError) as erro:
            raise ServicoIndisponivel(str(erro)) from erro


def _ler_erro(corpo: object) -> ErroProtocolo | None:
    try:
        return ErroProtocolo.de_json(corpo)
    except ValueError:
        return None
