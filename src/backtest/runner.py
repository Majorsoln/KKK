"""Kikapu → trades → P&L katika vipimo vya R — DOCTRINE §4.1, §5, R12.

Njia ya P&L kwa familia zilizoshikwa na saa:

```
kikapu → RCE.evaluate() → lots → bei za utekelezaji → P&L → R
```

RCE inafanya kila kitu cha gharama na ukubwa (R12). Kazi hapa ni tatu:
kuchukua bei sahihi, kuepuka kuhesabu gharama mara mbili, na kutoa hesabu
katika kipimo kinacholinganishika kati ya symbols.

---

**Kutohesabu spread mara mbili.** Bei za kuingia na kutoka ni za **upande
unaotekelezeka** (`ask` kununua, `bid` kuuza), kwa hiyo spread **tayari imo
ndani ya bei**. `cost_pips` ya RCE nayo inajumuisha spread — lakini inatumika
kwa **sizing** (§5: SL ikigongwa hasara ni hasa `risk_per_trade`), si kwa
kupunguza P&L.

Kwa hiyo:

```
net_pips = (kutoka − kuingia) kwa bei za utekelezaji   ← spread imo humo
           − commission_pips − swap_pips               ← hazipo kwenye bei
```

`spread_pips` na `slippage_pips` **hazitolewi tena**. Kuzitoa kungekuwa
kuhesabu mara mbili, na `gross_pips` (mid→mid) inaruhusu kosa hilo lionekane:

```
spread iliyolipwa = gross_pips − net_pips − commission − swap
```

---

**Kipimo cha RCE dhidi ya ticks.** Kila trade inahifadhi `spread_realised_pips`
(kutoka kwenye ticks za dakika ile) pamoja na `spread_rce_pips` (kadirio la
RCE kutoka madirisha ya nyuma). Tofauti yake ndiyo namba inayoamua kama RCE v2
inahitajika (§ mpango, Lango 3) — imepimwa, si kudhaniwa.

---

**Utekelezaji nao ni wa atomiki.** Arbiter ilishathibitisha kwamba kikapu
kinapitika, lakini `evaluate()` ina ukaguzi zaidi (bajeti, DD, lot ya chini).
Leg ikikataliwa hapa, kikapu **kizima** hakitradiwi na kinawekwa alama
`PARTIAL_EXECUTION` — si tukio halali la strategy iliyotangazwa.

---

**Njia kati ya kuingia na kutoka INAPIMWA** (uamuzi wa PD 2026-09-09).

Toleo la kwanza lilichukua bei mbili na kudhania stop haigongwi. Kipimo cha
F0 kilikataa dhana hiyo: **3.0% ya vikao 200**, si 0.3% niliyokadiria kwa
kanuni ya normal. Upendeleo unaotokana nayo ni **+0.036 R/siku**, wakati
athari nzima ya F0 ilikuwa 0.023 — **kasoro kubwa kuliko kitu chenyewe.**

Suluhisho si kuiga tick kwa tick. Linahitajika **jambo moja**: mwendo mbaya
kabisa (MAE) kati ya ncha mbili.

```
MAE ≥ sl_pips   →   R = −1.0 hasa      (RCE inapima lots ili iwe hivyo)
MAE < sl_pips   →   R kama ilivyokuwa  (hakuna kinachobadilika)
```

Usawa ni wa RCE, si wa kwetu: `risk_at_stop = lots × (sl + cost) ×
pip_value`, kwa hiyo `net_pips = −(sl + cost)` inatoa `pnl = −risk_at_stop`
kwa hesabu ile ile inayotumika kwa trade ya kawaida. Hakuna tawi la pekee
kwenye P&L.

**Dirisha la kupima ni `[kuingia + dirisha, kutoka)`** — dakika tano za
kujaza hazihesabiwi (position bado haijakamilika) wala za kutoka (tayari
tunatoka). Ni dakika 10 kati ya masaa tisa, na kuziacha ni kuelekea upande
wa matumaini kwa kiasi kinachojulikana.

**`path_ticks` isipotolewa, hakuna kinachopimwa na `Trade.path_modelled`
inabaki `False`.** Ni ili matokeo yasije yakadaiwa kuwa yamepimwa wakati
hayakupimwa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Sequence

from src.events.clock import BUY, SELL, Quotes, quotes, usiku_wa_swap
from src.portfolio.basket import Basket

PARTIAL_EXECUTION = "PARTIAL_EXECUTION"


class ExecuteError(RuntimeError):
    """Kikapu hakiwezi kutekelezwa kama kilivyoombwa."""


@dataclass(frozen=True)
class Trade:
    """Trade moja iliyokamilika, pamoja na ushahidi wa gharama zake."""

    family: str
    basket_id: str
    symbol: str
    side: str
    lots: float
    entry_at: datetime
    exit_at: datetime
    entry_price: float
    exit_price: float
    gross_pips: float               # mid → mid, bila gharama yoyote
    net_pips: float                 # utekelezaji, pamoja na commission/swap
    commission_pips: float
    swap_pips: float
    spread_realised_pips: float     # kutoka ticks za dakika hiyo
    spread_rce_pips: float          # kadirio la RCE (madirisha ya nyuma)
    risk_unit: float                # "1R" — hatari ya leg ya uzito KAMILI
    risk_taken: float               # hatari halisi baada ya uzito
    pnl_account: float
    pip_value_acct: float
    stopped: bool = False           # stop iligongwa kabla ya saa ya kutoka
    mae_pips: float = 0.0           # mwendo mbaya kabisa ndani ya dirisha
    path_modelled: bool = False     # je njia ilipimwa kabisa?
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def r(self) -> float:
        """P&L katika vipimo vya **R**, ambapo `1R` ni hatari ya uzito kamili.

        Kigawanyo ni `risk_unit`, si `risk_taken`. Tofauti ni ya makusudi:

        * `pnl / risk_taken` ingekuwa **ufanisi** wa trade — haitegemei uzito,
          kwa hiyo leg ya uzito 0.5 iliyoshinda ingeonekana sawa na ya 1.0.
        * `pnl / risk_unit` ni **mchango** — leg ya uzito 0.5 inachangia nusu.

        Curve ya portfolio ni **jumla** ya R za trades. Kwa mchango, jumla hiyo
        ina maana; kwa ufanisi, ingekuwa ikijumlisha uwiano, ambayo si kitu.
        """
        return self.pnl_account / self.risk_unit if self.risk_unit else 0.0

    @property
    def weight(self) -> float:
        return self.risk_taken / self.risk_unit if self.risk_unit else 0.0

    @property
    def spread_gap_pips(self) -> float:
        """Halisi − kadirio la RCE. Chanya = RCE ilidharau gharama.

        Kwenye dirisha la fix hii inatarajiwa kuwa chanya, kwa sababu madirisha
        ya nyuma ya RCE hayaoni upanukaji wa dakika ile. Ukubwa wake ndio
        unaoamua kama RCE v2 inahitajika.

        **Kwa trade iliyogongwa stop ni `nan`**: dirisha la kutoka
        halikutumika, kwa hiyo hakuna spread ya kwenda-na-kurudi
        iliyolipwa. Kuiweka namba hapo kungechafua kipimo cha Lango 3 kwa
        thamani isiyotoka kwenye trade yenyewe.
        """
        return self.spread_realised_pips - self.spread_rce_pips

    def render(self) -> str:
        if self.stopped:
            return (f"{self.family}/{self.symbol} {self.side} {self.lots:.2f} · "
                    f"STOP {self.exit_at:%H:%M:%S} · R {self.r:+.3f} · "
                    f"MAE {self.mae_pips:.1f}p")
        return (f"{self.family}/{self.symbol} {self.side} {self.lots:.2f} · "
                f"net {self.net_pips:+.2f}p · R {self.r:+.3f} · "
                f"spread {self.spread_realised_pips:.2f} "
                f"(RCE {self.spread_rce_pips:.2f}, pengo {self.spread_gap_pips:+.2f})")

    def to_json(self) -> dict[str, Any]:
        return {
            "family": self.family, "basket_id": self.basket_id,
            "symbol": self.symbol, "side": self.side, "lots": self.lots,
            "entry_at": self.entry_at.isoformat(),
            "exit_at": self.exit_at.isoformat(),
            "gross_pips": self.gross_pips, "net_pips": self.net_pips,
            "commission_pips": self.commission_pips, "swap_pips": self.swap_pips,
            "spread_realised_pips": self.spread_realised_pips,
            "spread_rce_pips": self.spread_rce_pips,
            "spread_gap_pips": self.spread_gap_pips,
            "pnl_account": self.pnl_account, "r": self.r,
            "risk_unit": self.risk_unit, "risk_taken": self.risk_taken,
            "weight": self.weight, "stopped": self.stopped,
            "mae_pips": self.mae_pips, "path_modelled": self.path_modelled,
        }


@dataclass
class Execution:
    """Matokeo ya kutekeleza kikapu kimoja."""

    basket: Basket
    trades: list[Trade] = field(default_factory=list)
    executed: bool = True
    reason: str = ""
    failing_symbol: str = ""

    @property
    def r(self) -> float:
        return sum(t.r for t in self.trades)

    @property
    def pnl_account(self) -> float:
        return sum(t.pnl_account for t in self.trades)

    @property
    def n_stopped(self) -> int:
        return sum(1 for t in self.trades if t.stopped)

    def render(self) -> str:
        if not self.executed:
            return (f"{self.basket.family}/{self.basket.basket_id}  "
                    f"{self.reason} ({self.failing_symbol}) — HAKUNA trade")
        return (f"{self.basket.family}/{self.basket.basket_id}  "
                f"trades {len(self.trades)} · R {self.r:+.3f} · "
                f"${self.pnl_account:+.2f}")


@dataclass(frozen=True)
class Excursion:
    """Mwendo mbaya kabisa ndani ya dirisha, na wakati wa kuvuka stop."""

    mae_pips: float
    touch_at: datetime | None

    @property
    def stopped(self) -> bool:
        return self.touch_at is not None


def excursion(
    ticks,
    *,
    side: str,
    entry_price: float,
    sl_pips: float,
    pip: float,
    start: datetime,
    end: datetime,
) -> Excursion:
    """MAE kwenye `[start, end)`, na tick ya KWANZA inayovuka stop.

    Bei inayotumika ni ya **kufunga**, si ya kufungua: SELL inafungwa kwa
    `ask`, BUY kwa `bid`. Kutumia upande wa kufungua kungepunguza kila mwendo
    kwa spread nzima na kuripoti kugongwa kuchache kuliko halisi — ndiyo
    kasoro iliyokuwa ndani ya `f0_run --angalia-stop` toleo la kwanza.
    """
    import numpy as np
    import pandas as pd

    if sl_pips <= 0:
        raise ExecuteError(f"`sl_pips` ni {sl_pips}; MAE haina kizingiti")

    upande = side.upper()
    safu = "ask" if upande == SELL else "bid"
    if safu not in ticks.columns:
        raise ExecuteError(f"ticks hazina safu `{safu}` kwa {upande}")

    stamps = pd.to_datetime(ticks["timestamp"], utc=True)
    ndani = (stamps >= start) & (stamps < end)
    kipande = ticks.loc[ndani]
    if kipande.empty:
        # Hakuna ushahidi wa njia. **Si sawa na "haikugongwa"** — mwitaji
        # ndiye anayeamua, kwa `path_modelled`.
        return Excursion(mae_pips=0.0, touch_at=None)

    bei = np.asarray(kipande[safu], dtype=float)
    ishara = -1.0 if upande == SELL else 1.0
    mwendo = ishara * (entry_price - bei) / pip          # chanya = kwenda vibaya

    mae = float(mwendo.max())
    vuka = np.flatnonzero(mwendo >= sl_pips)
    wakati = (pd.Timestamp(np.asarray(kipande["timestamp"])[vuka[0]])
              .tz_convert("UTC").to_pydatetime()) if vuka.size else None
    return Excursion(mae_pips=mae, touch_at=wakati)


def execute(
    basket: Basket,
    *,
    cfg,
    ticks_by_symbol: dict[str, Any],
    market: dict[str, Any],
    window_seconds: int = 300,
    risk_scale: float = 1.0,
    path_ticks: dict[str, Any] | None = None,
) -> Execution:
    """Tekeleza kikapu kizima, au usitekeleze chochote.

    `market[symbol]` ina kila kitu RCE inachohitaji kwa symbol hiyo:
    `spec`, `account`, `h1_spreads`, `m5_spreads`, `pip_value_acct`,
    `commission_round_turn`, `pip`.

    `risk_scale` inapunguza hatari kwa uzito wa leg (§5.1: nguvu ya ishara
    inapunguza HATARI, si lots moja kwa moja).
    """
    from src.rce.engine import MarketContext, Proposal, evaluate

    out = Execution(basket=basket)
    kusanya: list[Trade] = []
    wazi: list[str] = []

    usiku = usiku_wa_swap(basket.entry_at, basket.planned_exit_at)

    for leg in sorted(basket.legs, key=lambda l: l.symbol):
        m = market.get(leg.symbol)
        if m is None:
            raise ExecuteError(f"muktadha wa soko haupo kwa {leg.symbol}")
        pip = float(m["pip"])
        ticks = ticks_by_symbol.get(leg.symbol)
        if ticks is None:
            raise ExecuteError(f"ticks hazipo kwa {leg.symbol}")

        ndani: Quotes = quotes(ticks, basket.entry_at, window_seconds)
        nje: Quotes = quotes(ticks, basket.planned_exit_at, window_seconds)
        upande = leg.side.upper()

        proposal = Proposal(
            symbol=leg.symbol, direction=upande,
            entry=ndani.executable(upande),
            sl_pips=leg.sl_pips, tp_pips=leg.sl_pips,   # kutoka ni kwa SAA (§4.1)
            order_type="market", strategy=basket.family,
        )
        ctx = MarketContext(
            account=m["account"], spec=m["spec"],
            h1_spreads=list(m["h1_spreads"]), m5_spreads=list(m["m5_spreads"]),
            pip_value_acct=float(m["pip_value_acct"]),
            commission_round_turn=float(m["commission_round_turn"]),
            open_symbols=tuple(wazi),
            nights=usiku.nights, triple_nights=usiku.triple_nights,
            now=basket.entry_at,
        )
        order = evaluate(cfg, proposal, ctx)
        if not order.approved:
            return Execution(basket=basket, executed=False,
                             reason=f"{PARTIAL_EXECUTION}:{order.reason}",
                             failing_symbol=leg.symbol)

        # ---- P&L ----
        ishara = 1.0 if upande == BUY else -1.0
        bei_ndani = ndani.executable(upande)
        bei_nje = nje.executable(SELL if upande == BUY else BUY)

        gross = ishara * (nje.mid - ndani.mid) / pip
        utekelezaji = ishara * (bei_nje - bei_ndani) / pip
        comm = order.cost.commission_pips
        swap = order.cost.swap_pips
        net = utekelezaji - comm - swap
        spread_halisi = gross - utekelezaji
        toka = basket.planned_exit_at
        bei_toka = bei_nje

        # ---- je stop iligongwa kabla ya saa ya kutoka? ----
        njia = path_ticks.get(leg.symbol) if path_ticks else None
        ilipimwa = njia is not None
        mwendo = Excursion(0.0, None)
        if ilipimwa:
            mwendo = excursion(
                njia, side=upande, entry_price=bei_ndani,
                sl_pips=leg.sl_pips, pip=pip,
                start=basket.entry_at + timedelta(seconds=window_seconds),
                end=basket.planned_exit_at)

        if mwendo.stopped:
            # Hasara kwenye stop ni HASA `risk_at_stop` kwa mkataba wa RCE
            # (`sizing.py`: `risk_at_stop = lots × (sl + cost) × pip_value`).
            # Kwa hiyo `net_pips` moja inatosha; P&L inafuata njia ile ile.
            gross = -leg.sl_pips
            net = -(leg.sl_pips + order.cost.cost_pips)
            toka = mwendo.touch_at
            bei_toka = bei_ndani - ishara * leg.sl_pips * pip
            # Dirisha la kutoka halikutumika: hakuna spread ya kwenda-na-kurudi
            # iliyolipwa, kwa hiyo Lango 3 halipimwi kwenye trade hii.
            spread_halisi = float("nan")

        uzito = max(0.0, min(1.0, risk_scale * leg.strength))
        lots = order.lots * uzito
        pnl = net * lots * float(m["pip_value_acct"])

        kusanya.append(Trade(
            family=basket.family, basket_id=basket.basket_id,
            symbol=leg.symbol, side=upande, lots=lots,
            entry_at=basket.entry_at, exit_at=toka,
            entry_price=bei_ndani, exit_price=bei_toka,
            gross_pips=gross, net_pips=net,
            commission_pips=comm, swap_pips=swap,
            # Spread iliyolipwa HALISI ni gross − utekelezaji: inajumuisha
            # spread ya kuingia na ya kutoka, ndivyo trade inavyolipa.
            spread_realised_pips=spread_halisi,
            spread_rce_pips=order.cost.spread_pips,
            risk_unit=order.sizing.risk_at_stop,
            risk_taken=order.sizing.risk_at_stop * uzito,
            pnl_account=pnl, pip_value_acct=float(m["pip_value_acct"]),
            stopped=mwendo.stopped, mae_pips=mwendo.mae_pips,
            path_modelled=ilipimwa,
        ))
        wazi.append(leg.symbol)

    out.trades = kusanya
    return out


def execute_all(baskets: Sequence[Basket], **kw) -> list[Execution]:
    return [execute(b, **kw) for b in baskets]


__all__ = ["PARTIAL_EXECUTION", "ExecuteError", "Excursion", "excursion",
           "Trade", "Execution", "execute", "execute_all"]
