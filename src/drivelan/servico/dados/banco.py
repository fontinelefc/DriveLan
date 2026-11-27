"""Conexões SQLite, PRAGMAs e transações do serviço (FSD 5.3, 11.1 e 11.4).

O banco é gravado **somente** pelo serviço, por **uma única conexão de escrita** que vive numa
thread dedicada. Leituras pesadas (auditoria) usam uma segunda conexão, somente leitura, em outra
thread própria. Assim o laço `asyncio` nunca espera pelo disco: as funções de acesso são enviadas
às threads e o resultado volta como `Future`.

Toda conexão é aberta com os PRAGMAs da seção 11.1 e com controle explícito de transação
(`isolation_level=None`): gravações em mais de uma tabela usam `transacao`, que abre
`BEGIN IMMEDIATE` e desfaz tudo em caso de erro.

O arquivo do banco é criado com modo 0600 dentro da pasta de dados (0700), FSD 5.6.
"""

import asyncio
import os
import sqlite3
from collections.abc import Callable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

from drivelan.comum.diretorios import criar_diretorio_privado
from drivelan.servico.log_erros import LogErros

# PRAGMAs aplicados na abertura de toda conexão (FSD 11.1). Os valores são fixos no código.
PRAGMAS: tuple[tuple[str, str], ...] = (
    ("foreign_keys", "ON"),
    ("journal_mode", "WAL"),
    ("synchronous", "NORMAL"),
    ("busy_timeout", "5000"),
)

MODO_ARQUIVO_BANCO = 0o600

type FuncaoBanco[T] = Callable[[sqlite3.Connection], T]


class ErroBanco(Exception):
    """Falha ao abrir ou usar o banco de dados."""


def _aplicar_pragmas(conexao: sqlite3.Connection, *, somente_leitura: bool) -> None:
    for nome, valor in PRAGMAS:
        # Nome e valor vêm da constante acima, nunca de entrada externa.
        resultado = conexao.execute(f"PRAGMA {nome} = {valor}").fetchone()
        if nome == "journal_mode" and not somente_leitura:
            modo = str(resultado[0]).lower() if resultado else ""
            if modo != "wal":
                raise ErroBanco("o banco não aceitou o modo WAL")


def _criar_arquivo_privado(caminho: Path) -> None:
    """Cria o arquivo vazio do banco com modo 0600, se ainda não existir."""
    try:
        descritor = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_EXCL, MODO_ARQUIVO_BANCO)
    except FileExistsError:
        return
    os.close(descritor)


def abrir_conexao(caminho: Path, *, somente_leitura: bool = False) -> sqlite3.Connection:
    """Abre uma conexão com os PRAGMAs da seção 11.1.

    A conexão de escrita cria a pasta de dados (0700) e o arquivo (0600) quando não existem. A
    somente leitura exige que o banco já exista e recusa qualquer gravação.
    """
    if somente_leitura:
        if not caminho.is_file():
            raise ErroBanco("o banco ainda não existe")
        conexao = sqlite3.connect(
            f"{caminho.resolve().as_uri()}?mode=ro",
            uri=True,
            isolation_level=None,
            check_same_thread=True,
        )
    else:
        criar_diretorio_privado(caminho.parent)
        _criar_arquivo_privado(caminho)
        if os.name == "posix":
            caminho.chmod(MODO_ARQUIVO_BANCO)
        conexao = sqlite3.connect(caminho, isolation_level=None, check_same_thread=True)
    try:
        _aplicar_pragmas(conexao, somente_leitura=somente_leitura)
    except BaseException:
        conexao.close()
        raise
    return conexao


