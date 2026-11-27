"""Testes da estrutura criada pela `0001_inicial.sql` (FSD 11.2): tabelas, índices e regras."""

import io
import sqlite3
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from drivelan.servico.dados.banco import abrir_conexao
from drivelan.servico.dados.migracoes import executar_migracoes
from drivelan.servico.log_erros import LogErros

DATA = "2026-11-27T13:45:10.123Z"

TABELAS = {
    "schema_migracoes",
    "instalacao",
    "admin_controle",
    "identidade",
    "identidade_nome_historico",
    "conta",
    "pasta",
    "pasta_encerramento",
    "acesso",
    "bloqueio_dono",
    "bloqueio_pin_pasta",
    "lixeira_item",
    "arquivo_em_edicao",
    "auditoria",
    "auditoria_busca",
    "cliente_servidor_manual",
    "cliente_servidor_conhecido",
    "cliente_acesso",
    "cliente_alteracao_pendente",
    "cliente_edicao_ativa",
}

# Índices criados explicitamente (nome → é parcial?), conforme a seção 11.2.
INDICES = {
    "idx_identidade_nome_historico_identidade": False,
    "uq_conta_nome_normalizado": True,
    "idx_conta_situacao": False,
    "uq_pasta_nome_normalizado": True,
    "uq_pasta_caminho_normalizado": True,
    "idx_pasta_dono_situacao": False,
    "idx_pasta_situacao_apagada_em": False,
    "idx_pasta_lixeira_so_pendente": False,
    "uq_pasta_encerramento_programado": True,
    "idx_pasta_encerramento_situacao_termina": False,
    "uq_acesso_ativo": True,
    "idx_acesso_pasta_situacao": False,
    "uq_bloqueio_dono_ativo": True,
    "idx_bloqueio_dono_pasta_situacao": False,
    "idx_lixeira_item_pasta_situacao_excluido": False,
    "idx_lixeira_item_situacao_excluido": False,
    "idx_lixeira_item_situacao_finalizado": False,
    "uq_arquivo_em_edicao_caminho": False,
    "idx_arquivo_em_edicao_ultimo_sinal": False,
    "idx_auditoria_ocorrido": False,
    "idx_auditoria_pasta_ocorrido": False,
    "idx_auditoria_identidade_ocorrido": False,
    "idx_auditoria_acao_ocorrido": False,
    "idx_auditoria_pasta_identidade": False,
    "idx_cliente_servidor_conhecido_host": False,
    "uq_cliente_servidor_conhecido_local": True,
    "idx_cliente_acesso_conta_situacao": False,
    "idx_cliente_alteracao_pendente_so_usuario": False,
    "uq_cliente_edicao_ativa_acesso": False,
    "uq_cliente_edicao_ativa_pasta": False,
    "idx_cliente_edicao_ativa_so_usuario": False,
}

# Restrições UNIQUE declaradas nas tabelas (índices automáticos), por tabela e colunas.
UNICOS_DECLARADOS = {
    ("instalacao", ("instalacao_id",)),
    ("identidade", ("instalacao_id", "conta_uuid")),
    ("conta", ("uuid",)),
    ("conta", ("identidade_id",)),
    ("pasta", ("uuid",)),
    ("acesso", ("token_hash",)),
    ("bloqueio_pin_pasta", ("pasta_id", "tipo_chave", "valor_chave")),
    ("lixeira_item", ("uuid",)),
    ("arquivo_em_edicao", ("uuid",)),
    ("cliente_servidor_manual", ("conta_id", "endereco", "porta")),
    ("cliente_servidor_conhecido", ("instalacao_id",)),
    ("cliente_acesso", ("conta_id", "servidor_conhecido_id", "pasta_uuid")),
    ("cliente_alteracao_pendente", ("cliente_acesso_id", "caminho_remoto")),
}


