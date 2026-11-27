"""Executor de migrations do banco (FSD 11.3).

A estrutura do banco é criada e alterada **somente** por arquivos SQL numerados em
`dados/migracoes/` (`0001_inicial.sql`, `0002_<descricao>.sql`...). O executor:

1. lê as migrations empacotadas em ordem numérica;
2. ignora as já registradas em `schema_migracoes` e confere o checksum SHA-256 de cada uma; se
   uma migration aplicada foi alterada (ou não existe mais no pacote), registra erro no log e
   para sem tocar no banco;
3. antes de aplicar qualquer pendente num banco já existente, copia o banco para
   `drivelan.db.antes-<versao>` (ficam só as 3 cópias mais recentes);
4. aplica cada migration numa transação própria, registrando a versão na mesma transação.

A tabela `schema_migracoes` é criada pela própria `0001`: sem ela, o banco é novo e todas as
migrations estão pendentes (e não há o que copiar).

As migrations só rodam na inicialização do serviço ou pelo comando `drivelan-service --migrar`
(Fase 5). Não existe rota no canal local nem na rede para executá-las.
"""

import hashlib
import os
import re
import sqlite3
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

from drivelan.comum.protocolo import agora_utc, formatar_data_iso
from drivelan.servico.dados.banco import MODO_ARQUIVO_BANCO, transacao
from drivelan.servico.log_erros import LogErros

ORIGEM_LOG = "servico.dados.migracoes"
PADRAO_NOME = re.compile(r"^(?P<versao>\d{4})_(?P<descricao>[a-z0-9_]+)\.sql$")
PREFIXO_COPIA = ".antes-"
COPIAS_MANTIDAS = 3

# Bloco da 0001 que depende do FTS5 com o tokenizador trigram (FSD 11.2).
MARCADOR_TRIGRAM_INICIO = "-- drivelan:fts5-trigram:inicio"
MARCADOR_TRIGRAM_FIM = "-- drivelan:fts5-trigram:fim"
TABELA_BUSCA = "auditoria_busca"


# ------------------------------------------------------------------ erros


class ErroMigracao(Exception):
    """Base dos erros do executor. O serviço registra e tenta de novo depois (FSD 11.3)."""


class MigracaoInvalida(ErroMigracao):
    """Arquivo de migration com nome fora do padrão ou versão repetida."""


class MigracaoAlterada(ErroMigracao):
    """Uma migration já aplicada teve o conteúdo alterado (checksum diferente)."""

    def __init__(self, versao: int) -> None:
        super().__init__(f"migration {versao:04d} alterada depois de aplicada")
        self.versao = versao


class MigracaoDesconhecida(ErroMigracao):
    """O banco registra uma versão que não existe entre as migrations empacotadas."""

    def __init__(self, versao: int) -> None:
        super().__init__(f"migration {versao:04d} aplicada não existe no pacote")
        self.versao = versao


class FalhaMigracao(ErroMigracao):
    """Erro ao aplicar uma migration; a transação dela foi desfeita."""

    def __init__(self, versao: int) -> None:
        super().__init__(f"falha ao aplicar a migration {versao:04d}")
        self.versao = versao


# ------------------------------------------------------------------ leitura das migrations


@dataclass(frozen=True, slots=True)
class Migracao:
    versao: int
    nome: str
    sql: str
    checksum: str


def calcular_checksum(conteudo: bytes) -> str:
    """SHA-256 hexadecimal do conteúdo do arquivo, como gravado em `schema_migracoes`."""
    return hashlib.sha256(conteudo).hexdigest()


def pasta_migracoes() -> Traversable:
    """Pasta das migrations empacotadas (somente leitura no diretório do programa)."""
    return resources.files("drivelan.servico.dados") / "migracoes"


