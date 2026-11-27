"""Testes do executor de migrations (FSD 11.3)."""

import io
import os
import sqlite3
import stat
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from drivelan.servico.dados import migracoes as modulo_migracoes
from drivelan.servico.dados.banco import abrir_conexao
from drivelan.servico.dados.migracoes import (
    COPIAS_MANTIDAS,
    FalhaMigracao,
    Migracao,
    MigracaoAlterada,
    MigracaoDesconhecida,
    MigracaoInvalida,
    busca_fts_disponivel,
    calcular_checksum,
    caminho_copia,
    carregar_migracoes,
    dividir_comandos,
    executar_migracoes,
    listar_copias,
    pasta_migracoes,
    remover_bloco_trigram,
    versoes_aplicadas,
)
from drivelan.servico.log_erros import LogErros

POSIX = os.name == "posix"
MOMENTO = datetime(2026, 11, 27, 13, 45, 10, 123000, tzinfo=UTC)


def _relogio() -> datetime:
    return MOMENTO


@pytest.fixture
def pasta_logs(tmp_path: Path) -> Path:
    return tmp_path / "logs"


@pytest.fixture
def log(pasta_logs: Path) -> LogErros:
    return LogErros(pasta_logs, saida_erro=io.StringIO())


@pytest.fixture
def caminho_banco(tmp_path: Path) -> Path:
    return tmp_path / "dados" / "drivelan.db"


@pytest.fixture
def conexao(caminho_banco: Path) -> Iterator[sqlite3.Connection]:
    aberta = abrir_conexao(caminho_banco)
    yield aberta
    aberta.close()


def _texto_do_log(pasta_logs: Path) -> str:
    return "".join(p.read_text(encoding="utf-8") for p in sorted(pasta_logs.rglob("*.log")))


def _migracao(versao: int, sql: str, nome: str | None = None) -> Migracao:
    return Migracao(
        versao, nome or f"{versao:04d}_teste.sql", sql, calcular_checksum(sql.encode("utf-8"))
    )


def _esquema(conexao: sqlite3.Connection) -> list[tuple[str, str]]:
    return conexao.execute(
        "SELECT name, coalesce(sql, '') FROM sqlite_master ORDER BY name"
    ).fetchall()


# ------------------------------------------------------------------ leitura dos arquivos


def test_migrations_empacotadas_comecam_pela_0001() -> None:
    lista = carregar_migracoes()
    assert lista[0].versao == 1
    assert lista[0].nome == "0001_inicial.sql"
    conteudo = (pasta_migracoes() / "0001_inicial.sql").read_bytes()
    assert lista[0].checksum == calcular_checksum(conteudo)
    assert [m.versao for m in lista] == sorted(m.versao for m in lista)


