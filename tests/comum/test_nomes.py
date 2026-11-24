"""Testes da regra única de nomes (RN-68) e dos nomes gerados (FSD 21.8)."""

import unicodedata

import pytest

from drivelan.comum.diretorios import SistemaOperacional
from drivelan.comum.nomes import (
    CARACTERES_PROIBIDOS,
    LIMITE_NOME,
    MotivoNomeInvalido,
    NomeInvalido,
    adaptar_nome_para_copia,
    motivo_nome_invalido,
    nome_compativel,
    nome_conflito,
    nome_duplicado,
    nome_valido_no_sistema,
    nomes_iguais,
    normalizar_nome,
    normalizar_para_comparacao,
    validar_nome,
)

WINDOWS = SistemaOperacional.WINDOWS
LINUX = SistemaOperacional.LINUX

E_NFC = "é"  # "é" composto
E_NFD = "é"  # "e" + acento agudo combinante

# ------------------------------------------------------------------ nomes válidos


@pytest.mark.parametrize(
    "nome",
    [
        "relatorio.docx",
        "Relatório final.pdf",
        "a",
        "com10",
        "conx",
        "console.txt",
        "lpt0",
        "com0.txt",
        "nul-ish",
        "auxiliar.doc",
        ".bashrc",
        ".drivelan.txt",
        " inicio com espaço",
        "nome com espaços",
        "日本語のファイル",
        "emoji 📁",
        "x" * LIMITE_NOME,
        "ponto.no.meio",
        "\x7f-del-permitido",
    ],
)
def test_nomes_validos(nome: str) -> None:
    assert motivo_nome_invalido(nome) is None
    assert validar_nome(nome) == normalizar_nome(nome)
    assert nome_compativel(nome)


def test_drivelan_permitido_fora_da_raiz() -> None:
    assert motivo_nome_invalido(".drivelan") is None
    assert motivo_nome_invalido(".drivelan", na_raiz=False) is None


# ------------------------------------------------------------------ nomes inválidos


@pytest.mark.parametrize("caractere", sorted(CARACTERES_PROIBIDOS))
def test_caracteres_proibidos(caractere: str) -> None:
    for nome in (f"a{caractere}b", f"{caractere}inicio", f"fim{caractere}x"):
        assert motivo_nome_invalido(nome) is MotivoNomeInvalido.CARACTERE_PROIBIDO


def test_lista_de_caracteres_proibidos_do_fsd() -> None:
    assert frozenset('\\/:*?"<>|') == CARACTERES_PROIBIDOS


@pytest.mark.parametrize("codigo", range(32))
def test_caracteres_de_controle(codigo: int) -> None:
    assert motivo_nome_invalido(f"a{chr(codigo)}b") is MotivoNomeInvalido.CARACTERE_CONTROLE


@pytest.mark.parametrize(
    "nome",
    [
        "CON",
        "con",
        "Con",
        "PRN",
        "aux",
        "NUL",
        "nul.txt",
        "con.txt",
        "CON.TXT",
        "Com1.tar.gz",
        "lpt9",
        "LPT1.doc",
        "com5",
        "CON .txt",
    ],
)
def test_nomes_reservados(nome: str) -> None:
    assert motivo_nome_invalido(nome) is MotivoNomeInvalido.RESERVADO


@pytest.mark.parametrize("numero", range(1, 10))
def test_todos_os_com_e_lpt(numero: int) -> None:
    for prefixo in ("COM", "com", "LPT", "lpt"):
        assert motivo_nome_invalido(f"{prefixo}{numero}") is MotivoNomeInvalido.RESERVADO
        assert motivo_nome_invalido(f"{prefixo}{numero}.txt") is MotivoNomeInvalido.RESERVADO


@pytest.mark.parametrize("nome", ["arquivo.", "arquivo ", "arquivo. ", "a..", "pasta  "])
def test_final_em_ponto_ou_espaco(nome: str) -> None:
    assert motivo_nome_invalido(nome) is MotivoNomeInvalido.FINAL_INVALIDO


def test_nome_vazio() -> None:
    assert motivo_nome_invalido("") is MotivoNomeInvalido.VAZIO


@pytest.mark.parametrize("nome", [".", ".."])
def test_ponto_e_ponto_ponto(nome: str) -> None:
    assert motivo_nome_invalido(nome) is MotivoNomeInvalido.PONTO


