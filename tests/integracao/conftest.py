"""Fixtures compartilhadas dos testes do serviço."""

import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def pasta_curta() -> Iterator[Path]:
    """Pasta temporária de caminho curto, para caber no limite do socket Unix (108 bytes)."""
    caminho = Path(tempfile.mkdtemp(prefix="dl-"))
    try:
        yield caminho
    finally:
        shutil.rmtree(caminho, ignore_errors=True)
