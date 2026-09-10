"""F1 — hedge ya hisa kwenye fix ya mwisho wa mwezi — DOCTRINE §4, §9, §11.

**Mekanizimu.** Wawekezaji wanaoshikilia hisa za nje wanafunika hatari ya
sarafu kwa forwards. Thamani ya hisa inabadilika kila mwezi, kwa hiyo ukubwa
wa hedge unakuwa si sahihi — na unarekebishwa kwenye **fix ya 16:00 London
ya siku ya mwisho ya mwezi**, ambapo benchmarks zinapimwa.

```
hisa za nchi X zilipanda mwezi huu
   →  hedge ya mwekezaji wa nje iko ndogo mno
   →  anauza sarafu ya X zaidi kwenye fix
```

Ni mtiririko wa **mamlaka**: mwekezaji anayefuata benchmark hana chaguo la
kutorekebisha. Hiyo ndiyo tofauti yake na habari.

---

**Ni bet ya UWIANO, si ya mwelekeo wa dola.** Kila nchi ina hisa zake; hitaji
la hedge linatofautiana kati yao. Uzito unasawazishwa kwa cross-section
(`Σw = 0`), kwa hiyo **mwelekeo wa pamoja wa dola unatoka**, na kinachobaki ni
tofauti kati ya nchi. Bila kusawazisha, F1 ingekuwa bet ya dola yenye legs
sita — kitu tofauti kabisa, chenye `N_eff ≈ 1`.

**Kwa hiyo kikapu ni cha yote-au-hakuna** (`basket.py`). Leg moja ikikataliwa,
kilichobaki si F1 iliyopunguzwa — ni strategy nyingine yenye mwelekeo wa dola
usiokusudiwa.

---

**F1 HAIWEZI KUENDESHWA BILA ISHARA YA HISA.** `baskets` inadai `signal`;
hakuna chaguo-msingi. Bila utendaji wa faharasa za hisa, hakuna njia ya kujua
ni nani anauza nini — na "trade kila mwisho wa mwezi kwa uzito sawa"
si F1, ni bet ya dola isiyo na mekanizimu.

`PLACEHOLDER` ipo kwa **lango pekee**: `σ` na gharama hazitegemei ishara, kwa
hiyo uwezekano wa kupimika unaweza kujulikana kabla ya data ya hisa
kupatikana. Vikapu vyake vinabeba alama, na `p` **inakataliwa** kwa run yoyote
inayoibeba.

---

**Matukio ni 99, si 594.** Legs sita kwa tarehe moja ni **uchunguzi mmoja**:
zinasukumwa na fix ile ile, kwa saa ile ile, kwa mtiririko ule ule. Kuzihesabu
kama sita kungezidisha ushahidi kwa mara sita bila kuongeza taarifa hata
kidogo. Kizingiti chake ni kikali kuliko cha familia yoyote: `s ≥ 0.283`
inahitajika ili `(t*/s)² ≤ 99`.

---

**Regimes: `MONTH_END_FIX` NA `TURN_OF_YEAR`** (uamuzi wa PD). 31 Desemba ni
siku ya mwisho ya mwezi **na** iko ndani ya dirisha la mwisho wa mwaka.
Mekanizimu upo siku hiyo — benchmarks zinapimwa — kwa hiyo kuitoa kungekuwa
kupoteza tukio moja kati ya 99 kwa sababu ya sheria isiyohusika. Ukwasi mdogo
unashughulikiwa mahali pake: `max_spread` ya RCE inakataa leg ikiwa spread
imepanuka mno, na hilo ni **kipimo**, si dhana.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable, Iterable, Mapping, Sequence

from src.events.clock import LONDON_FIX, Anchor, siku_ya_mwisho_ya_mwezi
from src.families import stops as STOPS
from src.families.base import Declaration, FamilyError, Measurement
from src.portfolio.basket import BUY, SELL, Basket, Leg
from src.portfolio.regime import MONTH_END_FIX, TURN_OF_YEAR, regime_of

FAMILY = "F1"

# Majors sita za dola. Kila moja ina nchi yenye soko la hisa linaloweza
# kuhitaji hedge — ndiyo lango la §6.1. EURGBP haingii: haina upande wa dola.
SYMBOLS = ("EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "USDCHF", "USDCAD")

# Pairs ambazo dola iko UPANDE WA NUKUU. Kuuza dola = KUNUNUA pair.
USD_QUOTED = frozenset({"EURUSD", "GBPUSD", "AUDUSD"})

# ---------------------------------------------------------------------------
# §6.2 — symbols ZILIZOPITA lango la gharama (`scripts/gate_probe.py`,
# 2026-09-09, matukio 96, commission $7/lot):
#
#     EURUSD  3.89%   PITA        AUDUSD  9.92%   KATAA
#     GBPUSD  4.82%   PITA        USDCHF  8.03%   KATAA
#     USDJPY  5.35%   PITA
#     USDCAD  7.23%   PITA
#
# `SYMBOLS` ni seti ya **mekanizimu** (§6.1): nchi zenye masoko ya hisa
# yanayoweza kuhitaji hedge. `QUALIFIED` ni seti ya **gharama** (§6.2).
# Kuchuja hapa si marekebisho ya baada ya kuona matokeo — ndiyo utaratibu
# wa §6 wenyewe: "Symbol iliyokataliwa haiingii kwenye hesabu ya majaribio
# wala kwenye pooling."
#
# Ulinzi unaofanya hili liwe salama: lango linatumia **σ na gharama pekee**,
# halijui faida hata kidogo. Haliwezi kuchagua symbol kwa sababu ilifanya
# vizuri, kwa sababu haioni ilivyofanya.
#
# USDCHF imekataliwa kwa **pips 0.006** — 8.03% dhidi ya 8.00%. Iko ndani ya
# kelele ya kipimo. Sheria iliyotangazwa ndiyo inayoamua, si hukumu yangu;
# na kwa vyovyote jibu la F1 halitegemei leg moja ya mpakani.
# ---------------------------------------------------------------------------
QUALIFIED = ("EURUSD", "GBPUSD", "USDJPY", "USDCAD")

PIPS: dict[str, float] = {s: (0.01 if s.endswith("JPY") else 0.0001)
                          for s in SYMBOLS}
POINTS: dict[str, float] = {s: p / 10.0 for s, p in PIPS.items()}
CONTRACT_SIZE = 100_000.0


def pip_value(symbol: str, mid: float) -> float:
    """Thamani ya pip kwa lot moja, kwa akaunti ya USD.

    Pairs tatu tofauti, sheria tatu:

    ```
    EURUSD · GBPUSD · AUDUSD   dola ni NUKUU   →  100,000 × 0.0001 = $10
    USDJPY                     dola ni MSINGI  →  1,000 JPY ÷ bei
    USDCHF · USDCAD            dola ni MSINGI  →  100,000 × 0.0001 ÷ bei
    ```

    Kuweka `$10` kwa zote — jaribu la kawaida — kungekosea USDCHF kwa ~12%
    na USDJPY kwa ~33%.
    """
    if mid <= 0:
        raise FamilyError(f"{symbol}: bei si chanya ({mid})")
    pip = PIPS[symbol]
    if symbol in USD_QUOTED:
        return CONTRACT_SIZE * pip
    return CONTRACT_SIZE * pip / mid


FIX: Anchor = LONDON_FIX                # 16:00 Europe/London
WINDOW_SECONDS = 300

# Kuingia dakika 60 kabla ya fix; kutoka dakika 15 baada yake. Mtiririko wa
# hedge unatekelezwa KWENYE fix, kwa hiyo dirisha lazima lilizunguke: kuingia
# kabla shinikizo halijaanza, kutoka baada halijaisha.
ENTRY_OFFSET = timedelta(minutes=-60)
EXIT_OFFSET = timedelta(minutes=15)

SL_MOVE_MULT = 4.0
SL_LOOKBACK_SESSIONS = STOPS.LOOKBACK_SESSIONS
SL_MIN_SESSIONS = STOPS.MIN_SESSIONS
MOVE_TO_SIGMA = STOPS.MOVE_TO_SIGMA
session_move_pips = STOPS.session_move_pips
signed_move_pips = STOPS.signed_move_pips
stop_from_history = STOPS.stop_from_history
stop_from_moves = STOPS.stop_from_moves

# Kipaumbele cha juu kuliko zote: matukio 99 pekee. Kupoteza tukio moja ni
# 1% ya ushahidi wa F1, dhidi ya 0.05% kwa F0.
PRIORITY = 1

# §9: kizingiti 5.2 bps. EURUSD karibu na 1.10 → bp moja ni pips 1.1.
DECLARED_EDGE_PIPS = 5.7

MECHANISM = (
    "Wawekezaji wanaoshikilia hisa za nje wanarekebisha ukubwa wa hedge ya "
    "sarafu kwenye fix ya 16:00 London ya siku ya mwisho ya mwezi, ambapo "
    "benchmarks zinapimwa. Ni mtiririko wa MAMLAKA — anayefuata benchmark "
    "hana chaguo la kutorekebisha. Hitaji linatofautiana kati ya nchi kwa "
    "kadiri ya utendaji wa hisa zao, kwa hiyo ni bet ya UWIANO."
)

DECLARATION = Declaration(
    family=FAMILY,
    symbols=QUALIFIED,
    nanga=("16:00 Europe/London, siku ya mwisho ya kazi ya mwezi; "
           "kuingia dakika 60 kabla, kutoka dakika 15 baada"),
    mwelekeo=("kwa kila pair, kwa ishara ya hisa: kuuza dola → KUNUNUA pair "
              "yenye dola upande wa nukuu, KUUZA yenye dola upande wa msingi; "
              "uzito umesawazishwa kwa cross-section (Σw = 0)"),
    kuingia=(f"tick-VWAP ya upande unaotekelezeka kwenye sekunde "
             f"{WINDOW_SECONDS} kutoka nanga"),
    stop=(f"{SL_MOVE_MULT} × wastani wa |kutoka − kuingia| kwa vikao "
          f"{SL_LOOKBACK_SESSIONS} VILIVYOPITA (chini kabisa "
          f"{SL_MIN_SESSIONS}); bima pekee; ikigongwa, R = −1.0"),
    kutoka="kwa SAA, dakika 15 baada ya fix",
    ukubwa=("uzito ni |ishara| iliyosawazishwa; hatari inatoka RCE; "
            "kikapu ni cha YOTE-AU-HAKUNA"),
    mechanism=MECHANISM,
    eligible_regimes=(MONTH_END_FIX, TURN_OF_YEAR),
    trials=1,
    source=("Melvin & Prins na kazi zinazofuata juu ya urekebishaji wa hedge "
            "kwenye fix ya mwisho wa mwezi; ushahidi mwingi ni baada ya 2010."),
    params={
        "window_seconds": WINDOW_SECONDS,
        "entry_offset_min": ENTRY_OFFSET // timedelta(minutes=1),
        "exit_offset_min": EXIT_OFFSET // timedelta(minutes=1),
        "sl_move_mult": SL_MOVE_MULT,
        "sl_lookback_sessions": SL_LOOKBACK_SESSIONS,
        "sl_min_sessions": SL_MIN_SESSIONS,
        "priority": PRIORITY,
        "symbols_mechanism": list(SYMBOLS),
        "symbols_qualified": list(QUALIFIED),
        "gate_probe": "2026-09-09; AUDUSD 9.92% na USDCHF 8.03% zimekataliwa",
    },
)


# ===========================================================================
# Ishara — ya lazima
# ===========================================================================


@dataclass(frozen=True)
class Signal:
    """Uzito wa upande wa DOLA kwa kila symbol, umesawazishwa.

    `weights[symbol] > 0` inamaanisha *"kuuza dola dhidi ya sarafu hii"* —
    yaani hedgers wanahitaji kuuza dola kwa sababu hisa za nchi hiyo
    zilifanya vizuri. Ubadilishaji kuwa upande wa pair unafanywa na
    `baskets`, mara moja, kwa `USD_QUOTED`.
    """

    weights: Mapping[str, float]
    placeholder: bool = False
    meta: dict[str, Any] = field(default_factory=dict)

    TOLERANCE = 1e-6

    def __post_init__(self) -> None:
        mbaya = set(self.weights) - set(SYMBOLS)
        if mbaya:
            raise FamilyError(f"symbols hazijulikani: {sorted(mbaya)}")
        if not self.weights:
            raise FamilyError("ishara haina uzito hata mmoja")
        pungufu = set(QUALIFIED) - set(self.weights)
        if pungufu:
            raise FamilyError(
                f"ishara haina uzito kwa symbols zilizopita lango: "
                f"{sorted(pungufu)} — kikapu ni cha YOTE-AU-HAKUNA")
        jumla = sum(self.weights[s] for s in QUALIFIED)
        if abs(jumla) > max(self.TOLERANCE, 1e-3 * self.gross):
            raise FamilyError(
                f"uzito haujasawazishwa: Σw = {jumla:+.6f}. F1 ni bet ya "
                f"UWIANO; bila Σw = 0 ni bet ya mwelekeo wa dola yenye legs "
                f"sita, na hiyo ni familia nyingine")
        if any(abs(w) > 1.0 for w in self.weights.values()):
            raise FamilyError("uzito wowote hauwezi kuzidi 1.0 kwa ukubwa")

    @property
    def gross(self) -> float:
        return sum(abs(w) for w in self.weights.values())


# Ishara ya kupima LANGO pekee. `σ` na gharama hazitegemei ishara, kwa hiyo
# uwezekano wa kupimika unajulikana kabla ya data ya hisa. Vikapu vyake
# vinabeba alama, na `p` inakataliwa kwa run inayoibeba.
PLACEHOLDER = Signal(
    weights={s: (1.0 if s in USD_QUOTED else -1.0) for s in QUALIFIED},
    placeholder=True,
    meta={"kusudi": "lango la §6 pekee; si mekanizimu"},
)


def side_for(symbol: str, usd_weight: float) -> str:
    """Upande wa pair kwa uzito wa upande wa dola.

    `usd_weight > 0` = kuuza dola. Dola ikiwa NUKUU (EURUSD), kuuza dola ni
    **kununua** pair; ikiwa MSINGI (USDJPY), ni **kuuza**.
    """
    if usd_weight == 0:
        raise FamilyError(f"{symbol}: uzito sifuri hauna upande")
    kuuza_dola = usd_weight > 0
    if symbol in USD_QUOTED:
        return BUY if kuuza_dola else SELL
    return SELL if kuuza_dola else BUY


# ===========================================================================
# Madirisha na vikapu
# ===========================================================================


@dataclass(frozen=True)
class Session:
    """Ncha mbili za tukio, ikiwa UTC. Ni moja kwa kikapu kizima."""

    day: date
    leg: str
    side: str
    entry_at: datetime
    exit_at: datetime

    @property
    def hours(self) -> float:
        return (self.exit_at - self.entry_at).total_seconds() / 3600.0


LEG = "M"                               # mwisho wa mwezi — dirisha moja


def sessions_for(day: date) -> tuple[Session, ...]:
    """Dirisha moja la siku hii, ikiwa UTC. Legs zote sita zinalishiriki."""
    fix = FIX.at(day)
    ndani, nje = fix + ENTRY_OFFSET, fix + EXIT_OFFSET
    if nje <= ndani:
        raise FamilyError(f"{day}: kutoka si baada ya kuingia")
    return (Session(day, LEG, "", ndani, nje),)


def measurements(day: date) -> tuple[Measurement, ...]:
    """Symbols NNE kwenye dirisha MOJA. `key` ni symbol yenyewe, kwa sababu
    kila moja ina volatility yake na kwa hiyo stop yake."""
    s, = sessions_for(day)
    return tuple(Measurement(key=symbol, symbol=symbol,
                             entry_at=s.entry_at, exit_at=s.exit_at)
                 for symbol in QUALIFIED)


def eligible_days(
    days: Iterable[date],
    *,
    holidays: Iterable[date] = (),
    cb_days: Iterable[date] = (),
) -> list[date]:
    """Siku za mwisho wa mwezi zinazostahili.

    Regimes zinazokubalika ni **mbili**: `MONTH_END_FIX` na `TURN_OF_YEAR`.
    31 Desemba ni zote mbili; mekanizimu upo siku hiyo, kwa hiyo inaingia.
    """
    zilizofungwa = set(holidays)
    matukio = set(cb_days)
    ruhusa = set(DECLARATION.eligible_regimes)
    out = []
    for d in sorted(set(days)):
        if d != siku_ya_mwisho_ya_mwezi(d.year, d.month, zilizofungwa):
            continue
        if regime_of(d, holidays=zilizofungwa, cb_days=matukio) in ruhusa:
            out.append(d)
    return out


def baskets(
    days: Sequence[date],
    *,
    move_pips: Mapping[tuple[date, str], float] | Callable[[date, str], float | None],
    signal: Signal | Callable[[date], Signal | None],
    holidays: Iterable[date] = (),
    cb_days: Iterable[date] = (),
) -> list[Basket]:
    """Kikapu KIMOJA chenye legs sita kwa kila tarehe.

    `signal` **ni ya lazima**. Bila utendaji wa hisa hakuna njia ya kujua ni
    nani anauza nini, na "kwa uzito sawa" si F1 (ona docstring ya moduli).

    `move_pips[(siku, symbol)]` — hapa ufunguo wa pili ni **symbol**, si leg:
    kila symbol ina volatility yake, kwa hiyo kila moja ina stop yake.
    """
    pata_mwendo = (move_pips.get if hasattr(move_pips, "get")
                   else lambda k, _=None: move_pips(k[0], k[1]))
    pata_ishara = signal if callable(signal) else (lambda _d: signal)

    out: list[Basket] = []
    for d in eligible_days(days, holidays=holidays, cb_days=cb_days):
        ishara = pata_ishara(d)
        if ishara is None:
            continue
        s, = sessions_for(d)

        legs, pungufu = [], []
        for symbol in QUALIFIED:
            w = ishara.weights.get(symbol)
            if not w:
                pungufu.append(symbol)
                continue
            mwendo = pata_mwendo((d, symbol), None)
            if mwendo is None:
                pungufu.append(symbol)
                continue
            mwendo = float(mwendo)
            if mwendo <= 0:
                raise FamilyError(f"{d} {symbol}: mwendo si chanya ({mwendo})")
            # `Leg.weight` inabeba ISHARA ya upande wa dola, si ya pair.
            # `net_weight` ya kikapu inakuwa mfiduo wa dola uliobaki: sifuri
            # kwa kikapu kilichosawazishwa. Utekelezaji unatumia `side` na
            # `strength` (ukubwa), kwa hiyo hakuna kuhesabu mara mbili.
            kubwa = max(abs(ishara.weights[x]) for x in QUALIFIED
                        if ishara.weights.get(x))
            legs.append(Leg(symbol=symbol, side=side_for(symbol, w),
                            sl_pips=SL_MOVE_MULT * mwendo,
                            weight=w / kubwa,
                            meta={"usd_weight": w, "move_pips": mwendo}))
        # Kikapu ni cha YOTE-AU-HAKUNA: legs sita zilizosawazishwa. Tano
        # si F1 iliyopunguzwa, ni strategy nyingine yenye mwelekeo wa dola.
        if pungufu:
            continue
        out.append(Basket(
            family=FAMILY, basket_id=f"{FAMILY}:{d.isoformat()}",
            legs=tuple(legs), entry_at=s.entry_at, planned_exit_at=s.exit_at,
            priority=PRIORITY, atomic=True,
            eligible_regimes=DECLARATION.eligible_regimes,
        ))
    return out


def windows_to_read(baskets_: Sequence[Basket]) -> list[tuple[datetime, int]]:
    seti = {(b.entry_at, WINDOW_SECONDS) for b in baskets_}
    seti |= {(b.planned_exit_at, WINDOW_SECONDS) for b in baskets_}
    return sorted(seti)


__all__ = [
    "FAMILY", "SYMBOLS", "QUALIFIED", "USD_QUOTED", "PIPS", "POINTS", "CONTRACT_SIZE",
    "pip_value", "FIX", "WINDOW_SECONDS", "ENTRY_OFFSET", "EXIT_OFFSET",
    "SL_MOVE_MULT", "SL_LOOKBACK_SESSIONS", "SL_MIN_SESSIONS", "MOVE_TO_SIGMA",
    "PRIORITY", "DECLARED_EDGE_PIPS", "MECHANISM", "DECLARATION",
    "Signal", "PLACEHOLDER", "side_for", "Session", "LEG", "sessions_for",
    "session_move_pips", "signed_move_pips", "stop_from_history", "stop_from_moves",
    "measurements", "eligible_days", "baskets", "windows_to_read",
]
