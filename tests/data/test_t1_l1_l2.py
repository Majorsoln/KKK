"""T1 — DF-05..DF-08, DF-14: L1 checks, L2 bars, as-of, sentinel, splits."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest

from src.data.asof import asof_bar, asof_snapshot, assert_no_future_bars, decision_points
from src.data.bars import build_all_timeframes, build_bars, check_ohlc_sanity
from src.data.quality import (
    FAIL_BAD_TIMESTAMPS,
    FAIL_CLOCK_DRIFT,
    FAIL_INTRASESSION_GAP,
    FAIL_LOW_COVERAGE,
    FAIL_QUOTE,
    FAIL_STALE_FEED,
    check_clock_drift,
    check_coverage,
    check_gaps,
    check_monotonicity,
    check_quote_sanity,
    check_session_match,
    check_stale_feed,
)
from src.data.sentinel import run_sentinel, shuffle_future
from src.data.session_calendar import (
    KIND_FULL,
    KIND_PARTIAL,
    DayObservation,
    build_calendar,
    compare_with_assumed,
)
from src.data.splits import HoldoutViolation, SplitPlan, days_of


def _ticks(start: datetime, count: int, step_s: float = 1.0, spread: float = 0.0001):
    ts = pd.date_range(start, periods=count, freq=pd.Timedelta(seconds=step_s), tz="UTC")
    bid = pd.Series(1.1000 + pd.Series(range(count)) * 0.00001)
    return pd.DataFrame(
        {
            "timestamp": ts.astype("datetime64[us, UTC]"),
            "bid": bid.values,
            "ask": (bid + spread).values,
            "bid_vol": [1.0] * count,
            "ask_vol": [1.0] * count,
        }
    )


# ===========================================================================
# DF-05 — L1 checks 8 (spec §3)
# ===========================================================================


def test_check1_coverage():
    assert check_coverage(rows=995, expected_rows=1000, min_coverage=0.995).passed
    feli = check_coverage(rows=900, expected_rows=1000, min_coverage=0.995)
    assert not feli.passed and feli.reason == FAIL_LOW_COVERAGE


def test_check1_bila_matarajio_haihukumu():
    """Kalenda isipojua siku, coverage HAIHUKUMU — si kupita kwa uwongo."""
    result = check_coverage(rows=10, expected_rows=0, min_coverage=0.995)
    assert result.passed and "haijahukumiwa" in result.detail


def test_check2_monotonicity_inanasa_duplicate_na_kurudi_nyuma():
    frame = _ticks(datetime(2026, 8, 3, tzinfo=timezone.utc), 5)
    assert check_monotonicity(frame).passed

    vibaya = frame.copy()
    vibaya.loc[3, "timestamp"] = vibaya.loc[1, "timestamp"]
    result = check_monotonicity(vibaya)
    assert not result.passed and result.reason == FAIL_BAD_TIMESTAMPS


def test_check2_duplicate_chache_za_tick_feed_hazifelishi():
    """MT5 inatoa quotes mbili kwenye µs moja — ni kawaida, si kasoro."""
    frame = _ticks(datetime(2026, 8, 3, tzinfo=timezone.utc), 10_000, step_s=1.0)
    frame.loc[5000, "timestamp"] = frame.loc[4999, "timestamp"]  # duplicate MOJA
    assert check_monotonicity(frame, max_duplicate_frac=0.001).passed
    assert not check_monotonicity(frame, max_duplicate_frac=0.0).passed


def test_check2_kurudi_nyuma_hakuvumiliwi_hata_kwa_kikomo_kikubwa():
    frame = _ticks(datetime(2026, 8, 3, tzinfo=timezone.utc), 10_000, step_s=1.0)
    frame.loc[5000, "timestamp"] = frame.loc[10, "timestamp"]
    result = check_monotonicity(frame, max_duplicate_frac=0.5)
    assert not result.passed and result.reason == FAIL_BAD_TIMESTAMPS


def test_check5_zero_spread_inatofautishwa_na_crossed():
    """`bid == ask` na `bid > ask` zote zinafeli, lakini si kasoro moja."""
    frame = _ticks(datetime(2026, 8, 3, tzinfo=timezone.utc), 5)
    sifuri = frame.copy()
    sifuri.loc[2, "ask"] = sifuri.loc[2, "bid"]
    result = check_quote_sanity(sifuri, max_spread_pips=50.0, pip=0.0001)
    assert not result.passed
    assert "zero_spread=1" in result.detail and "crossed=0" in result.detail


def test_check3_gaps():
    frame = _ticks(datetime(2026, 8, 3, tzinfo=timezone.utc), 10, step_s=1.0)
    assert check_gaps(frame, max_gap_seconds=60).passed

    frame.loc[5:, "timestamp"] = frame.loc[5:, "timestamp"] + pd.Timedelta(hours=3)
    result = check_gaps(frame, max_gap_seconds=3600)
    assert not result.passed and result.reason == FAIL_INTRASESSION_GAP


def test_check5_quote_sanity_inanasa_crossed_na_spread_kubwa():
    frame = _ticks(datetime(2026, 8, 3, tzinfo=timezone.utc), 5)
    assert check_quote_sanity(frame, max_spread_pips=50.0, pip=0.0001).passed

    crossed = frame.copy()
    crossed.loc[2, "ask"] = crossed.loc[2, "bid"] - 0.0001
    result = check_quote_sanity(crossed, max_spread_pips=50.0, pip=0.0001)
    assert not result.passed and result.reason == FAIL_QUOTE

    wide = _ticks(datetime(2026, 8, 3, tzinfo=timezone.utc), 5, spread=0.01)
    assert not check_quote_sanity(wide, max_spread_pips=50.0, pip=0.0001).passed


def test_check6_session_match_inanasa_dst():
    frame = _ticks(datetime(2026, 8, 3, 7, 0, tzinfo=timezone.utc), 60, step_s=60)
    expected_open = datetime(2026, 8, 3, 7, 0, tzinfo=timezone.utc)
    expected_close = datetime(2026, 8, 3, 7, 59, tzinfo=timezone.utc)
    assert check_session_match(frame, expected_open, expected_close, 15).passed

    # Saa moja ya kuhama (DST) — inazidi uvumilivu wa dakika 15.
    shifted = expected_open + timedelta(hours=1)
    assert not check_session_match(frame, shifted, expected_close, 15).passed


def test_check7_clock_drift_inakataa_tick_ya_baadaye():
    frame = _ticks(datetime.now(timezone.utc) + timedelta(hours=2), 3)
    result = check_clock_drift(frame)
    assert not result.passed and result.reason == FAIL_CLOCK_DRIFT


def test_check7_inakataa_timestamp_isiyo_utc():
    frame = _ticks(datetime(2026, 8, 3, tzinfo=timezone.utc), 3)
    frame["timestamp"] = frame["timestamp"].dt.tz_convert("Europe/Berlin")
    assert not check_clock_drift(frame).passed


def test_check8_stale_feed_inapima_muda_si_idadi_ya_ticks():
    """Ticks 40 zenye quote moja kwa dakika = soko tulivu. Nusu saa = feed imeganda."""
    frame = _ticks(datetime(2026, 8, 3, tzinfo=timezone.utc), 1200, step_s=1.0)
    assert check_stale_feed(frame, max_stale_seconds=1800).passed

    # Ticks nyingi mno, quote ile ile, kwa dakika 20 — bado ni soko tulivu.
    tulivu = _ticks(datetime(2026, 8, 3, tzinfo=timezone.utc), 1200, step_s=1.0)
    tulivu.loc[:, "bid"] = 1.1
    tulivu.loc[:, "ask"] = 1.1001
    assert check_stale_feed(tulivu, max_stale_seconds=1800).passed, "dakika 20 < nusu saa"

    # Saa moja bila mabadiliko — hii ndiyo feed iliyoganda.
    ganda = _ticks(datetime(2026, 8, 3, tzinfo=timezone.utc), 3600, step_s=1.0)
    ganda.loc[:, "bid"] = 1.1
    ganda.loc[:, "ask"] = 1.1001
    result = check_stale_feed(ganda, max_stale_seconds=1800)
    assert not result.passed and result.reason == FAIL_STALE_FEED


def test_check8_ya_bars_iko_l2():
    """Kipimo cha spec (`high == low` mfululizo) kinahitaji bars — kiko L2."""
    from src.data.bars import check_flat_bars

    ticks = _ticks(datetime(2026, 8, 3, tzinfo=timezone.utc), 3600, step_s=1.0)
    bars = build_bars(ticks, "M5", "EURUSD")
    assert check_flat_bars(bars, max_flat=3).passed

    ganda = bars.copy()
    ganda.loc[:, "high"] = ganda["low"]
    result = check_flat_bars(ganda, max_flat=3)
    assert not result.passed and result.reason == FAIL_STALE_FEED


# ===========================================================================
# RS-03 — kalenda kutoka DATA (spec §3)
# ===========================================================================


def test_kalenda_inanasa_siku_ya_nusu_bila_kuiorodhesha():
    """Sikukuu ya nusu-siku inagunduliwa kwa DATA, si kwa orodha ya mkono."""
    obs = [
        DayObservation(date(2026, 12, d), ticks=100_000, first_ts=None, last_ts=None)
        for d in (21, 22, 23, 28, 29, 30)
    ]
    obs.append(DayObservation(date(2026, 12, 24), ticks=8_000, first_ts=None, last_ts=None))
    cal = build_calendar(obs, partial_frac=0.25)
    assert cal.kind_of(date(2026, 12, 23)) == KIND_FULL
    assert cal.kind_of(date(2026, 12, 24)) == KIND_PARTIAL
    assert "2026-12-24" in cal.partial_days()


def _wiki_za_fx(weeks: int = 8, symbol: str = "EURUSD") -> list[DayObservation]:
    """Wiki halisi za FX: Jumatatu–Alhamisi hadi usiku wa manane, Ijumaa 21:00."""
    obs: list[DayObservation] = []
    monday = date(2026, 1, 5)  # Jumatatu
    for week in range(weeks):
        for offset in range(5):
            day = monday + timedelta(days=week * 7 + offset)
            ijumaa = offset == 4
            minutes = 21 * 60 if ijumaa else 24 * 60
            start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
            obs.append(
                DayObservation(
                    day=day,
                    ticks=minutes * 40,
                    first_ts=start,
                    last_ts=start + timedelta(minutes=minutes - 1),
                    symbol=symbol,
                    minutes=minutes,
                )
            )
    return obs


def test_ijumaa_inapimwa_kwa_ijumaa_nyingine_si_kwa_wiki_nzima():
    """Soko linafunga 21:00 Ijumaa: dakika 87.5% na close dakika 180 mapema.

    Kupima Ijumaa kwa wastani wa Jumatatu–Alhamisi kunaifelisha kila wiki —
    yaani asilimia 20 ya siku zote za trading, kwa kipimo kibaya pekee.
    """
    cal = build_calendar(_wiki_za_fx())
    ijumaa = date(2026, 2, 6)
    jumatatu = date(2026, 2, 2)
    assert ijumaa.weekday() == 4 and jumatatu.weekday() == 0

    assert cal.expected_minutes("EURUSD", ijumaa) == 21 * 60
    assert cal.expected_minutes("EURUSD", jumatatu) == 24 * 60

    _, close = cal.expected_session("EURUSD", ijumaa)
    assert close.hour == 20 and close.minute == 59, "close ya Ijumaa, si ya Alhamisi"

    # Kwa matarajio haya, Ijumaa ya kawaida inapita checks zote mbili.
    assert check_coverage(21 * 60, cal.expected_minutes("EURUSD", ijumaa), 0.995).passed


def test_siku_haiwezi_kujiwekea_kizingiti_chake():
    """Siku iliyokatika ikiingia kwenye matarajio yake, ingepita daima."""
    obs = _wiki_za_fx()
    mbaya = date(2026, 2, 4)  # Jumatano iliyokatika nusu
    for item in obs:
        if item.day == mbaya:
            item.minutes = 12 * 60
            item.ticks = 12 * 60 * 40
    cal = build_calendar(obs)
    assert cal.expected_minutes("EURUSD", mbaya) == 24 * 60, "majirani, si yenyewe"
    assert not check_coverage(12 * 60, cal.expected_minutes("EURUSD", mbaya), 0.995).passed


def test_kalenda_ya_data_dhidi_ya_ya_kudhaniwa():
    from src.data.calendar import TradingCalendar

    obs = [
        DayObservation(date(2026, 8, d), ticks=50_000, first_ts=None, last_ts=None)
        for d in (3, 4, 5, 6)
    ]
    obs.append(DayObservation(date(2026, 8, 9), ticks=1_000, first_ts=None, last_ts=None))
    cal = build_calendar(obs)
    diff = compare_with_assumed(cal, TradingCalendar())
    assert "2026-08-07" in diff["silent_but_expected"], "Ijumaa haina data — inaripotiwa"
    assert "2026-08-09" in diff["active_but_excluded"], "Jumapili ina data — inaripotiwa"


# ===========================================================================
# DF-06 — L2 bars kutoka ticks (spec §4)
# ===========================================================================


def test_bars_zinajengwa_kutoka_ticks_na_zinabeba_spread_stats():
    ticks = _ticks(datetime(2026, 8, 3, tzinfo=timezone.utc), 3600, step_s=1.0)
    bars = build_bars(ticks, "M15", "EURUSD")
    assert len(bars) == 4  # saa moja = M15 nne
    assert set(["spread_mean", "spread_p50", "spread_p95", "spread_max"]) <= set(bars.columns)
    assert (bars["n_ticks"] == 900).all()
    assert bars["spread_mean"].iloc[0] == pytest.approx(1.0, abs=0.01)  # pip moja


def test_tf_zote_zinatoka_ticks_zile_zile_kwa_hiyo_zinalingana():
    """Spec §4: chanzo kimoja → D1..M5 zinalingana kikamilifu."""
    ticks = _ticks(datetime(2026, 8, 3, tzinfo=timezone.utc), 7200, step_s=1.0)
    tfs = build_all_timeframes(ticks, "EURUSD", ["H2", "H1", "M30"])
    assert tfs["H2"]["n_ticks"].sum() == tfs["H1"]["n_ticks"].sum() == tfs["M30"]["n_ticks"].sum()
    assert tfs["H1"].iloc[0]["open"] == tfs["M30"].iloc[0]["open"]


def test_bar_bila_tick_haipo_si_bar_tupu():
    """Spec §3: hakuna data ya kubuni — bar isiyo na tick HAIANDIKWI."""
    ticks = pd.concat(
        [
            _ticks(datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc), 60, step_s=1),
            _ticks(datetime(2026, 8, 3, 2, 0, tzinfo=timezone.utc), 60, step_s=1),
        ],
        ignore_index=True,
    )
    bars = build_bars(ticks, "H1", "EURUSD")
    assert len(bars) == 2, "saa ya 01:00 haina ticks — haipaswi kuwepo"


def test_check4_ohlc_sanity_inafanyika_l2():
    ticks = _ticks(datetime(2026, 8, 3, tzinfo=timezone.utc), 600, step_s=1)
    bars = build_bars(ticks, "M5", "EURUSD")
    assert check_ohlc_sanity(bars).passed

    vibaya = bars.copy()
    vibaya.loc[vibaya.index[0], "high"] = vibaya.iloc[0]["low"] - 1.0
    assert not check_ohlc_sanity(vibaya).passed


# ===========================================================================
# DF-07 — AS-OF (spec §4.1)
# ===========================================================================


def test_asof_mfano_wa_spec():
    """Spec §4.1: uamuzi wa H1 saa 10:00 → D1 ya jana, H4 ya 08:00, M15 ya 09:45."""
    # Data inaanza 08-01 ili D1 ya JANA iwepo ikiwa imefungwa — ndivyo spec inavyodai.
    ticks = _ticks(datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc), 60 * 60 * 36, step_s=1)
    tfs = build_all_timeframes(ticks, "EURUSD", ["D1", "H4", "H1", "M15"])
    t = pd.Timestamp("2026-08-02 10:00", tz="UTC")

    snapshot = asof_snapshot(tfs, t)
    assert snapshot["D1"].name == pd.Timestamp("2026-08-01", tz="UTC"), "D1 ya JANA"
    assert snapshot["H4"].name == pd.Timestamp("2026-08-02 04:00", tz="UTC"), "inafungwa 08:00"
    assert snapshot["M15"].name == pd.Timestamp("2026-08-02 09:45", tz="UTC")
    assert_no_future_bars(tfs, t)


def test_asof_bar_isiyofungwa_haitumiki_kamwe():
    ticks = _ticks(datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc), 3600, step_s=1)
    bars = build_bars(ticks, "H1", "EURUSD")
    # Bar ya 00:00 inafungwa 01:00; saa 00:30 haipaswi kuonekana bado.
    assert asof_bar(bars, "H1", pd.Timestamp("2026-08-03 00:30", tz="UTC")) is None
    assert asof_bar(bars, "H1", pd.Timestamp("2026-08-03 01:00", tz="UTC")) is not None


def test_decision_points_ni_close_za_h1():
    ticks = _ticks(datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc), 7200, step_s=1)
    bars = build_bars(ticks, "H1", "EURUSD")
    points = decision_points(bars)
    assert list(points) == [
        pd.Timestamp("2026-08-03 01:00", tz="UTC"),
        pd.Timestamp("2026-08-03 02:00", tz="UTC"),
    ]


# ===========================================================================
# DF-08 — SENTINEL (spec §4.2)
# ===========================================================================


def _bars_for_sentinel():
    ticks = _ticks(datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc), 3600 * 6, step_s=1)
    return {"H1": build_bars(ticks, "H1", "EURUSD")}


def test_sentinel_inapita_kwa_feature_ya_as_of():
    """Feature inayotii §4.1 haibadiliki data ya baadaye ikichanganywa."""

    def salama(bars_by_tf, t):
        bar = asof_bar(bars_by_tf["H1"], "H1", t)
        return {"close_asof": float(bar["close"]) if bar is not None else None}

    bars = _bars_for_sentinel()
    result = run_sentinel(bars, [pd.Timestamp("2026-08-03 03:00", tz="UTC")], salama)
    assert result.passed, result.leaked
    result.raise_if_leaked()


def test_sentinel_inanasa_feature_inayosoma_baadaye():
    """Feature inayosoma bar ya baadaye INAGUNDULIWA — build inasimama."""

    def inavuja(bars_by_tf, t):
        future = bars_by_tf["H1"][bars_by_tf["H1"].index > t]
        return {"close_ya_baadaye": float(future["close"].iloc[0]) if len(future) else None}

    bars = _bars_for_sentinel()
    result = run_sentinel(bars, [pd.Timestamp("2026-08-03 02:00", tz="UTC")], inavuja)
    assert not result.passed
    assert result.leaked[0]["feature"] == "close_ya_baadaye"
    with pytest.raises(AssertionError, match="UKIUKAJI WA §4.2"):
        result.raise_if_leaked()


def test_shuffle_future_haigusi_zilizopita():
    bars = _bars_for_sentinel()["H1"]
    t = pd.Timestamp("2026-08-03 02:00", tz="UTC")
    shuffled = shuffle_future(bars, t, seed=1)
    kabla = bars.index <= t
    assert (bars.loc[kabla, "close"].values == shuffled.loc[kabla, "close"].values).all()


# ===========================================================================
# DF-14 — SPLITS + lango G2 (spec §7, DATA_SPLIT_PLAN)
# ===========================================================================


def test_splits_zinatoka_config_pekee(cfg):
    plan = SplitPlan.from_config(cfg)
    assert plan.data_start == date(2016, 1, 4)
    assert plan.trainval_end == date(2024, 3, 31)
    assert plan.holdout_start == date(2024, 4, 1)
    assert plan.embargo_bars == 36  # horizon 24 × 1.5
    assert len(plan.folds()) == 5


def test_folds_zinapurgwa_kuzunguka_validation(cfg):
    plan = SplitPlan.from_config(cfg)
    for fold in plan.folds():
        for train_start, train_end in fold.train_ranges:
            assert train_end < fold.val_start or train_start > fold.val_end, (
                f"train {train_start}→{train_end} inagusa validation ya F{fold.index}"
            )


def test_walk_forward_train_inaanzia_mwanzo(cfg):
    plan = SplitPlan.from_config(cfg)
    for fold in plan.walk_forward():
        assert fold.train_ranges[0][0] == plan.data_start


def test_g2_holdout_guard_inasimamisha_r0_r7(cfg):
    plan = SplitPlan.from_config(cfg)
    plan.assert_trainval_only([date(2023, 5, 1), date(2020, 1, 6)], purpose="R2 screening")

    with pytest.raises(HoldoutViolation, match="UKIUKAJI WA G2"):
        plan.assert_trainval_only([date(2025, 1, 6)], purpose="R2 screening")


def test_g2_reserve_nayo_imezuiwa(cfg):
    plan = SplitPlan.from_config(cfg)
    assert plan.future_reserve_start == date(2026, 5, 1)
    with pytest.raises(HoldoutViolation):
        plan.assert_trainval_only([date(2026, 6, 1)], purpose="R1")


def test_kufungua_holdout_kunahitaji_sababu_na_idhini(cfg):
    plan = SplitPlan.from_config(cfg)
    with pytest.raises(HoldoutViolation):
        plan.open_holdout(reason="", authorised_by="PD")
    tukio = plan.open_holdout(reason="R8 attestation", authorised_by="PD")
    assert tukio["event"] == "holdout_opened"
    assert tukio["holdout_start"] == "2024-04-01"


def test_random_split_ni_marufuku(cfg):
    cfg.raw["splits"]["random_split"] = True
    with pytest.raises(ValueError, match="UVUJAJI"):
        SplitPlan.from_config(cfg)


def test_days_of_inatoa_siku_za_kipekee():
    index = pd.date_range("2026-08-03", periods=49, freq="1h", tz="UTC")
    assert days_of(index) == [date(2026, 8, 3), date(2026, 8, 4), date(2026, 8, 5)]
