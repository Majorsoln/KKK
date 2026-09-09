"""Gotobi — malipo ya waagizaji wa Japani — DOCTRINE §4, §9, §11.

**Mekanizimu.** Benki za Japani zinaweka *nakane* (仲値) — kiwango kimoja cha
siku kinachotumika kwa miamala yote ya wateja — saa **09:55 Asia/Tokyo**.
Waagizaji wanaonunua bidhaa kwa dola wanalipa siku za **gotobi** (五十日):
tarehe zinazogawanyika kwa 5. Siku hizo mahitaji ya dola yanajilimbikiza,
benki zinabidi zinunue dola sokoni ili kufunika oda za wateja, na shinikizo
linaishia kwenye fix.

```
09:00 → 09:55 JST    benki zinanunua dola kufunika oda za gotobi
09:55 JST            nakane inawekwa;  shinikizo linaisha
```

Kwa hiyo: **BUY USDJPY** kabla ya fix, **toka kwenye fix**.

Ni mtiririko wa **mkataba**, si wa habari: mwagizaji hana chaguo la kulipa
au kutolipa. Ndiyo tofauti kati ya Gotobi na familia ya benki kuu (F2,
iliyosimamishwa §9.1) — habari inaweza kuwa imeshapangwa kwenye bei, oda ya
malipo haiwezi.

---

**Kutoka ni dakika TANO ZINAZOISHIA kwenye fix, si zinazoanzia hapo.**

Shinikizo lipo **kabla** ya 09:55; baada yake limekwisha. `runner.execute`
inasoma `[kutoka, kutoka + dirisha)`, kwa hiyo nanga ya kutoka ni

```
09:55 JST − sekunde 300  =  09:50 JST      →  dirisha [09:50, 09:55)
```

Si chaguo la kigezo: inatokana na `WINDOW_SECONDS` na mahali pa fix.
Kuchukua `[09:55, 10:00)` kungekuwa kuuza **baada** ya mtiririko, ambapo bei
inaanza kurudi — na kungefuta edge nzima kwa ufafanuzi.

---

**Kalenda ya Japani ni sehemu ya mekanizimu, si urahisi.** Gotobi ni siku ya
**malipo ya benki**. Tarehe ÷5 ikianguka siku isiyo ya kazi, malipo
yanasogezwa mbele hadi siku ya kazi inayofuata. Bila sikukuu za Japani,
**tarehe 66 kati ya 548 (12%)** zingeshikwa vibaya — tungekosa siku zenye
mtiririko na kutrade siku zisizo nazo. Ona `events/jp_calendar.py`.

---

**JPY ina mtego wa thamani ya pip.** Kwa EURUSD, pip ni `$10` kwa lot daima.
Kwa USDJPY, pip ni `1,000 JPY` kwa lot — na thamani yake kwa dola ni
`1000 / bei`, inayobadilika kutoka `$9.09` (bei 110) hadi `$6.45` (bei 155).
Kuiweka thabiti kungebadilisha `commission_pips` kwa 40% kwenye sampuli yetu,
na lango la gharama la §6.2 lingeamua kwa namba isiyo sahihi.

---

**Onyo lililoandikwa kabla ya run.** Dirisha ni saa **1.33** pekee. `σ` inakua
kwa `√muda`, gharama haikui. Kwa makadirio ya EURUSD leg B (σ 15.86 pips kwa
saa 4.4), USDJPY kwenye saa 1.33 ina `σ ≈ 12` pips za JPY, wakati gharama ni
`≈ 2.1` pips. Uwiano `≈ 17%`, dhidi ya bajeti ya **8%**.

**Nabashiri Gotobi itakwama kwenye lango la gharama (§6.2), si kwenye `p`.**
Hilo si sababu ya kutoijenga: lango linapimwa, halikadiriwi, na makadirio
yangu yameshakosea mara mbili kwenye mradi huu. Likikwama, jibu ni *"dirisha
ni fupi mno kwa gharama hii"* — na halitagharimu α hata kidogo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable, Iterable, Mapping, Sequence

from src.events.clock import TOKYO_FIX, Anchor, ni_gotobi, ni_siku_ya_kazi
from src.events.jp_calendar import holidays_between
from src.families import stops as STOPS
from src.families.base import Declaration, FamilyError
from src.portfolio.basket import BUY, Basket, Leg
from src.portfolio.regime import NORMAL, regime_of

FAMILY = "Gotobi"
SYMBOL = "USDJPY"

LEG = "T"                               # Tokyo — leg moja pekee

# USDJPY: pip ni 0.01. **Thamani yake si thabiti** — ona docstring.
PIP = 0.01
POINT = 0.001
CONTRACT_SIZE = 100_000.0

# Familia hii ina symbol MOJA. `SYMBOLS`/`PIPS` zipo ili chombo cha
# jumla (`gate_probe`) kisihitaji kujua ni familia ipi.
SYMBOLS = (SYMBOL,)
PIPS = {SYMBOL: PIP}
POINTS = {SYMBOL: POINT}


def pip_value(mid: float) -> float:
    """Thamani ya pip kwa lot moja, kwa akaunti ya USD.

    `100,000 × 0.01 = 1,000 JPY` kwa pip; kwa dola ni `1000 ÷ bei`. Kwenye
    sampuli yetu bei inatoka ~102 hadi ~162, kwa hiyo thamani inatoka
    `$9.80` hadi `$6.17` — tofauti ya **37%**. Kuiweka thabiti kungebadilisha
    `commission_pips` kwa kiasi kile kile.
    """
    if mid <= 0:
        raise FamilyError(f"bei si chanya: {mid}")
    return CONTRACT_SIZE * PIP / mid


ENTRY: Anchor = Anchor(8, 30, "Asia/Tokyo", "kabla ya nakane")
FIX: Anchor = TOKYO_FIX                 # 09:55 Asia/Tokyo

WINDOW_SECONDS = 300

# Dirisha la kutoka ni dakika tano ZINAZOISHIA kwenye fix. Si chaguo — ni
# `FIX − WINDOW_SECONDS`, kwa sababu `execute` inasoma mbele kutoka nanga.
EXIT_OFFSET = timedelta(seconds=-WINDOW_SECONDS)

# §5.1. `4.0` ni ile ile ya F0 — imepimwa hapo (kugongwa 1.83% kwa miaka
# minane), si kubuniwa upya kwa familia hii.
SL_MOVE_MULT = 4.0

SL_LOOKBACK_SESSIONS = STOPS.LOOKBACK_SESSIONS
SL_MIN_SESSIONS = STOPS.MIN_SESSIONS
MOVE_TO_SIGMA = STOPS.MOVE_TO_SIGMA
session_move_pips = STOPS.session_move_pips
stop_from_history = STOPS.stop_from_history
stop_from_moves = STOPS.stop_from_moves

# Gotobi inafunga 00:55 UTC; F1 inafunguka 14:00. Haigongani na kitu, lakini
# inapewa kipaumbele cha kati kwa sababu ina matukio ~550 dhidi ya 99 za F1.
PRIORITY = 2

# Edge iliyotangazwa §9: **2.8 bps**. Kwa USDJPY karibu na 140, bp moja ni
# `140 × 0.0001 = 0.014` = pips 1.4, kwa hiyo 2.8 bps ≈ **pips 3.9 za JPY**.
# Inaandikwa kwa pips kwa sababu ndicho kipimo cha injini; ubadilishaji
# unafanywa hapa mara moja badala ya kila mahali.
DECLARED_EDGE_PIPS = 3.9

MECHANISM = (
    "Benki za Japani zinaweka nakane (仲値) saa 09:55 Asia/Tokyo, kiwango "
    "kimoja cha siku kwa miamala yote ya wateja. Waagizaji wanalipa siku za "
    "gotobi (tarehe ÷ 5), kwa hiyo mahitaji ya dola yanajilimbikiza siku hizo "
    "na benki zinabidi zinunue dola sokoni kabla ya fix. Ni mtiririko wa "
    "MKATABA — mwagizaji hana chaguo la kutolipa."
)

DECLARATION = Declaration(
    family=FAMILY,
    symbols=(SYMBOL,),
    nanga=("08:30 Asia/Tokyo → 09:50 Asia/Tokyo (dakika tano zinazoishia "
           "kwenye nakane ya 09:55); siku za gotobi pekee, kwa kalenda ya "
           "benki za Japani"),
    mwelekeo=f"{BUY} {SYMBOL} — mahitaji ya dola ya waagizaji kabla ya fix",
    kuingia=(f"tick-VWAP ya ask kwenye sekunde {WINDOW_SECONDS} kutoka "
             f"08:30 Asia/Tokyo"),
    stop=(f"{SL_MOVE_MULT} × wastani wa |kutoka − kuingia| kwa vikao "
          f"{SL_LOOKBACK_SESSIONS} VILIVYOPITA (chini kabisa "
          f"{SL_MIN_SESSIONS}); bima pekee; ikigongwa, R = −1.0"),
    kutoka="kwa SAA, kwenye dirisha linaloishia kwenye nakane",
    ukubwa="uzito 1.0 — hakuna ishara; hatari inatoka RCE, lots ∝ 1/mwendo",
    mechanism=MECHANISM,
    eligible_regimes=(NORMAL,),
    trials=1,
    source=("Desturi ya nakane ya benki za Japani; ushahidi wa kitaaluma na "
            "wa wataalamu unaishia miaka ya 2000. Inauzwa kama EA sokoni — "
            "msongamano unatarajiwa (§9)."),
    params={
        "window_seconds": WINDOW_SECONDS,
        "sl_move_mult": SL_MOVE_MULT,
        "sl_lookback_sessions": SL_LOOKBACK_SESSIONS,
        "sl_min_sessions": SL_MIN_SESSIONS,
        "priority": PRIORITY,
        "fix_tz": FIX.tz,
        "jp_calendar": True,
    },
)


# ===========================================================================
# Madirisha na vikapu
# ===========================================================================


@dataclass(frozen=True)
class Session:
    """Ncha mbili za kikao kimoja, ikiwa UTC."""

    day: date
    leg: str
    side: str
    entry_at: datetime
    exit_at: datetime

    @property
    def hours(self) -> float:
        return (self.exit_at - self.entry_at).total_seconds() / 3600.0

    def render(self) -> str:
        return (f"{FAMILY}:{self.day}:{self.leg} {self.side} "
                f"{self.entry_at:%H:%M}→{self.exit_at:%H:%M}Z "
                f"({self.hours:.2f}h)")


def sessions_for(day: date) -> tuple[Session, ...]:
    """Kikao kimoja cha siku hii, ikiwa UTC. Hakuna ukaguzi wa gotobi hapa."""
    ndani = ENTRY.at(day)
    nje = FIX.at(day) + EXIT_OFFSET
    if nje <= ndani:
        raise FamilyError(
            f"{day}: kutoka ({nje:%H:%M}Z) si baada ya kuingia "
            f"({ndani:%H:%M}Z) — nanga zinahitaji kupitiwa upya")
    return (Session(day, LEG, BUY, ndani, nje),)


def jp_holidays(days: Sequence[date]) -> set[date]:
    """Sikukuu za Japani zinazogusa dirisha lililotolewa."""
    if not days:
        return set()
    return holidays_between(min(days), max(days))


def eligible_days(
    days: Iterable[date],
    *,
    holidays: Iterable[date] | None = None,
    cb_days: Iterable[date] = (),
) -> list[date]:
    """Siku za gotobi zinazostahili: malipo ya benki **na** regime `NORMAL`.

    `holidays=None` inamaanisha *"tumia kalenda ya Japani"* — si *"hakuna
    sikukuu"*. Ni chaguo-msingi la makusudi: familia hii **haiwezi** kuwa
    sahihi bila kalenda, kwa hiyo kusahau kuipitisha hakupaswi kukubalika
    kimya.
    """
    orodha = list(days)
    zilizofungwa = set(jp_holidays(orodha) if holidays is None else holidays)
    matukio = set(cb_days)
    return [d for d in orodha
            if ni_siku_ya_kazi(d, zilizofungwa)
            and ni_gotobi(d, zilizofungwa)
            and regime_of(d, holidays=zilizofungwa, cb_days=matukio) == NORMAL]


def baskets(
    days: Sequence[date],
    *,
    move_pips: Mapping[tuple[date, str], float] | Callable[[date, str], float | None],
    holidays: Iterable[date] | None = None,
    cb_days: Iterable[date] = (),
) -> list[Basket]:
    """Vikapu vyote vya Gotobi kwa siku zilizotolewa."""
    pata = (move_pips.get if hasattr(move_pips, "get")
            else lambda k, _=None: move_pips(k[0], k[1]))

    out: list[Basket] = []
    for d in eligible_days(days, holidays=holidays, cb_days=cb_days):
        for s in sessions_for(d):
            mwendo = pata((d, s.leg), None)
            if mwendo is None:
                continue
            mwendo = float(mwendo)
            if mwendo <= 0:
                raise FamilyError(f"{d} {s.leg}: mwendo si chanya ({mwendo})")
            out.append(Basket(
                family=FAMILY,
                basket_id=f"{FAMILY}:{d.isoformat()}:{s.leg}",
                legs=(Leg(symbol=SYMBOL, side=s.side,
                          sl_pips=SL_MOVE_MULT * mwendo,
                          weight=1.0,
                          meta={"leg": s.leg, "move_pips": mwendo}),),
                entry_at=s.entry_at,
                planned_exit_at=s.exit_at,
                priority=PRIORITY,
                atomic=True,
                eligible_regimes=(NORMAL,),
            ))
    return out


def windows_to_read(baskets_: Sequence[Basket]) -> list[tuple[datetime, int]]:
    """Madirisha ya ticks yanayohitajika — `(mwanzo, sekunde)`."""
    seti = {(b.entry_at, WINDOW_SECONDS) for b in baskets_}
    seti |= {(b.planned_exit_at, WINDOW_SECONDS) for b in baskets_}
    return sorted(seti)


__all__ = [
    "FAMILY", "SYMBOL", "PIP", "POINT", "CONTRACT_SIZE", "pip_value",
    "LEG", "ENTRY", "FIX", "EXIT_OFFSET", "WINDOW_SECONDS", "SL_MOVE_MULT",
    "SL_LOOKBACK_SESSIONS", "SL_MIN_SESSIONS", "MOVE_TO_SIGMA", "PRIORITY",
    "DECLARED_EDGE_PIPS", "MECHANISM", "DECLARATION", "Session", "session_move_pips",
    "stop_from_history", "stop_from_moves", "sessions_for", "jp_holidays",
    "eligible_days", "baskets", "windows_to_read",
]
