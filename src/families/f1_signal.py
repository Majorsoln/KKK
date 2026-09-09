"""Ishara ya F1 kutoka utendaji wa hisa — DOCTRINE §4, §11.

**Kutoka kwenye mekanizimu hadi kwenye namba, hatua kwa hatua.**

Mwekezaji wa Marekani anashikilia hisa za nchi `C`, akifunika kwa kuuza sarafu
ya `C` mbeleni. Hisa za `C` zikipanda, thamani anayoifunika inakua — hedge
imekuwa ndogo mno, kwa hiyo **anauza sarafu ya `C` zaidi**, yaani **ananunua
dola**.

Upande wa pili una mwekezaji wa `C` anayeshikilia hisa za Marekani, akifunika
kwa kuuza dola. Hisa za Marekani zikipanda, **anauza dola zaidi**.

```
r_C  juu   →  kununua dola dhidi ya C
r_US juu   →  kuuza dola dhidi ya C
           ↓
z_C  =  r_US − r_C          (chanya = kuuza dola)
```

---

**Kusawazisha kunafuta Marekani kabisa — na hiyo ni sahihi.**

```
z_C − mean(z)  =  (r_US − r_C) − (r_US − mean(r))  =  −(r_C − mean(r))
```

`r_US` inatoka yenyewe. Kinachobaki ni: **uza sarafu ya soko la hisa
lililofanya vizuri kuliko wenzake; nunua ya lililofanya vibaya.** Ni bet ya
uwiano halisi, kama §4 ya `f1.py` inavyodai — si kwa sheria iliyoongezwa bali
kwa hesabu.

Faharasa ya Marekani bado inapakuliwa kwa **ukaguzi**: `mean(z)` yenyewe
inaonyesha mwelekeo wa jumla wa hedge ya dola mwezi huo, na ni kipimo cha
kuvutia hata kama hakiingii kwenye trade.

---

**LOOKAHEAD: kufunga kwa siku ya fix HAKUTUMIKI.**

Fix ni 16:00 London. FTSE inafunga 16:30, STOXX 16:30, S&P na TSX 21:00 —
zote **baada**. Nikkei inafunga 06:00 London, kabla, lakini sheria ni moja
kwa zote: **kufunga kwa `D − 1` au mapema**. Sheria moja inakaguliwa kwa
mstari mmoja; sheria ya kila soko peke yake inakosewa kimya.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Mapping, Sequence

from src.data.indices import Series
from src.families.base import FamilyError
from src.families.f1 import QUALIFIED, Signal

# Faharasa moja kwa kila sarafu iliyopita lango. Ni uamuzi wa **mekanizimu**
# (§6.1): soko la hisa la nchi inayomiliki sarafu hiyo.
INDEX_FOR: dict[str, str] = {
    "EURUSD": "STOXX50",        # eneo la euro
    "GBPUSD": "FTSE100",        # Uingereza
    "USDJPY": "NIKKEI225",      # Japani
    "USDCAD": "TSX",            # Kanada
}

# Faharasa ya Marekani. Haiingii kwenye trade (inatoka wakati wa kusawazisha)
# lakini inapakuliwa na kuripotiwa kwa ukaguzi.
US_INDEX = "SP500"

# Siku za kurudi nyuma kutoka tarehe ya fix. **Si kigezo cha kurekebishwa** —
# ni ndogo kabisa inayozuia lookahead kwa masoko yote manne.
LAG_DAYS = 1


def month_start(day: date) -> date:
    """Siku ya mwisho ya kalenda ya mwezi uliotangulia."""
    return day.replace(day=1) - timedelta(days=1)


@dataclass(frozen=True)
class Returns:
    """Utendaji wa kila faharasa kwa mwezi unaoishia kabla ya fix."""

    day: date
    start: date
    end: date
    by_index: dict[str, float]

    def render(self) -> str:
        vitu = " · ".join(f"{k} {v:+.2%}" for k, v in sorted(self.by_index.items()))
        return f"{self.day} ({self.start}→{self.end}): {vitu}"


def returns_for(
    day: date,
    series: Mapping[str, Series],
    *,
    lag_days: int = LAG_DAYS,
) -> Returns | None:
    """Utendaji wa mwezi kwa kila faharasa, **bila lookahead**.

    Dirisha ni `[mwisho wa mwezi uliopita, siku ya fix − lag]`, na kila ncha
    inatumia `asof` — kufunga kwa mwisho kwenye au kabla ya tarehe hiyo, kwa
    sababu kila soko lina sikukuu zake.

    `None` ikiwa faharasa yoyote haina data kwenye ncha yoyote: kikapu cha
    F1 ni cha **yote-au-hakuna**, kwa hiyo ishara isiyokamilika si ishara.
    """
    if lag_days < 1:
        raise FamilyError(
            f"lag_days ni {lag_days}. Kufunga kwa siku ya fix hakutumiki: "
            f"FTSE, STOXX, S&P na TSX zote zinafunga BAADA ya 16:00 London")

    mwisho = day - timedelta(days=lag_days)
    mwanzo = month_start(day)
    if mwisho <= mwanzo:
        return None

    out: dict[str, float] = {}
    for jina, s in series.items():
        a, b = s.asof(mwanzo), s.asof(mwisho)
        if a is None or b is None or a <= 0:
            return None
        out[jina] = b / a - 1.0
    return Returns(day=day, start=mwanzo, end=mwisho, by_index=out)


def signal_for(
    day: date,
    series: Mapping[str, Series],
    *,
    lag_days: int = LAG_DAYS,
    symbols: Sequence[str] = QUALIFIED,
) -> Signal | None:
    """`Signal` iliyosawazishwa kwa tarehe moja, au `None`.

    ```
    z_C   =  −(r_C − mean(r))        (baada ya kusawazisha; r_US inatoka)
    w_C   =  z_C / max|z|            (kubwa kabisa ni 1.0)
    ```
    """
    inahitajika = {INDEX_FOR[s] for s in symbols}
    pungufu = inahitajika - set(series)
    if pungufu:
        raise FamilyError(f"faharasa hazipo: {sorted(pungufu)}")

    r = returns_for(day, {k: v for k, v in series.items()
                          if k in inahitajika}, lag_days=lag_days)
    if r is None:
        return None

    kwa_symbol = {s: r.by_index[INDEX_FOR[s]] for s in symbols}
    wastani = sum(kwa_symbol.values()) / len(kwa_symbol)
    z = {s: -(v - wastani) for s, v in kwa_symbol.items()}

    kubwa = max(abs(v) for v in z.values())
    if kubwa == 0:
        # Masoko yote yalifanya sawa kabisa — hakuna uwiano wa kubet.
        # Nadra, lakini si kosa: hakuna ishara siku hiyo.
        return None

    return Signal(
        weights={s: v / kubwa for s, v in z.items()},
        placeholder=False,
        meta={"returns": kwa_symbol, "start": r.start, "end": r.end,
              "mean_return": wastani, "lag_days": lag_days},
    )


def signals(
    days: Sequence[date],
    series: Mapping[str, Series],
    *,
    lag_days: int = LAG_DAYS,
) -> dict[date, Signal]:
    """Ishara kwa siku zote zenye data kamili."""
    out = {}
    for d in days:
        s = signal_for(d, series, lag_days=lag_days)
        if s is not None:
            out[d] = s
    return out


__all__ = ["INDEX_FOR", "US_INDEX", "LAG_DAYS", "month_start", "Returns",
           "returns_for", "signal_for", "signals"]
