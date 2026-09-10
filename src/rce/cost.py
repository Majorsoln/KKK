"""RCE-03..RCE-08 — `cost_pips` na vipengele vyake vinne (spec §3).

```
cost_pips = spread_pips + slippage_pips + commission_pips + swap_pips
```

RCE ndiyo **MAMLAKA** ya gharama (§4.2 ya KAIROS_1_STANDARD): namba hii ina
chanzo KIMOJA na matumizi MAWILI — EV-gate ya model na sizing ya RCE. Model
**haihesabu** yake.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence

# Spec §3.1: PipSize ni 0.01 kwa JPY na XAU; 0.0001 kwa nyingine.
_PIP_001_QUOTES = ("JPY",)
_PIP_001_BASES = ("XAU", "XAG")

# Spec §3.4 hatua 2 — modes za swap za MT5.
SWAP_MODE_POINTS = "POINTS"
SWAP_MODE_CURRENCY = "CURRENCY"
SWAP_MODE_INTEREST = "INTEREST"


def pip_size(symbol: str) -> float:
    """PipSize ya symbol (spec §3.1). JPY/XAU → 0.01; nyingine → 0.0001."""
    upper = symbol.upper()
    if any(upper.startswith(base) for base in _PIP_001_BASES):
        return 0.01
    if upper[3:6] in _PIP_001_QUOTES or upper.endswith(_PIP_001_QUOTES):
        return 0.01
    return 0.0001


# --------------------------------------------------------------------------
# RCE-03 — spread: MSETO wa H1 base + M5 spike-guard (spec §3.1)
# --------------------------------------------------------------------------


def spread_effective(
    h1_spreads: Sequence[float],
    m5_spreads: Sequence[float],
    cfg,
) -> float:
    """`max(wastani wa spread ya H1, p95 ya spread ya M5)` — spec §3.1.

    H1 ndiyo msingi kwa sababu entry inatokea kwenye bar ya H1; M5 inaongezwa
    kwa sababu H1 inaficha spikes za ndani ya bar. Kutumia M5 **peke yake** ni
    kudharau gharama → lots kubwa mno → EV ya bandia.
    """
    base_window = int(cfg.get("spread_model.base_window", 100))
    spike_window = int(cfg.get("spread_model.spike_window", 288))
    quantile = float(cfg.get("spread_model.spike_quantile", 0.95))

    base_slice = list(h1_spreads)[-base_window:] if base_window else list(h1_spreads)
    spike_slice = list(m5_spreads)[-spike_window:] if spike_window else list(m5_spreads)

    spread_base = sum(base_slice) / len(base_slice) if base_slice else 0.0
    spread_vol_adj = _percentile(spike_slice, quantile) if spike_slice else 0.0

    combine = str(cfg.get("spread_model.combine", "max")).lower()
    if combine != "max":
        raise ValueError(
            f"`spread_model.combine` = {combine!r}; spec §3.1 inataka `max` "
            "(base ya H1 dhidi ya spike-guard ya M5)"
        )
    return max(spread_base, spread_vol_adj)


def _percentile(values: Iterable[float], q: float) -> float:
    """Percentile ya linear interpolation (sawa na `numpy.percentile` default)."""
    ordered = sorted(values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return float(ordered[0])
    position = q * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


# --------------------------------------------------------------------------
# RCE-04 — slippage: CAP, si utabiri (spec §3.2)
# --------------------------------------------------------------------------


def slippage_cap_pips(order_type: str, cfg, dynamic_estimate: float | None = None,
                      symbol: str | None = None) -> float:
    """`cap = min(dynamic(M5_vol), dhana ya backtest)` — INABANA TU (spec §3.2).

    Cap ikiruhusiwa **kulegea**, dhamana ya "live ≤ backtest" inavunjika na
    namba zilizothibitishwa hazingekuwa halali tena. Kwa hiyo `min`, si `max`.

    **Cap inaweza kuwa ya kila symbol (PD 2026-08-23).** Pips 0.1 ni point 1 kwa
    EURUSD na $0.001 kwa XAUUSD — chini ya tick moja ya dhahabu, kwa hiyo
    `order.deviation` ingekuwa **points 0** na karibu kila order ya dhahabu
    isingejaza. Namba moja kwa vyombo vyenye `pip` inayotofautiana mara 100
    haiwezi kuwa sahihi kwa vyote.

    Miundo miwili ya `risk.yaml` inakubalika:

    ```yaml
    slippage_cap_pips:            slippage_cap_pips:
      market:  0.1                  market:
      stop:    0.3                    default: 0.1
                                      XAUUSD:  12.0
    ```

    Muundo wa pili unapotumika, `symbol` ni **ya lazima**. Kuiacha na kurudisha
    `default` kimya kungetoa cap ya EURUSD kwa dhahabu — kosa ambalo halionekani
    hadi orders zianze kukataliwa live.
    """
    caps = cfg.get("slippage_cap_pips")
    key = order_type.lower()
    if key not in caps:
        raise ValueError(
            f"aina ya order {order_type!r} haipo kwenye `slippage_cap_pips` "
            f"({sorted(caps)}) — spec §3.2"
        )
    backtest_assumption = _cap_ya_symbol(caps[key], symbol, key)
    if not bool(cfg.get("slippage_cap_dynamic", True)) or dynamic_estimate is None:
        return backtest_assumption
    return min(float(dynamic_estimate), backtest_assumption)


def _cap_ya_symbol(entry, symbol: str | None, order_type: str) -> float:
    """Namba moja, au jedwali la symbols lenye `default`."""
    if not isinstance(entry, dict):
        return float(entry)
    if symbol is None:
        raise ValueError(
            f"`slippage_cap_pips.{order_type}` ni jedwali la symbols, kwa hiyo "
            f"`symbol` inahitajika. Bila yake, `default` ingetumika kimya kwa "
            f"symbol yenye cap yake — spec §3.2"
        )
    upper = symbol.upper()
    if upper in entry:
        return float(entry[upper])
    if "default" not in entry:
        raise ValueError(
            f"`slippage_cap_pips.{order_type}` halina `{upper}` wala `default` — spec §3.2"
        )
    return float(entry["default"])


def order_deviation_points(cap_pips: float, symbol: str, point: float) -> int:
    """`order.deviation` kwa POINTS — MT5 haitumii pips (spec §3.2)."""
    if point <= 0:
        raise ValueError("`point` ya symbol lazima iwe > 0 (inatoka MT5)")
    return int(round(cap_pips * (pip_size(symbol) / point)))


# --------------------------------------------------------------------------
# RCE-05..RCE-08 — commission, swap, pip conversion
# --------------------------------------------------------------------------


def commission_pips(commission_round_turn: float, pip_value_per_lot: float) -> float:
    """`commission_pips = commission_round_turn ÷ pip_value_per_lot` (spec §3.3).

    Thamani inayoingia HAPA ni ya **pande MBILI**. Broker akitoa bei ya upande
    mmoja, inaongezwa maradufu kabla ya kuandikwa kwenye `broker_costs.yaml`
    (`commission_usd_round_turn` — jina liko wazi kwa makusudi).
    """
    if pip_value_per_lot <= 0:
        raise ValueError("`pip_value_per_lot` lazima iwe > 0")
    return commission_round_turn / pip_value_per_lot


@dataclass(frozen=True)
class SymbolSpec:
    """Sifa za symbol zinazotoka **MT5**, si config (spec §3.4, §4)."""

    symbol: str
    point: float
    contract_size: float
    volume_min: float
    volume_step: float
    volume_max: float
    swap_long: float = 0.0
    swap_short: float = 0.0
    swap_mode: str = SWAP_MODE_POINTS


def swap_value_per_night(direction: str, spec: SymbolSpec) -> float:
    """Thamani ya swap ya usiku MMOJA kwa lot moja (spec §3.4 hatua 1–2)."""
    swap = spec.swap_long if direction.upper() == "BUY" else spec.swap_short
    mode = spec.swap_mode.upper()
    if mode == SWAP_MODE_CURRENCY:
        return float(swap)
    if mode == SWAP_MODE_POINTS:
        return float(swap) * spec.point * spec.contract_size
    if mode == SWAP_MODE_INTEREST:
        return (float(swap) / 100.0) * spec.contract_size
    raise ValueError(f"`swap_mode` {spec.swap_mode!r} haitambuliki (spec §3.4 hatua 2)")


def swap_pips(
    direction: str,
    spec: SymbolSpec,
    nights: float,
    pip_value_per_lot: float,
    triple_nights: float = 0.0,
) -> float:
    """`swap_pips = jumla ya swap ya usiku zote ÷ pip_value_per_lot` (spec §3.4).

    `nights` ni **takwimu ya strategy** (D1 ≈ 3.5; H1 intraday = 0), si dhana.
    `triple_nights` ni sehemu ya hizo zinazoangukia rollover ya Jumatano→Alhamisi
    (swap × 3). Zote zinatoka `broker_costs.yaml` — hakuna default kwenye code.
    """
    if nights <= 0:
        return 0.0
    if triple_nights > nights:
        raise ValueError("`triple_nights` haiwezi kuzidi `nights`")
    per_night = swap_value_per_night(direction, spec)
    total = per_night * (nights - triple_nights) + per_night * 3.0 * triple_nights
    return total / pip_value_per_lot


def count_rollovers(
    entry: datetime,
    exit_estimate: datetime,
    triple_day: str = "WED",
    rollover_hour: int = 0,
) -> tuple[int, int]:
    """Usiku halisi kati ya entry na exit: `(za kawaida, za triple)` (spec §3.4 hatua 3).

    Inatumika pale tarehe zinajulikana (live/backtest). Kwa sizing ya kabla ya
    trade, takwimu ya strategy (`nights`) ndiyo inayotumika badala yake.
    """
    days = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}
    triple_weekday = days[triple_day.upper()]
    normal = triple = 0
    cursor = entry.replace(hour=rollover_hour, minute=0, second=0, microsecond=0)
    if cursor <= entry:
        cursor += _ONE_DAY
    while cursor <= exit_estimate:
        # Swap inatozwa kwa siku iliyoisha — Jumatano→Alhamisi ndiyo triple.
        if (cursor - _ONE_DAY).weekday() == triple_weekday:
            triple += 1
        else:
            normal += 1
        cursor += _ONE_DAY
    return normal, triple


def pip_value_account(pip_value_quote: float, quote_to_account_rate: float = 1.0) -> float:
    """`pip_value_acct = pip_value_quote × rate(quote → account)` (spec §3.5).

    Inatumika kwenye lots NA kwenye `commission_pips`/`swap_pips` — zote
    zinatokana na fedha, si pips.
    """
    if quote_to_account_rate <= 0:
        raise ValueError("rate ya kubadilisha lazima iwe > 0")
    return pip_value_quote * quote_to_account_rate


# --------------------------------------------------------------------------
# Jumla
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CostBreakdown:
    """Vipengele vinne + jumla. Kila kimoja kinaonekana kwa ajili ya ukaguzi."""

    spread_pips: float
    slippage_pips: float
    commission_pips: float
    swap_pips: float

    @property
    def cost_pips(self) -> float:
        return self.spread_pips + self.slippage_pips + self.commission_pips + self.swap_pips

    def render(self) -> str:
        return (
            f"spread={self.spread_pips:.2f} slip={self.slippage_pips:.2f} "
            f"comm={self.commission_pips:.2f} swap={self.swap_pips:.2f} "
            f"-> cost_pips={self.cost_pips:.2f}"
        )


def compute_cost_pips(
    spread_pips: float,
    slippage_pips: float,
    commission_round_turn: float,
    pip_value_per_lot: float,
    direction: str = "BUY",
    spec: SymbolSpec | None = None,
    nights: float = 0.0,
    triple_nights: float = 0.0,
) -> CostBreakdown:
    """Vipengele vinne vya §3 vikiunganishwa kuwa `cost_pips` moja."""
    return CostBreakdown(
        spread_pips=spread_pips,
        slippage_pips=slippage_pips,
        commission_pips=commission_pips(commission_round_turn, pip_value_per_lot),
        swap_pips=(
            swap_pips(direction, spec, nights, pip_value_per_lot, triple_nights)
            if spec is not None and nights > 0
            else 0.0
        ),
    )


from datetime import timedelta as _timedelta  # noqa: E402  (chini ili kuepuka mzunguko wa usomaji)

_ONE_DAY = _timedelta(days=1)
