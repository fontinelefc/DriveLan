"""Ponto de entrada do `drivelan-service` (FSD 4.1, 5.5 e 6.1).

Opções desta fase:

- `--console`: roda em primeiro plano com o log também no terminal, sem registro como serviço;
- `--dados <pasta>`: pasta de dados alternativa de desenvolvimento (banco, configuração, logs e
  canal local ficam dentro dela);
- `--migrar`: executa as migrations pendentes e sai (exige administrador do SO, FSD 11.3 e 24.8).

Os demais comandos protegidos (`--definir-chave`, `--configurar-firewall`,
`--regenerar-identidade`) entram nas fases que os usam (8, 11 e 27). O registro como serviço do
Windows e a unidade systemd são da Fase 27; sem `--console`, o processo roda em primeiro plano
(como espera o systemd).
"""

import argparse
import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path

from drivelan.comum.diretorios import diretorios_servico
from drivelan.servico.dados.banco import BancoDados
from drivelan.servico.dados.migracoes import ErroMigracao
from drivelan.servico.inicializacao import OpcoesServico, executar_servico
from drivelan.servico.log_erros import LogErros, origem_de

ORIGEM_LOG = origem_de(__name__)

SAIDA_OK = 0
SAIDA_FALHA = 1
SAIDA_SEM_PRIVILEGIO = 2


def _criar_analisador() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(
        prog="drivelan-service",
        description="Serviço do DriveLan: hospeda as pastas compartilhadas na rede local.",
    )
    analisador.add_argument(
        "--console",
        action="store_true",
        help="roda em primeiro plano, com o log também no terminal (desenvolvimento)",
    )
    analisador.add_argument(
        "--dados",
        type=Path,
        metavar="PASTA",
        help="pasta de dados alternativa para desenvolvimento",
    )
    analisador.add_argument(
        "--migrar",
        action="store_true",
        help="executa as migrations pendentes do banco e sai (exige administrador do SO)",
    )
    return analisador


def _eh_administrador() -> bool:
    if sys.platform == "win32":
        from drivelan.servico.plataforma.windows import eh_administrador
    else:
        from drivelan.servico.plataforma.linux import eh_administrador
    return eh_administrador()


def migrar(dados_dev: Path | None) -> int:
    """`--migrar`: aplica as migrations pendentes e informa o resultado (FSD 11.3)."""
    if dados_dev is None and not _eh_administrador():
        print("drivelan-service: --migrar exige privilégio de administrador do sistema.")
        return SAIDA_SEM_PRIVILEGIO
    diretorios = diretorios_servico(dados_dev)
    log = LogErros(diretorios.logs, espelho=sys.stderr)
    try:
        banco = BancoDados.abrir(diretorios.banco, log)
    except ErroMigracao:
        print("drivelan-service: as migrations não foram aplicadas. Consulte o log de erros.")
        return SAIDA_FALHA
    except Exception as erro:
        codigo = log.erro_inesperado(ORIGEM_LOG, erro)
        print(f"drivelan-service: não foi possível abrir o banco. Código: {codigo}")
        return SAIDA_FALHA
    banco.fechar()
    print("drivelan-service: banco atualizado.")
    return SAIDA_OK


def main(argv: Sequence[str] | None = None) -> int:
    opcoes = _criar_analisador().parse_args(argv)
    if opcoes.migrar:
        return migrar(opcoes.dados)
    try:
        return asyncio.run(
            executar_servico(OpcoesServico(console=opcoes.console, dados_dev=opcoes.dados))
        )
    except KeyboardInterrupt:  # Ctrl+C no Windows; o asyncio já fechou tudo
        return SAIDA_OK


if __name__ == "__main__":
    sys.exit(main())
