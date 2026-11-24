"""Leitura e gravação do `drivelan.toml` (FSD 20.2).

- Leitura só pelo serviço, com `tomllib`; gravação só pelo serviço, com `tomli-w`, de forma
  atômica (arquivo temporário na mesma pasta e substituição), preservando as demais chaves.
- Arquivo ausente: é criado com os padrões. Arquivo ilegível: usa os padrões, registra `AVISO` e
  **não** é sobrescrito. Valor inválido: usa o padrão daquela chave e registra `AVISO`.
- Não existe arquivo `.env` (FSD 3.4). O arquivo não contém credenciais nem segredos.

As funções de leitura devolvem os avisos em vez de gravá-los, porque na inicialização o log é
ligado antes da leitura da configuração (FSD 6.1) e só depois se sabe o valor de `log.ativo`.
"""

import os
import tempfile
import time
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli_w

from drivelan.comum.diretorios import criar_diretorio_privado
from drivelan.comum.protocolo import PORTA_PADRAO
from drivelan.servico.log_erros import LogErros, origem_de

ORIGEM = origem_de(__name__)

PORTA_MINIMA = 1024
PORTA_MAXIMA = 65535
INTERVALO_VERIFICACAO = 60.0
"""Segundos entre as verificações da data de modificação do arquivo (FSD 19.1.3)."""

_MODO_ARQUIVO = 0o600

# Conteúdo gravado quando o arquivo não existe: os padrões da seção 20.2, com os comentários.
MODELO_PADRAO = f"""\
# Configuração técnica do DriveLan (FSD 20.2). Não contém credenciais nem segredos.

[log]
ativo = true          # liga ou desliga o log de erros

[rede]
interface = ""        # vazio = placa principal automática; ou o nome da placa
porta = {PORTA_PADRAO}         # porta TCP (protocolo) e UDP (descoberta por broadcast)
"""


@dataclass(frozen=True, slots=True)
class Configuracao:
    """Valores em uso, já validados (FSD 20.2)."""

    log_ativo: bool = True
    rede_interface: str = ""
    """Vazio = placa principal automática (a existência da placa é verificada na Fase 10)."""
    rede_porta: int = PORTA_PADRAO


@dataclass(frozen=True, slots=True)
class ResultadoLeitura:
    """Configuração lida e os avisos que devem ir para o log com o nível `AVISO`."""

    configuracao: Configuracao
    avisos: list[str] = field(default_factory=list)
    legivel: bool = True
    """`False` quando o arquivo existe mas não pôde ser lido (nesse caso nunca é sobrescrito)."""
    criado: bool = False
    """`True` quando o arquivo não existia e foi criado com os padrões."""


class ConfiguracaoIlegivel(Exception):
    """O arquivo existe mas não pode ser lido; por isso não pode ser sobrescrito (FSD 20.2)."""


# ---------------------------------------------------------------- leitura


def _ler_toml(caminho: Path) -> dict[str, Any]:
    """Lê e interpreta o arquivo. Levanta `FileNotFoundError` ou `ConfiguracaoIlegivel`."""
    try:
        bruto = caminho.read_bytes()
    except FileNotFoundError:
        raise
    except OSError as erro:
        raise ConfiguracaoIlegivel(
            f"não foi possível abrir o arquivo ({type(erro).__name__})"
        ) from erro
    try:
        return tomllib.loads(bruto.decode("utf-8"))
    except UnicodeDecodeError as erro:
        raise ConfiguracaoIlegivel("o arquivo não está em UTF-8") from erro
    except tomllib.TOMLDecodeError as erro:
        raise ConfiguracaoIlegivel(f"sintaxe TOML inválida ({erro})") from erro


def _secao(dados: Mapping[str, Any], nome: str, avisos: list[str]) -> Mapping[str, Any]:
    valor = dados.get(nome, {})
    if isinstance(valor, dict):
        return valor
    avisos.append(f"Seção [{nome}] inválida no arquivo de configuração; usando os valores padrão.")
    return {}


