"""§3 — COST_PIPS: spread · slippage · commission · swap (RCE-03..RCE-08).

```
cost_pips = spread_pips + slippage_pips + commission_pips + swap_pips
```

Kila kipengele kina sheria yake kwenye spec, na hapa kinatekelezwa kama
kilivyoandikwa:

* **§3.1 spread — MSETO:** `max(wastani wa H1, p95 ya M5)`. Si M5 pekee (hiyo ni
  kudharau gharama → lots kubwa mno → EV ya bandia).
* **§3.2 slippage — CAP, si utabiri:** `min(dynamic(M5), dhana ya backtest)`.
  Cap **inabana tu, hailegei** — ndiyo inayoshikilia dhamana ya "live ≤ backtest".
* **§3.3 commission — round-turn.** Broker akitoa bei ya upande mmoja → ×2.
* **§3.4 swap:** mwelekeo → mode (CURRENCY/POINTS/INTEREST) → usiku (Jumatano ×3).
* **§3.5 pip conversion:** `pip_value_acct = pip_value_quote × rate(quote→acct)`,
  inatumika kwenye lots NA kwenye commission/swap (zote zinatokana na fedha).

**Ishara ya swap (mkataba wa data, si mabadiliko ya spec):** fomula ya §3.4 ni
`swap_pips = jumla_ya_swap ÷ pip_value_per_lot` na jumla hiyo inaingia kwenye
`cost_pips` kwa kujumlishwa. Kwa hiyo `swap_long`/`swap_short` za
`broker_costs.yaml` zinahifadhiwa kama **gharama**: chanya = unalipa, hasi =
unalipwa. MT5 inatoa ishara kinyume (hasi = unalipa), kwa hiyo adapter
inayosoma MT5 inageuza ishara mahali pamoja — si hapa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Mapping, Sequence
from zoneinfo import ZoneInfo

import numpy as np

from .config import RiskConfig
from .symbols import SymbolSpec

RateLookup = Mapping[tuple[str, str], float] | Callable[[str, str], float] | None

_WEEKDAYS = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}


class CostError(RuntimeError):
    """Kigezo cha gharama hakipo au hakikubaliki."""


# --------------------------------------------------------------------------
# §3.1 — SPREAD
# --------------------------------------------------------------------------


def spread_pips(bid: float, ask: float, pip_size: float) -> float:
    """`spread_pips = (Ask − Bid) ÷ PipSize` (spec §3.1)."""
    if ask < bid:
        raise CostError(f"ask ({ask}) < bid ({bid})")
    return (ask - bid) / pip_size


@dataclass(frozen=True)
class SpreadResult:
    """Vipande vya spread ya mseto (kwa log — PD anaona kilichoshinda)."""

    base: float
    spike: float
    effective: float
    source: str  # "H1_base" au "M5_p95"


def spread_effective(
    h1_spreads: Sequence[float],
    m5_spreads: Sequence[float],
    cfg: RiskConfig,
) -> SpreadResult:
    """`spread_effective = max(wastani wa H1, p95 ya M5)` (spec §3.1)."""
    if cfg.spread_combine != "max":
        raise CostError(
            f"spread_model.combine = `{cfg.spread_combine}`; spec §3.1 inafafanua `max` pekee"
        )
    h1_window = np.asarray(h1_spreads, dtype=float)[-cfg.spread_base_window :]
    m5_window = np.asarray(m5_spreads, dtype=float)[-cfg.spread_spike_window :]
    if h1_window.size == 0 or m5_window.size == 0:
        raise CostError("spread ya H1 na ya M5 zote zinahitajika (spec §3.1)")

    base = float(np.mean(h1_window))
    spike = float(np.quantile(m5_window, cfg.spread_spike_quantile))
    effective = max(base, spike)
    return SpreadResult(
        base=base,
        spike=spike,
        effective=effective,
        source="H1_base" if base >= spike else "M5_p95",
    )


# --------------------------------------------------------------------------
# §3.2 — SLIPPAGE (CAP)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SlippageCap:
    cap_pips: float
    assumption_pips: float
    dynamic_pips: float | None
    binding: str  # "dynamic" (imebana) au "backtest_assumption"


def slippage_cap(
    cfg: RiskConfig,
    order_type: str,
    dynamic_estimate_pips: float | None = None,
) -> SlippageCap:
    """`cap = min(dynamic_estimate(M5_volatility), backtest_assumption)` (spec §3.2)."""
    caps = cfg.slippage_cap_pips
    key = order_type.lower()
    if key not in caps:
        raise CostError(
            f"slippage_cap_pips haina `{key}` kwenye config/risk.yaml "
            f"(zilizopo: {', '.join(sorted(caps))}) — kikomo hakibuniwi na code"
        )
    assumption = caps[key]
    if cfg.slippage_cap_dynamic and dynamic_estimate_pips is not None:
        # `min` ndiyo inayotekeleza "inabana TU, hailegei": dynamic kubwa kuliko
        # dhana ya backtest haiwezi kupandisha cap.
        cap = min(float(dynamic_estimate_pips), assumption)
    else:
        cap = assumption
    return SlippageCap(
        cap_pips=cap,
        assumption_pips=assumption,
        dynamic_pips=dynamic_estimate_pips,
        binding="dynamic" if cap < assumption else "backtest_assumption",
    )


def deviation_points(cap_pips: float, symbol: SymbolSpec) -> int:
    """`order.deviation = cap × (PipSize ÷ point)` — MT5 inatumia POINTS (spec §3.2)."""
    return int(round(cap_pips * symbol.pips_per_point))


# --------------------------------------------------------------------------
# §3.5 — PIP VALUE
# --------------------------------------------------------------------------


def _rate(rates: RateLookup, quote_ccy: str, account_ccy: str) -> float:
    if quote_ccy == account_ccy:
        return 1.0
    if rates is None:
        raise CostError(
            f"rate ya {quote_ccy}->{account_ccy} inahitajika (spec §3.5) lakini haikutolewa"
        )
    if callable(rates):
        return float(rates(quote_ccy, account_ccy))
    if (quote_ccy, account_ccy) in rates:
        return float(rates[(quote_ccy, account_ccy)])
    inverse = rates.get((account_ccy, quote_ccy))
    if inverse:
        return 1.0 / float(inverse)
    raise CostError(f"rate ya {quote_ccy}->{account_ccy} haipo kwenye rates zilizotolewa")


def pip_value_account(
    symbol: SymbolSpec,
    account_ccy: str,
    rates: RateLookup = None,
) -> float:
    """`pip_value_acct = pip_value_quote × rate(quote_ccy → account_ccy)` (spec §3.5)."""
    pip_value_quote = symbol.pip_size * symbol.contract_size
    return pip_value_quote * _rate(rates, symbol.quote_ccy, account_ccy)


# --------------------------------------------------------------------------
# §3.3 — COMMISSION
# --------------------------------------------------------------------------


def commission_pips(symbol: SymbolSpec, pip_value_acct: float, cfg: RiskConfig) -> float:
    """`commission_pips = commission_per_lot_round_turn ÷ pip_value_per_lot` (spec §3.3)."""
    side = cfg.commission_side.lower()
    if side not in ("round_turn", "one_side"):
        raise CostError(
            f"commission_side = `{cfg.commission_side}`; spec §3.3 inajua `round_turn` au `one_side`"
        )
    per_lot = symbol.commission_usd_round_turn
    if side == "one_side":
        per_lot *= 2.0  # "Broker akitoa bei ya upande mmoja, inaongezwa maradufu"
    return per_lot / pip_value_acct


# --------------------------------------------------------------------------
# §3.4 — SWAP
# --------------------------------------------------------------------------


def swap_per_night(symbol: SymbolSpec, direction: str) -> float:
    """Hatua 1–2 za §3.4: mwelekeo, kisha kubadilisha kwa `swap_mode`."""
    raw = symbol.swap_for(direction)
    mode = symbol.swap_mode_normalized
    if mode == "CURRENCY":
        return raw
    if mode == "POINTS":
        return raw * symbol.point * symbol.contract_size
    return (raw / 100.0) * symbol.contract_size  # INTEREST


def swap_nights_weight(
    entry_time: datetime,
    nights: float,
    cfg: RiskConfig,
) -> float:
    """Hatua 3 ya §3.4: usiku wa Jumatano→Alhamisi = ×3, nyingine ×1.

    `nights` inatoka kwenye takwimu za strategy (mf. D1 ≈ 3.5; H1 intraday = 0).
    Usiku wa mwisho ukiwa sehemu, unapewa uzito wa sehemu hiyo.
    """
    if nights <= 0:
        return 0.0
    triple_key = cfg.swap_triple_day.upper()
    if triple_key not in _WEEKDAYS:
        raise CostError(f"swap.triple_day = `{cfg.swap_triple_day}` haitambuliki")
    triple_weekday = _WEEKDAYS[triple_key]

    server_tz = ZoneInfo(cfg.day_reset_tz)
    if entry_time.tzinfo is None:
        entry_time = entry_time.replace(tzinfo=timezone.utc)
    local = entry_time.astimezone(server_tz)

    # Rollover ya kwanza baada ya entry (saa ya `swap.server_rollover_hour`).
    rollover = local.replace(
        hour=cfg.swap_rollover_hour, minute=0, second=0, microsecond=0
    )
    if rollover <= local:
        rollover += timedelta(days=1)

    weight = 0.0
    remaining = float(nights)
    while remaining > 1e-9:
        portion = min(1.0, remaining)
        # Usiku unaomalizika kwenye rollover hii ulianza siku iliyotangulia.
        night_start = (rollover - timedelta(days=1)).weekday()
        weight += portion * (3.0 if night_start == triple_weekday else 1.0)
        remaining -= portion
        rollover += timedelta(days=1)
    return weight


def swap_pips(
    symbol: SymbolSpec,
    direction: str,
    nights: float,
    entry_time: datetime,
    pip_value_acct: float,
    cfg: RiskConfig,
) -> float:
    """Hatua 4 ya §3.4: `swap_pips = jumla ya swap ya usiku zote ÷ pip_value_per_lot`."""
    if not cfg.swap_enabled or nights <= 0:
        return 0.0
    total = swap_per_night(symbol, direction) * swap_nights_weight(entry_time, nights, cfg)
    return total / pip_value_acct


# --------------------------------------------------------------------------
# Kuunganisha — cost_pips
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CostRequest:
    """Kila kitu kinachohitajika kuhesabu gharama ya pendekezo moja."""

    symbol: SymbolSpec
    direction: str
    order_type: str
    spread_pips: float
    entry_time: datetime
    nights: float = 0.0
    dynamic_slippage_pips: float | None = None


@dataclass(frozen=True)
class CostBreakdown:
    """Vipengele vinne vya §3 + vitu vinavyokwenda kwenye order."""

    spread_pips: float
    slippage_pips: float
    commission_pips: float
    swap_pips: float
    cost_pips: float
    pip_value_acct: float
    deviation_points: int
    slippage_cap: SlippageCap

    def to_log(self) -> dict[str, float | int | str]:
        return {
            "spread_pips": round(self.spread_pips, 4),
            "slippage_pips": round(self.slippage_pips, 4),
            "commission_pips": round(self.commission_pips, 4),
            "swap_pips": round(self.swap_pips, 4),
            "cost_pips": round(self.cost_pips, 4),
            "pip_value_acct": round(self.pip_value_acct, 4),
            "deviation_points": self.deviation_points,
            "slippage_binding": self.slippage_cap.binding,
        }


def compute_cost(
    request: CostRequest,
    cfg: RiskConfig,
    rates: RateLookup = None,
    account_ccy: str | None = None,
) -> CostBreakdown:
    """`cost_pips = spread + slippage + commission + swap` (spec §3)."""
    account = account_ccy or str(cfg.get("account_currency"))
    pip_value = pip_value_account(request.symbol, account, rates)
    cap = slippage_cap(cfg, request.order_type, request.dynamic_slippage_pips)
    commission = commission_pips(request.symbol, pip_value, cfg)
    swap = swap_pips(
        request.symbol,
        request.direction,
        request.nights,
        request.entry_time,
        pip_value,
        cfg,
    )
    total = request.spread_pips + cap.cap_pips + commission + swap
    return CostBreakdown(
        spread_pips=request.spread_pips,
        slippage_pips=cap.cap_pips,
        commission_pips=commission,
        swap_pips=swap,
        cost_pips=total,
        pip_value_acct=pip_value,
        deviation_points=deviation_points(cap.cap_pips, request.symbol),
        slippage_cap=cap,
    )
