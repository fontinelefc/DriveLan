"""Testes da base do projeto (Fase 1): estrutura, pontos de entrada e regras de importação."""

import ast
import importlib
import tomllib
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PACOTE = RAIZ / "src" / "drivelan"


def _modulos_importados(arquivo: Path) -> set[str]:
    """Devolve os nomes absolutos de todos os módulos importados por um arquivo."""
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
            nomes.add(no.module)
    return nomes


@pytest.mark.parametrize(
    "pasta",
    [
        "src/drivelan/comum",
        "src/drivelan/servico/api/local",
        "src/drivelan/servico/api/rede",
        "src/drivelan/servico/regras",
        "src/drivelan/servico/dados/migracoes",
        "src/drivelan/servico/dados/repositorios",
        "src/drivelan/servico/rede",
        "src/drivelan/servico/arquivos",
        "src/drivelan/servico/tarefas",
        "src/drivelan/servico/plataforma",
        "src/drivelan/app/controladores",
        "src/drivelan/app/modelos",
        "src/drivelan/app/telas",
        "src/drivelan/app/componentes",
        "src/drivelan/app/edicao",
        "src/drivelan/app/transferencias",
        "recursos/estilo",
        "recursos/fontes",
        "recursos/icones",
        "recursos/traducoes",
        "empacotamento/windows",
        "empacotamento/linux",
        "tests/servico",
        "tests/app",
        "tests/integracao",
    ],
)
def test_pastas_da_secao_5_5_existem(pasta: str) -> None:
    assert (RAIZ / pasta).is_dir()


@pytest.mark.parametrize("proibida", ["logs", "config", "public", "htdocs", "www", "public_html"])
def test_pastas_proibidas_nao_existem(proibida: str) -> None:
    # FSD 5.1 e 5.5: sem pastas públicas de servidor web e sem logs/ ou config/ no repositório.
    assert not (RAIZ / proibida).exists()


def test_nao_existe_arquivo_env() -> None:
    # FSD 3.4: proibido usar arquivo .env.
    assert not (RAIZ / ".env").exists()


def test_pontos_de_entrada_declarados() -> None:
    dados = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = dados["project"]["scripts"]
    assert scripts["drivelan-service"] == "drivelan.servico.__main__:main"
    assert scripts["drivelan"] == "drivelan.app.__main__:main"


def test_ponto_de_entrada_do_servico_executa(tmp_path: Path) -> None:
    # Sem argumentos o serviço roda até ser parado; `--migrar` executa e termina (Fase 5).
    principal = importlib.import_module("drivelan.servico.__main__")
    assert principal.main(["--migrar", "--dados", str(tmp_path)]) == 0


def test_ponto_de_entrada_do_app_executa() -> None:
    assert importlib.import_module("drivelan.app.__main__").main() == 0


@pytest.mark.parametrize(("origem", "proibido"), [("servico", "app"), ("app", "servico")])
def test_servico_e_app_nao_se_importam(origem: str, proibido: str) -> None:
    # FSD 5.5: servico/ e app/ só compartilham código por meio de comum/.
    alvo = f"drivelan.{proibido}"
    for arquivo in (PACOTE / origem).rglob("*.py"):
        for nome in _modulos_importados(arquivo):
            assert nome != alvo and not nome.startswith(f"{alvo}."), (
                f"{arquivo.relative_to(RAIZ)} importa {nome}"
            )


def test_fontes_embutidas_presentes() -> None:
    # FSD 3.3: Inter e JetBrains Mono embutidas, com a licença OFL.
    for familia in ("inter", "jetbrains-mono"):
        pasta = RAIZ / "recursos" / "fontes" / familia
        assert list(pasta.glob("*.ttf")), f"sem fontes em {familia}"
        assert (pasta / "OFL.txt").is_file()


def test_licenca_gplv3() -> None:
    texto = (RAIZ / "LICENSE").read_text(encoding="utf-8")
    assert "GNU GENERAL PUBLIC LICENSE" in texto
    assert "Version 3" in texto
