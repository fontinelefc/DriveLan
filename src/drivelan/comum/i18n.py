"""Textos de mensagens marcados para tradução (FSD 1.5, 3.3 e 12.1).

O serviço não usa Qt (FSD 3.2), então este módulo não importa o PySide6. Os textos ficam em
português do Brasil no código e são marcados com `QT_TRANSLATE_NOOP`, nome que o
`pyside6-lupdate` reconhece ao extrair as mensagens para o arquivo `.ts`.

Na exibição, os textos passam por `traduzir`. O tradutor padrão devolve o próprio texto
(o português é o único idioma da v1). O app instala `QCoreApplication.translate` com
`instalar_tradutor` na inicialização (Fase 6), usando os mesmos contextos.
"""

from collections.abc import Callable
from typing import Any

type Tradutor = Callable[[str, str], str]


def _tradutor_identidade(contexto: str, texto: str) -> str:
    """Tradutor padrão: devolve o texto original, em português."""
    return texto


_tradutor_atual: Tradutor = _tradutor_identidade


def QT_TRANSLATE_NOOP(contexto: str, texto: str) -> str:  # noqa: N802 — nome reconhecido pelo lupdate
    """Marca `texto` para extração no contexto `contexto`, sem traduzir."""
    return texto


def instalar_tradutor(tradutor: Tradutor | None) -> Tradutor:
    """Troca o tradutor em uso e devolve o anterior. `None` restaura o tradutor padrão."""
    global _tradutor_atual  # estado único do processo, trocado só na inicialização
    anterior = _tradutor_atual
    _tradutor_atual = tradutor if tradutor is not None else _tradutor_identidade
    return anterior


def traduzir(contexto: str, texto: str) -> str:
    """Devolve a tradução de `texto` no contexto informado."""
    return _tradutor_atual(contexto, texto)


def formatar(contexto: str, texto: str, **valores: Any) -> str:
    """Traduz `texto` e substitui os campos `{nome}` pelos valores informados."""
    return traduzir(contexto, texto).format(**valores)