@pytest.fixture
def bd(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    caminho = tmp_path / "dados" / "drivelan.db"
    conexao = abrir_conexao(caminho)
    executar_migracoes(conexao, caminho, LogErros(tmp_path / "logs", saida_erro=io.StringIO()))
    yield conexao
    conexao.close()


# ------------------------------------------------------------------ auxiliares de inserção


def _id(
    conexao: sqlite3.Connection, sql: str, parametros: dict[str, object] | tuple[object, ...]
) -> int:
    cursor = conexao.execute(sql, parametros)
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def identidade(conexao: sqlite3.Connection, nome: str = "joao") -> int:
    return _id(
        conexao,
        "INSERT INTO identidade (instalacao_id, conta_uuid, host_nome, nome_atual, criado_em, "
        "atualizado_em) VALUES (:inst, :conta, 'LAB-PC07', :nome, :d, :d)",
        {"inst": "a" * 64, "conta": str(uuid.uuid4()), "nome": nome, "d": DATA},
    )


def conta(conexao: sqlite3.Connection, nome: str = "joao", situacao: str = "ativa") -> int:
    return _id(
        conexao,
        "INSERT INTO conta (uuid, identidade_id, nome, nome_normalizado, pin_hash, situacao, "
        "criado_em, atualizado_em) VALUES (:u, :i, :n, :nn, 'hash', :s, :d, :d)",
        {
            "u": str(uuid.uuid4()),
            "i": identidade(conexao, nome),
            "n": nome,
            "nn": nome.casefold(),
            "s": situacao,
            "d": DATA,
        },
    )


def pasta(
    conexao: sqlite3.Connection,
    dono: int,
    nome: str = "Financeiro",
    situacao: str = "ativa",
    caminho: str | None = None,
) -> int:
    caminho = caminho or f"/home/maria/DriveLan/{nome}"
    return _id(
        conexao,
        "INSERT INTO pasta (uuid, conta_dono_id, nome, nome_normalizado, caminho, "
        "caminho_normalizado, so_dono, pin_hash, limite_bytes, situacao, criado_em, "
        "atualizado_em) VALUES (:u, :dono, :n, :nn, :c, :c, '1000', 'hash', 1048576, :s, :d, :d)",
        {
            "u": str(uuid.uuid4()),
            "dono": dono,
            "n": nome,
            "nn": nome.casefold(),
            "c": caminho,
            "s": situacao,
            "d": DATA,
        },
    )


def acesso(conexao: sqlite3.Connection, pasta_id: int, ident: int, situacao: str = "ativo") -> int:
    return _id(
        conexao,
        "INSERT INTO acesso (pasta_id, identidade_id, token_hash, situacao, concedido_em, "
        "criado_em, atualizado_em) VALUES (:p, :i, :t, :s, :d, :d, :d)",
        {"p": pasta_id, "i": ident, "t": uuid.uuid4().hex, "s": situacao, "d": DATA},
    )


def auditoria(
    conexao: sqlite3.Connection,
    pasta_id: int | None,
    alvo: str,
    ator: str = "sistema",
    ident: int | None = None,
    detalhes: str | None = None,
) -> int:
    return _id(
        conexao,
        "INSERT INTO auditoria (pasta_id, pasta_nome, ator_tipo, identidade_id, acao, "
        "alvo_caminho, detalhes, ocorrido_em) VALUES (:p, 'Financeiro', :a, :i, 'item_excluido', "
        ":alvo, :det, :d)",
        {"p": pasta_id, "a": ator, "i": ident, "alvo": alvo, "det": detalhes, "d": DATA},
    )


def servidor_conhecido(conexao: sqlite3.Connection, inst: str, local: int = 0) -> int:
    return _id(
        conexao,
        "INSERT INTO cliente_servidor_conhecido (instalacao_id, host_nome, local, "
        "primeiro_contato_em, ultimo_contato_em, criado_em, atualizado_em) "
        "VALUES (:inst, 'ADM-PC02', :l, :d, :d, :d, :d)",
        {"inst": inst, "l": local, "d": DATA},
    )


# ------------------------------------------------------------------ estrutura


def test_todas_as_tabelas(bd: sqlite3.Connection) -> None:
    nomes = {
        n
        for (n,) in bd.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'auditoria_busca_%'"
        )
    }
    assert nomes == TABELAS


def test_todos_os_indices_explicitos_inclusive_parciais(bd: sqlite3.Connection) -> None:
    encontrados: dict[str, bool] = {}
    for (tabela,) in bd.execute("SELECT name FROM sqlite_master WHERE type = 'table'"):
        for _seq, nome, _unico, origem, parcial in bd.execute(f"PRAGMA index_list('{tabela}')"):
            if origem == "c":
                encontrados[nome] = bool(parcial)
    assert encontrados == INDICES


