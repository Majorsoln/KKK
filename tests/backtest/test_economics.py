"""Lango la uchumi — DOCTRINE §8.4, R20.

Lango la bei nafuu linalokata wagombea wengi kwa hesabu ya mstari mmoja. Thamani
yake ni kupunguza idadi ya majaribio (§9) — kwa hiyo makosa hapa hayaonekani
kama hasara, yanaonekana kama sakafu ya kelele iliyo juu kupita kiasi.
"""

from __future__ import annotations

import math

import pytest

from src.backtest import economics as E


def _eco(edge, *, research=1.0, live=1.0, n=10) -> E.Economics:
    return E.Economics(n_trades=n, gross_edge_pips=edge,
                       research_cost_pips=research, live_sizing_cost_pips=live)


# ===========================================================================
# §8.4 — 2×, na mamlaka ni `live_sizing_cost`
# ===========================================================================


def test_edge_chini_ya_mara_mbili_inakataliwa():
    assert not _eco(1.9, live=1.0).passes
    assert _eco(1.9, live=1.0).reject_reason == E.REJECT_THIN_EDGE


def test_edge_ya_mara_mbili_KAMILI_inapita():
    """`2×` ndio dai; kufikia ni kutosha. Lango si `>` bali `≥`."""
    assert _eco(2.0, live=1.0).passes


def test_LIVE_ndiyo_yenye_mamlaka_si_RESEARCH():
    """R20 — swali si 'ilikuwaje', bali 'RCE itaisizisha kwa gharama ipi'.

    Hapa research ingepitisha (`3.0×`) lakini live inakataa (`1.5×`). Kutumia
    ya matumaini kimya ndiyo dhana inayofanya mfumo uonekane wenye faida.
    """
    eco = _eco(3.0, research=1.0, live=2.0)
    assert eco.edge_over_research == pytest.approx(3.0)
    assert eco.edge_over_live == pytest.approx(1.5)
    assert not eco.passes


def test_cost_sensitivity_ni_live_kwa_research():
    eco = _eco(3.0, research=1.0, live=1.4)
    assert eco.cost_sensitivity == pytest.approx(1.4)


def test_bila_trades_ni_NO_TRADES_si_kupita():
    eco = E.Economics(0, float("nan"), float("nan"), float("nan"))
    assert eco.reject_reason == E.REJECT_NO_TRADES and not eco.passes


def test_gharama_SIFURI_haipitishi():
    """Gharama sifuri si nafuu — ni gharama isiyopimwa.

    Kupitisha hapo kungekuwa kupitisha kwa sababu ya kutokujua, ambayo ndiyo
    hasa §2 inayoikataa.
    """
    eco = _eco(50.0, research=0.0, live=0.0)
    assert math.isnan(eco.edge_over_live)
    assert not eco.passes and eco.reject_reason == E.REJECT_THIN_EDGE


def test_edge_hasi_inakataliwa():
    assert not _eco(-5.0, live=1.0).passes


def test_inajielezea():
    text = _eco(3.0, live=1.0).render()
    assert "edge/live" in text and "SAWA" in text
    assert _eco(3.0, live=1.0).to_json()["required"] == E.KIZIDISHI


# ===========================================================================
# `measure` juu ya BacktestResult halisi
# ===========================================================================


def test_measure_inatumia_utambulisho_wa_11_4(cfg_risk):
    """`gross_mid = gross_pips + spread_pips` — si hesabu mpya ya bei.

    `execution` tayari inathibitisha utambulisho huo kwa `reconciliation_error`.
    Njia ya tatu ingekuwa nafasi ya tatu ya kukosea.
    """
    from tests.backtest.test_engine import _endesha

    out = _endesha([1, -1, 1], cfg_risk)
    eco = E.measure(out)

    assert eco.n_trades == out.n_trades
    kwa_mkono = sum(t.path.gross_pips + t.path.spread_pips
                    for t in out.trades) / out.n_trades
    assert eco.gross_edge_pips == pytest.approx(kwa_mkono)


def test_measure_bila_trades_ni_NO_TRADES(cfg_risk):
    from src.backtest.engine import BacktestResult
    from src.backtest.ledger import Ledger

    tupu = BacktestResult(strategy_id="x", symbol="EURUSD", ledger=Ledger())
    assert E.measure(tupu).reject_reason == E.REJECT_NO_TRADES


def test_research_inajumuisha_slippage_ILIYOTOKEA(cfg_risk):
    """`research_cost` ni ILIYOTOKEA, kwa hiyo slippage ni ya path si cap."""
    from tests.backtest.test_engine import _endesha

    out = _endesha([1, -1], cfg_risk)
    eco = E.measure(out)
    kwa_mkono = sum(
        t.path.spread_pips + abs(t.path.fill_slippage_pips)
        + t.path.commission_pips + t.path.swap_pips for t in out.trades
    ) / out.n_trades
    assert eco.research_cost_pips == pytest.approx(kwa_mkono)


def test_live_inatoka_kwa_RCE_si_kwa_path(cfg_risk):
    from tests.backtest.test_engine import _endesha

    out = _endesha([1, -1], cfg_risk)
    eco = E.measure(out)
    assert eco.live_sizing_cost_pips == pytest.approx(
        sum(t.attempt.cost_pips for t in out.trades) / out.n_trades
    )
