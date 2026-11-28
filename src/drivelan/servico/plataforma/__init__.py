"""Código específico de cada sistema operacional (FSD 5.5).

Este módulo guarda só o que é comum às plataformas: a identidade do processo que se conecta ao
canal local (FSD 15.5). `linux.py`, `windows.py` e `windows_pipe.py` têm o código de cada SO e só
são importados no sistema correspondente.
"""

from dataclasses import dataclass

import psutil

CHAVE_IDENTIDADE = "drivelan_identidade"
"""Nome da informação extra do transporte que guarda a `IdentidadeCliente` (servidor do pipe)."""


class CanalEmUso(Exception):
    """Outro processo já atende no endereço do canal local (falha impeditiva, FSD 6.1)."""


class IdentidadeIndisponivel(Exception):
    """Não foi possível identificar o usuário do SO ou o processo do cliente do canal local."""


@dataclass(frozen=True, slots=True)
class IdentidadeCliente:
    """Quem está do outro lado de uma conexão do canal local (FSD 15.5).

    `usuario_so` usa o mesmo formato de `pasta.so_dono` e `so_usuario` (FSD 11.2): o UID em texto
    no Linux e o SID no Windows. `processo_criado_em` (segundos desde a época) acompanha o PID para
    que um PID reaproveitado por outro processo não herde a sessão (FSD 15.5, Fase 7).
    """

    usuario_so: str
    pid: int
    processo_criado_em: float


def horario_criacao_processo(pid: int) -> float:
    """Horário de criação do processo; levanta `IdentidadeIndisponivel` se ele não existir mais."""
    try:
        return float(psutil.Process(pid).create_time())
    except (psutil.Error, OSError) as erro:
        raise IdentidadeIndisponivel(f"processo {pid} indisponível") from erro
