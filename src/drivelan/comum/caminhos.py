"""Caminhos do protocolo e conversão para o sistema operacional (FSD 21.4).

Um caminho do protocolo é texto relativo à raiz da pasta compartilhada, com `/` como
separador. Este módulo cobre o item 1 da seção 21.4 (formato) e o item 2 (NFC e RN-68 ao criar
ou renomear). A resolução no disco, os links, as junções e a área `.drivelan` no servidor
(itens 3 a 6) ficam em `servico/arquivos/validacao.py` (Fase 15).
"""

import re
from dataclasses import dataclass
from pathlib import PurePath

from drivelan.comum.nomes import (
    LIMITE_CAMINHO,
    MotivoNomeInvalido,
    NomeInvalido,
    normalizar_nome,
    validar_nome,
)

SEPARADOR = "/"
_LETRA_DE_UNIDADE = re.compile(r"^[A-Za-z]:")


class CaminhoInvalido(ValueError):
    """Caminho fora do formato do protocolo (código `caminho_invalido`).

    A mensagem é técnica e vai só para o log; o usuário recebe o texto genérico do código.
    """


@dataclass(frozen=True, slots=True)
class CaminhoProtocolo:
    """Caminho relativo já validado; a raiz da pasta tem zero componentes."""

    componentes: tuple[str, ...] = ()

    @property
    def texto(self) -> str:
        """Forma de texto do protocolo (`a/b/c.txt`; vazio para a raiz)."""
        return SEPARADOR.join(self.componentes)

    @property
    def eh_raiz(self) -> bool:
        return not self.componentes

    @property
    def nome(self) -> str:
        """Último componente; vazio para a raiz."""
        return self.componentes[-1] if self.componentes else ""

    @property
    def pai(self) -> "CaminhoProtocolo":
        """Caminho da subpasta que contém o item (a raiz é pai de si mesma)."""
        return CaminhoProtocolo(self.componentes[:-1])

    def juntar(self, nome: str) -> "CaminhoProtocolo":
        """Caminho de `nome` dentro deste caminho, validando o formato do componente."""
        _validar_componente(nome)
        if self.eh_raiz:
            return validar_caminho_protocolo(nome)
        return validar_caminho_protocolo(f"{self.texto}{SEPARADOR}{nome}")

    def __str__(self) -> str:
        return self.texto


RAIZ = CaminhoProtocolo()


def _validar_componente(componente: str) -> None:
    if not componente:
        raise CaminhoInvalido("componente vazio")
    if componente in {".", ".."}:
        raise CaminhoInvalido("componente . ou ..")
    if SEPARADOR in componente or "\\" in componente:
        raise CaminhoInvalido("separador dentro do componente")
    if "\x00" in componente:
        raise CaminhoInvalido("caractere nulo")


def validar_caminho_protocolo(texto: str, *, permitir_raiz: bool = False) -> CaminhoProtocolo:
    """Valida o formato de um caminho recebido (FSD 21.4, item 1).

    O texto é mantido como veio, sem NFC, para que itens já existentes com nomes fora da
    regra continuem localizáveis. O texto vazio representa a raiz, se `permitir_raiz`.
    """
    if texto == "":
        if permitir_raiz:
            return RAIZ
        raise CaminhoInvalido("caminho vazio")
    if texto.startswith(SEPARADOR):
        raise CaminhoInvalido("caminho absoluto")
    if "\\" in texto:
        raise CaminhoInvalido("barra invertida")
    if _LETRA_DE_UNIDADE.match(texto):
        raise CaminhoInvalido("letra de unidade")
    componentes = tuple(texto.split(SEPARADOR))
    for componente in componentes:
        _validar_componente(componente)
    return CaminhoProtocolo(componentes)


def validar_caminho_novo(texto: str) -> CaminhoProtocolo:
    """Valida o caminho de um item a criar ou renomear (FSD 21.4, itens 1 e 2).

    Aplica o formato, a NFC, a RN-68 ao último componente e o limite de 1.024 caracteres.
    Levanta `CaminhoInvalido` (formato) ou `NomeInvalido` (regra de nomes).
    """
    caminho = validar_caminho_protocolo(normalizar_nome(texto))
    na_raiz = len(caminho.componentes) == 1
    validar_nome(caminho.nome, na_raiz=na_raiz)
    if len(caminho.texto) > LIMITE_CAMINHO:
        raise NomeInvalido(MotivoNomeInvalido.CAMINHO_LONGO)
    return caminho


def para_caminho_do_sistema[C: PurePath](caminho: CaminhoProtocolo, raiz: C) -> C:
    """Converte para o formato do SO, juntando à raiz da pasta (FSD 21.4, item 3).

    Só converte: a resolução e a verificação de que o resultado fica dentro da raiz são feitas
    no servidor (Fase 15).
    """
    return raiz.joinpath(*caminho.componentes)


def de_caminho_relativo_do_sistema(relativo: PurePath) -> CaminhoProtocolo:
    """Converte um caminho relativo do SO (ex.: itens de uma pasta enviada) para o protocolo."""
    if relativo.is_absolute() or relativo.anchor:
        raise CaminhoInvalido("caminho do sistema não é relativo")
    partes = relativo.parts
    if not partes or partes == (".",):
        return RAIZ
    return validar_caminho_protocolo(SEPARADOR.join(partes))
