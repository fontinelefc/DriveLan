"""Log diário de erros em arquivo, contingência e retenção (FSD 19.1).

Cada evento vira uma linha UTF-8 em `<logs>/AAAA-MM/AAAA-MM-DD.log` (data local do evento):

    2026-11-12T10:15:03.120-03:00 | ERRO | servico.rede.anuncio_mdns | mensagem | chave=valor

seguida do rastreamento da pilha indentado, quando houver. Como o arquivo é escolhido pela data
de cada evento, a troca de dia (rotação diária) acontece sozinha.

Segurança (FSD 19.1.1 e 24.5): PINs, tokens, chave e conteúdo de arquivos **nunca** podem ir para
o log. As mensagens são textos fixos escritos no código; valores variáveis vão no contexto, e
chaves de contexto com nomes sensíveis (`pin`, `token`, `chave`...) têm o valor omitido. A pilha
é gravada sem variáveis locais.

Contingência (FSD 19.1.5): se a gravação falhar, o serviço não para. Os últimos 500 eventos ficam
num buffer em memória, cada evento também é escrito na saída de erro padrão (capturada pelo
journald no Linux) e a gravação é tentada de novo a cada 60 segundos; quando volta a funcionar, o
buffer é despejado nos arquivos.

A classe é segura para uso simultâneo pelo laço `asyncio`, pela thread do banco e pelo pool de
threads de disco.
"""

import calendar
import os
import re
import secrets
import sys
import threading
import time
import traceback
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import TextIO

from drivelan.comum.diretorios import criar_diretorio_privado

LIMITE_BUFFER_CONTINGENCIA = 500
"""Eventos guardados em memória enquanto a gravação em arquivo falha (FSD 19.1.5)."""

INTERVALO_NOVA_TENTATIVA = 60.0
"""Segundos entre as tentativas de voltar a gravar em arquivo (FSD 19.1.5)."""

MESES_RETENCAO = 3
"""Arquivos com data anterior a 3 meses são apagados pela tarefa diária (FSD 19.1.6)."""

TAMANHO_CODIGO_LOG = 8
"""Caracteres do código curto de erro inesperado exibido ao usuário (FSD 19.1.4)."""

VALOR_OMITIDO = "[omitido]"

# Partes de nomes de chaves de contexto que indicam dado sensível (FSD 24.5).
_PARTES_SENSIVEIS = ("pin", "token", "chave", "senha", "sessao", "segredo", "conteudo")

_INDENTACAO_PILHA = "    "
_RE_ARQUIVO_DIA = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.log$")
_RE_PASTA_MES = re.compile(r"^(\d{4})-(\d{2})$")
_MODO_ARQUIVO = 0o600
_O_BINARIO = getattr(os, "O_BINARY", 0)  # só existe no Windows


class NivelLog(StrEnum):
    """Níveis do log de erros (FSD 19.1.2). `AVISO` só para configuração inválida."""

    ERRO = "ERRO"
    CRITICO = "CRITICO"
    AVISO = "AVISO"


def origem_de(nome_modulo: str) -> str:
    """Origem do evento a partir do `__name__` (`drivelan.servico.rede.x` → `servico.rede.x`)."""
    prefixo = "drivelan."
    return nome_modulo.removeprefix(prefixo) if nome_modulo.startswith(prefixo) else nome_modulo


