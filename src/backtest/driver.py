"""Kuendesha familia yoyote kwenye ticks halisi — DOCTRINE §4, §6, §7, §9.

```
diski → madirisha → mwendo → stop → RCE → trades
      → LANGO LA §6 → curve ya siku → block bootstrap → `p`
```

**Mpangilio si wa bahati.** Malango ya §6 yanapimwa na kutangazwa **kabla**
`p` haijahesabiwa, na yakishindwa hii inasimama bila kuihesabu kabisa. Kuona
`p` kisha kuamua kama symbol inastahili ni jinsi toleo la kwanza lilivyoshindwa.

---

**Familia moja, code moja.** F0 ilikuwa na script yake; Gotobi ingekuwa na
yake, na baada ya miezi mitatu zingekuwa zimetofautiana kwa vitu vidogo
visivyoonekana — dirisha la MAE, mpangilio wa historia, mahali gharama
inapopimwa. Kila familia inatoa **sehemu chache zilizotangazwa**; kila kitu
kingine kiko hapa, mara moja.

Familia inatakiwa kutoa:

```
FAMILY · SYMBOL · PIP · POINT · CONTRACT_SIZE · WINDOW_SECONDS
DECLARATION · SL_MOVE_MULT · DECLARED_EDGE_PIPS
pip_value(mid) · eligible_days(days) · sessions_for(day) · baskets(days, move_pips=)
```

**`pip_value` ni function, si namba.** Kwa EURUSD ni `$10` daima; kwa USDJPY
ni `1000 ÷ bei`, inayobadilika kwa 37% kwenye sampuli yetu. Kuiweka namba
kungebadilisha `commission_pips` kwa kiasi kile kile, na lango la gharama
lingeamua kwa namba isiyo sahihi.

---

**Dirisha zima linasomwa**, si ncha pekee (§11): `runner.execute` inahitaji
njia ili kujua kama stop iligongwa. Kipande cha siku tano kinasomwa,
kinatumika, kinatupwa.
"""

from __future__ import annotations

import statistics as st
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Sequence

from src.analysis.curve import daily_r
from src.backtest.runner import execute
from src.data import ticks as TK
from src.events.clock import quotes
from src.families.qualify import Qualification, qualify
from src.rce.budget import AccountState
from src.rce.cost import SymbolSpec

# Siku kwa kila kipande. Dirisha zima linasomwa sasa (masaa 13 kwa siku kwa
# F0), kwa hiyo mwezi mmoja ungekuwa rows milioni 10+. Tano zinabaki chini ya
# milioni 2.5, na hakuna faili inayosomwa mara mbili — kila siku iko kwenye
# kipande kimoja tu.
DAYS_PER_CHUNK = 5


@dataclass
class RunSpec:
    """Vigezo vya akaunti na broker. Vinaingia kwenye ripoti kama vilivyo."""

    balance: float = 10_000.0
    commission_round_turn: float = 7.0
    volume_min: float = 0.01
    volume_step: float = 0.01
    volume_max: float = 50.0


@dataclass
class Sweep:
    """Kila kitu kilichotokea wakati wa kupita kwenye data."""

    trades: list = field(default_factory=list)
    moves: dict = field(default_factory=dict)
    missing: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    seconds: float = 0.0

    @property
    def stopped(self) -> list:
        return [t for t in self.trades if t.stopped]

    @property
    def finished(self) -> list:
        """Zilizomaliza kwa saa. Ndizo pekee zenye spread ya kwenda-na-kurudi."""
        return [t for t in self.trades if not t.stopped]


def chunks(days: Sequence[date], *, size: int = DAYS_PER_CHUNK):
    return [list(days[i:i + size]) for i in range(0, len(days), size)]


def market(family, spec: RunSpec, *, spread_pips: float, mid: float) -> dict:
    """Kila kitu RCE inachohitaji, kikiwa kimepimwa kwenye bei ya sasa."""
    return {
        "spec": SymbolSpec(symbol=family.SYMBOL, point=family.POINT,
                           contract_size=family.CONTRACT_SIZE,
                           volume_min=spec.volume_min,
                           volume_step=spec.volume_step,
                           volume_max=spec.volume_max),
        "account": AccountState(current_balance=spec.balance, today_profit=0.0,
                                today_loss=0.0, open_positions=0),
        "h1_spreads": [spread_pips] * 120,
        "m5_spreads": [spread_pips] * 300,
        "pip_value_acct": family.pip_value(mid),
        "commission_round_turn": spec.commission_round_turn,
        "pip": family.PIP,
    }


