"""F0 — mtiririko wa saa za nchi — DOCTRINE §4, §9, §11.

**Mekanizimu.** Sarafu inashuka wakati wa saa za biashara za nchi yake, na
inapanda wakati wa saa za nje. Sababu inayopendekezwa kwenye fasihi ni
mtiririko wa oda za wateja wa ndani — wawekezaji wa ndani wanaonunua mali za
nje wanauza sarafu ya ndani wakati wa saa zao za kazi — pamoja na wenye soko wa
ndani wanaobeba inventory mchana kwao na kuisukuma nje jioni.

Kwa EURUSD hiyo inatoa **legs mbili zenye mwelekeo tofauti kwa siku moja**:

```
A   kufunguka London → kufunga London     saa za ndani za EURO   → SELL
B   kufunga London  → kufunga New York    saa za ndani za DOLA   → BUY
```

Kwamba mielekeo inapingana ndiyo inayofanya F0 iwe mtihani safi: **si bet ya
mwelekeo wa dola.** Ikiwa faida inatoka kwenye mwelekeo wa dola kwa kipindi
chetu, legs mbili zitafutana na jibu litakuwa sifuri. Kinachoweza kunusurika ni
muundo wa **saa za siku** pekee.

---

**Kwa nini nanga ya kati ni 17:00 Europe/London, si 12:00 America/New_York.**

Jedwali la §9 linaandika nanga za F0 kama *"08:00 London · 12:00 NY"*. Nyakati
hizo mbili ni **kitu kile kile** kwa wiki 49 kati ya 52: 17:00 London ni 12:00
New York majira ya baridi na majira ya joto sawa.

Zinatofautiana kwenye wiki za **mpito wa DST**, ambapo EU na US zinabadilisha
tarehe tofauti (§11). Kwenye wiki hizo:

```
17:00 London  =  12:00 NY   (kawaida)
              =  13:00 NY   (wiki ~3 kwa mwaka)
```

Mekanizimu unasema *"madawati ya Ulaya yanaenda nyumbani"*. Hiyo ni saa ya
**London**, si ya New York. Kuweka nanga ya kufunga kwa Ulaya kwenye saa ya
Marekani kungehamisha mpaka kwa saa moja kwa siku ~120 kati ya 1,900 — mahali
ambapo hakuna sababu ya kiuchumi ya kuhamisha. Ndiyo kasoro ambayo §11
inaionya: nanga inayohama kwa sababu ya nchi isiyohusika.

Kwa hiyo kila mpaka unashikwa kwenye saa ya soko linaloutengeneza. Hili ni
**tangazo**, si uteuzi: limeandikwa kabla ya row moja ya data kusomwa, na
halibadilishwi baada ya kuona matokeo. Halihesabiki kama jaribio la ziada kwa
sababu mbadala haujaendeshwa wala hautaendeshwa.

---

**Kutoka ni kwa saa** (§4.1) — mekanizimu una umri unaojulikana, unaisha
madawati yanapofungwa. **Stop ni bima** (§4.2): `k × ATR(dirisha)`, na ATR
inapimwa kwa **vikao vilivyopita pekee**. Hiyo inatoa `lots ∝ 1/ATR` bila
mfumo wa pili wa ukubwa (§5.1).

`k` si kigezo huru cha kubadilishwa mpaka jibu lipendeze: `R = net_pips /
(sl_pips + cost_pips)`, kwa hiyo `k` ni **kipimo**, si ishara. Inabadilisha
ukubwa wa R, si alama yake wala mpangilio wa siku.

**Hakuna ishara.** Uzito ni 1.0 kila siku. F0 ni ya kalenda tupu — ndiyo maana
inaendeshwa kwanza, na ndiyo maana ina **jaribio moja**.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable, Iterable, Mapping, Sequence

from src.events.clock import (
    LONDON_CLOSE,
    LONDON_OPEN,
    NY_CLOSE,
    Anchor,
    ni_siku_ya_kazi,
)
from src.families.base import Declaration, FamilyError
from src.portfolio.basket import BUY, SELL, Basket, Leg
from src.portfolio.regime import NORMAL, regime_of

FAMILY = "F0"
SYMBOL = "EURUSD"

LEG_A = "A"                             # saa za Ulaya
LEG_B = "B"                             # saa za Marekani

A_ENTRY: Anchor = LONDON_OPEN           # 08:00 Europe/London
A_EXIT: Anchor = LONDON_CLOSE           # 17:00 Europe/London
B_EXIT: Anchor = NY_CLOSE               # 16:30 America/New_York

# Dirisha la tick-VWAP kwa kila ncha (§7.4). Sekunde 300 ni ile ile
# inayotumika kwenye udhibiti chanya na kwenye `runner.execute`.
WINDOW_SECONDS = 300

# Leg B inaingia pale dirisha la kutoka la leg A linapoishia. **Si chaguo** —
# ni matokeo ya `WINDOW_SECONDS`. Bila hilo, bei ya kutoka ya A na ya kuingia
# ya B zingehesabiwa kutoka ticks zilezile, na akaunti ingekuwa na nafasi mbili
# za symbol moja kwa dakika tano (arbiter ingekataa ya pili).
B_ENTRY_DELAY = timedelta(seconds=WINDOW_SECONDS)

# §5.1 — stop ni mizidisho ya mwendo wa dirisha. Ona docstring: hii ni kipimo,
# si ishara.
SL_ATR_MULT = 2.0

# Vikao vya nyuma vinavyotumika kupima ATR. Ni vya NYUMA pekee.
SL_LOOKBACK_SESSIONS = 20
SL_MIN_SESSIONS = 10

# Kipaumbele kwenye arbiter: namba kubwa = inasubiri. F0 ina matukio ~1,900;
# F1 ina 99. Familia adimu inapewa nafasi kwanza kwa sababu kupoteza tukio
# moja kati ya 99 ni 1% ya ushahidi wake, dhidi ya 0.05% kwa F0.
PRIORITY = 3

MECHANISM = (
    "Sarafu inashuka wakati wa saa za biashara za nchi yake na inapanda wakati "
    "wa saa za nje (mtiririko wa wateja wa ndani + inventory ya wenye soko). "
    "EURUSD ina pande zote mbili: saa za Ulaya na saa za Marekani ziko ndani "
    "ya siku moja, kwa hiyo legs mbili zinapima mekanizimu ULE ULE kwa "
    "mielekeo miwili."
)

DECLARATION = Declaration(
    family=FAMILY,
    symbols=(SYMBOL,),
    nanga=("A: 08:00 Europe/London → 17:00 Europe/London · "
           "B: 17:05 Europe/London → 16:30 America/New_York"),
    mwelekeo=(f"A: {SELL} {SYMBOL} (saa za ndani za euro) · "
              f"B: {BUY} {SYMBOL} (saa za ndani za dola)"),
    kuingia=(f"tick-VWAP ya upande unaotekelezeka kwenye sekunde "
             f"{WINDOW_SECONDS} kutoka nanga (ask kununua, bid kuuza)"),
    stop=(f"{SL_ATR_MULT} × ATR ya dirisha lile lile kwa vikao "
          f"{SL_LOOKBACK_SESSIONS} VILIVYOPITA (chini kabisa "
          f"{SL_MIN_SESSIONS}); bima pekee, si mkakati"),
    kutoka="kwa SAA, kwenye nanga ya kutoka; stop haitumiki kama lengo",
    ukubwa="uzito 1.0 — hakuna ishara; hatari inatoka RCE, lots ∝ 1/ATR",
    mechanism=MECHANISM,
    eligible_regimes=(NORMAL,),
    trials=1,
    source="Ranaldo (2009) · Breedon & Ranaldo (2013) — ushahidi unaishia ~2007",
    params={
        "window_seconds": WINDOW_SECONDS,
        "sl_atr_mult": SL_ATR_MULT,
        "sl_lookback_sessions": SL_LOOKBACK_SESSIONS,
        "sl_min_sessions": SL_MIN_SESSIONS,
        "priority": PRIORITY,
        "pivot_tz": A_EXIT.tz,
    },
)


# ===========================================================================
# ATR — vikao vilivyopita PEKEE
# ===========================================================================


def atr_from_ranges(
    ranges: Mapping[tuple[date, str], float],
    *,
    lookback: int = SL_LOOKBACK_SESSIONS,
    min_sessions: int = SL_MIN_SESSIONS,
) -> dict[tuple[date, str], float]:
    """Wastani wa mwendo wa dirisha kwa vikao vilivyotangulia.

    `ranges[(siku, leg)]` ni mwendo ULIOPIMWA wa dirisha hilo siku hiyo. Jibu
    la siku fulani linatumia **siku zilizotangulia pekee** — siku yenyewe
    haiingii. Bila hilo, stop ingejua mwendo wa siku ambayo bado
    haijatokea, na ukubwa wa position ungekuwa na lookahead: siku zenye mwendo
    mkubwa zingepewa lots ndogo *kwa sababu* mwendo ulikuwa mkubwa.

    Siku zisizo na vikao `min_sessions` vya nyuma hazipati jibu, kwa hiyo
    hazizalishi kikapu. Ni gharama ya kuanzia, si uteuzi.
    """
    if lookback < 1:
        raise FamilyError(f"lookback ni {lookback}, si ≥ 1")
    if min_sessions < 1 or min_sessions > lookback:
        raise FamilyError(
            f"min_sessions {min_sessions} haiko kati ya 1 na lookback {lookback}")

    out: dict[tuple[date, str], float] = {}
    kwa_leg: dict[str, list[float]] = {}
    for (siku, leg) in sorted(ranges, key=lambda k: (k[1], k[0])):
        nyuma = kwa_leg.setdefault(leg, [])
        if len(nyuma) >= min_sessions:
            teule = nyuma[-lookback:]
            out[(siku, leg)] = sum(teule) / len(teule)
        thamani = float(ranges[(siku, leg)])
        if thamani <= 0:
            raise FamilyError(f"mwendo si chanya: {siku} {leg} → {thamani}")
        nyuma.append(thamani)
    return out


# ===========================================================================
# Madirisha na vikapu
# ===========================================================================


@dataclass(frozen=True)
class Session:
    """Ncha mbili za leg moja, siku moja, ikiwa UTC."""

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


def sessions_for(day: date) -> tuple[Session, Session]:
    """Legs mbili za siku hii, ikiwa UTC. Hakuna ukaguzi wa regime hapa."""
    a_in = A_ENTRY.at(day)
    a_out = A_EXIT.at(day)
    b_in = a_out + B_ENTRY_DELAY
    b_out = B_EXIT.at(day)

    if a_out <= a_in:
        raise FamilyError(f"{day}: kufunga London si baada ya kufunguka")
    if b_out <= b_in:
        # Haiwezekani kwa kalenda ya sasa (17:00 London ni 12:00 au 13:00 NY),
        # lakini sheria ya DST ikibadilika — na imebadilika mara mbili tangu
        # 2007 — hii inalipuka badala ya kutoa leg ya urefu hasi kimya.
        raise FamilyError(
            f"{day}: leg B ingekuwa na urefu {(b_out - b_in)} — kufunga New "
            f"York ({b_out:%H:%M}Z) si baada ya kufunga London + dirisha "
            f"({b_in:%H:%M}Z). Sheria ya DST imebadilika; nanga zinahitaji "
            f"kupitiwa upya kabla ya run yoyote"
        )

    return (
        Session(day, LEG_A, SELL, a_in, a_out),
        Session(day, LEG_B, BUY, b_in, b_out),
    )


def eligible_days(
    days: Iterable[date],
    *,
    holidays: Iterable[date] = (),
    cb_days: Iterable[date] = (),
) -> list[date]:
    """Siku ambazo F0 inaendeshwa: siku ya kazi **na** regime `NORMAL`.

    Kutokuendesha siku ya fix ya mwisho wa mwezi si kuzunguka lango — ni
    ufafanuzi wa F0 uliotangazwa mbele (`src/portfolio/regime.py`).
    """
    zilizofungwa = set(holidays)
    matukio = set(cb_days)
    return [d for d in days
            if ni_siku_ya_kazi(d, zilizofungwa)
            and regime_of(d, holidays=zilizofungwa, cb_days=matukio) == NORMAL]


def baskets(
    days: Sequence[date],
    *,
    atr_pips: Mapping[tuple[date, str], float] | Callable[[date, str], float | None],
    holidays: Iterable[date] = (),
    cb_days: Iterable[date] = (),
) -> list[Basket]:
    """Vikapu vyote vya F0 kwa siku zilizotolewa.

    Kikapu kimoja kwa kila leg — si kimoja chenye legs mbili. Legs zina
    `entry_at` tofauti, na `Basket` ni **nia moja kwenye dirisha moja**.
    Kuzichanganya kungelazimisha nanga moja kwa mbili.

    `atr_pips` inaweza kuwa mapping au function. Ikirudisha `None` (au ikikosa
    ufunguo), siku hiyo **hairuki kimya**: leg hiyo haizalishwi, kwa sababu
    bila stop hakuna lots (§5).
    """
    pata = (atr_pips.get if hasattr(atr_pips, "get")
            else lambda k, _=None: atr_pips(k[0], k[1]))

    out: list[Basket] = []
    for d in eligible_days(days, holidays=holidays, cb_days=cb_days):
        for s in sessions_for(d):
            atr = pata((d, s.leg), None)
            if atr is None:
                continue
            atr = float(atr)
            if atr <= 0:
                raise FamilyError(f"{d} {s.leg}: ATR si chanya ({atr})")
            out.append(Basket(
                family=FAMILY,
                basket_id=f"{FAMILY}:{d.isoformat()}:{s.leg}",
                legs=(Leg(symbol=SYMBOL, side=s.side,
                          sl_pips=SL_ATR_MULT * atr,
                          weight=1.0,
                          meta={"leg": s.leg, "atr_pips": atr}),),
                entry_at=s.entry_at,
                planned_exit_at=s.exit_at,
                priority=PRIORITY,
                atomic=True,
                eligible_regimes=(NORMAL,),
            ))
    return out


def windows_to_read(baskets_: Sequence[Basket]) -> list[tuple[datetime, int]]:
    """Madirisha ya ticks yanayohitajika — `(mwanzo, sekunde)`.

    F0 inasoma sekunde 300 kwenye kila ncha ya kila leg: dakika 20 kwa siku
    kati ya 1,440. Kupakia siku nzima kungekuwa mara 72 ya kile
    kinachotumika, na kwa miaka nane ya ticks hiyo ni tofauti kati ya
    dakika na masaa.
    """
    seti = {(b.entry_at, WINDOW_SECONDS) for b in baskets_}
    seti |= {(b.planned_exit_at, WINDOW_SECONDS) for b in baskets_}
    return sorted(seti)


__all__ = [
    "FAMILY", "SYMBOL", "LEG_A", "LEG_B", "A_ENTRY", "A_EXIT", "B_EXIT",
    "WINDOW_SECONDS", "B_ENTRY_DELAY", "SL_ATR_MULT", "SL_LOOKBACK_SESSIONS",
    "SL_MIN_SESSIONS", "PRIORITY", "MECHANISM", "DECLARATION",
    "Session", "atr_from_ranges", "sessions_for", "eligible_days", "baskets",
    "windows_to_read",
]
