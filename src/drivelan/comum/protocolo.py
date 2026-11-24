"""Constantes, códigos de erro e formatos de mensagem dos protocolos internos (FSD 23).

Vale para os dois protocolos: o canal local (app ↔ serviço) e o protocolo DriveLan v1 entre
instalações. Ambos usam JSON em UTF-8 e o mesmo formato de erro (FSD 23.6).
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from drivelan.comum.i18n import QT_TRANSLATE_NOOP, formatar, traduzir

CONTEXTO = "Protocolo"

# ------------------------------------------------------------------ constantes

VERSAO_PROTOCOLO = 1
PREFIXO_REDE = "/v1"
PREFIXO_LOCAL = "/local/v1"
PORTA_PADRAO = 47820
"""Porta TCP do protocolo e UDP da descoberta por broadcast (FSD 20.2)."""

CABECALHO_SESSAO = "X-DriveLan-Sessao"
CABECALHO_ADMIN = "X-DriveLan-Admin"
CABECALHO_TRANSPORTE = "X-DriveLan-Transporte"
CABECALHO_PEDIDO = "X-DriveLan-Pedido"
CABECALHO_TAMANHO = "X-DriveLan-Tamanho"
CABECALHO_TRANSFERENCIA = "X-DriveLan-Transferencia"
CABECALHO_EDICAO = "X-DriveLan-Edicao"

LIMITE_JSON_BYTES = 64 * 1024
"""Tamanho máximo de um corpo JSON (FSD 24.9)."""

LIMITE_UDP_BYTES = 1024
"""Tamanho máximo de uma mensagem de descoberta por broadcast (FSD 23.2)."""

TAMANHO_BLOCO = 256 * 1024
"""Bloco do streaming de arquivos no canal local (FSD 23.8)."""


# ------------------------------------------------------------------ erros (FSD 23.6)


class CodigoErro(StrEnum):
    """Códigos de erro da tabela 23.6."""

    REQUISICAO_INVALIDA = "requisicao_invalida"
    NOME_INVALIDO = "nome_invalido"
    CAMINHO_INVALIDO = "caminho_invalido"
    SESSAO_INVALIDA = "sessao_invalida"
    TRANSPORTE_INVALIDO = "transporte_invalido"
    TOKEN_INVALIDO = "token_invalido"  # noqa: S105 — código de erro, não é segredo
    PIN_INCORRETO = "pin_incorreto"
    ACESSO_NEGADO = "acesso_negado"
    USUARIO_BLOQUEADO = "usuario_bloqueado"
    PASTA_DESATIVADA = "pasta_desativada"
    PIN_BLOQUEADO_TEMPORARIAMENTE = "pin_bloqueado_temporariamente"
    NAO_ENCONTRADO = "nao_encontrado"
    NOME_EXISTENTE = "nome_existente"
    EM_EDICAO = "em_edicao"
    PASTA_ENCERRADA = "pasta_encerrada"
    PASTA_CHEIA = "pasta_cheia"
    DISCO_DONO_CHEIO = "disco_dono_cheio"
    PASTA_SOMENTE_LEITURA = "pasta_somente_leitura"
    NOME_INCOMPATIVEL_BLOQUEADO = "nome_incompativel_bloqueado"
    ERRO_INTERNO = "erro_interno"


STATUS_HTTP: Mapping[CodigoErro, int] = {
    CodigoErro.REQUISICAO_INVALIDA: 400,
    CodigoErro.NOME_INVALIDO: 400,
    CodigoErro.CAMINHO_INVALIDO: 400,
    CodigoErro.SESSAO_INVALIDA: 401,
    CodigoErro.TRANSPORTE_INVALIDO: 401,
    CodigoErro.TOKEN_INVALIDO: 401,
    CodigoErro.PIN_INCORRETO: 401,
    CodigoErro.ACESSO_NEGADO: 403,
    CodigoErro.USUARIO_BLOQUEADO: 403,
    CodigoErro.PASTA_DESATIVADA: 403,
    CodigoErro.PIN_BLOQUEADO_TEMPORARIAMENTE: 429,
    CodigoErro.NAO_ENCONTRADO: 404,
    CodigoErro.NOME_EXISTENTE: 409,
    CodigoErro.EM_EDICAO: 409,
    CodigoErro.PASTA_ENCERRADA: 410,
    CodigoErro.PASTA_CHEIA: 507,
    CodigoErro.DISCO_DONO_CHEIO: 507,
    CodigoErro.PASTA_SOMENTE_LEITURA: 423,
    CodigoErro.NOME_INCOMPATIVEL_BLOQUEADO: 423,
    CodigoErro.ERRO_INTERNO: 500,
}
"""Status HTTP de cada código (FSD 23.6)."""

# Somente os textos definidos no FSD (16.4, RN-21, RN-56, 15.7). Os demais códigos recebem a
# mensagem montada pela regra que os gera.
_MENSAGENS_PADRAO: dict[CodigoErro, str] = {
    CodigoErro.ACESSO_NEGADO: QT_TRANSLATE_NOOP(
        "Protocolo", "Você não tem permissão para esta ação."
    ),
    CodigoErro.USUARIO_BLOQUEADO: QT_TRANSLATE_NOOP(
        "Protocolo", "Você foi bloqueado pelo dono desta pasta."
    ),
    CodigoErro.PASTA_DESATIVADA: QT_TRANSLATE_NOOP(
        "Protocolo", "Esta pasta está desativada no momento."
    ),
    CodigoErro.TOKEN_INVALIDO: QT_TRANSLATE_NOOP(
        "Protocolo", "Seu acesso a esta pasta foi revogado."
    ),
    CodigoErro.PASTA_SOMENTE_LEITURA: QT_TRANSLATE_NOOP(
        "Protocolo", "A pasta está em encerramento e aceita apenas cópias."
    ),
    CodigoErro.PASTA_CHEIA: QT_TRANSLATE_NOOP("Protocolo", "Pasta cheia. Contate o dono da pasta."),
    CodigoErro.DISCO_DONO_CHEIO: QT_TRANSLATE_NOOP(
        "Protocolo", "Sem espaço no computador do dono. Contate o dono da pasta."
    ),
}

_MENSAGEM_ERRO_INTERNO = QT_TRANSLATE_NOOP(
    "Protocolo",
    "Não foi possível concluir a ação. Tente novamente. Se o problema continuar, procure o TI. "
    "Código: {codigo}",
)


def mensagem_padrao(codigo: CodigoErro) -> str | None:
    """Texto do FSD para o código, já traduzido, ou `None` se o código não tem texto fixo."""
    texto = _MENSAGENS_PADRAO.get(codigo)
    return traduzir(CONTEXTO, texto) if texto is not None else None


def mensagem_erro_interno(codigo_log: str) -> str:
    """Mensagem genérica de erro inesperado, com o código curto do log (FSD 19.1.4)."""
    return formatar(CONTEXTO, _MENSAGEM_ERRO_INTERNO, codigo=codigo_log)


def _exigir_dicionario(valor: object, descricao: str) -> dict[str, Any]:
    if not isinstance(valor, dict) or not all(isinstance(c, str) for c in valor):
        raise ValueError(f"{descricao} deve ser um objeto JSON")
    return valor


def _exigir_texto(valor: object, descricao: str) -> str:
    if not isinstance(valor, str):
        raise ValueError(f"{descricao} deve ser texto")
    return valor


@dataclass(frozen=True, slots=True)
class ErroProtocolo:
    """Resposta de erro `{"erro": {"codigo", "mensagem", "dados"}}` (FSD 23.6)."""

    codigo: CodigoErro
    mensagem: str
    dados: Mapping[str, Any] = field(default_factory=dict)

    @property
    def status_http(self) -> int:
        return STATUS_HTTP[self.codigo]

    def para_json(self) -> dict[str, Any]:
        return {
            "erro": {
                "codigo": self.codigo.value,
                "mensagem": self.mensagem,
                "dados": dict(self.dados),
            }
        }

    @classmethod
    def de_json(cls, objeto: object) -> "ErroProtocolo":
        """Lê uma resposta de erro; levanta `ValueError` se o formato estiver errado."""
        erro = _exigir_dicionario(_exigir_dicionario(objeto, "resposta").get("erro"), "erro")
        codigo_texto = _exigir_texto(erro.get("codigo"), "erro.codigo")
        try:
            codigo = CodigoErro(codigo_texto)
        except ValueError:
            raise ValueError("erro.codigo desconhecido") from None
        mensagem = _exigir_texto(erro.get("mensagem"), "erro.mensagem")
        dados = _exigir_dicionario(erro.get("dados", {}), "erro.dados")
        return cls(codigo, mensagem, dados)


# ------------------------------------------------------------------ datas (FSD 11.1)


def agora_utc() -> datetime:
    return datetime.now(UTC)


def formatar_data_iso(momento: datetime) -> str:
    """Data em ISO 8601 UTC com milissegundos (`2026-11-12T13:45:10.123Z`, FSD 11.1)."""
    if momento.tzinfo is None:
        raise ValueError("a data precisa ter fuso horário")
    return momento.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def ler_data_iso(texto: str) -> datetime:
    """Lê uma data no formato de `formatar_data_iso` (ou outro ISO 8601 com fuso)."""
    momento = datetime.fromisoformat(texto)
    if momento.tzinfo is None:
        raise ValueError("a data precisa ter fuso horário")
    return momento.astimezone(UTC)


# ------------------------------------------------------------------ eventos (FSD 23.5)


class TipoEvento(StrEnum):
    """Tipos de mensagem do WebSocket de eventos entre instalações (FSD 23.5)."""

    ASSINAR = "assinar"
    EDICAO_SINAL = "edicao_sinal"
    ASSINATURA_RESULTADO = "assinatura_resultado"
    ENCERRAMENTO_PROGRAMADO = "encerramento_programado"
    ENCERRAMENTO_ALTERADO = "encerramento_alterado"
    ENCERRAMENTO_CANCELADO = "encerramento_cancelado"
    PASTA_DESATIVADA = "pasta_desativada"
    PASTA_ENCERRADA = "pasta_encerrada"
    ACESSO_REVOGADO = "acesso_revogado"
    EDICAO_LIBERADA = "edicao_liberada"
    CONTEUDO_ALTERADO = "conteudo_alterado"


@dataclass(frozen=True, slots=True)
class MensagemEvento:
    """Mensagem `{"tipo", "id", "dados", "enviado_em"}` (FSD 23.5).

    `tipo` é texto para que o canal local possa usar tipos próprios (seção 23.8).
    """

    tipo: str
    id: str
    dados: Mapping[str, Any]
    enviado_em: str

    @classmethod
    def criar(cls, tipo: str, dados: Mapping[str, Any] | None = None) -> "MensagemEvento":
        """Nova mensagem com identificador UUID v4 e horário atual."""
        return cls(str(tipo), str(uuid.uuid4()), dict(dados or {}), formatar_data_iso(agora_utc()))

    def para_json(self) -> dict[str, Any]:
        return {
            "tipo": self.tipo,
            "id": self.id,
            "dados": dict(self.dados),
            "enviado_em": self.enviado_em,
        }

    @classmethod
    def de_json(cls, objeto: object) -> "MensagemEvento":
        """Lê uma mensagem de evento; levanta `ValueError` se o formato estiver errado."""
        mensagem = _exigir_dicionario(objeto, "mensagem")
        tipo = _exigir_texto(mensagem.get("tipo"), "tipo")
        identificador = _exigir_texto(mensagem.get("id"), "id")
        dados = _exigir_dicionario(mensagem.get("dados", {}), "dados")
        enviado_em = _exigir_texto(mensagem.get("enviado_em"), "enviado_em")
        ler_data_iso(enviado_em)
        return cls(tipo, identificador, dados, enviado_em)
