"""Testes dos caminhos do protocolo (FSD 21.4, itens 1 e 2)."""

from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from drivelan.comum.caminhos import (
    RAIZ,
    CaminhoInvalido,
    CaminhoProtocolo,
    de_caminho_relativo_do_sistema,
    para_caminho_do_sistema,
    validar_caminho_novo,
    validar_caminho_protocolo,
)
from drivelan.comum.nomes import MotivoNomeInvalido, NomeInvalido

E_NFC = "\u00e9"
E_NFD = "e\u0301"


@pytest.mark.parametrize(
    ("texto", "componentes"),
    [
        ("a", ("a",)),
        ("a/b/c.txt", ("a", "b", "c.txt")),
        ("Relatórios/2026/janeiro.pdf", ("Relatórios", "2026", "janeiro.pdf")),
        ("com espaço/arquivo final.txt", ("com espaço", "arquivo final.txt")),
        (".oculto/x", (".oculto", "x")),
        ("...", ("...",)),
        ("pasta/a:b", ("pasta", "a:b")),  # nome incompatível já existente continua localizável
        ("pasta/con.txt", ("pasta", "con.txt")),
        ("x/C:", ("x", "C:")),
    ],
)
def test_caminhos_validos(texto: str, componentes: tuple[str, ...]) -> None:
    caminho = validar_caminho_protocolo(texto)
    assert caminho.componentes == componentes
    assert caminho.texto == texto


@pytest.mark.parametrize(
    "texto",
    [
        "/a",
        "/",
        "//servidor/pasta",
        "a\\b",
        "\\a",
        "C:/x",
        "c:x",
        "Z:",
        "C:\\Windows",
        "a//b",
        "a/",
        "a/b/",
        "./a",
        "a/./b",
        "a/../b",
        "..",
        "../fora",
        "a/..",
        ".",
        "a\x00b",
    ],
)
def test_caminhos_invalidos(texto: str) -> None:
    with pytest.raises(CaminhoInvalido):
        validar_caminho_protocolo(texto)


def test_vazio_so_com_permissao_de_raiz() -> None:
    with pytest.raises(CaminhoInvalido):
        validar_caminho_protocolo("")
    raiz = validar_caminho_protocolo("", permitir_raiz=True)
    assert raiz == RAIZ
    assert raiz.eh_raiz
    assert raiz.texto == ""


def test_formato_nao_aplica_nfc() -> None:
    assert validar_caminho_protocolo(f"caf{E_NFD}").texto == f"caf{E_NFD}"


def test_propriedades() -> None:
    caminho = validar_caminho_protocolo("a/b/c.txt")
    assert caminho.nome == "c.txt"
    assert caminho.pai == CaminhoProtocolo(("a", "b"))
    assert caminho.pai.pai.pai == RAIZ
    assert RAIZ.pai == RAIZ
    assert RAIZ.nome == ""
    assert str(caminho) == "a/b/c.txt"


def test_juntar() -> None:
    assert RAIZ.juntar("a").juntar("b.txt").texto == "a/b.txt"


@pytest.mark.parametrize("nome", ["", ".", "..", "a/b", "a\\b", "C:", "x\x00"])
def test_juntar_recusa_componentes_invalidos(nome: str) -> None:
    with pytest.raises(CaminhoInvalido):
        RAIZ.juntar(nome)


def test_juntar_aceita_dois_pontos_fora_da_raiz() -> None:
    assert RAIZ.juntar("a").juntar("C:").texto == "a/C:"


# ------------------------------------------------------------------ caminho novo (item 2)


def test_caminho_novo_aplica_nfc() -> None:
    caminho = validar_caminho_novo(f"pasta/caf{E_NFD}.txt")
    assert caminho.texto == f"pasta/caf{E_NFC}.txt"


