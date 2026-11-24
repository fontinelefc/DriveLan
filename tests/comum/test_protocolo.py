"""Testes das constantes, erros e mensagens do protocolo (FSD 23.5 e 23.6)."""

import json
import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest

from drivelan.comum.protocolo import (
    LIMITE_JSON_BYTES,
    PORTA_PADRAO,
    STATUS_HTTP,
    TAMANHO_BLOCO,
    CodigoErro,
    ErroProtocolo,
    MensagemEvento,
    TipoEvento,
    formatar_data_iso,
    ler_data_iso,
    mensagem_erro_interno,
    mensagem_padrao,
)


def test_constantes_do_fsd() -> None:
    assert PORTA_PADRAO == 47820
    assert LIMITE_JSON_BYTES == 65536
    assert TAMANHO_BLOCO == 262144


def test_todo_codigo_tem_status_http() -> None:
    assert set(STATUS_HTTP) == set(CodigoErro)


@pytest.mark.parametrize(
    ("codigo", "status"),
    [
        (CodigoErro.REQUISICAO_INVALIDA, 400),
        (CodigoErro.SESSAO_INVALIDA, 401),
        (CodigoErro.TRANSPORTE_INVALIDO, 401),
        (CodigoErro.ACESSO_NEGADO, 403),
        (CodigoErro.NAO_ENCONTRADO, 404),
        (CodigoErro.EM_EDICAO, 409),
        (CodigoErro.PASTA_ENCERRADA, 410),
        (CodigoErro.PASTA_SOMENTE_LEITURA, 423),
        (CodigoErro.PIN_BLOQUEADO_TEMPORARIAMENTE, 429),
        (CodigoErro.ERRO_INTERNO, 500),
        (CodigoErro.PASTA_CHEIA, 507),
        (CodigoErro.DISCO_DONO_CHEIO, 507),
    ],
)
def test_status_da_tabela(codigo: CodigoErro, status: int) -> None:
    assert STATUS_HTTP[codigo] == status


def test_mensagens_definidas_no_fsd() -> None:
    assert mensagem_padrao(CodigoErro.PASTA_CHEIA) == "Pasta cheia. Contate o dono da pasta."
    assert mensagem_padrao(CodigoErro.ACESSO_NEGADO) == "Você não tem permissão para esta ação."
    assert mensagem_padrao(CodigoErro.NAO_ENCONTRADO) is None


def test_mensagem_de_erro_interno() -> None:
    assert mensagem_erro_interno("7F3A91C2") == (
        "Não foi possível concluir a ação. Tente novamente. Se o problema continuar, "
        "procure o TI. Código: 7F3A91C2"
    )


def test_erro_ida_e_volta_em_json() -> None:
    erro = ErroProtocolo(CodigoErro.PIN_INCORRETO, "PIN incorreto.", {"tentativas_restantes": 3})
    texto = json.dumps(erro.para_json())
    assert json.loads(texto) == {
        "erro": {
            "codigo": "pin_incorreto",
            "mensagem": "PIN incorreto.",
            "dados": {"tentativas_restantes": 3},
        }
    }
    assert ErroProtocolo.de_json(json.loads(texto)) == erro
    assert erro.status_http == 401


def test_erro_sem_dados() -> None:
    lido = ErroProtocolo.de_json({"erro": {"codigo": "acesso_negado", "mensagem": "x"}})
    assert lido.dados == {}


@pytest.mark.parametrize(
    "objeto",
    [
        None,
        [],
        {},
        {"erro": "texto"},
        {"erro": {"codigo": "inexistente", "mensagem": "x"}},
        {"erro": {"codigo": 1, "mensagem": "x"}},
        {"erro": {"codigo": "acesso_negado"}},
        {"erro": {"codigo": "acesso_negado", "mensagem": "x", "dados": []}},
    ],
)
def test_erro_malformado(objeto: object) -> None:
    with pytest.raises(ValueError):
        ErroProtocolo.de_json(objeto)


def test_formato_da_data() -> None:
    momento = datetime(2026, 11, 12, 13, 45, 10, 123456, tzinfo=UTC)
    assert formatar_data_iso(momento) == "2026-11-12T13:45:10.123Z"


def test_data_convertida_para_utc() -> None:
    momento = datetime(2026, 11, 12, 10, 45, 10, 123000, tzinfo=timezone(timedelta(hours=-3)))
    assert formatar_data_iso(momento) == "2026-11-12T13:45:10.123Z"


def test_data_sem_fuso_e_recusada() -> None:
    with pytest.raises(ValueError):
        formatar_data_iso(datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        ler_data_iso("2026-01-01T00:00:00")


def test_ler_data() -> None:
    assert ler_data_iso("2026-11-12T13:45:10.123Z") == datetime(
        2026, 11, 12, 13, 45, 10, 123000, tzinfo=UTC
    )


def test_evento_criado() -> None:
    evento = MensagemEvento.criar(TipoEvento.ACESSO_REVOGADO, {"motivo": "bloqueado"})
    assert evento.tipo == "acesso_revogado"
    assert uuid.UUID(evento.id).version == 4
    assert evento.enviado_em.endswith("Z")
    assert MensagemEvento.de_json(json.loads(json.dumps(evento.para_json()))) == evento


def test_evento_sem_dados() -> None:
    assert MensagemEvento.criar(TipoEvento.ENCERRAMENTO_CANCELADO).dados == {}


@pytest.mark.parametrize(
    "objeto",
    [
        None,
        {"tipo": "x", "id": "1", "dados": {}},
        {"tipo": 1, "id": "1", "dados": {}, "enviado_em": "2026-11-12T13:45:10.123Z"},
        {"tipo": "x", "id": "1", "dados": [], "enviado_em": "2026-11-12T13:45:10.123Z"},
        {"tipo": "x", "id": "1", "dados": {}, "enviado_em": "ontem"},
    ],
)
def test_evento_malformado(objeto: object) -> None:
    with pytest.raises(ValueError):
        MensagemEvento.de_json(objeto)


def test_tipos_de_evento_da_secao_23_5() -> None:
    assert {t.value for t in TipoEvento} == {
        "assinar",
        "edicao_sinal",
        "assinatura_resultado",
        "encerramento_programado",
        "encerramento_alterado",
        "encerramento_cancelado",
        "pasta_desativada",
        "pasta_encerrada",
        "acesso_revogado",
        "edicao_liberada",
        "conteudo_alterado",
    }