@contextmanager
def transacao(conexao: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Executa o bloco numa transação `BEGIN IMMEDIATE`; qualquer exceção desfaz tudo (11.4)."""
    if conexao.in_transaction:
        raise ErroBanco("já existe uma transação aberta nesta conexão")
    conexao.execute("BEGIN IMMEDIATE")
    try:
        yield conexao
    except BaseException:
        conexao.execute("ROLLBACK")
        raise
    else:
        conexao.execute("COMMIT")


class _ConexaoEmThread:
    """Uma conexão SQLite que só é usada dentro da sua própria thread."""

    def __init__(self, nome_thread: str) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=nome_thread)
        self._conexao: sqlite3.Connection | None = None

    def abrir(self, caminho: Path, *, somente_leitura: bool) -> None:
        def _abrir() -> None:
            self._conexao = abrir_conexao(caminho, somente_leitura=somente_leitura)

        self._executor.submit(_abrir).result()

    def submeter[T](self, funcao: FuncaoBanco[T]) -> "Future[T]":
        def _executar() -> T:
            if self._conexao is None:
                raise ErroBanco("a conexão está fechada")
            return funcao(self._conexao)

        return self._executor.submit(_executar)

    def fechar(self) -> None:
        def _fechar() -> None:
            if self._conexao is not None:
                self._conexao.close()
                self._conexao = None

        try:
            self._executor.submit(_fechar).result()
        except RuntimeError:
            return  # executor já encerrado: nada a fechar
        self._executor.shutdown(wait=True)


class BancoDados:
    """Banco do serviço: escrita única numa thread dedicada e leitura numa segunda (FSD 5.3).

    Use `BancoDados.abrir(...)`, que também executa as migrations pendentes antes de liberar o
    banco (FSD 6.1, etapa 3). Os métodos assíncronos são para o laço `asyncio`; os `_sincrono`,
    para comandos de linha de comando e testes.
    """

    NOME_THREAD_ESCRITA = "drivelan-banco-escrita"
    NOME_THREAD_LEITURA = "drivelan-banco-leitura"

    def __init__(self, caminho: Path) -> None:
        self._caminho = caminho
        self._escrita = _ConexaoEmThread(self.NOME_THREAD_ESCRITA)
        self._leitura = _ConexaoEmThread(self.NOME_THREAD_LEITURA)
        self._aberto = False

    @property
    def caminho(self) -> Path:
        return self._caminho

    @classmethod
    def abrir(cls, caminho: Path, log: LogErros, *, migrar: bool = True) -> "BancoDados":
        """Abre o banco, executa as migrations (na thread de escrita) e abre a leitura.

        Erros de migration são registrados no log pelo executor e repassados ao chamador, que
        decide a nova tentativa (FSD 11.3: o serviço tenta de novo a cada 30 segundos).
        """
        from drivelan.servico.dados.migracoes import executar_migracoes

        banco = cls(caminho)
        try:
            banco._escrita.abrir(caminho, somente_leitura=False)
            if migrar:
                banco._escrita.submeter(
                    lambda conexao: executar_migracoes(conexao, caminho, log)
                ).result()
            banco._leitura.abrir(caminho, somente_leitura=True)
        except BaseException:
            banco.fechar()
            raise
        banco._aberto = True
        return banco

    # ------------------------------------------------------------ uso síncrono

    def escrever_sincrono[T](self, funcao: FuncaoBanco[T]) -> T:
        """Executa `funcao` na conexão de escrita (sem abrir transação) e espera o resultado."""
        return self._escrita.submeter(funcao).result()

    def gravar_em_transacao_sincrono[T](self, funcao: FuncaoBanco[T]) -> T:
        """Executa `funcao` numa transação da conexão de escrita e espera o resultado."""
        return self._escrita.submeter(_em_transacao(funcao)).result()

    def ler_sincrono[T](self, funcao: FuncaoBanco[T]) -> T:
        """Executa `funcao` na conexão somente leitura e espera o resultado."""
        return self._leitura.submeter(funcao).result()

    # ------------------------------------------------------------ uso assíncrono

    async def escrever[T](self, funcao: FuncaoBanco[T]) -> T:
        return await asyncio.wrap_future(self._escrita.submeter(funcao))

    async def gravar_em_transacao[T](self, funcao: FuncaoBanco[T]) -> T:
        return await asyncio.wrap_future(self._escrita.submeter(_em_transacao(funcao)))

    async def ler[T](self, funcao: FuncaoBanco[T]) -> T:
        return await asyncio.wrap_future(self._leitura.submeter(funcao))

    # ------------------------------------------------------------ encerramento

    def fechar(self) -> None:
        """Fecha as duas conexões nas próprias threads. Pode ser chamado mais de uma vez."""
        self._leitura.fechar()
        self._escrita.fechar()
        self._aberto = False


def _em_transacao[T](funcao: FuncaoBanco[T]) -> FuncaoBanco[T]:
    def _executar(conexao: sqlite3.Connection) -> T:
        with transacao(conexao):
            return funcao(conexao)

    return _executar
