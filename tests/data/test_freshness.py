"""DF-04 — ONYO: siku ya trading bila data mpya ya broker.

Spec: `docs/DATA_FEATURE_STANDARD.md` §2.2 ("kila mwezi usiorekodiwa ni data ya
broker iliyopotea bure"). Rejista: DF-04 (CI/alert).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.data.freshness import (
    STATUS_ALERT,
    STATUS_NOT_STARTED,
    STATUS_OK,
    STATUS_SKIPPED,
    check_freshness,
)
from src.data.recorder import RecorderSettings, TickRecorder
from src.data.mt5_source import ReplayTickSource
from tests.data.test_recorder import MONDAY, TUESDAY, WEDNESDAY, ticks_for_days


def _record(cfg, frames, now, symbols=("EURUSD",)):
    settings = RecorderSettings.from_config(cfg)
    settings.symbols = list(symbols)
    recorder = TickRecorder(ReplayTickSource(frames), cfg, settings=settings, clock=lambda: now)
    recorder.poll_once()
    return recorder


def test_bila_partition_ya_broker_hadhi_ni_not_started(cfg, l0_root, aggregator_partitions):
    """Data ya aggregator pekee haitoshi — pengo la provenance (§2.2) bado liko wazi."""
    from src.data.manifest import hash_l0_tree

    hash_l0_tree(cfg, l0_root=l0_root)
    report = check_freshness(cfg, now=WEDNESDAY.replace(hour=12))
    assert report.status == STATUS_NOT_STARTED
    assert report.exit_code == 1
    assert "provenance: broker" in report.reason


def test_siku_zote_zilizorekodiwa_ni_ok(cfg, l0_root):
    frames = {"EURUSD": ticks_for_days([MONDAY, TUESDAY])}
    _record(cfg, frames, now=WEDNESDAY.replace(hour=12))
    report = check_freshness(cfg, now=WEDNESDAY.replace(hour=12))
    assert report.status == STATUS_OK
    assert report.exit_code == 0
    assert report.symbols[0].last_partition_day == "2026-08-04"


def test_siku_ya_trading_iliyokosekana_inazalisha_onyo(cfg, l0_root):
    """Jumanne haina data ingawa ni siku kamili ya trading → ALERT."""
    frames = {"EURUSD": ticks_for_days([MONDAY, WEDNESDAY])}
    thursday = MONDAY + timedelta(days=3)
    _record(cfg, frames, now=thursday.replace(hour=12))
    report = check_freshness(cfg, now=thursday.replace(hour=12))
    assert report.status == STATUS_ALERT
    assert report.exit_code == 1
    assert report.symbols[0].missing_days == ["2026-08-04"]


def test_pengo_ndani_ya_kipindi_kilichorekodiwa_linagunduliwa(cfg, l0_root):
    """Recorder ikikaa kimya siku kadhaa kisha kurudi, siku zilizorukwa bado ni ONYO."""
    wed = datetime(2026, 7, 29, tzinfo=timezone.utc)
    mon = datetime(2026, 8, 3, tzinfo=timezone.utc)
    _record(cfg, {"EURUSD": ticks_for_days([wed])}, now=wed + timedelta(days=1, hours=12))
    _record(cfg, {"EURUSD": ticks_for_days([mon])}, now=mon + timedelta(days=1, hours=12))

    report = check_freshness(cfg, now=mon + timedelta(days=1, hours=12))
    assert report.status == STATUS_ALERT
    assert report.symbols[0].missing_days == ["2026-07-30", "2026-07-31"]


def test_wikendi_haizalishi_onyo(cfg, l0_root):
    """Ijumaa imerekodiwa; Jumamosi/Jumapili si siku kamili za trading."""
    friday = datetime(2026, 8, 7, tzinfo=timezone.utc)
    monday_next = datetime(2026, 8, 10, tzinfo=timezone.utc)
    _record(cfg, {"EURUSD": ticks_for_days([friday])}, now=monday_next.replace(hour=6))
    report = check_freshness(cfg, now=monday_next.replace(hour=6))
    assert report.status == STATUS_OK
    assert report.symbols[0].missing_days == []


def test_sikukuu_ya_kalenda_haizalishi_onyo(cfg, l0_root):
    """`recorder.calendar.holidays_md` (01-01, 12-25) inatolewa kwenye matarajio."""
    dec24 = datetime(2026, 12, 24, tzinfo=timezone.utc)  # Alhamisi
    dec25 = datetime(2026, 12, 25, tzinfo=timezone.utc)  # Ijumaa — sikukuu
    dec28 = datetime(2026, 12, 28, tzinfo=timezone.utc)  # Jumatatu
    _record(cfg, {"EURUSD": ticks_for_days([dec24])}, now=dec25.replace(hour=6))
    report = check_freshness(cfg, now=dec28.replace(hour=6))
    assert "2026-12-25" not in report.symbols[0].missing_days
    assert report.status == STATUS_OK


def test_grace_hours_inazuia_onyo_la_haraka_mno(cfg, l0_root):
    """Siku iliyofungwa punde (chini ya `grace_hours`) bado haiko kwenye dirisha."""
    frames = {"EURUSD": ticks_for_days([MONDAY])}
    now = TUESDAY.replace(hour=12)  # 2026-08-04 12:00 — grace 26h
    _record(cfg, frames, now=now)
    report = check_freshness(cfg, now=now)
    assert report.window_end == "2026-08-03"
    assert report.status == STATUS_OK


def test_storage_isiyowekwa_inaruka_bila_kufelisha_build(research_root):
    """CI ya repo haina storage ya research — lango linaruka, halifelishi build."""
    from src.data.config import load_config
    from tests.conftest import REPO_ROOT

    cfg_no_storage = load_config(REPO_ROOT / "config" / "data.yaml", env={})
    report = check_freshness(cfg_no_storage, now=WEDNESDAY)
    assert report.status == STATUS_SKIPPED
    assert report.exit_code == 0


def test_ripoti_inaweza_kutolewa_kwa_json_na_maandishi(cfg, l0_root):
    _record(cfg, {"EURUSD": ticks_for_days([MONDAY])}, now=WEDNESDAY.replace(hour=12))
    report = check_freshness(cfg, now=WEDNESDAY.replace(hour=12))
    payload = report.to_json()
    assert payload["status"] == report.status
    assert payload["symbols"][0]["symbol"] == "EURUSD"
    assert "DF-04 freshness" in report.render()