def test_carregar_em_ordem_numerica_ignorando_outros_arquivos(tmp_path: Path) -> None:
    (tmp_path / "0010_dez.sql").write_text("SELECT 10;", encoding="utf-8")
    (tmp_path / "0002_dois.sql").write_text("SELECT 2;", encoding="utf-8")
    (tmp_path / "0001_um.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "LEIAME.txt").write_text("não é migration", encoding="utf-8")
    assert [m.versao for m in carregar_migracoes(tmp_path)] == [1, 2, 10]


@pytest.mark.parametrize(
    "nome", ["1_curto.sql", "0001-traco.sql", "0001_Maiuscula.sql", "abcd_x.sql", "0000_zero.sql"]
)
def test_nome_fora_do_padrao_recusado(tmp_path: Path, nome: str) -> None:
    (tmp_path / nome).write_text("SELECT 1;", encoding="utf-8")
    with pytest.raises(MigracaoInvalida):
        carregar_migracoes(tmp_path)


def test_versao_repetida_recusada(tmp_path: Path) -> None:
    (tmp_path / "0001_um.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "0001_outro.sql").write_text("SELECT 1;", encoding="utf-8")
    with pytest.raises(MigracaoInvalida, match="repetida"):
        carregar_migracoes(tmp_path)


# ------------------------------------------------------------------ divisão dos comandos


def test_dividir_comandos_respeita_gatilhos_textos_e_comentarios() -> None:
    sql = """
    -- comentário com ; ponto e vírgula
    CREATE TABLE t (a TEXT DEFAULT 'x;y');
    /* bloco ; comentado */
    CREATE TRIGGER g AFTER INSERT ON t BEGIN
        INSERT INTO t (a) VALUES ('a;b');
        DELETE FROM t WHERE a = ';';
    END;
    INSERT INTO t (a) VALUES ('fim');
    -- só comentário no final
    """
    comandos = dividir_comandos(sql)
    assert len(comandos) == 3
    assert comandos[1].rstrip().endswith("END;")
    conexao = sqlite3.connect(":memory:")
    for comando in comandos:
        conexao.execute(comando)
    conexao.close()


@pytest.mark.parametrize(
    "sql",
    [
        "CREATE TABLE t (a INTEGER); CREATE TRIGGER g AFTER INSERT ON t BEGIN SELECT 1;",
        "INSERT INTO t (a) VALUES ('texto sem fim;",
    ],
)
def test_comando_incompleto_no_final_recusado(sql: str) -> None:
    with pytest.raises(MigracaoInvalida):
        dividir_comandos(sql)


def test_comando_com_erro_de_sintaxe_falha_sem_aplicar(
    conexao: sqlite3.Connection, caminho_banco: Path, log: LogErros
) -> None:
    m1 = _migracao(1, _sql_base() + " CREATE TABLE u (b")
    with pytest.raises(FalhaMigracao):
        executar_migracoes(conexao, caminho_banco, log, [m1])
    assert versoes_aplicadas(conexao) == {}


def test_remover_bloco_trigram() -> None:
    sql = (pasta_migracoes() / "0001_inicial.sql").read_text(encoding="utf-8")
    sem_fts = remover_bloco_trigram(sql)
    assert "auditoria_busca" in sql
    assert "USING fts5" not in sem_fts
    assert "CREATE TRIGGER" not in sem_fts
    assert "CREATE TABLE auditoria (" in sem_fts


# ------------------------------------------------------------------ execução


def test_banco_do_zero(conexao: sqlite3.Connection, caminho_banco: Path, log: LogErros) -> None:
    aplicadas = executar_migracoes(conexao, caminho_banco, log, relogio=_relogio)
    esperadas = [m.versao for m in carregar_migracoes()]
    assert aplicadas == esperadas
    linhas = conexao.execute("SELECT versao, nome, checksum, aplicada_em FROM schema_migracoes")
    primeira = linhas.fetchone()
    assert primeira == (
        1,
        "0001_inicial.sql",
        carregar_migracoes()[0].checksum,
        "2026-11-27T13:45:10.123Z",
    )
    # Banco novo: não há o que copiar.
    assert listar_copias(caminho_banco) == []
    assert busca_fts_disponivel(conexao)
    assert not conexao.in_transaction


def test_execucao_duplicada_nao_reaplica(
    conexao: sqlite3.Connection, caminho_banco: Path, log: LogErros
) -> None:
    executar_migracoes(conexao, caminho_banco, log)
    esquema = _esquema(conexao)
    assert executar_migracoes(conexao, caminho_banco, log) == []
    assert executar_migracoes(conexao, caminho_banco, log) == []
    assert _esquema(conexao) == esquema
    total = conexao.execute("SELECT count(*) FROM schema_migracoes").fetchone()[0]
    assert total == len(carregar_migracoes())
    assert conexao.execute("SELECT count(*) FROM admin_controle").fetchone()[0] == 1
    assert listar_copias(caminho_banco) == []


def test_execucao_duplicada_em_nova_conexao(caminho_banco: Path, log: LogErros) -> None:
    for _ in range(2):
        conexao = abrir_conexao(caminho_banco)
        executar_migracoes(conexao, caminho_banco, log)
        conexao.close()
    conexao = abrir_conexao(caminho_banco)
    assert list(versoes_aplicadas(conexao)) == [m.versao for m in carregar_migracoes()]
    conexao.close()


def test_migration_alterada_para_sem_tocar_no_banco(
    conexao: sqlite3.Connection, caminho_banco: Path, log: LogErros, pasta_logs: Path
) -> None:
    m1 = _migracao(
        1,
        "CREATE TABLE schema_migracoes (versao INTEGER PRIMARY KEY, nome TEXT, "
        "checksum TEXT, aplicada_em TEXT); CREATE TABLE a (x INTEGER);",
    )
    executar_migracoes(conexao, caminho_banco, log, [m1])
    esquema = _esquema(conexao)

    alterada = _migracao(1, m1.sql + " CREATE TABLE intrusa (y INTEGER);")
    m2 = _migracao(2, "CREATE TABLE b (z INTEGER);")
    with pytest.raises(MigracaoAlterada) as erro:
        executar_migracoes(conexao, caminho_banco, log, [alterada, m2])
    assert erro.value.versao == 1
    assert _esquema(conexao) == esquema
    assert listar_copias(caminho_banco) == []
    assert conexao.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    texto = _texto_do_log(pasta_logs)
    assert "| ERRO |" in texto
    assert "versao=1" in texto
    assert "intrusa" not in texto  # o conteúdo da migration nunca vai para o log


def test_versao_desconhecida_para(
    conexao: sqlite3.Connection, caminho_banco: Path, log: LogErros, pasta_logs: Path
) -> None:
    executar_migracoes(conexao, caminho_banco, log)
    conexao.execute(
        "INSERT INTO schema_migracoes (versao, nome, checksum, aplicada_em) VALUES (?, ?, ?, ?)",
        (999, "0999_futura.sql", "0" * 64, "2026-11-27T00:00:00.000Z"),
    )
    with pytest.raises(MigracaoDesconhecida):
        executar_migracoes(conexao, caminho_banco, log)
    assert "versao=999" in _texto_do_log(pasta_logs)


def _sql_base() -> str:
    return (
        "CREATE TABLE schema_migracoes (versao INTEGER PRIMARY KEY, nome TEXT NOT NULL, "
        "checksum TEXT NOT NULL, aplicada_em TEXT NOT NULL);"
        "CREATE TABLE dado (valor TEXT);"
        "INSERT INTO dado (valor) VALUES ('original');"
    )


def test_copia_de_seguranca_antes_das_pendentes(
    conexao: sqlite3.Connection, caminho_banco: Path, log: LogErros
) -> None:
    m1 = _migracao(1, _sql_base())
    executar_migracoes(conexao, caminho_banco, log, [m1])
    m2 = _migracao(2, "UPDATE dado SET valor = 'migrado';")
    m3 = _migracao(3, "CREATE TABLE nova (a INTEGER);")
    assert executar_migracoes(conexao, caminho_banco, log, [m1, m2, m3]) == [2, 3]

    copia = caminho_copia(caminho_banco, 2)
    assert copia.name == "drivelan.db.antes-0002"
    assert listar_copias(caminho_banco) == [copia]  # uma cópia por execução, não por migration
    antes = sqlite3.connect(copia)
    try:
        assert antes.execute("SELECT valor FROM dado").fetchone()[0] == "original"
        assert [v for (v,) in antes.execute("SELECT versao FROM schema_migracoes")] == [1]
    finally:
        antes.close()
    assert conexao.execute("SELECT valor FROM dado").fetchone()[0] == "migrado"
    if POSIX:
        assert stat.S_IMODE(copia.stat().st_mode) == 0o600


def test_mantem_so_as_tres_copias_mais_recentes(
    conexao: sqlite3.Connection, caminho_banco: Path, log: LogErros
) -> None:
    lista = [_migracao(1, _sql_base())]
    executar_migracoes(conexao, caminho_banco, log, lista)
    for versao in range(2, 7):
        lista.append(_migracao(versao, f"CREATE TABLE t{versao} (a INTEGER);"))
        executar_migracoes(conexao, caminho_banco, log, lista)
    nomes = [p.name for p in listar_copias(caminho_banco)]
    assert len(nomes) == COPIAS_MANTIDAS
    assert nomes == [f"drivelan.db.antes-{v:04d}" for v in (4, 5, 6)]


def test_falha_desfaz_so_a_migration_com_erro(
    conexao: sqlite3.Connection, caminho_banco: Path, log: LogErros, pasta_logs: Path
) -> None:
    m1 = _migracao(1, _sql_base())
    m2 = _migracao(2, "CREATE TABLE boa (a INTEGER);")
    m3 = _migracao(3, "CREATE TABLE parcial (a INTEGER); INSERT INTO inexistente VALUES (1);")
    with pytest.raises(FalhaMigracao) as erro:
        executar_migracoes(conexao, caminho_banco, log, [m1, m2, m3])
    assert erro.value.versao == 3
    assert list(versoes_aplicadas(conexao)) == [1, 2]
    tabelas = {n for (n,) in conexao.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "boa" in tabelas
    assert "parcial" not in tabelas
    assert not conexao.in_transaction
    assert "versao=3" in _texto_do_log(pasta_logs)

    # Corrigida a migration, a próxima execução continua de onde parou.
    m3_corrigida = _migracao(3, "CREATE TABLE parcial (a INTEGER);")
    assert executar_migracoes(conexao, caminho_banco, log, [m1, m2, m3_corrigida]) == [3]


def test_arquivo_invalido_no_pacote_registra_erro(
    conexao: sqlite3.Connection,
    caminho_banco: Path,
    log: LogErros,
    pasta_logs: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pasta = tmp_path / "migracoes"
    pasta.mkdir()
    (pasta / "1_errada.sql").write_text("SELECT 1;", encoding="utf-8")
    monkeypatch.setattr(modulo_migracoes, "pasta_migracoes", lambda: pasta)
    with pytest.raises(MigracaoInvalida):
        executar_migracoes(conexao, caminho_banco, log)
    assert "| ERRO |" in _texto_do_log(pasta_logs)


def test_sem_trigram_cria_banco_sem_fts(
    conexao: sqlite3.Connection,
    caminho_banco: Path,
    log: LogErros,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(modulo_migracoes, "suporta_trigram", lambda _c: False)
    executar_migracoes(conexao, caminho_banco, log)
    assert not busca_fts_disponivel(conexao)
    # O checksum registrado continua sendo o do arquivo inteiro.
    assert versoes_aplicadas(conexao)[1] == carregar_migracoes()[0].checksum
    conexao.execute(
        "INSERT INTO auditoria (ator_tipo, acao, alvo_caminho, ocorrido_em) "
        "VALUES ('sistema', 'lixeira_item_expirado', 'a/b.txt', '2026-11-27T00:00:00.000Z')"
    )
    # Alternativa da consulta: LIKE (implementada na Fase 9).
    achados = conexao.execute(
        "SELECT count(*) FROM auditoria WHERE alvo_caminho LIKE ?", ("%b.t%",)
    ).fetchone()[0]
    assert achados == 1
    # Nova execução não tenta recriar nada.
    monkeypatch.undo()
    assert executar_migracoes(conexao, caminho_banco, log) == []
    assert not busca_fts_disponivel(conexao)
