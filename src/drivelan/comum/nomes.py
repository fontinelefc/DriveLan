"""Regra única de nomes de arquivos e pastas (RN-68) e nomes gerados (FSD 21.8).

A RN-68 vale na criação, renomeação, envio e movimentação, em qualquer sistema: um nome
aceito aqui é válido tanto no Windows quanto no Linux. Itens já existentes fora da regra
(colocados direto no disco do dono) são identificados por `nome_compativel` e, na cópia para
o computador, recebem um nome adaptado por `adaptar_nome_para_copia`.
"""

import unicodedata
from collections.abc import Iterable
from enum import StrEnum

from drivelan.comum.diretorios import SistemaOperacional, sistema_atual
from drivelan.comum.i18n import QT_TRANSLATE_NOOP, traduzir

CONTEXTO = "Nomes"

CARACTERES_PROIBIDOS = frozenset('\\/:*?"<>|')
"""Caracteres recusados em qualquer nome (RN-68)."""

NOMES_RESERVADOS = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{n}" for n in range(1, 10)}
    | {f"lpt{n}" for n in range(1, 10)}
)
"""Nomes reservados do Windows, comparados em minúsculas e sem a extensão (RN-68)."""

LIMITE_NOME = 255
"""Máximo de caracteres de um nome (RN-68)."""

LIMITE_CAMINHO = 1024
"""Máximo de caracteres de um caminho relativo (RN-68)."""

NOME_AREA_INTERNA = ".drivelan"
"""Área interna na raiz de cada pasta compartilhada (FSD 21.3)."""

SUBSTITUTO = "_"
"""Caractere usado no nome adaptado para cópia (RN-68)."""


class MotivoNomeInvalido(StrEnum):
    """Motivo da recusa de um nome; `texto` completa "Nome inválido: <motivo>." (FSD 14.2)."""

    VAZIO = "vazio"
    PONTO = "ponto"
    CARACTERE_CONTROLE = "caractere_controle"
    CARACTERE_PROIBIDO = "caractere_proibido"
    FINAL_INVALIDO = "final_invalido"
    RESERVADO = "reservado"
    AREA_INTERNA = "area_interna"
    NOME_LONGO = "nome_longo"
    CAMINHO_LONGO = "caminho_longo"

    @property
    def texto(self) -> str:
        """Descrição do motivo para o usuário, já traduzida."""
        return traduzir(CONTEXTO, _TEXTOS_MOTIVO[self])


_TEXTOS_MOTIVO: dict[MotivoNomeInvalido, str] = {
    MotivoNomeInvalido.VAZIO: QT_TRANSLATE_NOOP("Nomes", "o nome não pode ficar vazio"),
    MotivoNomeInvalido.PONTO: QT_TRANSLATE_NOOP("Nomes", 'o nome não pode ser "." nem ".."'),
    MotivoNomeInvalido.CARACTERE_CONTROLE: QT_TRANSLATE_NOOP(
        "Nomes", "o nome contém caracteres de controle"
    ),
    MotivoNomeInvalido.CARACTERE_PROIBIDO: QT_TRANSLATE_NOOP(
        "Nomes", 'não use os caracteres \\ / : * ? " < > |'
    ),
    MotivoNomeInvalido.FINAL_INVALIDO: QT_TRANSLATE_NOOP(
        "Nomes", "o nome não pode terminar com ponto ou espaço"
    ),
    MotivoNomeInvalido.RESERVADO: QT_TRANSLATE_NOOP("Nomes", "este nome é reservado pelo Windows"),
    MotivoNomeInvalido.AREA_INTERNA: QT_TRANSLATE_NOOP(
        "Nomes", "este nome é reservado para uso interno do DriveLan"
    ),
    MotivoNomeInvalido.NOME_LONGO: QT_TRANSLATE_NOOP(
        "Nomes", "o nome pode ter no máximo 255 caracteres"
    ),
    MotivoNomeInvalido.CAMINHO_LONGO: QT_TRANSLATE_NOOP(
        "Nomes", "o caminho pode ter no máximo 1.024 caracteres"
    ),
}