def test_restricoes_unique_declaradas(bd: sqlite3.Connection) -> None:
    encontrados: set[tuple[str, tuple[str, ...]]] = set()
    for (tabela,) in bd.execute("SELECT name FROM sqlite_master WHERE type = 'table'"):
        for _seq, nome, unico, origem, _parcial in bd.execute(f"PRAGMA index_list('{tabela}')"):
            if unico and origem == "u":
                colunas = tuple(c[2] for c in bd.execute(f"PRAGMA index_info('{nome}')"))
                encontrados.add((tabela, colunas))
    assert encontrados == UNICOS_DECLARADOS


def test_indice_da_auditoria_em_ordem_decrescente(bd: sqlite3.Connection) -> None:
    colunas = bd.execute("PRAGMA index_xinfo('idx_auditoria_ocorrido')").fetchall()
    chaves = [(c[2], c[3]) for c in colunas if c[5]]  # (nome, desc) só das colunas-chave
    assert chaves == [("ocorrido_em", 1), ("id", 1)]


def test_gatilhos_da_busca(bd: sqlite3.Connection) -> None:
    gatilhos = {n for (n,) in bd.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    assert gatilhos == {"auditoria_busca_inclusao", "auditoria_busca_exclusao"}


def test_integridade(bd: sqlite3.Connection) -> None:
    assert bd.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert bd.execute("PRAGMA foreign_key_check").fetchall() == []


def test_chaves_estrangeiras_e_acoes(bd: sqlite3.Connection) -> None:
    def acoes(tabela: str) -> dict[str, tuple[str, str]]:
        return {
            linha[3]: (linha[2], linha[6])
            for linha in bd.execute(f"PRAGMA foreign_key_list('{tabela}')")
        }

    assert acoes("pasta")["conta_dono_id"] == ("conta", "RESTRICT")
    assert acoes("acesso")["pasta_id"] == ("pasta", "CASCADE")
    assert acoes("acesso")["identidade_id"] == ("identidade", "NO ACTION")
    assert acoes("auditoria")["pasta_id"] == ("pasta", "CASCADE")
    assert acoes("identidade_nome_historico")["identidade_id"] == ("identidade", "CASCADE")
    assert acoes("cliente_acesso")["conta_id"] == ("conta", "CASCADE")
    assert acoes("cliente_acesso")["servidor_conhecido_id"] == (
        "cliente_servidor_conhecido",
        "NO ACTION",
    )
    assert acoes("cliente_edicao_ativa")["pasta_id"] == ("pasta", "CASCADE")


# ------------------------------------------------------------------ linhas únicas e dados iniciais


def test_admin_controle_linha_unica(bd: sqlite3.Connection) -> None:
    linha = bd.execute(
        "SELECT id, erros_no_ciclo, ciclos_bloqueio, bloqueado_ate, atualizado_em "
        "FROM admin_controle"
    ).fetchall()
    assert len(linha) == 1
    assert linha[0][:4] == (1, 0, 0, None)
    assert linha[0][4].endswith("Z") and len(linha[0][4]) == len(DATA)
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute("INSERT INTO admin_controle (id, atualizado_em) VALUES (2, ?)", (DATA,))
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute("UPDATE admin_controle SET erros_no_ciclo = 5")


def test_instalacao_nao_e_criada_e_tem_linha_unica(bd: sqlite3.Connection) -> None:
    assert bd.execute("SELECT count(*) FROM instalacao").fetchone()[0] == 0
    sql = (
        "INSERT INTO instalacao (id, instalacao_id, host_nome, chave_admin_hash, versao_app, "
        "criado_em, atualizado_em) VALUES (?, ?, 'PC', 'hash', '0.1', ?, ?)"
    )
    bd.execute(sql, (1, "a" * 64, DATA, DATA))
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute(sql, (2, "b" * 64, DATA, DATA))


# ------------------------------------------------------------------ CHECKs


@pytest.mark.parametrize(
    ("sql", "valor"),
    [
        ("UPDATE conta SET situacao = ?", "bloqueada"),
        ("UPDATE conta SET pin_temporario = ?", 2),
        ("UPDATE conta SET erros_pin = ?", -1),
        ("UPDATE pasta SET situacao = ?", "removida"),
        ("UPDATE pasta SET limite_bytes = ?", 0),
        ("UPDATE pasta SET bytes_conteudo = ?", -1),
        ("UPDATE pasta SET lixeira_so_pendente = ?", 3),
    ],
)
def test_checks_de_conta_e_pasta(bd: sqlite3.Connection, sql: str, valor: object) -> None:
    pasta(bd, conta(bd))
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute(sql, (valor,))


def test_checks_de_acesso(bd: sqlite3.Connection) -> None:
    ident = identidade(bd, "ana")
    id_acesso = acesso(bd, pasta(bd, conta(bd)), ident)
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute("UPDATE acesso SET situacao = 'suspenso' WHERE id = ?", (id_acesso,))
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute("UPDATE acesso SET motivo_remocao = 'outro' WHERE id = ?", (id_acesso,))
    bd.execute(
        "UPDATE acesso SET situacao = 'removido', motivo_remocao = 'pin_exigido_na_reativacao' "
        "WHERE id = ?",
        (id_acesso,),
    )


def test_checks_de_auditoria(bd: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        auditoria(bd, None, "x", ator="usuario")  # usuário exige identidade
    with pytest.raises(sqlite3.IntegrityError):
        auditoria(bd, None, "x", ator="visitante")
    with pytest.raises(sqlite3.IntegrityError):
        auditoria(bd, None, "x", detalhes="{não é json")
    auditoria(bd, None, "x", ator="usuario", ident=identidade(bd), detalhes='{"quantidade": 2}')


def test_porta_do_servidor_manual(bd: sqlite3.Connection) -> None:
    id_conta = conta(bd)
    sql = (
        "INSERT INTO cliente_servidor_manual (conta_id, endereco, porta, criado_em, "
        "atualizado_em) VALUES (?, '192.168.0.10', ?, ?, ?)"
    )
    for porta_invalida in (0, 65536):
        with pytest.raises(sqlite3.IntegrityError):
            bd.execute(sql, (id_conta, porta_invalida, DATA, DATA))
    bd.execute(sql, (id_conta, 47820, DATA, DATA))
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute(sql, (id_conta, 47820, DATA, DATA))


def test_edicao_ativa_exige_exatamente_um_destino(bd: sqlite3.Connection) -> None:
    id_conta = conta(bd)
    id_pasta = pasta(bd, id_conta)
    servidor = servidor_conhecido(bd, "c" * 64)
    id_cliente = _id(
        bd,
        "INSERT INTO cliente_acesso (conta_id, servidor_conhecido_id, pasta_uuid, pasta_nome, "
        "dono_rotulo, token, situacao, concedido_em, criado_em, atualizado_em) "
        "VALUES (:c, :s, :u, 'Financeiro', 'maria@ADM-PC02', 'tok', 'ativo', :d, :d, :d)",
        {"c": id_conta, "s": servidor, "u": str(uuid.uuid4()), "d": DATA},
    )
    sql = (
        "INSERT INTO cliente_edicao_ativa (conta_id, cliente_acesso_id, pasta_id, caminho_remoto, "
        "trava_uuid, versao_base, arquivo_local, so_usuario, iniciada_em, criado_em, "
        "atualizado_em) VALUES (?, ?, ?, 'a.txt', 't', 'v1', '/tmp/a', '1000', ?, ?, ?)"
    )
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute(sql, (id_conta, None, None, DATA, DATA, DATA))
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute(sql, (id_conta, id_cliente, id_pasta, DATA, DATA, DATA))
    bd.execute(sql, (id_conta, id_cliente, None, DATA, DATA, DATA))
    bd.execute(sql, (id_conta, None, id_pasta, DATA, DATA, DATA))
    with pytest.raises(sqlite3.IntegrityError):  # índice único da pasta própria
        bd.execute(sql, (id_conta, None, id_pasta, DATA, DATA, DATA))
    with pytest.raises(sqlite3.IntegrityError):  # índice único da pasta remota
        bd.execute(sql, (id_conta, id_cliente, None, DATA, DATA, DATA))


# ------------------------------------------------------------------ índices únicos parciais


def test_nome_de_conta_unico_exceto_excluida(bd: sqlite3.Connection) -> None:
    primeira = conta(bd, "joao")
    with pytest.raises(sqlite3.IntegrityError):
        conta(bd, "JOAO")  # mesmo nome normalizado
    bd.execute("UPDATE conta SET situacao = 'desativada' WHERE id = ?", (primeira,))
    with pytest.raises(sqlite3.IntegrityError):
        conta(bd, "joao")  # desativada continua reservando o nome
    bd.execute("UPDATE conta SET situacao = 'excluida' WHERE id = ?", (primeira,))
    conta(bd, "joao")  # nome reutilizável após a exclusão (RN-03)


def test_nome_e_caminho_de_pasta_unicos_exceto_apagada(bd: sqlite3.Connection) -> None:
    dono = conta(bd)
    primeira = pasta(bd, dono, "Financeiro")
    with pytest.raises(sqlite3.IntegrityError):
        pasta(bd, dono, "financeiro", caminho="/outro/lugar")
    with pytest.raises(sqlite3.IntegrityError):
        pasta(bd, dono, "Outra", caminho="/home/maria/DriveLan/Financeiro")
    bd.execute("UPDATE pasta SET situacao = 'apagada' WHERE id = ?", (primeira,))
    pasta(bd, dono, "Financeiro")


def test_um_encerramento_programado_por_pasta(bd: sqlite3.Connection) -> None:
    id_pasta = pasta(bd, conta(bd))
    sql = (
        "INSERT INTO pasta_encerramento (pasta_id, tipo, iniciado_em, termina_em, situacao, "
        "criado_em, atualizado_em) VALUES (?, 'desativar', ?, ?, ?, ?, ?)"
    )
    primeiro = _id(bd, sql, (id_pasta, DATA, DATA, "programado", DATA, DATA))
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute(sql, (id_pasta, DATA, DATA, "programado", DATA, DATA))
    bd.execute("UPDATE pasta_encerramento SET situacao = 'cancelado' WHERE id = ?", (primeiro,))
    bd.execute(sql, (id_pasta, DATA, DATA, "programado", DATA, DATA))
    bd.execute(sql, (id_pasta, DATA, DATA, "concluido", DATA, DATA))
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute(sql, (id_pasta, DATA, DATA, "pausado", DATA, DATA))


def test_um_acesso_ativo_por_pasta_e_identidade(bd: sqlite3.Connection) -> None:
    id_pasta = pasta(bd, conta(bd))
    ident = identidade(bd, "ana")
    primeiro = acesso(bd, id_pasta, ident)
    with pytest.raises(sqlite3.IntegrityError):
        acesso(bd, id_pasta, ident)
    bd.execute("UPDATE acesso SET situacao = 'removido' WHERE id = ?", (primeiro,))
    acesso(bd, id_pasta, ident)  # novo acesso = nova linha (FSD 14.3)


def test_um_bloqueio_ativo_por_pasta_e_identidade(bd: sqlite3.Connection) -> None:
    id_pasta = pasta(bd, conta(bd))
    ident = identidade(bd, "ana")
    sql = (
        "INSERT INTO bloqueio_dono (pasta_id, identidade_id, situacao, bloqueado_em, criado_em, "
        "atualizado_em) VALUES (?, ?, ?, ?, ?, ?)"
    )
    bd.execute(sql, (id_pasta, ident, "ativo", DATA, DATA, DATA))
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute(sql, (id_pasta, ident, "ativo", DATA, DATA, DATA))
    bd.execute("UPDATE bloqueio_dono SET situacao = 'desbloqueado'")
    bd.execute(sql, (id_pasta, ident, "ativo", DATA, DATA, DATA))


def test_um_unico_servidor_conhecido_local(bd: sqlite3.Connection) -> None:
    servidor_conhecido(bd, "a" * 64, local=1)
    servidor_conhecido(bd, "b" * 64, local=0)
    servidor_conhecido(bd, "c" * 64, local=0)
    with pytest.raises(sqlite3.IntegrityError):
        servidor_conhecido(bd, "d" * 64, local=1)
    with pytest.raises(sqlite3.IntegrityError):
        servidor_conhecido(bd, "b" * 64)  # instalacao_id único


def test_bloqueio_pin_unico_por_chave(bd: sqlite3.Connection) -> None:
    id_pasta = pasta(bd, conta(bd))
    sql = (
        "INSERT INTO bloqueio_pin_pasta (pasta_id, tipo_chave, valor_chave, ultimo_erro_em, "
        "criado_em, atualizado_em) VALUES (?, ?, ?, ?, ?, ?)"
    )
    bd.execute(sql, (id_pasta, "ip", "192.168.0.7", DATA, DATA, DATA))
    bd.execute(sql, (id_pasta, "instalacao", "192.168.0.7", DATA, DATA, DATA))
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute(sql, (id_pasta, "ip", "192.168.0.7", DATA, DATA, DATA))
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute(sql, (id_pasta, "mac", "x", DATA, DATA, DATA))


# ------------------------------------------------------------------ chaves estrangeiras


def test_chave_estrangeira_inexistente_recusada(bd: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        acesso(bd, 999, 999)


def test_conta_dona_de_pasta_nao_pode_ser_apagada(bd: sqlite3.Connection) -> None:
    dono = conta(bd)
    pasta(bd, dono)
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute("DELETE FROM conta WHERE id = ?", (dono,))


def test_identidade_referenciada_nao_pode_ser_apagada(bd: sqlite3.Connection) -> None:
    ident = identidade(bd, "ana")
    auditoria(bd, None, "x", ator="usuario", ident=ident)
    with pytest.raises(sqlite3.IntegrityError):
        bd.execute("DELETE FROM identidade WHERE id = ?", (ident,))


def test_apagar_pasta_remove_em_cascata(bd: sqlite3.Connection) -> None:
    id_pasta = pasta(bd, conta(bd))
    acesso(bd, id_pasta, identidade(bd, "ana"))
    auditoria(bd, id_pasta, "docs/relatorio.docx")
    auditoria(bd, None, "evento sem pasta")
    bd.execute("DELETE FROM pasta WHERE id = ?", (id_pasta,))
    assert bd.execute("SELECT count(*) FROM acesso").fetchone()[0] == 0
    assert bd.execute("SELECT count(*) FROM auditoria").fetchone()[0] == 1


# ------------------------------------------------------------------ busca FTS5 trigram


def _buscar(bd: sqlite3.Connection, termo: str) -> list[int]:
    return [
        rowid
        for (rowid,) in bd.execute(
            "SELECT rowid FROM auditoria_busca WHERE auditoria_busca MATCH ? ORDER BY rowid",
            (f'"{termo}"',),
        )
    ]


def test_busca_trigram_sem_diferenciar_maiusculas(bd: sqlite3.Connection) -> None:
    primeiro = auditoria(bd, None, "Documentos/Relatório Anual.docx")
    auditoria(bd, None, "fotos/praia.jpg")
    assert _buscar(bd, "relatório") == [primeiro]
    assert _buscar(bd, "ANUAL") == [primeiro]
    assert _buscar(bd, "inexistente") == []


def test_busca_inclui_destino_e_nome_da_pasta(bd: sqlite3.Connection) -> None:
    id_registro = _id(
        bd,
        "INSERT INTO auditoria (pasta_nome, ator_tipo, acao, alvo_caminho, alvo_caminho_novo, "
        "ocorrido_em) VALUES ('Financeiro', 'sistema', 'item_movido', 'a.txt', 'novo/b.txt', :d)",
        {"d": DATA},
    )
    assert _buscar(bd, "novo/b") == [id_registro]
    assert _buscar(bd, "financ") == [id_registro]


def test_busca_atualizada_ao_apagar_direto_e_por_cascata(bd: sqlite3.Connection) -> None:
    id_pasta = pasta(bd, conta(bd))
    solto = auditoria(bd, None, "planilha-custos.xlsx")
    da_pasta = auditoria(bd, id_pasta, "planilha-vendas.xlsx")
    assert _buscar(bd, "planilha") == [solto, da_pasta]
    bd.execute("DELETE FROM auditoria WHERE id = ?", (solto,))
    assert _buscar(bd, "planilha") == [da_pasta]
    bd.execute("DELETE FROM pasta WHERE id = ?", (id_pasta,))
    assert _buscar(bd, "planilha") == []
    bd.execute("INSERT INTO auditoria_busca (auditoria_busca) VALUES ('integrity-check')")
