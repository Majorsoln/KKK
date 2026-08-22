"""Hatua ya pili ya utekelezaji — EXECUTION (DOCTRINE §11.1–§11.4, R13).

Order iliyopita RCE bado si trade. Bei inaweza kuhama zaidi ya `deviation` kabla
haijajazwa, na hapo **haijazi** badala ya kujaza kwa bei mbaya (RCE §3.2). Kwa
hiyo hatua hii ina matokeo mawili: `FILL` na `NO_FILL`.

**Njia ya trade, si ya mid.** BUY inaingia kwa `ask` na kutoka kwa `bid`; SELL
kinyume chake. Kwa hiyo **spread iko NDANI ya mwendo uliopatikana** — na
haitozwi tena kando. Kuitoza mara mbili kungefanya kila strategy ionekane mbaya
kuliko ilivyo, kwa kiasi ambacho hakuna mtu angekigundua kwenye jumla.

Gharama zinazoongezwa kando ni **commission** na **swap** pekee.

**Uhakiki uliojengwa ndani (§11.4, R7):** `net_pips` inahesabiwa kwa njia mbili —
kwa njia ya trade (spread ndani) na kwa njia ya mid (spread ikitolewa kwa uwazi).
Zisipolingana, mojawapo ina kasoro, na `reconciliation_error` inaonyesha ipi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.rce.cost import pip_size

from .ledger import FILL, NO_FILL

# Sababu za kutoka
TP = "TP"
SL = "SL"
TIME_STOP = "TIME_STOP"
UNRESOLVED = "UNRESOLVED"

# Sababu za kutojaza
SLIPPAGE_CAP = "slippage_cap"
NO_TICKS = "no_ticks_after_signal"


class ExecutionError(RuntimeError):
    """Ticks hazitoshi kutekeleza, au vigezo havieleweki."""


@dataclass(frozen=True)
class ExecSpec:
    """Vigezo vya utekelezaji. Vyote vinatoka RCE au strategy, hakuna cha kubuni."""

    symbol: str
    direction: str            # BUY / SELL
    sl_pips: float
    tp_pips: float
    deviation_pips: float     # cap ya RCE (§3.2)
    commission_pips: float    # round-turn, kutoka RCE
    time_stop_minutes: int
    swap_pips_per_night: float = 0.0

    @property
    def pip(self) -> float:
        return pip_size(self.symbol)

    @property
    def sign(self) -> int:
        return 1 if self.direction.upper() == "BUY" else -1


@dataclass(frozen=True)
class TradePath:
    outcome: str                       # FILL / NO_FILL
    reject_reason: str = ""

    entry_time: Any = None
    entry_price: float | None = None   # bei ya TRADE (BUY: ask)
    entry_mid: float | None = None
    fill_slippage_pips: float = 0.0

    exit_time: Any = None
    exit_price: float | None = None    # bei ya TRADE (BUY: bid)
    exit_mid: float | None = None
    exit_reason: str = ""

    gross_pips: float = 0.0            # njia ya TRADE — spread IKO NDANI
    spread_pips: float = 0.0           # kwa taarifa; imeshaingia kwenye gross
    commission_pips: float = 0.0
    swap_pips: float = 0.0
    net_pips: float = 0.0

    mfe_pips: float = 0.0
    mae_pips: float = 0.0
    holding_minutes: float = 0.0
    n_ticks: int = 0
    reconciliation_error: float = 0.0

    @property
    def resolved(self) -> bool:
        """Trade isiyofikia mwisho ndani ya data haihesabiki — kama bar ya nusu."""
        return self.outcome == FILL and self.exit_reason != UNRESOLVED

    def to_json(self) -> dict[str, Any]:
        payload = {k: v for k, v in self.__dict__.items()}
        for key in ("entry_time", "exit_time"):
            if payload.get(key) is not None:
                payload[key] = str(payload[key])
        return payload


def execute(ticks, spec: ExecSpec, *, signal_time, requested_price: float) -> TradePath:
    """Tembea njia ya ticks kutoka signal hadi kutoka.

    `ticks` ni frame yenye `timestamp`, `bid`, `ask`, **iliyopangwa**, na
    ikianzia si baadaye kuliko `signal_time`.
    """
    import numpy as np
    import pandas as pd

    missing = {"timestamp", "bid", "ask"} - set(ticks.columns)
    if missing:
        raise ExecutionError(f"safu hazipo: {sorted(missing)} — §4.1 inadai bid/ask")

    # Muda wote unahesabiwa kwa NANOSEKUNDE za int64.
    #
    # `as_unit("ns")` si ya mapambo: pandas inahifadhi DatetimeIndex kwa
    # RESOLUTION inayotofautiana (µs kwa pandas 3, ns kwa 2), wakati
    # `Timestamp.value` DAIMA ni nanosekunde. Kuchanganya vipimo viwili
    # kunatoa tofauti ya mara 1,000 — na tofauti ya namna hiyo haitoi kosa,
    # inatoa jibu lisilo sahihi.
    stamps = pd.DatetimeIndex(pd.to_datetime(ticks["timestamp"], utc=True)).as_unit("ns")
    stamps_ns = stamps.view("int64")
    t_signal = _utc(signal_time).as_unit("ns")
    after = int(np.searchsorted(stamps_ns, t_signal.value))
    if after >= len(stamps):
        return TradePath(outcome=NO_FILL, reject_reason=NO_TICKS)

    bid = ticks["bid"].to_numpy(dtype=float)
    ask = ticks["ask"].to_numpy(dtype=float)
    pip, sign = spec.pip, spec.sign

    # ---- FILL au NO_FILL ----
    #
    # Bei ya kuingia ni ya upande wa trade: BUY inanunua kwa `ask`. Slippage ni
    # tofauti kati ya bei hiyo na iliyoombwa, kwa upande unaotugharimu. Ikizidi
    # cap ya RCE, order HAIJAZI — haijazwi kwa bei mbaya (RCE §3.2).
    entry_price = ask[after] if sign > 0 else bid[after]
    slip_pips = sign * (entry_price - requested_price) / pip
    if slip_pips > spec.deviation_pips:
        return TradePath(
            outcome=NO_FILL, reject_reason=SLIPPAGE_CAP,
            fill_slippage_pips=float(slip_pips),
        )

    entry_mid = (bid[after] + ask[after]) / 2.0
    entry_time = stamps[after]                     # Timestamp ya UTC

    # ---- barriers kwa bei ya KUTOKA ----
    #
    # BUY inatoka kwa `bid`; kwa hiyo TP na SL zote zinapimwa kwa `bid`. Tick
    # moja haiwezi kugusa zote mbili (moja iko juu, nyingine chini ya bei ile
    # ile), kwa hiyo hakuna utata wa nani kwanza.
    exit_side = bid if sign > 0 else ask

    path = exit_side[after:]
    times_ns = stamps_ns[after:]
    deadline_ns = t_signal.value + spec.time_stop_minutes * 60 * 1_000_000_000

    moved = sign * (path - entry_price) / pip          # pips kwa upande wetu
    hit_tp = np.flatnonzero(moved >= spec.tp_pips)
    hit_sl = np.flatnonzero(moved <= -spec.sl_pips)
    hit_time = np.flatnonzero(times_ns >= deadline_ns)

    first = {}
    if hit_tp.size:
        first[TP] = int(hit_tp[0])
    if hit_sl.size:
        first[SL] = int(hit_sl[0])
    if hit_time.size:
        first[TIME_STOP] = int(hit_time[0])

    if first:
        exit_reason = min(first, key=lambda k: first[k])
        idx = first[exit_reason]
    else:
        # Data imeisha kabla ya kutoka. Si TIME_STOP na si hasara — trade
        # haijafika mwisho, kama bar isiyofungwa. Haihesabiki.
        exit_reason, idx = UNRESOLVED, len(path) - 1

    exit_price = float(path[idx])
    exit_mid = float((bid[after + idx] + ask[after + idx]) / 2.0)

    # ---- gharama ----
    #
    # `gross_pips` ni njia ya TRADE, kwa hiyo spread IMESHAINGIA. Inayoongezwa
    # ni commission na swap pekee.
    gross = float(sign * (exit_price - entry_price) / pip)
    exit_time = stamps[after + idx]
    nights = _nights(entry_time, exit_time)
    swap = nights * spec.swap_pips_per_night
    net = gross - spec.commission_pips - swap

    # ---- §11.4 / R7: njia ya PILI kwa namba ile ile ----
    #
    # Kwa mid, spread inatolewa kwa uwazi. Zote mbili lazima zitoe `net` ile
    # ile; zisipolingana, mojawapo ina kasoro.
    spread_entry = float((ask[after] - bid[after]) / pip)
    spread_exit = float((ask[after + idx] - bid[after + idx]) / pip)
    spread_total = (spread_entry + spread_exit) / 2.0
    gross_mid = float(sign * (exit_mid - entry_mid) / pip)
    net_kwa_mid = gross_mid - spread_total - spec.commission_pips - swap

    return TradePath(
        outcome=FILL,
        entry_time=entry_time, entry_price=float(entry_price),
        entry_mid=float(entry_mid), fill_slippage_pips=float(slip_pips),
        exit_time=exit_time, exit_price=exit_price, exit_mid=exit_mid,
        exit_reason=exit_reason,
        gross_pips=gross, spread_pips=spread_total,
        commission_pips=spec.commission_pips, swap_pips=float(swap), net_pips=float(net),
        mfe_pips=float(moved[: idx + 1].max()), mae_pips=float(moved[: idx + 1].min()),
        holding_minutes=float((exit_time - entry_time).total_seconds() / 60.0),
        n_ticks=int(idx + 1),
        reconciliation_error=float(abs(net - net_kwa_mid)),
    )


def _utc(moment):
    """Timestamp ya UTC, ikiwa `moment` ina tz au haina.

    `pd.Timestamp(x, tz="UTC")` inalipuka pale `x` ilipo tayari na tz. Kizuizi
    hicho ni cha pandas, si cha maana — lakini kikiachwa, kila mpigaji simu
    atalazimika kukumbuka aina ya ingizo lake.
    """
    import pandas as pd

    ts = pd.Timestamp(moment)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def _nights(entry, exit_) -> int:
    """Idadi ya mipaka ya siku iliyovukwa — swap inalipwa kwa kila moja."""
    return max(0, (exit_.date() - entry.date()).days)