def _aviso_valor(chave: str, padrao: object) -> str:
    # O valor inválido não é repetido no log: só a chave e o padrão adotado.
    return f"Valor inválido para {chave} no arquivo de configuração; usando o padrão {padrao!r}."


def _tem_caractere_de_controle(texto: str) -> bool:
    return any(ord(caractere) < 32 or ord(caractere) == 127 for caractere in texto)


def validar(dados: Mapping[str, Any]) -> tuple[Configuracao, list[str]]:
    """Aplica as validações e os fallbacks da tabela da seção 20.2."""
    padrao = Configuracao()
    avisos: list[str] = []
    log = _secao(dados, "log", avisos)
    rede = _secao(dados, "rede", avisos)

    ativo = log.get("ativo", padrao.log_ativo)
    if not isinstance(ativo, bool):
        avisos.append(_aviso_valor("log.ativo", padrao.log_ativo))
        ativo = padrao.log_ativo

    interface = rede.get("interface", padrao.rede_interface)
    if not isinstance(interface, str) or _tem_caractere_de_controle(interface):
        avisos.append(_aviso_valor("rede.interface", padrao.rede_interface))
        interface = padrao.rede_interface

    porta = rede.get("porta", padrao.rede_porta)
    # `bool` é subclasse de `int` em Python: `porta = true` precisa ser recusado.
    if (
        isinstance(porta, bool)
        or not isinstance(porta, int)
        or not PORTA_MINIMA <= porta <= PORTA_MAXIMA
    ):
        avisos.append(_aviso_valor("rede.porta", padrao.rede_porta))
        porta = padrao.rede_porta

    return Configuracao(ativo, interface, porta), avisos


def carregar_configuracao(caminho: Path) -> ResultadoLeitura:
    """Lê o `drivelan.toml`, criando-o com os padrões se não existir (FSD 20.2)."""
    try:
        dados = _ler_toml(caminho)
    except FileNotFoundError:
        try:
            criar_diretorio_privado(caminho.parent)
            gravar_atomico(caminho, MODELO_PADRAO.encode("utf-8"))
        except OSError as erro:
            aviso = (
                "Não foi possível criar o arquivo de configuração "
                f"({type(erro).__name__}); usando os valores padrão."
            )
            return ResultadoLeitura(Configuracao(), [aviso])
        return ResultadoLeitura(Configuracao(), criado=True)
    except ConfiguracaoIlegivel as erro:
        aviso = f"Arquivo de configuração ilegível: {erro}; usando os valores padrão."
        return ResultadoLeitura(Configuracao(), [aviso], legivel=False)
    configuracao, avisos = validar(dados)
    return ResultadoLeitura(configuracao, avisos)


def registrar_avisos(log: LogErros, resultado: ResultadoLeitura) -> None:
    """Grava os avisos da leitura no log com o nível `AVISO` (FSD 19.1.1)."""
    for aviso in resultado.avisos:
        log.aviso(ORIGEM, aviso)


# ---------------------------------------------------------------- gravação