class NomeInvalido(ValueError):
    """Nome recusado pela RN-68 (código de protocolo `nome_invalido`)."""

    def __init__(self, motivo: MotivoNomeInvalido) -> None:
        super().__init__(motivo.value)
        self.motivo = motivo


# ------------------------------------------------------------------ normalização


def normalizar_nome(nome: str) -> str:
    """Nome em Unicode NFC (RN-68)."""
    return unicodedata.normalize("NFC", nome)


def normalizar_para_comparacao(nome: str) -> str:
    """Chave de comparação sem maiúsculas: NFC + `casefold()` (FSD 11.1, campos `*_normalizado`)."""
    return unicodedata.normalize("NFC", normalizar_nome(nome).casefold())


def nomes_iguais(nome_a: str, nome_b: str) -> bool:
    """Indica se dois nomes são o mesmo item dentro de uma subpasta (RN-68, FSD 21.4 item 6)."""
    return normalizar_para_comparacao(nome_a) == normalizar_para_comparacao(nome_b)


# ------------------------------------------------------------------ validação


def _eh_controle(caractere: str) -> bool:
    return ord(caractere) < 32


def _eh_reservado(nome: str) -> bool:
    """Reservado com ou sem extensão (`con`, `CON.txt`, `com1.tar.gz`)."""
    base = nome.split(".", 1)[0].rstrip(" ")
    return base.casefold() in NOMES_RESERVADOS


def motivo_nome_invalido(nome: str, *, na_raiz: bool = False) -> MotivoNomeInvalido | None:
    """Devolve o motivo pelo qual `nome` viola a RN-68, ou `None` se ele for válido.

    `na_raiz` indica que o item fica na raiz da pasta compartilhada, onde `.drivelan` é proibido.
    """
    nome = normalizar_nome(nome)
    if not nome:
        return MotivoNomeInvalido.VAZIO
    if nome in {".", ".."}:
        return MotivoNomeInvalido.PONTO
    if any(_eh_controle(c) for c in nome):
        return MotivoNomeInvalido.CARACTERE_CONTROLE
    if any(c in CARACTERES_PROIBIDOS for c in nome):
        return MotivoNomeInvalido.CARACTERE_PROIBIDO
    if nome[-1] in {".", " "}:
        return MotivoNomeInvalido.FINAL_INVALIDO
    if _eh_reservado(nome):
        return MotivoNomeInvalido.RESERVADO
    if na_raiz and normalizar_para_comparacao(nome) == NOME_AREA_INTERNA:
        return MotivoNomeInvalido.AREA_INTERNA
    if len(nome) > LIMITE_NOME:
        return MotivoNomeInvalido.NOME_LONGO
    return None


def validar_nome(nome: str, *, na_raiz: bool = False) -> str:
    """Devolve o nome em NFC ou levanta `NomeInvalido` com o motivo (RN-68)."""
    motivo = motivo_nome_invalido(nome, na_raiz=na_raiz)
    if motivo is not None:
        raise NomeInvalido(motivo)
    return normalizar_nome(nome)


def nome_compativel(nome: str, *, na_raiz: bool = False) -> bool:
    """`False` para itens existentes fora da RN-68 ("Nome incompatível com Windows")."""
    return motivo_nome_invalido(nome, na_raiz=na_raiz) is None


def nome_valido_no_sistema(nome: str, sistema: SistemaOperacional) -> bool:
    """Indica se o sistema de destino aceita o nome como está (FSD 21.9).

    No Windows vale a RN-68 completa; no Linux só são impossíveis o nome vazio, `.`, `..`,
    a barra e o caractere nulo.
    """
    if sistema is SistemaOperacional.WINDOWS:
        return nome_compativel(nome)
    return nome not in {"", ".", ".."} and "/" not in nome and "\x00" not in nome


