"""Config halisi za `config/` — si za kubuni.

`cfg_risk` ni `risk.yaml`: RCE inasoma vigezo vyake vyote kutoka hapo, na test
inayozibuni ingepima code dhidi ya dhana yake yenyewe badala ya dhidi ya
kitakachoendeshwa.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.rce.config import load_config

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def cfg_risk():
    return load_config(REPO / "config" / "risk.yaml")


@pytest.fixture
def cfg():
    return load_config(REPO / "config" / "data.yaml")
