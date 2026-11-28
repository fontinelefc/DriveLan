"""`GET /local/v1/estado`: versão, host e se o serviço está pronto (FSD 23.8, sem sessão)."""

import socket
from importlib import metadata

from aiohttp import web

from drivelan.comum.protocolo import VERSAO_PROTOCOLO
from drivelan.servico.api.local.aplicacao import CHAVE_DEPENDENCIAS, responder_json


def versao_instalada() -> str:
    try:
        return metadata.version("drivelan")
    except metadata.PackageNotFoundError:
        return "0+desconhecida"


async def obter_estado(pedido: web.Request) -> web.Response:
    dependencias = pedido.app[CHAVE_DEPENDENCIAS]
    return responder_json(
        {
            "versao": versao_instalada(),
            "versao_protocolo": VERSAO_PROTOCOLO,
            "host": socket.gethostname(),
            "pronto": dependencias.pronto(),
        }
    )
