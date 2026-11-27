"""Testes das conexões, PRAGMAs, transações e threads do banco (FSD 5.3, 11.1 e 11.4)."""

import io
import os
import sqlite3
import stat
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from drivelan.servico.dados.banco import (
    BancoDados,
    ErroBanco,
    abrir_conexao,
    transacao,
)
from drivelan.servico.log_erros import LogErros

POSIX = os.name == "posix"


@pytest.fixture
def log(tmp_path: Path) -> LogErros:
    return LogErros(tmp_path / "logs", saida_erro=io.StringIO())


@pytest.fixture
def caminho_banco(tmp_path: Path) -> Path:
    return tmp_path / "dados" / "drivelan.db"


@pytest.fixture
def banco(caminho_banco: Path, log: LogErros) -> Iterator[BancoDados]:
    aberto = BancoDados.abrir(caminho_banco, log)
    yield aberto
    aberto.fechar()


def _pragmas(conexao: sqlite3.Connection) -> dict[str, object]:
    return {
        nome: conexao.execute(f"PRAGMA {nome}").fetchone()[0]
        for nome in ("foreign_keys", "journal_mode", "synchronous", "busy_timeout")
    }


PRAGMAS_ESPERADOS = {
    "foreign_keys": 1,
    "journal_mode": "wal",
    "synchronous": 1,
    "busy_timeout": 5000,
}


def test_conexao_de_escrita_aplica_pragmas(caminho_banco: Path) -> None:
    conexao = abrir_conexao(caminho_banco)
    try:
        assert _pragmas(conexao) == PRAGMAS_ESPERADOS
        assert conexao.isolation_level is None
    finally:
        conexao.close()


def test_conexao_somente_leitura_aplica_pragmas_e_recusa_escrita(caminho_banco: Path) -> None:
    escrita = abrir_conexao(caminho_banco)
    escrita.execute("CREATE TABLE t (a INTEGER)")
    leitura = abrir_conexao(caminho_banco, somente_leitura=True)
    try:
        assert _pragmas(leitura) == PRAGMAS_ESPERADOS
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            leitura.execute("INSERT INTO t (a) VALUES (1)")
    finally:
        leitura.close()
        escrita.close()


def test_somente_leitura_exige_banco_existente(caminho_banco: Path) -> None:
    with pytest.raises(ErroBanco):
        abrir_conexao(caminho_banco, somente_leitura=True)
    assert not caminho_banco.exists()