def gerar_codigo_log() -> str:
    """Código curto aleatório de 8 hexadecimais maiúsculos (ex.: `7F3A91C2`, FSD 19.1.4)."""
    return secrets.token_hex(TAMANHO_CODIGO_LOG // 2).upper()


def chave_sensivel(chave: str) -> bool:
    """Indica se o nome da chave de contexto sugere um segredo que não pode ir para o log."""
    minuscula = chave.casefold()
    return any(parte in minuscula for parte in _PARTES_SENSIVEIS)


def _escapar(texto: str) -> str:
    """Impede que um valor quebre a linha ou crie campos falsos (injeção de linhas no log)."""
    return (
        texto.replace("\\", "\\\\")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        .replace("|", "\\|")
    )


def _formatar_contexto(contexto: Mapping[str, object]) -> str:
    """`chave=valor` separados por espaço, com segredos omitidos e valores escapados."""
    partes: list[str] = []
    for chave, valor in contexto.items():
        texto = _escapar(VALOR_OMITIDO if chave_sensivel(chave) else str(valor))
        if texto == "" or any(caractere in texto for caractere in ' ="'):
            texto = '"' + texto.replace('"', '\\"') + '"'
        partes.append(f"{_escapar(chave)}={texto}")
    return " ".join(partes)


def _formatar_pilha(excecao: BaseException) -> str:
    """Rastreamento da pilha (sem variáveis locais), indentado em cada linha."""
    texto = "".join(traceback.format_exception(excecao)).rstrip("\n")
    return "\n".join(_INDENTACAO_PILHA + linha for linha in texto.splitlines())


def formatar_evento(
    momento: datetime,
    nivel: NivelLog,
    origem: str,
    mensagem: str,
    contexto: Mapping[str, object] | None = None,
    excecao: BaseException | None = None,
) -> str:
    """Monta o texto de um evento no formato da seção 19.1.2 (sem a quebra de linha final)."""
    if momento.tzinfo is None:
        raise ValueError("o momento do evento precisa ter fuso horário")
    campos = [
        momento.isoformat(timespec="milliseconds"),
        nivel.value,
        _escapar(origem),
        _escapar(mensagem),
    ]
    if contexto:
        campos.append(_formatar_contexto(contexto))
    texto = " | ".join(campos)
    if excecao is not None:
        texto += "\n" + _formatar_pilha(excecao)
    return texto


def caminho_do_dia(pasta_logs: Path, dia: date) -> Path:
    """`<logs>/AAAA-MM/AAAA-MM-DD.log` (FSD 19.1.2)."""
    return pasta_logs / f"{dia:%Y-%m}" / f"{dia:%Y-%m-%d}.log"


def _hora_local() -> datetime:
    return datetime.now().astimezone()


@dataclass(frozen=True, slots=True)
class _Evento:
    dia: date
    texto: str


@dataclass(frozen=True, slots=True)
class EstadoContingencia:
    """Situação da contingência, para o aviso da aba Logs de erros (FSD 12.16 e 19.1.5)."""

    falha_desde: datetime | None
    """Hora local da primeira falha não resolvida; `None` se a gravação está normal."""
    eventos: list[str]
    """Eventos guardados em memória, do mais antigo ao mais recente."""

    @property
    def em_contingencia(self) -> bool:
        return self.falha_desde is not None


class LogErros:
    """Log de erros do serviço (FSD 19.1)."""

    def __init__(
        self,
        pasta_logs: Path,
        *,
        ativo: bool = True,
        relogio: Callable[[], datetime] = _hora_local,
        relogio_monotonico: Callable[[], float] = time.monotonic,
        saida_erro: TextIO | None = None,
    ) -> None:
        self._pasta = pasta_logs
        self._ativo = ativo
        self._relogio = relogio
        self._monotonico = relogio_monotonico
        self._saida_erro = saida_erro
        self._trava = threading.Lock()
        self._buffer: deque[_Evento] = deque(maxlen=LIMITE_BUFFER_CONTINGENCIA)
        self._falha_desde: datetime | None = None
        self._ultima_tentativa = 0.0

    # ------------------------------------------------------------ configuração

    @property
    def pasta(self) -> Path:
        return self._pasta

    @property
    def ativo(self) -> bool:
        return self._ativo

    def definir_ativo(self, ativo: bool) -> None:
        """Liga ou desliga o log (`log.ativo`, FSD 19.1.3). Desligado, nada é gravado."""
        with self._trava:
            self._ativo = ativo
            if not ativo:
                # Nada é gravado com o log desligado, nem o que estava pendente.
                self._buffer.clear()
                self._falha_desde = None

    # ------------------------------------------------------------ registro

    def registrar(
        self,
        nivel: NivelLog,
        origem: str,
        mensagem: str,
        contexto: Mapping[str, object] | None = None,
        excecao: BaseException | None = None,
    ) -> None:
        """Registra um evento. Nunca levanta exceção por falha de gravação."""
        with self._trava:
            if not self._ativo:
                return
            momento = self._relogio()
            evento = _Evento(
                momento.date(),
                formatar_evento(momento, nivel, origem, mensagem, contexto, excecao),
            )
            if self._falha_desde is None:
                try:
                    self._gravar([evento])
                except OSError:
                    self._entrar_em_contingencia(momento)
                else:
                    return
            self._guardar_em_memoria(evento)
            if self._monotonico() - self._ultima_tentativa >= INTERVALO_NOVA_TENTATIVA:
                self._tentar_despejar()

    def erro(
        self,
        origem: str,
        mensagem: str,
        contexto: Mapping[str, object] | None = None,
        excecao: BaseException | None = None,
    ) -> None:
        self.registrar(NivelLog.ERRO, origem, mensagem, contexto, excecao)

    def critico(
        self,
        origem: str,
        mensagem: str,
        contexto: Mapping[str, object] | None = None,
        excecao: BaseException | None = None,
    ) -> None:
        self.registrar(NivelLog.CRITICO, origem, mensagem, contexto, excecao)

    def aviso(
        self, origem: str, mensagem: str, contexto: Mapping[str, object] | None = None
    ) -> None:
        """`AVISO` é usado só para valores de configuração inválidos (FSD 19.1.2)."""
        self.registrar(NivelLog.AVISO, origem, mensagem, contexto)

    def erro_inesperado(
        self,
        origem: str,
        excecao: BaseException,
        contexto: Mapping[str, object] | None = None,
        mensagem: str = "Erro inesperado",
    ) -> str:
        """Registra um erro inesperado e devolve o código curto mostrado ao usuário (19.1.4).

        Com o log desligado nada é gravado, mas o código é gerado e devolvido do mesmo jeito,
        para a mensagem genérica ao usuário (`mensagem_erro_interno`).
        """
        codigo = gerar_codigo_log()
        self.registrar(
            NivelLog.ERRO, origem, mensagem, {"codigo": codigo, **(contexto or {})}, excecao
        )
        return codigo

    # ------------------------------------------------------------ contingência

    def tentar_novamente(self) -> bool:
        """Tenta despejar o buffer agora (chamado pelo agendador). Devolve se a gravação voltou."""
        with self._trava:
            if self._falha_desde is None:
                return True
            return self._tentar_despejar()

    def estado_contingencia(self) -> EstadoContingencia:
        with self._trava:
            return EstadoContingencia(self._falha_desde, [e.texto for e in self._buffer])

    def _entrar_em_contingencia(self, momento: datetime) -> None:
        self._falha_desde = momento
        self._ultima_tentativa = self._monotonico()
        self._escrever_saida_erro(
            "drivelan-service: falha ao gravar o log em arquivo; "
            "os registros estão sendo mantidos temporariamente na memória."
        )

    def _guardar_em_memoria(self, evento: _Evento) -> None:
        self._buffer.append(evento)
        self._escrever_saida_erro(evento.texto)

    def _tentar_despejar(self) -> bool:
        self._ultima_tentativa = self._monotonico()
        # Grava em blocos consecutivos do mesmo dia e tira cada bloco do buffer assim que ele é
        # gravado: uma falha no meio do despejo não duplica linhas na tentativa seguinte.
        while self._buffer:
            dia = self._buffer[0].dia
            bloco: list[_Evento] = []
            for evento in self._buffer:
                if evento.dia != dia:
                    break
                bloco.append(evento)
            try:
                self._gravar(bloco)
            except OSError:
                return False
            for _ in bloco:
                self._buffer.popleft()
        self._falha_desde = None
        return True

    def _escrever_saida_erro(self, texto: str) -> None:
        saida = self._saida_erro if self._saida_erro is not None else sys.stderr
        try:
            saida.write(texto + "\n")
            saida.flush()
        except (OSError, ValueError):
            pass  # sem saída de erro disponível: o evento continua no buffer

    # ------------------------------------------------------------ gravação

    def _gravar(self, eventos: Iterable[_Evento]) -> None:
        """Grava os eventos em ordem, cada um no arquivo do seu dia. Levanta `OSError`."""
        por_dia: dict[date, list[str]] = {}
        for evento in eventos:
            por_dia.setdefault(evento.dia, []).append(evento.texto)
        for dia, textos in por_dia.items():
            caminho = caminho_do_dia(self._pasta, dia)
            # As duas pastas são criadas uma a uma: com `parents=True`, só a última recebe 0700.
            criar_diretorio_privado(self._pasta)
            criar_diretorio_privado(caminho.parent)
            conteudo = "".join(texto + "\n" for texto in textos).encode("utf-8")
            descritor = os.open(
                caminho, os.O_WRONLY | os.O_APPEND | os.O_CREAT | _O_BINARIO, _MODO_ARQUIVO
            )
            try:
                escrito = 0
                while escrito < len(conteudo):
                    escrito += os.write(descritor, conteudo[escrito:])
            finally:
                os.close(descritor)


# ---------------------------------------------------------------- retenção (FSD 19.1.6)


def _subtrair_meses(dia: date, meses: int) -> date:
    """Mesma data `meses` meses antes; o dia é ajustado ao fim do mês (31/05 - 3 → 28 ou 29/02)."""
    indice = dia.year * 12 + (dia.month - 1) - meses
    ano, mes_zero = divmod(indice, 12)
    mes = mes_zero + 1
    return date(ano, mes, min(dia.day, calendar.monthrange(ano, mes)[1]))


def data_limite_retencao(hoje: date) -> date:
    """Arquivos com data **anterior** a esta são apagados."""
    return _subtrair_meses(hoje, MESES_RETENCAO)


def _data_do_arquivo(pasta_mes: str, nome: str) -> date | None:
    """Data de um arquivo de log, se o nome e a pasta seguirem o padrão `AAAA-MM/AAAA-MM-DD.log`."""
    encontrado = _RE_ARQUIVO_DIA.match(nome)
    if encontrado is None:
        return None
    ano, mes, dia = (int(parte) for parte in encontrado.groups())
    if pasta_mes != f"{ano:04d}-{mes:02d}":
        return None
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def aplicar_retencao(pasta_logs: Path, hoje: date) -> int:
    """Apaga logs com data anterior a 3 meses e remove pastas de mês vazias (FSD 19.1.6).

    Só toca em arquivos com o padrão do log; qualquer outro arquivo é preservado. Devolve quantos
    arquivos foram apagados. Usada pela tarefa diária do agendador.
    """
    limite = data_limite_retencao(hoje)
    apagados = 0
    if not pasta_logs.is_dir():
        return 0
    for pasta_mes in sorted(pasta_logs.iterdir()):
        if not _RE_PASTA_MES.match(pasta_mes.name) or not pasta_mes.is_dir():
            continue
        if pasta_mes.is_symlink():
            continue
        for arquivo in sorted(pasta_mes.iterdir()):
            data_arquivo = _data_do_arquivo(pasta_mes.name, arquivo.name)
            if data_arquivo is None or data_arquivo >= limite:
                continue
            if arquivo.is_file() and not arquivo.is_symlink():
                arquivo.unlink()
                apagados += 1
        if not any(pasta_mes.iterdir()):
            pasta_mes.rmdir()
    return apagados
