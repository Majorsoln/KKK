"""RCE-05, RCE-07, RCE-09..RCE-12 — gate, sizing, swap, fill-rate."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.rce.cost import (
    SWAP_MODE_CURRENCY,
    SWAP_MODE_INTEREST,
    SWAP_MODE_POINTS,
    SymbolSpec,
    count_rollovers,
    pip_value_account,
    swap_pips,
    swap_value_per_night,
)
from src.rce.gate import (
    REJECT_DAILY_LOSS,
    REJECT_MAX_CORRELATED,
    REJECT_MAX_OPEN,
    REJECT_MAX_SPREAD,
    REJECT_MAX_TOTAL_DD,
    REJECT_NEWS,
    GateContext,
    correlation_groups_of,
    evaluate_gate,
)
from src.rce.sizing import REJECT_BELOW_MIN_LOT, compute_lots

SPEC = SymbolSpec(
    symbol="EURUSD",
    point=0.00001,
    contract_size=100_000,
    volume_min=0.01,
    volume_step=0.01,
    volume_max=50.0,
)


# ===========================================================================
# RCE-07 — swap: modes tatu + triple Jumatano (spec §3.4)
# ===========================================================================


@pytest.mark.parametrize(
    "mode, swap, expected",
    [
        (SWAP_MODE_CURRENCY, -2.5, -2.5),  # thamani inatumika moja kwa moja
        (SWAP_MODE_POINTS, -8.0, -8.0 * 0.00001 * 100_000),  # swap × point × contract
        (SWAP_MODE_INTEREST, -3.0, (-3.0 / 100.0) * 100_000),  # (swap ÷ 100) × contract
    ],
)
def test_rce07_modes_zote_tatu(mode, swap, expected):
    """Spec §3.4 hatua 2: CURRENCY · POINTS · INTEREST."""
    spec = SymbolSpec(
        symbol="EURUSD",
        point=0.00001,
        contract_size=100_000,
        volume_min=0.01,
        volume_step=0.01,
        volume_max=50.0,
        swap_long=swap,
        swap_mode=mode,
    )
    assert swap_value_per_night("BUY", spec) == pytest.approx(expected)


def test_rce07_mwelekeo_unachagua_swap_sahihi():
    """Spec §3.4 hatua 1: BUY → swap_long · SELL → swap_short."""
    spec = SymbolSpec(
        symbol="EURUSD",
        point=0.00001,
        contract_size=100_000,
        volume_min=0.01,
        volume_step=0.01,
        volume_max=50.0,
        swap_long=-1.0,
        swap_short=+0.4,
        swap_mode=SWAP_MODE_CURRENCY,
    )
    assert swap_value_per_night("BUY", spec) == pytest.approx(-1.0)
    assert swap_value_per_night("SELL", spec) == pytest.approx(0.4)


def test_rce07_triple_jumatano_ni_mara_tatu():
    """Spec §3.4 hatua 3: Jumatano → Alhamisi = swap × 3."""
    spec = SymbolSpec(
        symbol="EURUSD",
        point=0.00001,
        contract_size=100_000,
        volume_min=0.01,
        volume_step=0.01,
        volume_max=50.0,
        swap_long=-1.0,
        swap_mode=SWAP_MODE_CURRENCY,
    )
    kawaida = swap_pips("BUY", spec, nights=3, pip_value_per_lot=10.0)
    na_triple = swap_pips("BUY", spec, nights=3, pip_value_per_lot=10.0, triple_nights=1)
    assert kawaida == pytest.approx(-3.0 / 10.0)
    assert na_triple == pytest.approx(-5.0 / 10.0), "usiku 2 + (1 × 3) = 5"


def test_rce07_intraday_haina_swap():
    """Spec §3.4 hatua 4: H1 intraday = usiku 0 → swap_pips = 0."""
    assert swap_pips("BUY", SPEC, nights=0, pip_value_per_lot=10.0) == 0.0


def test_rce07_count_rollovers_inahesabu_jumatano_moja():
    """Jumatano→Alhamisi ndiyo triple; nyingine ni za kawaida."""
    entry = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)  # Jumatatu
    exit_ = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)  # Ijumaa
    normal, triple = count_rollovers(entry, exit_)
    assert triple == 1, "usiku wa Jumatano→Alhamisi"
    assert normal == 3


# ===========================================================================
# RCE-08 — pip conversion (spec §3.5)
# ===========================================================================


def test_rce08_pip_value_inabadilishwa_kwa_sarafu_ya_akaunti():
    """Spec §3.5: akaunti USD, EURGBP → pip_value inategemea GBPUSD."""
    assert pip_value_account(10.0, quote_to_account_rate=1.27) == pytest.approx(12.7)
    assert pip_value_account(10.0) == pytest.approx(10.0)


# ===========================================================================
# RCE-09 — lots + mipaka ya broker (spec §4)
# ===========================================================================


def test_rce09_hasara_kwenye_sl_ni_hasa_risk_iliyotengwa():
    """Spec §4: gharama iko denominator, kwa hiyo SL ikigongwa hasara = risk."""
    result = compute_lots(
        risk_per_trade=100.0, sl_pips=20.0, cost_pips=2.0, pip_value_acct=10.0, spec=SPEC
    )
    assert result.lots_raw == pytest.approx(100.0 / (22.0 * 10.0))
    assert result.risk_at_stop <= 100.0


def test_rce09_lots_zinashushwa_kwa_volume_step():
    """Kuzungusha juu kungeongeza hasara juu ya risk — kwa hiyo tunashusha."""
    result = compute_lots(
        risk_per_trade=100.0, sl_pips=20.0, cost_pips=2.0, pip_value_acct=10.0, spec=SPEC
    )
    assert result.lots == pytest.approx(0.45)  # raw 0.4545 -> 0.45
    assert result.risk_at_stop < 100.0


def test_rce09_chini_ya_volume_min_ni_reject():
    """Spec §4: ikishuka chini ya `volume_min` → REJECT."""
    result = compute_lots(
        risk_per_trade=0.5, sl_pips=100.0, cost_pips=3.0, pip_value_acct=10.0, spec=SPEC
    )
    assert result.rejected
    assert result.reason == REJECT_BELOW_MIN_LOT
    assert result.lots == 0.0


def test_rce09_volume_max_inabana():
    result = compute_lots(
        risk_per_trade=1_000_000.0,
        sl_pips=10.0,
        cost_pips=1.0,
        pip_value_acct=10.0,
        spec=SPEC,
    )
    assert result.lots == pytest.approx(SPEC.volume_max)


# ===========================================================================
# RCE-10..RCE-12 — gate (spec §5, §5b)
# ===========================================================================


def _ctx(**kwargs) -> GateContext:
    base = dict(
        symbol="EURUSD",
        open_positions=0,
        open_symbols=(),
        current_balance=10_000.0,
        today_loss=0.0,
        spread_pips=1.0,
        news_imminent=False,
        now=datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
    )
    base.update(kwargs)
    return GateContext(**base)


def test_rce10_check1_max_open_trades(risk_cfg):
    assert evaluate_gate(risk_cfg, _ctx(open_positions=7)).reason == REJECT_MAX_OPEN
    assert evaluate_gate(risk_cfg, _ctx(open_positions=6)).passed


def test_rce10_check2_max_correlated_inaangalia_makundi_yote(risk_cfg):
    """Spec §5 check 2: **makundi YOTE ya pair**, si moja."""
    assert set(correlation_groups_of("EURUSD", risk_cfg.get("correlation_groups"))) == {
        "USD_group",
        "EUR_group",
    }
    decision = evaluate_gate(
        risk_cfg, _ctx(open_positions=3, open_symbols=("GBPUSD", "AUDUSD", "NZDUSD"))
    )
    assert decision.reason.startswith(REJECT_MAX_CORRELATED)
    assert "USD_group" in decision.reason


def test_rce10_check3_daily_loss_brake(risk_cfg):
    """Spec §5 check 3: hasara ≥ 0.75 × base **NA** positions wazi."""
    # base = 400; 0.75 × 400 = 300
    assert evaluate_gate(risk_cfg, _ctx(today_loss=300.0, open_positions=1)).reason == (
        REJECT_DAILY_LOSS
    )
    assert evaluate_gate(risk_cfg, _ctx(today_loss=300.0, open_positions=0)).passed, (
        "bila positions wazi, brake haitumiki (spec inasema NA)"
    )


def test_rce11_dd_inazuia_entries_mpya_pekee(risk_cfg):
    """Spec §5 check 4 + kumbukumbu ya PD: DD **HAIFUNGI** positions zilizo wazi."""
    decision = evaluate_gate(risk_cfg, _ctx(current_balance=8_900.0, open_positions=3))
    assert not decision.passed
    assert decision.reason == REJECT_MAX_TOTAL_DD
    assert "close" not in decision.to_log()["lifecycle"].lower(), (
        "gate inakataa ENTRY; haina mamlaka ya kufunga positions"
    )


def test_rce10_check5_max_spread(risk_cfg):
    assert evaluate_gate(risk_cfg, _ctx(spread_pips=2.5)).reason == REJECT_MAX_SPREAD
    assert evaluate_gate(risk_cfg, _ctx(spread_pips=2.0)).passed  # kikomo ni <=


def test_rce10_check6_news(risk_cfg):
    """`trade_news: true` kwenye config → news haizuii."""
    assert evaluate_gate(risk_cfg, _ctx(news_imminent=True)).passed
    risk_cfg.raw["trade_news"] = False
    assert evaluate_gate(risk_cfg, _ctx(news_imminent=True)).reason == REJECT_NEWS


def test_rce10_mpangilio_wa_ukaguzi_ni_wa_spec(risk_cfg):
    """Ukaguzi wa KWANZA unaoshindwa ndio unaotoa sababu (spec §5)."""
    decision = evaluate_gate(
        risk_cfg,
        _ctx(open_positions=7, current_balance=8_000.0, spread_pips=99.0, today_loss=999.0),
    )
    assert decision.reason == REJECT_MAX_OPEN, "check 1 inatangulia zote"


def test_rce10_reject_ina_fingerprint_ya_config(risk_cfg):
    """Spec §5: rekodi ya REJECTED ina sababu + config-fingerprint."""
    log = evaluate_gate(risk_cfg, _ctx(open_positions=7)).to_log()
    assert log["lifecycle"] == "REJECTED"
    assert log["reason"] == REJECT_MAX_OPEN
    assert log["config_fingerprint"] == risk_cfg.config_hash
    assert log["checked_at"]


def test_rce12_gate_haina_kumbukumbu_ya_signal_iliyokataliwa(risk_cfg):
    """Spec §5b: hakuna foleni — kila wito ni tathmini MPYA, isiyo na historia."""
    ctx = _ctx(open_positions=7)
    kwanza = evaluate_gate(risk_cfg, ctx)
    assert not kwanza.passed

    # Hali ikibadilika, jibu linabadilika mara moja — hakuna kitu kilichohifadhiwa.
    pili = evaluate_gate(risk_cfg, _ctx(open_positions=0))
    assert pili.passed

    import src.rce.gate as gate_module

    hali = [
        name
        for name, value in vars(gate_module).items()
        if isinstance(value, (list, dict, set)) and not name.startswith("_")
    ]
    assert not hali, f"module ina hali inayodumu — §5b inakataza foleni: {hali}"