@pytest.mark.skipif(not POSIX, reason="modos POSIX")
def test_permissoes_da_pasta_e_do_arquivo(banco: BancoDados, caminho_banco: Path) -> None:
    assert stat.S_IMODE(caminho_banco.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(caminho_banco.stat().st_mode) == 0o600


@pytest.mark.skipif(not POSIX, reason="modos POSIX")
def test_permissao_corrigida_em_banco_existente(caminho_banco: Path) -> None:
    caminho_banco.parent.mkdir(parents=True)
    caminho_banco.touch(mode=0o644)
    caminho_banco.chmod(0o644)
    abrir_conexao(caminho_banco).close()
    assert stat.S_IMODE(caminho_banco.stat().st_mode) == 0o600


def test_transacao_confirma(caminho_banco: Path) -> None:
    conexao = abrir_conexao(caminho_banco)
    conexao.execute("CREATE TABLE t (a INTEGER)")
    with transacao(conexao):
        conexao.execute("INSERT INTO t (a) VALUES (1)")
        conexao.execute("INSERT INTO t (a) VALUES (2)")
    assert conexao.execute("SELECT count(*) FROM t").fetchone()[0] == 2
    assert not conexao.in_transaction
    conexao.close()


def test_transacao_desfaz_tudo_em_erro(caminho_banco: Path) -> None:
    conexao = abrir_conexao(caminho_banco)
    conexao.execute("CREATE TABLE t (a INTEGER NOT NULL)")
    with pytest.raises(sqlite3.IntegrityError), transacao(conexao):
        conexao.execute("INSERT INTO t (a) VALUES (1)")
        conexao.execute("INSERT INTO t (a) VALUES (NULL)")
    assert conexao.execute("SELECT count(*) FROM t").fetchone()[0] == 0
    assert not conexao.in_transaction
    conexao.close()


def test_transacao_aninhada_recusada(caminho_banco: Path) -> None:
    conexao = abrir_conexao(caminho_banco)
    with transacao(conexao), pytest.raises(ErroBanco), transacao(conexao):
        pass  # pragma: no cover
    conexao.close()


def test_escrita_sempre_na_mesma_thread_dedicada(banco: BancoDados) -> None:
    nomes = {banco.escrever_sincrono(lambda _c: threading.current_thread().name) for _ in range(5)}
    assert len(nomes) == 1
    nome = nomes.pop()
    assert nome.startswith(BancoDados.NOME_THREAD_ESCRITA)
    assert nome != threading.current_thread().name


def test_leitura_em_thread_separada_e_somente_leitura(banco: BancoDados) -> None:
    nome = banco.ler_sincrono(lambda _c: threading.current_thread().name)
    assert nome.startswith(BancoDados.NOME_THREAD_LEITURA)
    with pytest.raises(sqlite3.OperationalError):
        banco.ler_sincrono(
            lambda c: c.execute("UPDATE admin_controle SET erros_no_ciclo = 1").rowcount
        )


def test_gravacao_em_transacao_desfeita_em_erro(banco: BancoDados) -> None:
    def gravar_e_falhar(conexao: sqlite3.Connection) -> None:
        conexao.execute("UPDATE admin_controle SET erros_no_ciclo = 3")
        raise RuntimeError("falha simulada")

    with pytest.raises(RuntimeError):
        banco.gravar_em_transacao_sincrono(gravar_e_falhar)
    valor = banco.ler_sincrono(
        lambda c: c.execute("SELECT erros_no_ciclo FROM admin_controle").fetchone()[0]
    )
    assert valor == 0


def test_leitura_ve_o_que_a_escrita_confirmou(banco: BancoDados) -> None:
    banco.gravar_em_transacao_sincrono(
        lambda c: c.execute("UPDATE admin_controle SET erros_no_ciclo = 2").rowcount
    )
    valor = banco.ler_sincrono(
        lambda c: c.execute("SELECT erros_no_ciclo FROM admin_controle").fetchone()[0]
    )
    assert valor == 2


@pytest.mark.asyncio
async def test_api_assincrona(banco: BancoDados) -> None:
    linhas = await banco.gravar_em_transacao(
        lambda c: c.execute("UPDATE admin_controle SET ciclos_bloqueio = 1").rowcount
    )
    assert linhas == 1
    ciclos = await banco.ler(
        lambda c: c.execute("SELECT ciclos_bloqueio FROM admin_controle").fetchone()[0]
    )
    assert ciclos == 1
    nome = await banco.escrever(lambda _c: threading.current_thread().name)
    assert nome.startswith(BancoDados.NOME_THREAD_ESCRITA)


def test_fechar_e_idempotente_e_impede_uso(caminho_banco: Path, log: LogErros) -> None:
    banco = BancoDados.abrir(caminho_banco, log)
    banco.fechar()
    banco.fechar()
    with pytest.raises(RuntimeError):
        banco.escrever_sincrono(lambda _c: None)


def test_abrir_sem_migrar_nao_cria_tabelas(caminho_banco: Path, log: LogErros) -> None:
    banco = BancoDados.abrir(caminho_banco, log, migrar=False)
    try:
        tabelas = banco.ler_sincrono(
            lambda c: c.execute("SELECT count(*) FROM sqlite_master").fetchone()[0]
        )
        assert tabelas == 0
    finally:
        banco.fechar()
