"""Kufunga kwa siku kwa faharasa za hisa — DOCTRINE §11.

F1 inahitaji utendaji wa hisa kujua **ni nani anauza nini** kwenye fix. Bila
hiyo, "trade kila mwisho wa mwezi" si F1 — ni bet ya dola isiyo na mekanizimu.

---

**Mtego mmoja unaotawala moduli hii: LOOKAHEAD.**

Fix ni saa 16:00 London siku `D`. Kufunga kwa siku hiyo:

```
Nikkei 225      kunafunga 15:00 JST     =  06:00 London   ← kabla ya fix
FTSE 100        kunafunga 16:30 London                    ← BAADA ya fix
EURO STOXX      kunafunga 17:30 CET     =  16:30 London   ← BAADA
S&P 500 · TSX   kunafunga 16:00 NY      =  21:00 London   ← BAADA
```

Kutumia kufunga kwa `D` kungekuwa kujua bei ambazo hazijawahi kuwepo wakati
trade inafanywa. Kwa hiyo **kila kitu hapa kinatumia kufunga kwa `D − 1` au
mapema**, kwa symbols zote bila ubaguzi — hata Nikkei, ambayo kufunga kwake
kunafika kabla ya fix. Sheria moja kwa zote ni rahisi kukagua; sheria ya kila
soko peke yake ni rahisi kukosea kimya.

Gharama ya hilo ni ndogo (siku moja ya utendaji kati ya ~21); faida ni kwamba
lookahead **haiwezekani kimuundo**, si kwamba imeepukwa kwa uangalifu.

---

**`asof` si `lookup`.** Faharasa zina sikukuu zao — FTSE haifanyi kazi siku ya
Boxing Day, Nikkei haifanyi kazi Golden Week. Kuomba tarehe isiyokuwepo
kunarudisha **kufunga kwa mwisho kabla yake**, si `None` wala `NaN`. Ndivyo
mwekezaji halisi anavyoona soko.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Mapping, Sequence

# Majina ya safu yanayokubalika. Stooq inatoa `Date,Open,High,Low,Close,Volume`;
# vyanzo vingine vinatofautiana kwa herufi kubwa na ndogo.
DATE_COLUMNS = ("date", "data", "time", "timestamp")
CLOSE_COLUMNS = ("close", "zamkniecie", "adj close", "adj_close", "price")

# Chini ya hapa, mfululizo hauwezi kutumika kwa ishara ya mwezi kwa mwezi.
MIN_ROWS = 200


class IndexError_(RuntimeError):
    """Faharasa haiwezi kupakiwa au kutumika kama ilivyoombwa."""


@dataclass(frozen=True)
class Series:
    """Mfululizo mmoja wa kufunga kwa siku, umepangwa na umekaguliwa."""

    name: str
    days: tuple[date, ...]
    closes: tuple[float, ...]
    source: str = ""

    def __post_init__(self) -> None:
        if len(self.days) != len(self.closes):
            raise IndexError_(f"{self.name}: siku {len(self.days)} dhidi ya "
                              f"bei {len(self.closes)}")
        if len(self.days) < MIN_ROWS:
            raise IndexError_(
                f"{self.name}: rows {len(self.days)} pekee, chini ya "
                f"{MIN_ROWS}. Mfululizo mfupi hauwezi kutoa ishara ya mwezi "
                f"kwa mwezi; angalia chanzo badala ya kuendelea")
        if list(self.days) != sorted(self.days):
            raise IndexError_(f"{self.name}: siku hazijapangwa")
        if len(set(self.days)) != len(self.days):
            raise IndexError_(f"{self.name}: siku zinajirudia")
        mbaya = [d for d, c in zip(self.days, self.closes) if not c > 0]
        if mbaya:
            raise IndexError_(f"{self.name}: bei isiyo chanya kwenye "
                              f"{mbaya[:3]} ({len(mbaya)} kwa jumla)")

    @property
    def start(self) -> date:
        return self.days[0]

    @property
    def end(self) -> date:
        return self.days[-1]

    def asof(self, day: date) -> float | None:
        """Kufunga kwa mwisho **kwenye au kabla ya** `day`.

        `None` ikiwa `day` iko kabla ya mfululizo kuanza. Si `NaN`: mwitaji
        anatakiwa kuamua, na `NaN` ingeenea kimya kwenye hesabu zote.
        """
        import bisect

        i = bisect.bisect_right(self.days, day)
        return self.closes[i - 1] if i else None

    def render(self) -> str:
        return (f"{self.name:<12} rows {len(self.days):>6,}  "
                f"{self.start} → {self.end}")


def read_csv(path: Path | str, *, name: str = "") -> Series:
    """Soma CSV yenye safu za tarehe na kufunga. Chanzo chochote."""
    import csv

    path = Path(path)
    if not path.exists():
        raise IndexError_(f"faili haipo: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise IndexError_(f"{path}: haina row hata moja")

    vichwa = {k.strip().lower(): k for k in rows[0] if k}
    d_col = next((vichwa[c] for c in DATE_COLUMNS if c in vichwa), None)
    c_col = next((vichwa[c] for c in CLOSE_COLUMNS if c in vichwa), None)
    if d_col is None or c_col is None:
        raise IndexError_(
            f"{path}: hakuna safu ya tarehe/kufunga (zilizopo: "
            f"{sorted(vichwa)}). Inatarajiwa mojawapo ya {DATE_COLUMNS} na "
            f"{CLOSE_COLUMNS}")

    pamoja: dict[date, float] = {}
    kuruka = 0
    for r in rows:
        raw_d, raw_c = (r.get(d_col) or "").strip(), (r.get(c_col) or "").strip()
        if not raw_d or not raw_c or raw_c.lower() in ("n/a", "null", "-"):
            kuruka += 1
            continue
        try:
            d = datetime.fromisoformat(raw_d[:10]).date()
            c = float(raw_c)
        except ValueError:
            kuruka += 1
            continue
        if c > 0:
            pamoja[d] = c
        else:
            kuruka += 1

    siku = sorted(pamoja)
    return Series(name=name or path.stem, days=tuple(siku),
                  closes=tuple(pamoja[d] for d in siku), source=str(path))


def load(paths: Mapping[str, Path | str]) -> dict[str, Series]:
    """`{jina: njia}` → `{jina: Series}`, zote zikiwa zimekaguliwa."""
    return {jina: read_csv(njia, name=jina) for jina, njia in paths.items()}


def coverage(series: Mapping[str, Series], days: Sequence[date]) -> dict:
    """Je kila faharasa inafunika kila tarehe inayohitajika?

    Inaripotiwa **kabla** ya ishara kujengwa. Faharasa isiyofunika mwaka
    mmoja ingetoa ishara isiyo kamili kwa miezi 12, na kikapu cha
    yote-au-hakuna kingesimama kimya kwa miezi hiyo — ikionekana kama
    "matukio machache" badala ya "data haipo".
    """
    out = {}
    for jina, s in series.items():
        nje = [d for d in days if d < s.start or d > s.end]
        out[jina] = {"start": s.start, "end": s.end, "rows": len(s.days),
                     "missing": len(nje),
                     "first_missing": nje[0] if nje else None}
    return out


__all__ = ["DATE_COLUMNS", "CLOSE_COLUMNS", "MIN_ROWS", "IndexError_",
           "Series", "read_csv", "load", "coverage"]
