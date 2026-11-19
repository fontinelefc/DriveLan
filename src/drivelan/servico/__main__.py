"""Ponto de entrada do `drivelan-service` (FSD 5.5).

Nesta fase existe apenas o esqueleto. As opções de linha de comando
(`--console`, `--dados`, `--migrar`, `--definir-chave`, `--configurar-firewall`,
`--regenerar-identidade`) e a ordem de inicialização da seção 6.1 do FSD são
implementadas a partir da Fase 5 do `docs/PLANO.md`.
"""

import sys


def main() -> int:
    """Executa o serviço. Ainda não implementado (Fase 5)."""
    print("drivelan-service: esqueleto da Fase 1; o serviço é implementado na Fase 5.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
