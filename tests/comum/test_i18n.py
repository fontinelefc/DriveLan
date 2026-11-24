"""Testes da base de textos traduzíveis (FSD 12.1)."""

from collections.abc import Iterator

import pytest

from drivelan.comum import i18n
from drivelan.comum.nomes import MotivoNomeInvalido


@pytest.fixture(autouse=True)
def _restaurar_tradutor() -> Iterator[None]:
    yield
    i18n.instalar_tradutor(None)


def test_marcador_devolve_o_texto() -> None:
    assert i18n.QT_TRANSLATE_NOOP("Ctx", "Olá") == "Olá"


def test_tradutor_padrao_e_identidade() -> None:
    assert i18n.traduzir("Ctx", "Pasta criada.") == "Pasta criada."


def test_instalar_tradutor() -> None:
    anterior = i18n.instalar_tradutor(lambda contexto, texto: f"[{contexto}] {texto}")
    assert i18n.traduzir("Ctx", "Oi") == "[Ctx] Oi"
    assert anterior("Ctx", "Oi") == "Oi"


def test_formatar() -> None:
    assert i18n.formatar("Ctx", "Restam {n} tentativas.", n=3) == "Restam 3 tentativas."


def test_motivos_usam_o_tradutor() -> None:
    i18n.instalar_tradutor(lambda contexto, texto: texto.upper())
    assert MotivoNomeInvalido.VAZIO.texto == "O NOME NÃO PODE FICAR VAZIO"
