"""Injini ya saa za matukio — DOCTRINE §7.4, §11.

Familia zote za mzunguko wa kwanza zimeshikwa na **saa**, si na bar. F0 inaingia
08:00 Europe/London na kutoka 12:00 America/New_York. F1 inaingia 15:00 London
siku ya mwisho ya mwezi. Gotobi ni 09:55 Asia/Tokyo.

Kuandika nyakati hizo kama saa za UTC zilizokwama ni **hitilafu ya kimya
inayotokea kwa mifumo**:

```
16:00 Europe/London  =  15:00 UTC  (majira ya baridi)
                     =  16:00 UTC  (BST)

na EU inabadilisha Jumapili ya MWISHO ya Machi; US inabadilisha Jumapili ya PILI.
```

Kati ya tarehe hizo mbili — na tena Oktoba/Novemba — tofauti kati ya London na
New York ni **saa 4**, si 5. Wiki ~6 kwa mwaka.

F0 ndiyo iliyo hatarini zaidi kwa sababu ina **nanga mbili** zinazohama kwa
tarehe **tofauti**: siku 8 × miaka 8 kwa kila mpito, takribani **matukio 240
yaliyoshikwa kwenye dakika isiyo sahihi** kama saa za UTC zingekwama.

Kwa hiyo kila nanga inahifadhiwa kama `(saa ya mtaa, IANA tz)` na inageuzwa
wakati wa kuulizwa. Hakuna saa ya UTC inayoandikwa kwenye ufafanuzi wa familia.

---

**Bei inatoka kwenye ticks, si kwenye bars, na ni ya upande unaotekelezeka.**

`tick-VWAP` ya **ask** kwa kununua, ya **bid** kwa kuuza. Kutumia mid
kungerudisha nusu ya spread kama edge — takribani 0.6 pips kwa mguu, ambayo
kwa F1 yenye edge inayotarajiwa ya ~5 bps ni upendeleo wa 10–15% juu.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

BUY = "BUY"
SELL = "SELL"

# Siku za wiki zinazohesabika kama siku za soko. FX inafunguliwa Jumapili
# 17:00 New York, lakini Jumapili ni **sehemu ya siku** — ona §11. Familia
# hazishikwi Jumapili.
SIKU_ZA_KAZI = (0, 1, 2, 3, 4)          # Jumatatu … Ijumaa


class ClockError(RuntimeError):
    """Nanga haiwezi kutatuliwa kama ilivyoombwa."""


# ===========================================================================
# Nanga: (saa ya mtaa, IANA tz) → UTC
# ===========================================================================


@dataclass(frozen=True)
class Anchor:
    """Saa ya mtaa pamoja na eneo lake. **Kamwe si saa ya UTC iliyokwama.**

    `tz` ni jina la IANA (`Europe/London`), si offset. Offset inabadilika mara
    mbili kwa mwaka; jina halibadiliki.
    """

    hour: int
    minute: int
    tz: str
    name: str = ""

    def __post_init__(self) -> None:
        if not (0 <= self.hour <= 23 and 0 <= self.minute <= 59):
            raise ClockError(f"saa si halali: {self.hour:02d}:{self.minute:02d}")
        try:
            ZoneInfo(self.tz)
        except Exception as exc:                       # noqa: BLE001
            raise ClockError(f"IANA tz haijulikani: {self.tz!r}") from exc

    def at(self, day: date) -> datetime:
        """Nanga hii siku hiyo, ikiwa UTC.

        `fold=0` inachaguliwa kwa makusudi kwa saa inayojirudia (usiku wa
        kurudisha saa nyuma): ni tukio la KWANZA. Kuchagua la pili
        kungebadilisha bei kwa saa nzima kwenye siku moja ya mwaka, na tofauti
        hiyo isingeonekana kama kosa.
        """
        ndani = datetime(day.year, day.month, day.day, self.hour, self.minute,
                         tzinfo=ZoneInfo(self.tz), fold=0)
        # Saa isiyokuwepo (usiku wa kusonga saa mbele) inarudisha saa
        # iliyofuata kwa kanuni ya `zoneinfo`. Hilo ni sahihi kwa soko:
        # dakika hiyo haikuwepo, kwa hiyo tukio linakuwa lililo karibu nayo.
        return ndani.astimezone(ZoneInfo("UTC"))

    def render(self) -> str:
        jina = f"{self.name} · " if self.name else ""
        return f"{jina}{self.hour:02d}:{self.minute:02d} {self.tz}"


# Nanga zinazotumika. Zinaandikwa hapa MARA MOJA ili familia zisiziandike
# tena kila moja kwa namna yake.
LONDON_OPEN = Anchor(8, 0, "Europe/London", "kufunguka London")
LONDON_FIX = Anchor(16, 0, "Europe/London", "fix ya London")
NY_NOON = Anchor(12, 0, "America/New_York", "adhuhuri New York")
NY_CLOSE = Anchor(16, 30, "America/New_York", "kufunga New York")
NY_ROLLOVER = Anchor(17, 0, "America/New_York", "rollover — mpaka wa siku")
TOKYO_FIX = Anchor(9, 55, "Asia/Tokyo", "fix ya Tokyo")


# ===========================================================================
# Kalenda
# ===========================================================================


def ni_siku_ya_kazi(day: date, holidays: Iterable[date] = ()) -> bool:
    return day.weekday() in SIKU_ZA_KAZI and day not in set(holidays)


def siku_za_kazi_za_mwezi(year: int, month: int,
                          holidays: Iterable[date] = ()) -> list[date]:
    zilizofungwa = set(holidays)
    siku = []
    d = date(year, month, 1)
    while d.month == month:
        if ni_siku_ya_kazi(d, zilizofungwa):
            siku.append(d)
        d += timedelta(days=1)
    return siku


def siku_ya_mwisho_ya_mwezi(year: int, month: int,
                            holidays: Iterable[date] = ()) -> date:
    """Siku ya mwisho ya kazi ya mwezi, **kwa kalenda ya nchi husika**.

    §11: 31 Desemba ni sikukuu Japani, si Uingereza. Sheria moja ya "siku ya
    mwisho ya kazi" inayotumia kalenda moja ingechagua tarehe TOFAUTI kwa legs
    tofauti za F1, na kuvunja usawa wa cross-section kimya.

    Kwa hiyo `holidays` ni ya lazima kwa kila leg, si hiari.
    """
    siku = siku_za_kazi_za_mwezi(year, month, holidays)
    if not siku:
        raise ClockError(f"{year}-{month:02d} haina siku ya kazi hata moja")
    return siku[-1]


def ni_siku_ya_mwisho_ya_mwezi(day: date, holidays: Iterable[date] = ()) -> bool:
    return day == siku_ya_mwisho_ya_mwezi(day.year, day.month, holidays)


def ni_gotobi(day: date, holidays: Iterable[date] = ()) -> bool:
    """Siku ya Gotobi: tarehe inayogawanyika kwa 5 (5,10,15,20,25,30).

    Ikiwa siku hiyo si ya kazi, malipo yanasogezwa **mbele** hadi siku ya kazi
    inayofuata — ndiyo desturi ya benki za Japani. Kwa hiyo siku ya kazi
    inayofuata sikukuu ya Gotobi nayo ni Gotobi.
    """
    zilizofungwa = set(holidays)
    if not ni_siku_ya_kazi(day, zilizofungwa):
        return False
    if day.day % 5 == 0:
        return True
    # Je kuna siku ya Gotobi isiyo ya kazi iliyosogezwa hadi hapa?
    nyuma = day - timedelta(days=1)
    while not ni_siku_ya_kazi(nyuma, zilizofungwa):
        if nyuma.month == day.month and nyuma.day % 5 == 0:
            return True
        nyuma -= timedelta(days=1)
    return False


def siku_ya_soko(moment: datetime) -> date:
    """Siku ya soko ya FX inaanza **17:00 America/New_York**, si 00:00 UTC.

    Ndipo rollover na swap zinapotokea. Kutumia 00:00 UTC kungegawa siku
    katikati ya saa yenye ukwasi mdogo kuliko zote, na kila kipimo cha D1
    kingechafuliwa.
    """
    ndani = moment.astimezone(ZoneInfo("America/New_York"))
    d = ndani.date()
    return d + timedelta(days=1) if ndani.time() >= time(17, 0) else d


# ===========================================================================
# Bei: tick-VWAP ya upande unaotekelezeka
# ===========================================================================


@dataclass(frozen=True)
class Fill:
    """Bei iliyopatikana, pamoja na ushahidi wa jinsi ilivyopatikana."""

    price: float
    n_ticks: int
    volume: float
    start: datetime
    end: datetime
    side: str

    def render(self) -> str:
        return (f"{self.side} {self.price:.5f} · ticks {self.n_ticks:,} · "
                f"{self.start:%H:%M:%S}→{self.end:%H:%M:%S}")


def vwap(
    ticks,
    start: datetime,
    window_seconds: int,
    side: str,
    *,
    volume_col: str | None = None,
) -> Fill:
    """tick-VWAP ya **upande unaotekelezeka** kwenye dirisha `[start, start+w)`.

    `BUY` inatumia `ask`; `SELL` inatumia `bid`. Mid haitumiki popote —
    ingerudisha nusu ya spread kama edge isiyokuwepo.

    Bila safu ya volume, kila tick ina uzito sawa (VWAP inakuwa TWAP ya ticks).
    Hiyo ni sahihi kwa data ya retail isiyo na volume halisi, na inaandikwa
    kwenye `Fill.volume` ili isije ikadhaniwa ni volume ya soko.
    """
    import numpy as np
    import pandas as pd

    upande = side.upper()
    if upande not in (BUY, SELL):
        raise ClockError(f"upande si halali: {side!r} — ni {BUY} au {SELL}")
    if window_seconds <= 0:
        raise ClockError(f"dirisha lazima liwe > 0, si {window_seconds}")

    safu = "ask" if upande == BUY else "bid"
    if safu not in ticks.columns:
        raise ClockError(f"ticks hazina safu `{safu}`")

    end = start + timedelta(seconds=window_seconds)
    stamps = pd.to_datetime(ticks["timestamp"], utc=True)
    ndani = (stamps >= start) & (stamps < end)
    kipande = ticks.loc[ndani]

    if kipande.empty:
        raise ClockError(
            f"hakuna tick hata moja kati ya {start:%Y-%m-%d %H:%M:%S} na "
            f"{end:%H:%M:%S} UTC — dirisha halina bei, na kubuni moja "
            f"kungefanya tukio lionekane limetradiwa wakati halikutradiwa"
        )

    bei = np.asarray(kipande[safu], dtype=float)
    if volume_col and volume_col in kipande.columns:
        uzito = np.asarray(kipande[volume_col], dtype=float)
    else:
        uzito = np.ones(len(bei), dtype=float)

    jumla = float(uzito.sum())
    return Fill(
        price=float((bei * uzito).sum() / jumla) if jumla > 0 else float(bei.mean()),
        n_ticks=int(len(bei)),
        volume=jumla,
        start=start,
        end=end,
        side=upande,
    )


@dataclass(frozen=True)
class Rollovers:
    """Rollovers zilizovukwa, kwa **mkataba wa `rce.cost.swap_pips`**.

    `triple_nights` ni **sehemu ya** `nights`, si nyongeza yake. Ndio mkataba
    ambao `swap_pips` inaudai (`triple_nights > nights` inalipuka), na test
    yake inauandika: `nights=3, triple=1` → *"usiku 2 + (1 × 3) = 5"*.

    **Mtego:** `rce.cost.count_rollovers` inarudisha `(kawaida, triple)`
    **zilizotenganishwa** — jumla ni `kawaida + triple`. Kupeleka matokeo yake
    moja kwa moja kwenye `swap_pips` kunashusha usiku mmoja kwa kila Jumatano.
    Si kasoro ndani ya RCE — `engine.py` inapokea namba hizo kutoka nje — ni
    mtego kwa anayeiita. Darasa hili ndiyo mahali pekee ambapo ubadilishaji
    unafanyika, ili usije ukafanyika kwa namna tofauti kila mahali.
    """

    nights: int
    triple_nights: int

    def __post_init__(self) -> None:
        if self.triple_nights > self.nights:
            raise ClockError(
                f"triple {self.triple_nights} > nights {self.nights} — "
                f"`swap_pips` inadai triple iwe SEHEMU ya nights"
            )

    @property
    def billed_nights(self) -> int:
        """Usiku wa kulipiwa: za kawaida mara moja, za Jumatano mara tatu."""
        return self.nights + 2 * self.triple_nights

    def render(self) -> str:
        tatu = f", triple {self.triple_nights}" if self.triple_nights else ""
        return f"rollovers {self.nights}{tatu} → kulipiwa {self.billed_nights}"


def usiku_wa_swap(entry: datetime, exit_at: datetime) -> Rollovers:
    """Rollovers kati ya kuingia na kutoka — DOCTRINE §11.

    Sheria ya soko: **rollover ya Jumatano 17:00 New York inatozwa mara tatu**,
    kwa sababu tarehe ya thamani inaruka Ijumaa → Jumatatu (T+2).

    **Kwa nini `rce.cost.count_rollovers` haitumiki hapa.** Inapima Jumatano
    kwa `(cursor − siku 1).weekday()` — mantiki iliyoandikwa kwa mpaka wa
    **usiku wa manane**, ambapo `cursor` inakaa mwishoni mwa usiku. Ikihamishiwa
    `rollover_hour=17` inakosea kwa siku moja:

    ```
    Jumatano 10:00 NY → Alhamisi 10:00 NY   (inavuka rollover MOJA ya Jumatano)
        soko:          mara tatu
        RCE @ 17:00:   ya kawaida        ← imekosea
        RCE @ 00:00:   mara tatu         ← sahihi, lakini mpaka si wa FX
    ```

    Si kasoro ndani ya RCE — `engine.py` inapokea `nights`/`triple_nights`
    kutoka nje, na chaguo-msingi cha usiku wa manane ni sahihi kwa matumizi
    yake. Ni **dhana isiyotangazwa** kwenye function, na RCE haiguswi.

    Kwa nini hii inatokea kwa mifumo: FOMC inatangaza Jumatano 14:00 New York.
    Kushikilia saa 24 kunavuka rollover ya Jumatano **daima**. Kwa position ya
    sarafu yenye riba kubwa hiyo ni gharama inayohusiana na **mwelekeo** — na
    ingeonekana kama uthibitisho wa mekanizimu badala ya kama gharama.

    Trade ya masaa manne ndani ya kikao kimoja hairudishi chochote — ndiyo hali
    ya kawaida ya familia zote za mzunguko wa kwanza.
    """
    if exit_at < entry:
        raise ClockError("kutoka kabla ya kuingia")

    ny = ZoneInfo("America/New_York")
    a = entry.astimezone(ny)
    b = exit_at.astimezone(ny)

    nights = triple = 0
    # `datetime + timedelta` kwenye datetime yenye tz inaongeza saa za MTAA na
    # kubakiza tzinfo — kwa hiyo 17:00 inabaki 17:00 hata kwenye mpito wa DST.
    cursor = a.replace(hour=17, minute=0, second=0, microsecond=0)
    if cursor <= a:
        cursor += timedelta(days=1)
    while cursor <= b:
        nights += 1
        if cursor.weekday() == 2:              # Jumatano
            triple += 1
        cursor += timedelta(days=1)

    return Rollovers(nights=nights, triple_nights=triple)


@dataclass(frozen=True)
class Quotes:
    """Pande zote mbili kwenye dirisha moja — ili `mid` isihesabiwe mara mbili.

    Bei ya utekelezaji ni `ask` kwa kununua na `bid` kwa kuuza. `mid` ni ya
    **kuripoti pekee**: `gross_pips` (mid→mid) dhidi ya `net_pips`
    (utekelezaji→utekelezaji) inatoa spread iliyolipwa HALISI, na hiyo
    inalinganishwa na iliyokadiriwa na RCE.
    """

    bid: float
    ask: float
    n_ticks: int
    start: datetime
    end: datetime

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    def executable(self, side: str) -> float:
        return self.ask if side.upper() == BUY else self.bid

    def spread_pips(self, pip: float) -> float:
        return (self.ask - self.bid) / pip


def quotes(ticks, start: datetime, window_seconds: int) -> Quotes:
    """`bid` na `ask` VWAP kwenye dirisha lilelile, kwa kupita mara moja."""
    b = vwap(ticks, start, window_seconds, SELL)
    a = vwap(ticks, start, window_seconds, BUY)
    return Quotes(bid=b.price, ask=a.price, n_ticks=a.n_ticks,
                  start=a.start, end=a.end)


def dirisha_la_tukio(anchor: Anchor, day: date, *, offset_minutes: int = 0
                     ) -> datetime:
    """Nanga siku hiyo, ikiwa imesogezwa kwa dakika, ikiwa UTC.

    `offset_minutes` hasi = kabla ya nanga. Hesabu inafanywa **baada ya**
    kugeuza kuwa UTC, kwa hiyo dakika 60 kabla ya fix ni dakika 60 halisi hata
    kwenye siku ya mpito wa DST.
    """
    return anchor.at(day) + timedelta(minutes=offset_minutes)


__all__ = [
    "BUY", "SELL", "Anchor", "ClockError", "Fill",
    "LONDON_OPEN", "LONDON_FIX", "NY_NOON", "NY_CLOSE", "NY_ROLLOVER",
    "TOKYO_FIX",
    "ni_siku_ya_kazi", "siku_za_kazi_za_mwezi", "siku_ya_mwisho_ya_mwezi",
    "ni_siku_ya_mwisho_ya_mwezi", "ni_gotobi", "siku_ya_soko",
    "Rollovers", "usiku_wa_swap", "Quotes", "quotes", "vwap",
    "dirisha_la_tukio",
]