def carregar_migracoes(pasta: Traversable | Path | None = None) -> list[Migracao]:
    """Lê os arquivos `NNNN_descricao.sql`, em ordem numérica."""
    origem: Traversable | Path = pasta_migracoes() if pasta is None else pasta
    migracoes: dict[int, Migracao] = {}
    for item in origem.iterdir():
        if not item.is_file() or not item.name.endswith(".sql"):
            continue
        encontrado = PADRAO_NOME.match(item.name)
        if encontrado is None:
            raise MigracaoInvalida(f"nome de migration fora do padrão: {item.name}")
        versao = int(encontrado["versao"])
        if versao == 0:
            raise MigracaoInvalida("a numeração das migrations começa em 0001")
        if versao in migracoes:
            raise MigracaoInvalida(f"versão de migration repetida: {versao:04d}")
        conteudo = item.read_bytes()
        migracoes[versao] = Migracao(
            versao, item.name, conteudo.decode("utf-8"), calcular_checksum(conteudo)
        )
    return [migracoes[versao] for versao in sorted(migracoes)]


# ------------------------------------------------------------------ preparo do SQL


def dividir_comandos(sql: str) -> list[str]:
    """Divide um script em comandos completos, respeitando `;` em gatilhos, textos e comentários.

    Executar comando a comando permite manter toda a migration e o registro da versão numa
    única transação, com o registro feito por parâmetros (sem montar SQL com texto).
    """
    comandos: list[str] = []
    acumulado = ""
    for parte in sql.split(";"):
        acumulado += parte + ";"
        if sqlite3.complete_statement(acumulado):
            comando = acumulado.strip()
            if _tem_conteudo(comando):
                comandos.append(comando)
            acumulado = ""
    if _tem_conteudo(acumulado.removesuffix(";")):
        raise MigracaoInvalida("a migration termina com um comando incompleto")
    return comandos


def _tem_conteudo(trecho: str) -> bool:
    """Indica se sobra algo além de espaços, comentários e `;`."""
    sem_comentarios = re.sub(r"--[^\n]*", "", trecho)
    sem_comentarios = re.sub(r"/\*.*?\*/", "", sem_comentarios, flags=re.DOTALL)
    return sem_comentarios.replace(";", "").strip() != ""


def remover_bloco_trigram(sql: str) -> str:
    """Retira o bloco FTS5 `trigram` da migration (alternativa com `LIKE`, FSD 11.2)."""
    padrao = re.compile(
        re.escape(MARCADOR_TRIGRAM_INICIO) + r".*?" + re.escape(MARCADOR_TRIGRAM_FIM),
        flags=re.DOTALL,
    )
    return padrao.sub("", sql)


def suporta_trigram(conexao: sqlite3.Connection) -> bool:
    """Indica se o SQLite em uso tem FTS5 com o tokenizador `trigram`."""
    try:
        conexao.execute(
            "CREATE VIRTUAL TABLE temp.drivelan_teste_trigram USING fts5(a, tokenize='trigram')"
        )
    except sqlite3.Error:
        return False
    conexao.execute("DROP TABLE temp.drivelan_teste_trigram")
    return True


def busca_fts_disponivel(conexao: sqlite3.Connection) -> bool:
    """Indica se a busca por nome da auditoria usa FTS5 (senão, `LIKE`; Fase 9)."""
    linha = conexao.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (TABELA_BUSCA,)
    ).fetchone()
    return linha is not None


# ------------------------------------------------------------------ cópias de segurança


def caminho_copia(caminho_banco: Path, versao: int) -> Path:
    return caminho_banco.with_name(f"{caminho_banco.name}{PREFIXO_COPIA}{versao:04d}")


def listar_copias(caminho_banco: Path) -> list[Path]:
    """Cópias `drivelan.db.antes-NNNN`, da mais antiga para a mais recente (pela versão)."""
    padrao = re.compile(re.escape(caminho_banco.name + PREFIXO_COPIA) + r"(\d{4,})$")
    copias: list[tuple[int, Path]] = []
    for item in caminho_banco.parent.iterdir():
        encontrado = padrao.match(item.name)
        if encontrado is not None and item.is_file():
            copias.append((int(encontrado[1]), item))
    return [caminho for _, caminho in sorted(copias)]


def copiar_banco(conexao: sqlite3.Connection, caminho_banco: Path, versao: int) -> Path:
    """Copia o banco (API de backup do SQLite, coerente com o WAL) antes da migration `versao`."""
    destino = caminho_copia(caminho_banco, versao)
    temporario = destino.with_name(destino.name + ".tmp")
    temporario.unlink(missing_ok=True)
    descritor = os.open(temporario, os.O_WRONLY | os.O_CREAT | os.O_EXCL, MODO_ARQUIVO_BANCO)
    os.close(descritor)
    try:
        copia = sqlite3.connect(temporario)
        try:
            conexao.backup(copia)
        finally:
            copia.close()
        os.replace(temporario, destino)
    except BaseException:
        temporario.unlink(missing_ok=True)
        raise
    for antiga in listar_copias(caminho_banco)[:-COPIAS_MANTIDAS]:
        antiga.unlink(missing_ok=True)
    return destino