def gravar_atomico(caminho: Path, conteudo: bytes) -> None:
    """Grava num temporário da mesma pasta e substitui o arquivo de uma vez.

    Em qualquer falha, o arquivo original continua intacto e o temporário é removido.
    """
    descritor, nome_temporario = _criar_temporario(caminho)
    temporario = Path(nome_temporario)
    try:
        with os.fdopen(descritor, "wb") as arquivo:
            arquivo.write(conteudo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
    except BaseException:
        temporario.unlink(missing_ok=True)
        raise
    _sincronizar_pasta(caminho.parent)


def _criar_temporario(caminho: Path) -> tuple[int, str]:
    # `mkstemp` cria o arquivo com modo 0600, acessível só ao serviço.
    return tempfile.mkstemp(prefix=f".{caminho.name}.", suffix=".tmp", dir=caminho.parent)


def _sincronizar_pasta(pasta: Path) -> None:
    """Garante no POSIX que a troca de nome sobreviva a uma queda de energia."""
    if os.name != "posix":
        return
    descritor = os.open(pasta, os.O_RDONLY)
    try:
        os.fsync(descritor)
    finally:
        os.close(descritor)


def _mesclar(base: dict[str, Any], alteracoes: Mapping[str, Any]) -> dict[str, Any]:
    resultado = dict(base)
    for chave, valor in alteracoes.items():
        atual = resultado.get(chave)
        if isinstance(valor, Mapping) and isinstance(atual, dict):
            resultado[chave] = _mesclar(atual, valor)
        else:
            resultado[chave] = dict(valor) if isinstance(valor, Mapping) else valor
    return resultado


def gravar_valores(caminho: Path, alteracoes: Mapping[str, Any]) -> None:
    """Altera chaves do arquivo preservando as demais (ex.: `{"rede": {"interface": "eth0"}}`).

    Usada pela troca de placa de rede (fluxo 13.27). Se o arquivo existir e estiver ilegível,
    levanta `ConfiguracaoIlegivel` e não o sobrescreve. Os comentários do arquivo não são
    preservados (o `tomli-w` grava só os dados).
    """
    try:
        dados = _ler_toml(caminho)
    except FileNotFoundError:
        criar_diretorio_privado(caminho.parent)
        dados = tomllib.loads(MODELO_PADRAO)
    gravar_atomico(caminho, tomli_w.dumps(_mesclar(dados, alteracoes)).encode("utf-8"))


# ---------------------------------------------------------------- recarga (FSD 19.1.3)


class MonitorConfiguracao:
    """Relê o arquivo quando a data de modificação muda, no máximo a cada 60 segundos.

    O agendador do serviço chama `verificar()` periodicamente; ao detectar mudança, o novo valor
    de `log.ativo` é aplicado ao log e os avisos são registrados.
    """

    def __init__(
        self,
        caminho: Path,
        log: LogErros,
        *,
        relogio: Callable[[], float] = time.monotonic,
        intervalo: float = INTERVALO_VERIFICACAO,
    ) -> None:
        self._caminho = caminho
        self._log = log
        self._relogio = relogio
        self._intervalo = intervalo
        self._ultima_verificacao: float | None = None
        self._marca = self._marca_atual()

    def _marca_atual(self) -> tuple[int, int] | None:
        """Data de modificação e tamanho do arquivo; `None` se não puder ser consultado."""
        try:
            estado = self._caminho.stat()
        except OSError:
            return None
        return (estado.st_mtime_ns, estado.st_size)

    def carregar(self) -> Configuracao:
        """Leitura inicial: lê, aplica `log.ativo` e registra os avisos (FSD 6.1, etapa 2)."""
        resultado = carregar_configuracao(self._caminho)
        self._marca = self._marca_atual()
        self._ultima_verificacao = self._relogio()
        self._aplicar(resultado)
        return resultado.configuracao

    def verificar(self) -> Configuracao | None:
        """Devolve a nova configuração se o arquivo mudou; senão `None`."""
        agora = self._relogio()
        if (
            self._ultima_verificacao is not None
            and agora - self._ultima_verificacao < self._intervalo
        ):
            return None
        self._ultima_verificacao = agora
        marca = self._marca_atual()
        if marca == self._marca:
            return None
        resultado = carregar_configuracao(self._caminho)
        self._marca = self._marca_atual()
        self._aplicar(resultado)
        return resultado.configuracao

    def _aplicar(self, resultado: ResultadoLeitura) -> None:
        # Primeiro liga ou desliga: com o log desligado, nem os avisos são gravados.
        self._log.definir_ativo(resultado.configuracao.log_ativo)
        registrar_avisos(self._log, resultado)
