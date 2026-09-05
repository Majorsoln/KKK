"""Config halisi ya `config/data.yaml` — si ya kubuni.

Tarehe za mgawanyo (`data_start`, `trainval_end`, `holdout_start`) ni sehemu ya
mkataba wa §16.1. Test inayozibuni ingepima code dhidi ya dhana yake yenyewe
badala ya dhidi ya kile mfumo utakachokiendesha.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.rce.config import load_config

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def cfg():
    return load_config(REPO / "config" / "data.yaml")
