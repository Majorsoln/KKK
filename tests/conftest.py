"""Config HALISI za `config/` — si za kubuni.

Test inayobuni vigezo ingepima code dhidi ya dhana yake yenyewe badala ya
dhidi ya kitakachoendeshwa.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.rce.config import load_config

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def cfg_risk():
    return load_config(REPO / "config" / "risk.yaml")