# ------------------------------------------------------------------ nomes gerados


def _separar_extensao(nome: str, *, eh_pasta: bool = False) -> tuple[str, str]:
    """Separa base e extensão (`relatorio.docx` → `relatorio`, `.docx`).

    Pastas não têm extensão, e um ponto inicial não começa extensão (`.bashrc`).
    """
    if eh_pasta:
        return nome, ""
    posicao = nome.rfind(".")
    if posicao <= 0:
        return nome, ""
    return nome[:posicao], nome[posicao:]


def _montar_nome(base: str, sufixo: str, extensao: str) -> str:
    """Junta as partes respeitando 255 caracteres: encurta a base e, se preciso, a extensão."""
    excesso = len(base) + len(sufixo) + len(extensao) - LIMITE_NOME
    if excesso > 0:
        corte = min(excesso, len(base))
        base = base[: len(base) - corte]
        excesso -= corte
    if excesso > 0:
        extensao = extensao[: len(extensao) - excesso]
    nome = base + sufixo + extensao
    # Um corte pode deixar ponto ou espaço no fim, o que a RN-68 não aceita.
    return nome.rstrip(". ") or SUBSTITUTO


def adaptar_nome_para_copia(nome: str, sistema: SistemaOperacional | None = None) -> str:
    """Nome usado ao copiar um item para o computador de destino (RN-68, FSD 21.9).

    Se o destino aceita o nome, ele é mantido. Senão: cada caractere proibido (ou de controle)
    vira `_`, pontos e espaços finais são removidos e nomes reservados recebem `_` no início.
    O arquivo original nunca é alterado; colisões no destino seguem a RN-63.
    """
    nome = normalizar_nome(nome)
    destino = sistema if sistema is not None else sistema_atual()
    if nome_valido_no_sistema(nome, destino):
        return nome
    adaptado = "".join(
        SUBSTITUTO if c in CARACTERES_PROIBIDOS or _eh_controle(c) else c for c in nome
    )
    adaptado = adaptado.rstrip(". ")
    if not adaptado:
        return SUBSTITUTO
    if _eh_reservado(adaptado):
        adaptado = SUBSTITUTO + adaptado
    base, extensao = _separar_extensao(adaptado)
    return _montar_nome(base, "", extensao)


def _chaves(existentes: Iterable[str]) -> set[str]:
    return {normalizar_para_comparacao(n) for n in existentes}


def nome_duplicado(nome: str, existentes: Iterable[str], *, eh_pasta: bool = False) -> str:
    """Primeiro `nome (N).ext` livre, com N a partir de 2 (RN-63 e restauração, FSD 21.8).

    A comparação com `existentes` não diferencia maiúsculas e minúsculas.
    """
    ocupados = _chaves(existentes)
    base, extensao = _separar_extensao(normalizar_nome(nome), eh_pasta=eh_pasta)
    numero = 2
    while True:
        candidato = _montar_nome(base, f" ({numero})", extensao)
        if normalizar_para_comparacao(candidato) not in ocupados:
            return candidato
        numero += 1


def nome_conflito(nome: str, usuario: str, existentes: Iterable[str]) -> str:
    """Nome da cópia de conflito (RN-47, FSD 21.8).

    `nome (conflito joao).ext`; se já existir, `nome (conflito joao 2).ext`, e assim por diante.
    """
    ocupados = _chaves(existentes)
    base, extensao = _separar_extensao(normalizar_nome(nome))
    usuario = normalizar_nome(usuario)
    numero = 1
    while True:
        complemento = "" if numero == 1 else f" {numero}"
        candidato = _montar_nome(base, f" (conflito {usuario}{complemento})", extensao)
        if normalizar_para_comparacao(candidato) not in ocupados:
            return candidato
        numero += 1