@pytest.mark.parametrize("nome", [".drivelan", ".DriveLan", ".DRIVELAN"])
def test_area_interna_na_raiz(nome: str) -> None:
    assert motivo_nome_invalido(nome, na_raiz=True) is MotivoNomeInvalido.AREA_INTERNA
    assert motivo_nome_invalido(nome, na_raiz=False) is None


def test_limite_de_255_caracteres() -> None:
    assert motivo_nome_invalido("x" * 255) is None
    assert motivo_nome_invalido("x" * 256) is MotivoNomeInvalido.NOME_LONGO


def test_limite_conta_caracteres_apos_nfc() -> None:
    # 255 "é" decompostos (510 pontos de código) viram 255 caracteres em NFC.
    assert motivo_nome_invalido(E_NFD * 255) is None
    assert motivo_nome_invalido(E_NFD * 256) is MotivoNomeInvalido.NOME_LONGO


def test_validar_nome_levanta_com_motivo() -> None:
    with pytest.raises(NomeInvalido) as erro:
        validar_nome("a:b")
    assert erro.value.motivo is MotivoNomeInvalido.CARACTERE_PROIBIDO
    assert isinstance(erro.value, ValueError)


@pytest.mark.parametrize("motivo", list(MotivoNomeInvalido))
def test_todo_motivo_tem_texto_em_portugues(motivo: MotivoNomeInvalido) -> None:
    assert motivo.texto
    assert motivo.texto == motivo.texto.strip()


# ------------------------------------------------------------------ Unicode e maiúsculas


def test_validar_nome_devolve_nfc() -> None:
    resultado = validar_nome(f"relat{E_NFD}rio.txt")
    assert resultado == f"relat{E_NFC}rio.txt"
    assert unicodedata.is_normalized("NFC", resultado)


@pytest.mark.parametrize(
    ("nome_a", "nome_b"),
    [
        ("Relatorio.docx", "relatorio.docx"),
        ("RELATORIO.DOCX", "relatorio.docx"),
        (f"caf{E_NFC}", f"caf{E_NFD}"),
        (f"CAF{E_NFC.upper()}", f"caf{E_NFD}"),
        ("Straße", "STRASSE"),
        ("ǅ", "ǆ"),
    ],
)
def test_nomes_iguais(nome_a: str, nome_b: str) -> None:
    assert nomes_iguais(nome_a, nome_b)
    assert normalizar_para_comparacao(nome_a) == normalizar_para_comparacao(nome_b)


def test_nomes_diferentes() -> None:
    assert not nomes_iguais("relatorio.docx", "relatorio.doc")
    assert not nomes_iguais("a", "á")


def test_normalizacao_para_comparacao_e_nfc() -> None:
    assert unicodedata.is_normalized("NFC", normalizar_para_comparacao(f"CAF{E_NFD}"))


# ------------------------------------------------------------------ SO de destino


@pytest.mark.parametrize("nome", ["con.txt", "a:b", "fim.", "x\x01y", "a*b?"])
def test_nomes_aceitos_no_linux_e_recusados_no_windows(nome: str) -> None:
    assert nome_valido_no_sistema(nome, LINUX)
    assert not nome_valido_no_sistema(nome, WINDOWS)


@pytest.mark.parametrize("nome", ["", ".", "..", "a/b", "a\x00b"])
def test_nomes_impossiveis_no_linux(nome: str) -> None:
    assert not nome_valido_no_sistema(nome, LINUX)


# ------------------------------------------------------------------ nome adaptado na cópia


@pytest.mark.parametrize(
    ("original", "adaptado"),
    [
        ("relatorio.docx", "relatorio.docx"),
        ("a:b.txt", "a_b.txt"),
        ('x\\/:*?"<>|y', "x_________y"),
        ("con.txt", "_con.txt"),
        ("CON", "_CON"),
        ("lpt1", "_lpt1"),
        ("arquivo.", "arquivo"),
        ("arquivo. . ", "arquivo"),
        ("con.", "_con"),
        ("a\x01b", "a_b"),
        ("...", "_"),
        ("   ", "_"),
        ("ab:.", "ab_"),
    ],
)
def test_adaptar_nome_para_windows(original: str, adaptado: str) -> None:
    assert adaptar_nome_para_copia(original, WINDOWS) == adaptado


def test_adaptacao_para_linux_mantem_nomes_aceitos() -> None:
    assert adaptar_nome_para_copia("con.txt", LINUX) == "con.txt"
    assert adaptar_nome_para_copia("a:b", LINUX) == "a:b"


