"""Sifa za symbol kutoka broker (MT5 / `config/broker_costs.yaml`).

Namba hizi ni za **broker**, si za spec: `volume_min/step/max`, commission,
swap, contract_size, point. Spec §3.3 inasema ziishi `broker_costs.yaml`
("si kwenye code"), na PD ndiye anazitoa (§2A ya IMPLEMENTATION_PLAN, TRACK E).

Sheria ya usalama: symbol isiyokuwa na namba zilizothibitishwa **haipewi**
thamani za kubuni — `symbol_spec()` inatupa hitilafu. Sizing kwa namba za
kubuni ni hatari kuliko kutokutrade.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .config import RiskConfig

SWAP_MODES = ("CURRENCY", "POINTS", "INTEREST")

# Spec §3.1: PipSize ni 0.01 kwa JPY/XAU, 0.0001 kwa nyingine.
_PIP_SIZE_JPY_XAU = 0.01
_PIP_SIZE_DEFAULT = 0.0001


class SymbolSpecError(RuntimeError):
    """Namba za broker kwa symbol hii hazipo au hazikubaliki."""


def pip_size_for(symbol: str, quote_ccy: str | None = None) -> float:
    """PipSize kwa sheria ya spec §3.1 (0.01 kwa JPY/XAU · 0.0001 kwa nyingine)."""
    name = symbol.upper()
    quote = (quote_ccy or name[3:6] if len(name) >= 6 else "").upper()
    if quote == "JPY" or name.startswith("XAU") or name.startswith("XAG"):
        return _PIP_SIZE_JPY_XAU
    return _PIP_SIZE_DEFAULT


@dataclass(frozen=True)
class SymbolSpec:
    """Sifa za symbol zinazohitajika na §3 na §4 za spec."""

    name: str
    digits: int
    point: float
    pip_size: float
    contract_size: float
    base_ccy: str
    quote_ccy: str
    volume_min: float
    volume_step: float
    volume_max: float
    commission_usd_round_turn: float
    swap_long: float = 0.0
    swap_short: float = 0.0
    swap_mode: str = "CURRENCY"

    def __post_init__(self) -> None:
        if self.swap_mode.upper() not in SWAP_MODES:
            raise SymbolSpecError(
                f"{self.name}: swap_mode `{self.swap_mode}` haitambuliki "
                f"(spec §3.4: {', '.join(SWAP_MODES)})"
            )
        for field_name in ("point", "pip_size", "contract_size", "volume_min", "volume_step"):
            if getattr(self, field_name) <= 0:
                raise SymbolSpecError(f"{self.name}: `{field_name}` lazima iwe > 0")
        if self.volume_max < self.volume_min:
            raise SymbolSpecError(f"{self.name}: volume_max < volume_min")

    @property
    def swap_mode_normalized(self) -> str:
        return self.swap_mode.upper()

    def swap_for(self, direction: str) -> float:
        """Spec §3.4 hatua 1: BUY → swap_long · SELL → swap_short."""
        side = direction.upper()
        if side not in ("BUY", "SELL"):
            raise SymbolSpecError(f"mwelekeo `{direction}` si BUY wala SELL")
        return self.swap_long if side == "BUY" else self.swap_short

    @property
    def pips_per_point(self) -> float:
        """Spec §3.2: `order.deviation = cap × (PipSize ÷ point)` — MT5 inatumia POINTS."""
        return self.pip_size / self.point


# --------------------------------------------------------------------------
# Kusoma kutoka broker_costs.yaml
# --------------------------------------------------------------------------

_REQUIRED_FIELDS = (
    "digits",
    "point",
    "contract_size",
    "base_ccy",
    "quote_ccy",
    "volume_min",
    "volume_step",
    "volume_max",
    "commission_usd_round_turn",
)


def _merged_entry(cfg: RiskConfig, symbol: str) -> dict[str, Any] | None:
    symbols = cfg.broker_costs.get("symbols") or {}
    entry = symbols.get(symbol)
    if entry is None:
        return None
    defaults = cfg.broker_costs.get("defaults") or {}
    return {**defaults, **entry}


def symbol_spec(cfg: RiskConfig, symbol: str) -> SymbolSpec:
    """SymbolSpec kutoka `broker_costs.yaml`. Namba zisipothibitishwa → hitilafu."""
    if not cfg.broker_costs:
        raise SymbolSpecError(
            "config/broker_costs.yaml haipo — PD anatoa namba za broker "
            "(commission round-turn, swap, volume_min/step/max) kabla ya sizing yoyote"
        )
    if not bool(cfg.broker_costs.get("confirmed_by_pd", False)):
        raise SymbolSpecError(
            "broker_costs.yaml ina `confirmed_by_pd: false` — namba bado ni nafasi tupu. "
            "Sizing kwa namba za kubuni hairuhusiwi (spec §3.3, §4)."
        )
    entry = _merged_entry(cfg, symbol)
    if entry is None:
        raise SymbolSpecError(f"{symbol}: haipo kwenye broker_costs.yaml")
    missing = [field for field in _REQUIRED_FIELDS if entry.get(field) is None]
    if missing:
        raise SymbolSpecError(f"{symbol}: broker_costs.yaml haina {', '.join(missing)}")

    quote_ccy = str(entry["quote_ccy"])
    return SymbolSpec(
        name=symbol,
        digits=int(entry["digits"]),
        point=float(entry["point"]),
        pip_size=float(entry.get("pip_size") or pip_size_for(symbol, quote_ccy)),
        contract_size=float(entry["contract_size"]),
        base_ccy=str(entry["base_ccy"]),
        quote_ccy=quote_ccy,
        volume_min=float(entry["volume_min"]),
        volume_step=float(entry["volume_step"]),
        volume_max=float(entry["volume_max"]),
        commission_usd_round_turn=float(entry["commission_usd_round_turn"]),
        swap_long=float(entry.get("swap_long", 0.0)),
        swap_short=float(entry.get("swap_short", 0.0)),
        swap_mode=str(entry.get("swap_mode", "CURRENCY")),
    )


def symbol_specs(cfg: RiskConfig, symbols: Iterable[str]) -> dict[str, SymbolSpec]:
    return {symbol: symbol_spec(cfg, symbol) for symbol in symbols}


def missing_broker_numbers(cfg: RiskConfig) -> list[str]:
    """Ripoti kwa PD: symbols zilizo kwenye config lakini bila namba kamili."""
    symbols = (cfg.broker_costs.get("symbols") or {}) if cfg.broker_costs else {}
    gaps: list[str] = []
    for symbol in sorted(symbols):
        entry = _merged_entry(cfg, symbol) or {}
        missing = [field for field in _REQUIRED_FIELDS if entry.get(field) is None]
        if missing:
            gaps.append(f"{symbol}: {', '.join(missing)}")
    if not symbols:
        gaps.append("hakuna symbol yoyote yenye namba za broker")
    return gaps


__all__ = [
    "SWAP_MODES",
    "SymbolSpec",
    "SymbolSpecError",
    "missing_broker_numbers",
    "pip_size_for",
    "symbol_spec",
    "symbol_specs",
]