@pytest.mark.parametrize(
    ("texto", "motivo"),
    [
        ("pasta/a:b", MotivoNomeInvalido.CARACTERE_PROIBIDO),
        ("pasta/con.txt", MotivoNomeInvalido.RESERVADO),
        ("pasta/fim.", MotivoNomeInvalido.FINAL_INVALIDO),
        ("pasta/x\x1f", MotivoNomeInvalido.CARACTERE_CONTROLE),
        (".drivelan", MotivoNomeInvalido.AREA_INTERNA),
        (".DriveLan", MotivoNomeInvalido.AREA_INTERNA),
        ("pasta/" + "x" * 256, MotivoNomeInvalido.NOME_LONGO),
    ],
)
def test_caminho_novo_aplica_rn68(texto: str, motivo: MotivoNomeInvalido) -> None:
    with pytest.raises(NomeInvalido) as erro:
        validar_caminho_novo(texto)
    assert erro.value.motivo is motivo


def test_drivelan_em_subpasta_e_permitido_ao_criar() -> None:
    assert validar_caminho_novo("pasta/.drivelan").texto == "pasta/.drivelan"


def test_caminho_novo_recusa_formato_invalido() -> None:
    with pytest.raises(CaminhoInvalido):
        validar_caminho_novo("../fora")
    with pytest.raises(CaminhoInvalido):
        validar_caminho_novo("")


def test_limite_de_1024_caracteres() -> None:
    componente = "x" * 200
    no_limite = "/".join([componente] * 5) + "/" + "y" * 19  # 5*200 + 5 + 19 = 1024
    assert len(no_limite) == 1024
    assert validar_caminho_novo(no_limite).texto == no_limite
    with pytest.raises(NomeInvalido) as erro:
        validar_caminho_novo(no_limite + "z")
    assert erro.value.motivo is MotivoNomeInvalido.CAMINHO_LONGO


# ------------------------------------------------------------------ conversão para o SO


def test_para_caminho_do_sistema_linux() -> None:
    caminho = validar_caminho_protocolo("a/b/c.txt")
    assert para_caminho_do_sistema(caminho, PurePosixPath("/home/u/DriveLan/Aulas")) == (
        PurePosixPath("/home/u/DriveLan/Aulas/a/b/c.txt")
    )


def test_para_caminho_do_sistema_windows() -> None:
    caminho = validar_caminho_protocolo("a/b/c.txt")
    resultado = para_caminho_do_sistema(caminho, PureWindowsPath(r"D:\DriveLan\Aulas"))
    assert str(resultado) == r"D:\DriveLan\Aulas\a\b\c.txt"


def test_raiz_para_caminho_do_sistema(tmp_path: Path) -> None:
    assert para_caminho_do_sistema(RAIZ, tmp_path) == tmp_path


@pytest.mark.parametrize(
    "relativo",
    [PurePosixPath("a/b/c.txt"), PureWindowsPath(r"a\b\c.txt")],
)
def test_de_caminho_relativo_do_sistema(relativo: PurePosixPath | PureWindowsPath) -> None:
    assert de_caminho_relativo_do_sistema(relativo).texto == "a/b/c.txt"


def test_relativo_vazio_e_raiz() -> None:
    assert de_caminho_relativo_do_sistema(PurePosixPath(".")) == RAIZ


@pytest.mark.parametrize(
    "relativo",
    [
        PurePosixPath("/etc/passwd"),
        PureWindowsPath(r"C:\Windows"),
        PureWindowsPath(r"C:relativo"),
        PureWindowsPath(r"\\servidor\pasta\x"),
        PurePosixPath("../fora"),
        PurePosixPath("a/../../b"),
    ],
)
def test_de_caminho_relativo_recusa_fugas(relativo: PurePosixPath | PureWindowsPath) -> None:
    with pytest.raises(CaminhoInvalido):
        de_caminho_relativo_do_sistema(relativo)


def test_ida_e_volta() -> None:
    caminho = validar_caminho_protocolo("Relatórios/2026/janeiro.pdf")
    raiz = PureWindowsPath(r"D:\DriveLan\X")
    relativo = para_caminho_do_sistema(caminho, raiz).relative_to(raiz)
    assert de_caminho_relativo_do_sistema(relativo) == caminho
