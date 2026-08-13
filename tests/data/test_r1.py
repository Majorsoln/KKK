"""R1 — ukaguzi wa labels (T2: RS-04, DF-21, K1-07, DF-20).

Kesi hapa hazijaribu kwamba code inakimbia; zinajaribu kwamba **ripoti
inaweza kufeli**. Ukaguzi usioweza kufeli kimuundo ndilo somo kubwa la T1
(`clock_drift` 0/34,089), kwa hiyo kila kigezo cha R1 kina test inayolazimisha
FAIL — si PASS pekee.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import pytest

from src.data.labels import (
    SL_FIRST,
    TIMEOUT,
    TP_FIRST,
    resolve_m1_arrays,
    resolve_point,
)
from src.data.r1 import (
    attach_flags,
    base_rates,
    build_report,
    expected_r,
    fill_bootstrap,
    holdout_violations,
    quantile_mid_vs_trade,
    setup_vs_control,
    year_stability,
)

T0 = datetime(2020, 6, 1, 12, 0, tzinfo=timezone.utc)
SL_GRID = [0.5, 1.0]
TP_GRID = [0.5, 1.0]


# ===========================================================================
# Vipimo vipya vya toleo la 2 la labels
# ===========================================================================


def _ticks(n: int, bid_path, spread: float = 0.0002) -> pd.DataFrame:
    stamps = pd.date_range(T0, periods=n, freq="1s", tz="UTC")
    bid = np.asarray(bid_path, dtype=float)
    return pd.DataFrame(
        {
            "timestamp": stamps.astype("datetime64[us, UTC]"),
            "bid": bid,
            "ask": bid + spread,
        }
    )


HORIZON = pd.Timestamp(T0) + pd.Timedelta(hours=24)


def test_touch_price_ni_bei_ya_tick_si_bei_ya_barrier():
    """Gap ikiruka SL, `touch_price` inasoma bei ILIYOFIKIWA — ndiyo slippage.

    Bila hii, L-C ingelazimika kupita kwenye ticks mara ya pili kwa points
    52,000, au slippage ingekuwa dhana ya sifuri.
    """
    bid = np.full(600, 1.1000)
    bid[300:] = 1.0970                     # gap ya pips 30 chini ya SL zote
    point = resolve_point(_ticks(600, bid), pd.Timestamp(T0), HORIZON, 1, 0.0010, [1.0], [1.0])
    assert point is not None
    cell = point.cells[0]
    assert cell.outcome == SL_FIRST
    barrier = point.entry_trade - 1.0 * 0.0010
    assert cell.touch_price == pytest.approx(1.0970)
    # Bei imepita barrier — hilo ndilo lililopimwa, si kwamba iligusa tu.
    assert cell.touch_price < barrier


def test_quantile_ya_trade_iko_chini_ya_ya_mid_kwa_spread():
    """§5.1 — MID dhidi ya trade: tofauti ni spread, na inapimika.

    BUY inanunua kwa ask na kufunga kwa bid, kwa hiyo kipimo cha trade
    kinaanza chini kwa spread nzima. Uamuzi wa PD (MID) upimwe kwa namba.
    """
    bid = np.linspace(1.1000, 1.1010, 600)
    point = resolve_point(_ticks(600, bid), pd.Timestamp(T0), HORIZON, 1, 0.0010, [2.0], [2.0])
    assert point is not None
    assert point.quantile_y > point.quantile_y_trade
    # Tofauti ≈ spread ÷ ATR (units za ATR) — si namba ya bahati nasibu.
    assert point.quantile_y - point.quantile_y_trade == pytest.approx(0.0002 / 0.0010, rel=0.05)


def test_m1_inashindwa_pale_ticks_zinapojibu():
    """Bar MOJA inagusa SL na TP — ticks zinajua ipi ilianza, M1 haijui.

    Hii ndiyo hoja ya §5 ("bar haisemi ipi iligusa kwanza") ikiwa namba.
    """
    bid = np.full(180, 1.1000)
    bid[10] = 1.1030      # TP juu... (sekunde ya 10)
    bid[20] = 1.0970      # ...kisha SL chini — dakika ILE ILE
    ticks = _ticks(180, bid)
    stamps = ticks["timestamp"].astype("datetime64[us, UTC]").astype("int64").to_numpy()

    tick_point = resolve_point(ticks, pd.Timestamp(T0), HORIZON, 1, 0.0010, [1.0], [1.0])
    m1 = resolve_m1_arrays(
        stamps, ticks["bid"].to_numpy(), ticks["ask"].to_numpy(),
        pd.Timestamp(T0), HORIZON, 1, 0.0010, [1.0], [1.0],
    )
    assert tick_point.cells[0].outcome == TP_FIRST     # TP ilifika kwanza kweli
    assert m1.outcomes[0] == SL_FIRST                  # M1 inachagua tahadhari
    assert m1.ambiguous[0] is True                     # na inakiri kwamba haijui


def test_m1_inakubaliana_pale_hakuna_utata():
    bid = np.linspace(1.1000, 1.1040, 600)   # inapanda tu
    ticks = _ticks(600, bid)
    stamps = ticks["timestamp"].astype("datetime64[us, UTC]").astype("int64").to_numpy()
    m1 = resolve_m1_arrays(
        stamps, ticks["bid"].to_numpy(), ticks["ask"].to_numpy(),
        pd.Timestamp(T0), HORIZON, 1, 0.0010, SL_GRID, TP_GRID,
    )
    assert all(o == TP_FIRST for o in m1.outcomes)
    assert not any(m1.ambiguous)


# ===========================================================================
# Takwimu za R1
# ===========================================================================


def _barriers(rows: list[tuple], symbol: str = "EURUSD") -> pd.DataFrame:
    """(siku, sl, tp, outcome, is_setup) → frame ya cells."""
    return pd.DataFrame(
        [
            {
                "symbol": symbol,
                "decision_time": pd.Timestamp(day, tz="UTC"),
                "sl_atr": sl,
                "tp_atr": tp,
                "outcome": outcome,
                "tie_break": False,
                "timeout_return_r": 0.0 if outcome == TIMEOUT else None,
                "sl_pips": 10.0,
                "touch_past_pips": None if outcome == TIMEOUT else 0.1,
                "is_setup": is_setup,
                "is_control": not is_setup,
                "atr_pips": 12.0,
            }
            for day, sl, tp, outcome, is_setup in rows
        ]
    )


def test_base_rate_inaondoa_timeout_kabla_ya_jiometri():
    """RS-04 — p_tp ni kati ya ZILIZOFIKA, si kati ya zote.

    Timeout haikufika popote; kuijumuisha kungeshusha p_tp kwa utaratibu na
    kuonyesha "hitilafu ya jiometri" kila mara.
    """
    rows = [("2020-01-01", 1.0, 1.0, TP_FIRST, True)] * 40
    rows += [("2020-01-01", 1.0, 1.0, SL_FIRST, True)] * 40
    rows += [("2020-01-01", 1.0, 1.0, TIMEOUT, True)] * 20
    rates = base_rates(_barriers(rows))
    assert len(rates) == 1
    assert rates.loc[0, "p_tp"] == pytest.approx(0.5)       # 40/(40+40), si 40/100
    assert rates.loc[0, "geometry"] == pytest.approx(0.5)   # sl/(sl+tp)
    assert rates.loc[0, "timeout_frac"] == pytest.approx(0.2)


def test_jiometri_inatarajia_uwiano_wa_sl_kwa_sl_jumlisha_tp():
    rows = [("2020-01-01", 0.5, 2.0, TP_FIRST, True)] * 10
    rates = base_rates(_barriers(rows))
    assert rates.loc[0, "geometry"] == pytest.approx(0.2)   # 0.5/(0.5+2.0)


def test_ev_r_inahesabu_timeout_kama_darasa_si_sifuri():
    """§2.1 ya KAIROS-1 — madarasa MATATU. Timeout ina return yake."""
    frame = _barriers([("2020-01-01", 1.0, 2.0, TIMEOUT, True)])
    frame.loc[0, "timeout_return_r"] = 0.4
    assert expected_r(frame) == pytest.approx(0.4)
    # Gharama inashuka kwa R kwa `cost/sl_pips`, si kwa pips moja kwa moja.
    assert expected_r(frame, cost_pips=1.0) == pytest.approx(0.4 - 0.1)


def test_utulivu_unaonyesha_miaka_tofauti_kama_tofauti():
    rows = [("2020-01-01", 1.0, 1.0, TP_FIRST, True)] * 90
    rows += [("2020-01-01", 1.0, 1.0, SL_FIRST, True)] * 10
    rows += [("2021-01-01", 1.0, 1.0, TP_FIRST, True)] * 10
    rows += [("2021-01-01", 1.0, 1.0, SL_FIRST, True)] * 90
    years = year_stability(_barriers(rows))
    assert list(years["year"]) == [2020, 2021]
    assert years.loc[0, "p_tp"] == pytest.approx(0.9)
    assert years.loc[1, "p_tp"] == pytest.approx(0.1)


def test_setup_dhidi_ya_control_inatoa_tofauti_na_ukubwa_wake():
    """DF-20 — filter isiyotofautiana na nasibu haijafanya kazi yoyote."""
    rows = [("2020-01-01", 1.0, 1.0, TP_FIRST, True)] * 600
    rows += [("2020-01-01", 1.0, 1.0, SL_FIRST, True)] * 400
    rows += [("2020-01-01", 1.0, 1.0, TP_FIRST, False)] * 500
    rows += [("2020-01-01", 1.0, 1.0, SL_FIRST, False)] * 500
    out = setup_vs_control(_barriers(rows))
    assert out["setup"]["p_tp"] == pytest.approx(0.6)
    assert out["control"]["p_tp"] == pytest.approx(0.5)
    assert out["delta_p_tp"] == pytest.approx(0.1)
    assert out["delta_z"] > 3          # tofauti kubwa kuliko kelele yake


def test_fill_inatenganisha_stop_na_limit():
    """§5.3 — SL ni stop (umbali = hasara), TP ni limit (umbali si faida)."""
    frame = _barriers(
        [("2020-01-01", 1.0, 1.0, SL_FIRST, True)] * 10
        + [("2020-01-01", 1.0, 1.0, TP_FIRST, True)] * 10
    )
    frame.loc[:9, "touch_past_pips"] = 0.5      # stop imepita cap ya 0.3
    frame.loc[10:, "touch_past_pips"] = 2.0
    out = fill_bootstrap(frame, cap_stop=0.3)
    assert out["stop_sl"]["n"] == 10
    assert out["stop_sl"]["within_cap"] == pytest.approx(0.0)
    assert out["stop_sl"]["over_cap"] == 10
    assert out["limit_tp"]["p50"] == pytest.approx(2.0)
    assert out["market_prior"] == 0.98


def test_g2_inasimamisha_ripoti_badala_ya_kuonya(cfg):
    """Holdout ndani ya points = SIMAMA, si onyo — takwimu zisihesabiwe.

    Onyo lingeacha namba za holdout zikiwa zimeshaandikwa kwenye ripoti;
    baada ya hapo hakuna namna ya kuzisahau.
    """
    points = pd.DataFrame(
        {
            "symbol": ["EURUSD"],
            "decision_time": [pd.Timestamp("2025-01-01", tz="UTC")],
            "direction": [1],
            "is_setup": [True],
            "is_control": [False],
            "atr_pips": [10.0],
            "quantile_y": [0.1],
            "quantile_y_trade": [0.05],
            "spread_entry_pips": [0.5],
        }
    )
    barriers = _barriers([("2025-01-01", 1.0, 1.0, TP_FIRST, True)])
    report = build_report(cfg, points, barriers, date(2024, 4, 1))
    assert not report.ok
    assert any("G2" in p for p in report.problems)
    assert report.payload == {}          # hakuna takwimu hata moja


def test_cells_chache_kuliko_kikomo_zinafelisha_r1(cfg):
    """`min_labels_per_cell` ni kigezo cha T2, si pendekezo."""
    points = pd.DataFrame(
        {
            "symbol": ["EURUSD"] * 2,
            "decision_time": pd.to_datetime(["2020-01-01", "2020-01-02"], utc=True),
            "direction": [1, -1],
            "is_setup": [True, True],
            "is_control": [False, False],
            "atr_pips": [10.0, 10.0],
            "quantile_y": [0.1, 0.2],
            "quantile_y_trade": [0.05, 0.15],
            "spread_entry_pips": [0.5, 0.5],
        }
    )
    barriers = _barriers(
        [("2020-01-01", 1.0, 1.0, TP_FIRST, True), ("2020-01-02", 1.0, 1.0, SL_FIRST, True)]
    )
    report = build_report(cfg, points, barriers, date(2024, 4, 1))
    assert not report.ok
    assert any("chini ya" in p for p in report.problems)
    # Ripoti bado inatoka — FAIL yenye namba ni bora kuliko FAIL tupu.
    assert report.payload["totals"]["cells"] == 2


def test_tie_break_sifuri_inaelezwa_si_kupuuzwa(cfg):
    """0.00% si pengo la kipimo — §5.2 yenyewe inasema haiwezi kuwaka."""
    n = 300
    points = pd.DataFrame(
        {
            "symbol": ["EURUSD"] * n,
            "decision_time": pd.date_range("2020-01-01", periods=n, freq="1D", tz="UTC"),
            "direction": np.where(np.arange(n) % 2 == 0, 1, -1),
            "is_setup": [True] * n,
            "is_control": [False] * n,
            "atr_pips": [10.0] * n,
            "quantile_y": np.linspace(-1, 1, n),
            "quantile_y_trade": np.linspace(-1.2, 0.8, n),
            "spread_entry_pips": [0.5] * n,
        }
    )
    days = pd.date_range("2020-01-01", periods=n, freq="1D").strftime("%Y-%m-%d")
    rows = [
        (day, 1.0, 1.0, TP_FIRST if i % 2 else SL_FIRST, True) for i, day in enumerate(days)
    ]
    report = build_report(cfg, points, barriers=_barriers(rows), holdout_start=date(2024, 4, 1))
    assert report.ok
    assert any("HAIWEZI kuwaka" in note for note in report.notes)


def test_attach_flags_inaunganisha_kwa_symbol_na_muda():
    """Join kwa muda PEKEE ingechanganya symbols — decision_time inarudiwa."""
    points = pd.DataFrame(
        {
            "symbol": ["EURUSD", "GBPUSD"],
            "decision_time": pd.to_datetime(["2020-01-01", "2020-01-01"], utc=True),
            "is_setup": [True, False],
            "is_control": [False, True],
            "atr_pips": [10.0, 20.0],
        }
    )
    barriers = pd.concat(
        [
            _barriers([("2020-01-01", 1.0, 1.0, TP_FIRST, True)], symbol="EURUSD"),
            _barriers([("2020-01-01", 1.0, 1.0, TP_FIRST, True)], symbol="GBPUSD"),
        ],
        ignore_index=True,
    ).drop(columns=["is_setup", "is_control", "atr_pips"])
    joined = attach_flags(barriers, points)
    assert len(joined) == 2
    assert bool(joined.loc[joined["symbol"] == "EURUSD", "is_setup"].iloc[0])
    assert not bool(joined.loc[joined["symbol"] == "GBPUSD", "is_setup"].iloc[0])


def test_quantile_mid_vs_trade_inapewa_ishara_ya_trade():
    """BUY iko chini ya mid, SELL iko juu — bila ishara zinafutana hadi ~0.

    Hii ndiyo kasoro iliyopatikana kwenye R1 ya kwanza (2026-08-13): XAUUSD
    yenye spread ya pips 35 ilionyesha tofauti ya 0.0029 ATR, ikisomeka kama
    "uamuzi wa §5.1 hauna athari".
    """
    n = 100
    direction = np.where(np.arange(n) % 2 == 0, 1, -1)
    mid = np.linspace(-1, 1, n)
    # Gharama ya kweli: 0.05 ATR kwa KILA point, ikielekea upande wa trade.
    trade = mid - direction * 0.05
    points = pd.DataFrame(
        {
            "symbol": ["XAUUSD"] * n,
            "direction": direction,
            "quantile_y": mid,
            "quantile_y_trade": trade,
            "spread_entry_pips": [30.0] * n,
            "spread_exit_pips": [30.0] * n,
            "atr_pips": [300.0] * n,
        }
    )
    out = quantile_mid_vs_trade(points, [0.10, 0.50, 0.90])
    assert out.loc[0, "symbol"] == "XAUUSD"
    assert out.loc[0, "shift_p50"] == pytest.approx(0.05)
    assert out.loc[0, "shift_mean"] == pytest.approx(0.05)
    # Wastani wa pamoja unafuta gharama nzima — ndiyo sababu ya kipimo kipya.
    assert out.loc[0, "pooled_mean_diff"] == pytest.approx(0.0, abs=1e-9)
    # Ulinganisho huru: (30+30)/2/300 = 0.10 ... kwa hiyo shift_p50 ikitofautiana
    # sana na hii, mmoja kati ya viwili ni kosa. Hapa fixture imeweka 0.05.
    assert out.loc[0, "shift_expected_p50"] == pytest.approx(0.10)


def test_kigezo_cha_fold_kinaweza_kufeli_pale_pooled_haiwezi(cfg):
    """`min_labels_per_cell` pooled haiwezi kufeli — cha fold kinaweza.

    Kila point inapata cells zote 25, kwa hiyo pooled kila cell ina idadi ILE
    ILE: kigezo kinatoa jibu lile lile bila kujali data. Symbol yenye labels
    za kutosha kwa jumla lakini zilizojaa ndani ya fold MOJA haiwezi
    kufundishwa kwenye folds nyingine — na pooled haitasema neno.
    """
    from src.data.splits import SplitPlan

    from src.data.r1 import cell_coverage

    folds = SplitPlan.from_config(cfg).folds()
    # Points 300 zote ndani ya fold ya kwanza (2016) — nyingine tupu kabisa.
    days = pd.date_range("2016-02-01", periods=300, freq="1D").strftime("%Y-%m-%d")
    rows = [(day, 1.0, 1.0, TP_FIRST if i % 2 else SL_FIRST, True) for i, day in enumerate(days)]
    rows += [("2017-10-01", 1.0, 1.0, TP_FIRST, True)] * 5      # fold 2: chache mno
    coverage = cell_coverage(_barriers(rows), folds)

    kwa_fold = dict(zip(coverage["fold"], coverage["n_min"]))
    assert kwa_fold[1] == 300
    assert kwa_fold[2] == 5, "fold yenye njaa lazima ionekane"
    assert coverage["n_min"].min() < 200 <= 300


def test_holdout_violations_inahesabu_si_kudhani():
    points = pd.DataFrame(
        {"decision_time": pd.to_datetime(["2024-03-31", "2024-04-01", "2025-01-01"], utc=True)}
    )
    assert holdout_violations(points, date(2024, 4, 1)) == 2
