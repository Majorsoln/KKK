"""RCE-05 — fill_rate: kipimo cha lazima cha cap.

Spec: `RISK_COST_ENGINE.md` §3.2 ("Kipimo cha lazima — FILL RATE")
"""

from __future__ import annotations

import json

import pytest

from src.rce.fills import ACTION_A, ACTION_B, FillTracker


def _send(tracker: FillTracker, symbol: str, filled: bool, fill_px: float | None = None) -> None:
    tracker.record(
        symbol=symbol,
        direction="BUY",
        order_type="stop",
        requested_px=157.500,
        cap_pips=0.3,
        filled=filled,
        fill_px=fill_px,
        pip_size=0.01,
    )


def test_fill_rate_ni_zilizojaza_kugawa_zilizotumwa(cfg):
    tracker = FillTracker(cfg)
    for _ in range(7):
        _send(tracker, "USDJPY", True, 157.502)
    for _ in range(3):
        _send(tracker, "USDJPY", False)
    assert tracker.sent == 10 and tracker.filled == 7
    assert tracker.fill_rate() == pytest.approx(0.7)


def test_bila_orders_hakuna_fill_rate(cfg):
    """Hakuna hukumu kabla ya data — None, si 0.0."""
    tracker = FillTracker(cfg)
    assert tracker.fill_rate() is None
    assert tracker.status().ok


def test_chini_ya_fill_rate_min_kunatoa_onyo(cfg):
    """`fill_rate < 0.60` → ONYO: "cap ni ngumu; strategy inatofautiana na utafiti"."""
    assert cfg.fill_rate_min == 0.60
    tracker = FillTracker(cfg)
    for _ in range(5):
        _send(tracker, "USDJPY", True, 157.501)
    for _ in range(5):
        _send(tracker, "USDJPY", False)

    status = tracker.status()
    assert status.fill_rate == pytest.approx(0.5)
    assert not status.ok
    assert "cap ni ngumu" in status.warning
    assert status.actions == (ACTION_A, ACTION_B)


def test_juu_ya_kizingiti_hakuna_onyo(cfg):
    tracker = FillTracker(cfg)
    for _ in range(6):
        _send(tracker, "USDJPY", True, 157.501)
    for _ in range(4):
        _send(tracker, "USDJPY", False)
    assert tracker.status().ok


def test_slippage_halisi_inarekodiwa_kwa_kila_fill(cfg):
    """§3.2: kila fill inarekodi requested_px, fill_px, slippage halisi."""
    tracker = FillTracker(cfg)
    _send(tracker, "USDJPY", True, 157.503)
    record = tracker.records[0]
    assert record.requested_px == 157.500
    assert record.fill_px == 157.503
    assert record.slippage_pips == pytest.approx(0.3, abs=0.001)
    assert tracker.records[0].cap_pips == 0.3


def test_order_isiyojaza_haina_slippage(cfg):
    tracker = FillTracker(cfg)
    _send(tracker, "USDJPY", False)
    assert tracker.records[0].slippage_pips is None


def test_kipimo_kinapatikana_kwa_kila_symbol(cfg):
    tracker = FillTracker(cfg)
    for _ in range(4):
        _send(tracker, "USDJPY", True, 157.501)
    for _ in range(4):
        _send(tracker, "EURUSD", False)
    assert tracker.fill_rate("USDJPY") == pytest.approx(1.0)
    assert tracker.fill_rate("EURUSD") == pytest.approx(0.0)
    assert "EURUSD" in tracker.status("EURUSD").warning


def test_rekodi_zinaandikwa_kwenye_log_ya_jsonl(cfg, tmp_path):
    path = tmp_path / "fills" / "fills.jsonl"
    tracker = FillTracker(cfg, log_path=path)
    _send(tracker, "USDJPY", True, 157.502)
    _send(tracker, "USDJPY", False)
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["symbol"] == "USDJPY" and first["filled"] is True
    assert first["slippage_pips"] == pytest.approx(0.2, abs=0.001)