# ------------------------------------------------------------------ execução


def versoes_aplicadas(conexao: sqlite3.Connection) -> dict[int, str]:
    """Versões registradas e seus checksums; vazio quando o banco é novo."""
    existe = conexao.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migracoes'"
    ).fetchone()
    if existe is None:
        return {}
    linhas = conexao.execute("SELECT versao, checksum FROM schema_migracoes ORDER BY versao")
    return {int(versao): str(checksum) for versao, checksum in linhas}


def _conferir_aplicadas(
    aplicadas: dict[int, str], disponiveis: dict[int, Migracao], log: LogErros
) -> None:
    for versao, checksum in aplicadas.items():
        migracao = disponiveis.get(versao)
        if migracao is None:
            log.erro(
                ORIGEM_LOG,
                "Migration registrada no banco não existe no pacote",
                {"versao": versao},
            )
            raise MigracaoDesconhecida(versao)
        if migracao.checksum != checksum:
            log.erro(
                ORIGEM_LOG,
                "Migration já aplicada foi alterada; nada foi executado",
                {"versao": versao, "nome": migracao.nome},
            )
            raise MigracaoAlterada(versao)


def _aplicar(
    conexao: sqlite3.Connection,
    migracao: Migracao,
    comandos: Iterable[str],
    relogio: Callable[[], datetime],
) -> None:
    with transacao(conexao):
        for comando in comandos:
            conexao.execute(comando)
        conexao.execute(
            "INSERT INTO schema_migracoes (versao, nome, checksum, aplicada_em) "
            "VALUES (?, ?, ?, ?)",
            (migracao.versao, migracao.nome, migracao.checksum, formatar_data_iso(relogio())),
        )


def executar_migracoes(
    conexao: sqlite3.Connection,
    caminho_banco: Path,
    log: LogErros,
    migracoes: Sequence[Migracao] | None = None,
    *,
    relogio: Callable[[], datetime] = agora_utc,
) -> list[int]:
    """Aplica as migrations pendentes e devolve as versões aplicadas (FSD 11.3).

    Deve rodar na conexão de escrita. Em qualquer erro, registra no log e levanta uma subclasse
    de `ErroMigracao`; as migrations já concluídas continuam aplicadas e nada fica pela metade.
    """
    try:
        lista = carregar_migracoes() if migracoes is None else list(migracoes)
    except MigracaoInvalida as erro:
        log.erro(ORIGEM_LOG, "Arquivo de migration inválido", excecao=erro)
        raise
    disponiveis = {migracao.versao: migracao for migracao in lista}
    aplicadas = versoes_aplicadas(conexao)
    _conferir_aplicadas(aplicadas, disponiveis, log)

    pendentes = [m for m in lista if m.versao not in aplicadas]
    if not pendentes:
        return []

    if aplicadas:
        try:
            copiar_banco(conexao, caminho_banco, pendentes[0].versao)
        except (OSError, sqlite3.Error) as erro:
            log.erro(
                ORIGEM_LOG,
                "Falha ao copiar o banco antes das migrations",
                {"versao": pendentes[0].versao},
                erro,
            )
            raise FalhaMigracao(pendentes[0].versao) from erro

    trigram = suporta_trigram(conexao)
    aplicadas_agora: list[int] = []
    for migracao in pendentes:
        sql = migracao.sql if trigram else remover_bloco_trigram(migracao.sql)
        try:
            _aplicar(conexao, migracao, dividir_comandos(sql), relogio)
        except (sqlite3.Error, MigracaoInvalida) as erro:
            log.erro(
                ORIGEM_LOG,
                "Falha ao aplicar migration; a transação foi desfeita",
                {"versao": migracao.versao, "nome": migracao.nome},
                erro,
            )
            raise FalhaMigracao(migracao.versao) from erro
        aplicadas_agora.append(migracao.versao)
    return aplicadas_agora