def test_adaptacao_aplica_nfc() -> None:
    assert adaptar_nome_para_copia(f"caf{E_NFD}:x", WINDOWS) == f"caf{E_NFC}_x"


@pytest.mark.parametrize("original", ["a:b.txt", "con.txt", "fim. ", "x\x1fy", "...", "?" * 300])
def test_nome_adaptado_sempre_passa_na_rn68(original: str) -> None:
    resultado = adaptar_nome_para_copia(original, WINDOWS)
    assert nome_compativel(resultado), resultado
    assert len(resultado) <= LIMITE_NOME


def test_adaptacao_encurta_preservando_extensao() -> None:
    original = "a:" + "b" * 300 + ".docx"
    resultado = adaptar_nome_para_copia(original, WINDOWS)
    assert len(resultado) == LIMITE_NOME
    assert resultado.startswith("a_bbb")
    assert resultado.endswith("b.docx")


# ------------------------------------------------------------------ nome duplicado (RN-63)


def test_duplicado_primeiro_numero_livre() -> None:
    assert nome_duplicado("relatorio.docx", ["relatorio.docx"]) == "relatorio (2).docx"


def test_duplicado_pula_numeros_ocupados() -> None:
    existentes = ["relatorio.docx", "relatorio (2).docx", "relatorio (3).docx"]
    assert nome_duplicado("relatorio.docx", existentes) == "relatorio (4).docx"


def test_duplicado_usa_o_primeiro_buraco() -> None:
    existentes = ["relatorio.docx", "relatorio (3).docx"]
    assert nome_duplicado("relatorio.docx", existentes) == "relatorio (2).docx"


def test_duplicado_sem_diferenciar_maiusculas() -> None:
    existentes = ["Relatorio.docx", "RELATORIO (2).DOCX"]
    assert nome_duplicado("relatorio.docx", existentes) == "relatorio (3).docx"


def test_duplicado_sem_extensao_e_oculto() -> None:
    assert nome_duplicado("LEIAME", ["LEIAME"]) == "LEIAME (2)"
    assert nome_duplicado(".bashrc", [".bashrc"]) == ".bashrc (2)"


def test_duplicado_usa_a_ultima_extensao() -> None:
    assert nome_duplicado("copia.tar.gz", []) == "copia.tar (2).gz"


def test_duplicado_de_pasta_nao_separa_extensao() -> None:
    assert nome_duplicado("projeto.v1", ["projeto.v1"], eh_pasta=True) == "projeto.v1 (2)"


def test_duplicado_respeita_255_caracteres() -> None:
    nome = "b" * 251 + ".txt"
    resultado = nome_duplicado(nome, [nome])
    assert len(resultado) == LIMITE_NOME
    assert resultado.endswith(" (2).txt")
    assert nome_compativel(resultado)


def test_duplicado_com_extensao_enorme() -> None:
    nome = "a." + "x" * 253
    resultado = nome_duplicado(nome, [nome])
    assert len(resultado) <= LIMITE_NOME
    assert nome_compativel(resultado)


# ------------------------------------------------------------------ conflito (RN-47)


def test_conflito_primeiro_nome() -> None:
    assert nome_conflito("relatorio.docx", "joao", []) == "relatorio (conflito joao).docx"


def test_conflito_numerado() -> None:
    existentes = ["relatorio (conflito joao).docx"]
    assert nome_conflito("relatorio.docx", "joao", existentes) == "relatorio (conflito joao 2).docx"
    existentes.append("relatorio (conflito joao 2).docx")
    assert nome_conflito("relatorio.docx", "joao", existentes) == "relatorio (conflito joao 3).docx"


def test_conflito_sem_diferenciar_maiusculas() -> None:
    existentes = ["RELATORIO (CONFLITO JOAO).DOCX"]
    assert nome_conflito("relatorio.docx", "joao", existentes) == "relatorio (conflito joao 2).docx"


def test_conflito_respeita_255_caracteres() -> None:
    nome = "c" * 250 + ".docx"
    resultado = nome_conflito(nome, "joao.silva", [])
    assert len(resultado) == LIMITE_NOME
    assert resultado.endswith(" (conflito joao.silva).docx")
    assert nome_compativel(resultado)


@pytest.mark.parametrize("usuario", ["joao", "maria.souza", "ana-paula", "zé_2"])
def test_nomes_de_conflito_passam_na_rn68(usuario: str) -> None:
    assert nome_compativel(nome_conflito("planilha.xlsx", usuario, []))
