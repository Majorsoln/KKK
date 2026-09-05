"""Fixtures za RCE — config HALISI ya repo, si ya kubuni.

Golden tests zinapima spec dhidi ya `config/risk.yaml` iliyopo. Kigezo
kikibadilishwa hapo bila spec kubadilika, test itafeli — ndivyo lango G10
linavyofanya kazi kwa vitendo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.rce.config import load_config

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def risk_cfg():
    return load_config(REPO_ROOT / "config" / "risk.yaml")


@pytest.fixture
def broker_costs():
    return load_config(REPO_ROOT / "config" / "broker_costs.yaml")