def sweep(family, inv, days: Sequence[date], spec: RunSpec, *, cfg,
          progress=None) -> Sweep:
    """Pita vipande vyote: quotes → mwendo → stop → kikapu → trade."""
    partitions = inv.of(family.SYMBOL)
    out = Sweep()
    historia: dict[str, list[float]] = {}
    t0 = time.time()

    for kundi in chunks(days):
        maombi = []
        for d in kundi:
            for s in family.sessions_for(d):
                # Kuingia → kutoka + dirisha la kutoka, ikiwa ombi MOJA.
                urefu = int((s.exit_at - s.entry_at).total_seconds())
                maombi.append((s.entry_at, urefu + family.WINDOW_SECONDS))
        frame = TK.read_windows(inv, family.SYMBOL, maombi,
                                partitions=partitions)

        for d in kundi:
            for s in family.sessions_for(d):
                try:
                    ndani = quotes(frame, s.entry_at, family.WINDOW_SECONDS)
                    nje = quotes(frame, s.exit_at, family.WINDOW_SECONDS)
                except Exception as exc:                       # noqa: BLE001
                    out.missing.append((d, s.leg, str(exc)[:80]))
                    continue

                # Stop ya leo inatoka kwenye historia ya JANA. Inasomwa kabla
                # ya mwendo wa leo kuongezwa — hapo ndipo lookahead ingeingia.
                nyuma = historia.setdefault(s.leg, [])
                m = family.stop_from_history(nyuma)
                if m is not None:
                    vikapu = family.baskets([d], move_pips={(d, s.leg): m})
                    for k in vikapu:
                        soko = {family.SYMBOL: market(
                            family, spec,
                            spread_pips=ndani.spread_pips(family.PIP),
                            mid=ndani.mid)}
                        jibu = execute(k, cfg=cfg,
                                       ticks_by_symbol={family.SYMBOL: frame},
                                       market=soko,
                                       window_seconds=family.WINDOW_SECONDS,
                                       path_ticks={family.SYMBOL: frame})
                        if jibu.executed:
                            out.trades.extend(jibu.trades)
                        else:
                            out.rejected.append((d, s.leg, jibu.reason))

                kiasi = family.session_move_pips(ndani, nje, pip=family.PIP)
                out.moves[(d, s.leg)] = kiasi
                nyuma.append(kiasi)

        if progress:
            progress(f"   {kundi[0]:%Y-%m-%d}  siku {len(kundi):>2}  "
                     f"trades {len(out.trades):>5,}  stop {len(out.stopped):>4,}")
    out.seconds = time.time() - t0
    return out


# ===========================================================================
# Vipimo na lango
# ===========================================================================


@dataclass
class Measured:
    """Vipimo vyote vinavyoingia kwenye lango la §6, kwa kila leg."""

    per_leg: dict
    worst_leg: str
    curve: Any
    gap: list

    @property
    def move_pips(self) -> float:
        return self.per_leg[self.worst_leg]["move_pips"]

    @property
    def sigma_pips(self) -> float:
        return self.per_leg[self.worst_leg]["sigma_pips"]

    @property
    def cost_pips(self) -> float:
        return self.per_leg[self.worst_leg]["cost_pips"]


def measure(family, sw: Sweep, days: Sequence[date]) -> Measured:
    """Vipimo kwa KILA leg peke yake.

    Legs za urefu tofauti zina `σ` tofauti (F0: masaa 9 dhidi ya 4.4), kwa
    hiyo uwiano wa gharama si mmoja. Kuchanganya kungefanya leg fupi ijifiche
    nyuma ya ndefu, na §6.2 inasema *"σ ya dirisha la kushikilia"*, si *"σ ya
    wastani wa familia"*.
    """
    kwa_leg: dict[str, dict] = {}
    for leg in sorted({l for (_, l) in sw.moves}):
        m = [v for (_, l), v in sw.moves.items() if l == leg]
        t_leg = [t for t in sw.finished if t.basket_id.endswith(f":{leg}")]
        if not m or not t_leg:
            continue
        wastani = st.fmean(m)
        gharama = st.fmean(t.spread_realised_pips + t.commission_pips
                           for t in t_leg)
        sigma = wastani * family.MOVE_TO_SIGMA
        kwa_leg[leg] = {"move_pips": wastani, "sigma_pips": sigma,
                        "cost_pips": gharama, "n": len(t_leg),
                        "ratio": gharama / sigma}
    if not kwa_leg:
        raise RuntimeError("hakuna leg yenye trade — hakuna cha kupima")

    return Measured(
        per_leg=kwa_leg,
        worst_leg=max(kwa_leg, key=lambda k: kwa_leg[k]["ratio"]),
        curve=daily_r(sw.trades, days=list(days)),
        gap=sorted(t.spread_gap_pips for t in sw.finished),
    )


def sharpe_per_day(family, mz: Measured, *, edge_pips: float,
                   n_legs: int) -> float:
    """Sharpe-kwa-siku **ILIYOTANGAZWA**, si iliyopatikana.

    Inatokana na edge ya §9 (iliyoandikwa kabla) na volatility **iliyopimwa**
    — si kwenye faida iliyotokea. Ikitoka kwenye faida, lango la 6.3
    lingekuwa likijipima lenyewe: familia iliyofanya vizuri ingedai kwamba
    ilihitaji matukio machache, na kila kitu kingepita.
    """
    sl = family.SL_MOVE_MULT * mz.move_pips
    kikomo = sl + mz.cost_pips
    edge_R = edge_pips / kikomo
    sigma_R = mz.sigma_pips / kikomo
    return (n_legs * edge_R) / (sigma_R * (n_legs ** 0.5))


def gate(family, mz: Measured, *, edge_pips: float, n_legs: int
         ) -> tuple[Qualification, float]:
    """Lango la §6, likiwa limepimwa kwa leg mbaya kabisa."""
    s = sharpe_per_day(family, mz, edge_pips=edge_pips, n_legs=n_legs)
    q = qualify(
        family.FAMILY, family.SYMBOL,
        mechanism_ok=True, mechanism_note=family.DECLARATION.source,
        cost_pips=mz.cost_pips, sigma_pips=mz.sigma_pips,
        n_events=mz.curve.n_active, sharpe_per_event=s,
    )
    return q, s


__all__ = ["DAYS_PER_CHUNK", "RunSpec", "Sweep", "Measured", "chunks",
           "market", "sweep", "measure", "sharpe_per_day", "gate"]
