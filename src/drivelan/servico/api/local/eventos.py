"""`GET /local/v1/eventos`: WebSocket de eventos do canal local (FSD 23.8).

Nesta fase o WebSocket só é aberto com a identidade do usuário do SO e mantido vivo por ping a
cada 30 segundos (FSD 23.5). Os eventos (sessão, notificações, transferências, `mostrar_lixeira_so`)
e o vínculo com a sessão de conta entram nas fases que os produzem (7 em diante).
"""

from aiohttp import WSMsgType, web

from drivelan.servico.api.local.aplicacao import CHAVE_DEPENDENCIAS, identidade_do_pedido

INTERVALO_PING = 30.0
"""Ping do WebSocket a cada 30 segundos (FSD 23.5)."""


async def abrir_eventos(pedido: web.Request) -> web.WebSocketResponse:
    dependencias = pedido.app[CHAVE_DEPENDENCIAS]
    identidade = identidade_do_pedido(pedido)
    ws = web.WebSocketResponse(heartbeat=INTERVALO_PING)
    await ws.prepare(pedido)
    dependencias.conexoes_eventos.adicionar(ws, identidade)
    try:
        async for mensagem in ws:
            if mensagem.type is WSMsgType.ERROR:
                break
            # Nenhuma mensagem do app é esperada nesta fase; são ignoradas.
    finally:
        dependencias.conexoes_eventos.remover(ws)
    return ws
