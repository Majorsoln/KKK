"""RCE-01, RCE-02 — bajeti ya siku, penalty, na reset ya 00:00 CE(S)T.

Spec: `RISK_COST_ENGINE.md` §2
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.rce.budget import AccountState, DayCounters, compute_budget, trading_day


def test_penalty_ni_nusu_ya_dd_ya_jumla(cfg):
    """`penalty = penalty_factor × max(0, base_balance − current_balance)`."""
    result = compute_budget(AccountState(current_balance=9_400.0), cfg)
    assert result.total_drawdown == pytest.approx(600.0)
    assert result.penalty == pytest.approx(300.0)


def test_faida_juu_ya_base_balance_haitoi_penalty_hasi(cfg):
    """`max(0, ...)` — akaunti ikiwa juu ya rejea, penalty ni 0, si bonasi."""
    result = compute_budget(AccountState(current_balance=10_500.0), cfg)
    assert result.total_drawdown == 0.0
    assert result.penalty == 0.0
    assert result.budget == pytest.approx(400.0)


def test_faida_na_hasara_za_leo_ni_vihesabu_viwili_tofauti(cfg):
    """Safu ya 4 ya §2: 400 − 125 − 150 + 50 = 175 (si 400 − 125 − 50)."""
    result = compute_budget(
        AccountState(current_balance=9_750.0, today_profit=100.0, today_loss=150.0), cfg
    )
    assert result.budget == pytest.approx(175.0)


def test_risk_per_trade_ni_budget_kugawa_max_open(cfg):
    result = compute_budget(AccountState(current_balance=10_000.0), cfg)
    assert result.risk_per_trade == pytest.approx(400.0 / cfg.max_open_trades)


def test_base_balance_ni_rejea_isiyobadilika(cfg):
    """Salio la sasa linabadilika; `base` inabaki 4% ya rejea ya config."""
    for balance in (10_000.0, 9_000.0, 12_000.0):
        assert compute_budget(AccountState(current_balance=balance), cfg).base == pytest.approx(400.0)


def test_hasara_inaandikwa_kama_thamani_chanya(cfg):
    with pytest.raises(ValueError):
        AccountState(current_balance=10_000.0, today_loss=-50.0)


# --------------------------------------------------------------------------
# RCE-02 — reset ya 00:00 CE(S)T
# --------------------------------------------------------------------------


def test_siku_ya_biashara_inahesabiwa_kwa_saa_za_config(cfg):
    """23:30 UTC ya kiangazi tayari ni kesho Berlin (CEST = UTC+2)."""
    assert cfg.day_reset_tz == "Europe/Berlin"
    late = datetime(2026, 8, 4, 23, 30, tzinfo=timezone.utc)
    assert trading_day(late, cfg).isoformat() == "2026-08-05"
    early = datetime(2026, 8, 4, 21, 30, tzinfo=timezone.utc)
    assert trading_day(early, cfg).isoformat() == "2026-08-04"


def test_reset_ya_majira_ya_baridi_inafuata_cet(cfg):
    """Wakati wa CET (UTC+1), 23:30 UTC bado ni siku ile ile."""
    winter = datetime(2026, 1, 15, 22, 30, tzinfo=timezone.utc)
    assert trading_day(winter, cfg).isoformat() == "2026-01-15"
    after = datetime(2026, 1, 15, 23, 30, tzinfo=timezone.utc)
    assert trading_day(after, cfg).isoformat() == "2026-01-16"


def test_vihesabu_vya_leo_vinareset_saa_sifuri(cfg):
    start = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
    counters = DayCounters(cfg, start)
    counters.record_closed_trade(-150.0, start)
    counters.record_closed_trade(100.0, start)
    assert (counters.today_loss, counters.today_profit) == (150.0, 100.0)

    next_day = datetime(2026, 8, 4, 22, 30, tzinfo=timezone.utc)  # 00:30 Berlin
    assert counters.roll_to(next_day) is True
    assert (counters.today_loss, counters.today_profit) == (0.0, 0.0)


def test_penalty_hairesetiwi_siku_mpya_inapoanza(cfg):
    """Vihesabu vya leo vinareset; `penalty` inafuata DD ya jumla — haireset."""
    start = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
    counters = DayCounters(cfg, start)
    counters.record_closed_trade(-200.0, start)
    account = counters.apply_to(AccountState(current_balance=9_800.0))
    assert compute_budget(account, cfg).budget == pytest.approx(400.0 - 100.0 - 200.0)

    counters.roll_to(datetime(2026, 8, 4, 22, 30, tzinfo=timezone.utc))
    tomorrow = counters.apply_to(AccountState(current_balance=9_800.0))
    result = compute_budget(tomorrow, cfg)
    assert result.penalty == pytest.approx(100.0)  # DD bado ipo
    assert result.budget == pytest.approx(300.0)  # hasara ya jana imeondoka
