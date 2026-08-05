"""Fixtures za tests za tabaka la data (T0).

Data ya kweli ya L0 iko nje ya repo (sheria ya README), kwa hiyo tests
zinatengeneza partitions ndogo za **matoleo yote mawili** ya schema (spec §2.1)
ndani ya `tmp_path`. Namba ni chache lakini muundo ni ule ule wa data halisi.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.data.config import load_config

REPO_ROOT = Path(__file__).resolve().parents[1]

# Ticks 6 za kufikirika: bid < ask kila wakati, volumes zipo pande zote mbili.
BASE_TICKS = [
    # (dakika baada ya 09:00, bid, ask, bid_vol, ask_vol)
    (0, 1.09001, 1.09011, 1.0, 2.0),
    (1, 1.09003, 1.09014, 3.0, 1.0),
    (2, 1.09002, 1.09012, 2.5, 2.5),
    (3, 1.09007, 1.09018, 4.0, 1.5),
    (4, 1.09010, 1.09019, 1.5, 3.0),
    (5, 1.09008, 1.09017, 2.0, 2.0),
]


def _timestamps(day: datetime) -> list[datetime]:
    return [day.replace(hour=9, minute=0) + timedelta(minutes=offset) for offset, *_ in BASE_TICKS]


def variant_a_frame(day: datetime | None = None) -> pd.DataFrame:
    """Toleo A: `timestamp, bid, ask, bid_vol, ask_vol` kwa µs (symbols 9)."""
    day = day or datetime(2026, 8, 3, tzinfo=timezone.utc)
    return pd.DataFrame(
        {
            "timestamp": pd.Series(_timestamps(day), dtype="datetime64[us, UTC]"),
            "bid": [row[1] for row in BASE_TICKS],
            "ask": [row[2] for row in BASE_TICKS],
            "bid_vol": [row[3] for row in BASE_TICKS],
            "ask_vol": [row[4] for row in BASE_TICKS],
        }
    )


def variant_b_frame(day: datetime | None = None) -> pd.DataFrame:
    """Toleo B: `ts, bid, ask, bid_volume, ask_volume` kwa ms (EURCHF/GBPJPY/XAUUSD)."""
    day = day or datetime(2026, 8, 3, tzinfo=timezone.utc)
    epoch_ms = [int(stamp.timestamp() * 1000) for stamp in _timestamps(day)]
    return pd.DataFrame(
        {
            "ts": pd.Series(epoch_ms, dtype="int64"),
            "bid": [row[1] for row in BASE_TICKS],
            "ask": [row[2] for row in BASE_TICKS],
            "bid_volume": [row[3] for row in BASE_TICKS],
            "ask_volume": [row[4] for row in BASE_TICKS],
        }
    )


@pytest.fixture
def research_root(tmp_path: Path) -> Path:
    root = tmp_path / "research"
    root.mkdir()
    return root


@pytest.fixture
def cfg(research_root: Path):
    """Config halisi ya repo, ikielekezwa kwenye storage ya muda."""
    config = load_config(
        REPO_ROOT / "config" / "data.yaml",
        env={
            "ELITEFX_RESEARCH_ROOT": str(research_root),
            "ELITEFX_HOLDOUT_ROOT": str(research_root / "_holdout"),
        },
    )
    # `recorder.broker_id` ni tupu kwenye repo (PD anaijaza kwa broker wake).
    # Tests zinahitaji kitambulisho ili guard ya §2.2 ipite; zinazoipima yenyewe
    # zinaweka thamani yao kwenye RecorderSettings.
    config.raw.setdefault("recorder", {})["broker_id"] = "test-broker"
    return config


@pytest.fixture
def l0_root(research_root: Path) -> Path:
    root = research_root / "data" / "L0_raw"
    root.mkdir(parents=True)
    return root


@pytest.fixture
def aggregator_partitions(l0_root: Path) -> dict[str, Path]:
    """Partitions za aggregator: Toleo A (daily) na Toleo B (monthly)."""
    a_path = l0_root / "provenance=aggregator" / "symbol=EURUSD" / "2026" / "2026-08-03.parquet"
    b_path = l0_root / "provenance=aggregator" / "symbol=XAUUSD" / "2026" / "2026-08.parquet"
    a_path.parent.mkdir(parents=True, exist_ok=True)
    b_path.parent.mkdir(parents=True, exist_ok=True)
    variant_a_frame().to_parquet(a_path, index=False)
    variant_b_frame().to_parquet(b_path, index=False)
    return {"A": a_path, "B": b_path}
