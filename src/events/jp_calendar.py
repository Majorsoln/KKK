"""Kalenda ya sikukuu za Japani — DOCTRINE §11.

Gotobi ni **siku ya malipo ya benki**, si tarehe ya kalenda. Tarehe
inayogawanyika kwa 5 ikianguka siku isiyo ya kazi, malipo yanasogezwa
**mbele** hadi siku ya kazi inayofuata. Kwa hiyo bila kalenda ya Japani,
tarehe ya tukio inakosewa — na kukosea kunafanya vitu viwili:

```
siku yenye mtiririko  →  tunaikosa
siku isiyo na kitu    →  tunaitrade
```

Vyote viwili vinaongeza kelele. Havipotoshi mwelekeo, lakini vinapunguza
nguvu — na Gotobi ina matukio ~600 pekee, kwa hiyo hakuna cha kupoteza.

**Bila kalenda hii, makadirio ni matukio ~25–30 kati ya 600 (4–5%)
yaliyoshikwa kwenye tarehe isiyo sahihi.**

---

**Kilichomo na kisichomo.** Sikukuu za tarehe thabiti, za Jumatatu ya
n-th (*Happy Monday*), na **ikwinoksi mbili** (fomula ya 1980–2099, sahihi
kwa mwaka wowote kwenye sampuli yetu). Pamoja na siku za mbadala
(振替休日: sikukuu ikianguka Jumapili, Jumatatu inayofuata inafungwa) na
sikukuu za benki za mwisho wa mwaka.

Zilizohamishwa kwa Olimpiki (2020, 2021) zimeandikwa kama vighairi, si
kama sheria — kwa sababu ndivyo zilivyokuwa.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

# Tarehe thabiti: (mwezi, siku, mwaka wa kuanzia, mwaka wa kuishia)
_THABITI = (
    (1, 1, 1949, 9999),      # 元日
    (2, 11, 1967, 9999),     # 建国記念の日
    (2, 23, 2020, 9999),     # 天皇誕生日 (tangu 2020)
    (12, 23, 1989, 2018),    # 天皇誕生日 (Heisei)
    (4, 29, 1949, 9999),     # 昭和の日 / みどりの日
    (5, 3, 1949, 9999),      # 憲法記念日
    (5, 4, 2007, 9999),      # みどりの日
    (5, 5, 1949, 9999),      # こどもの日
    (8, 11, 2016, 9999),     # 山の日
    (11, 3, 1948, 9999),     # 文化の日
    (11, 23, 1948, 9999),    # 勤労感謝の日
)

# Jumatatu ya n-th: (mwezi, n, mwaka wa kuanzia)
_JUMATATU = (
    (1, 2, 2000),            # 成人の日
    (7, 3, 2003),            # 海の日
    (9, 3, 2003),            # 敬老の日
    (10, 2, 2000),           # スポーツの日
)

# Sikukuu za BENKI (si za taifa) — masoko ya Japani yamefungwa.
_BENKI = ((1, 2), (1, 3), (12, 31))

# Olimpiki ya Tokyo ilihamisha sikukuu tatu mwaka 2020 na tatu 2021.
# Ni vighairi vilivyoandikwa kwenye sheria, si mfumo.
_OLIMPIKI = {
    2020: {"ondoa": [(7, 20), (10, 12), (8, 11)],
           "ongeza": [(7, 23), (7, 24), (8, 10)]},
    2021: {"ondoa": [(7, 19), (10, 11), (8, 11)],
           "ongeza": [(7, 22), (7, 23), (8, 8)]},
}


def _ikwinoksi(year: int) -> tuple[int, int]:
    """Siku za 春分の日 na 秋分の日 (Machi, Septemba).

    Fomula ya kawaida, sahihi kwa 1980–2099. Ikwinoksi ni **kipimo cha
    anga**, si sheria, kwa hiyo tarehe inabadilika mwaka hadi mwaka —
    na 春分 mara nyingi inaanguka tarehe 20 au 21, ambazo ni ÷5 au karibu.
    """
    n = year - 1980
    machi = math.floor(20.8431 + 0.242194 * n - n // 4)
    septemba = math.floor(23.2488 + 0.242194 * n - n // 4)
    return machi, septemba


def _nth_jumatatu(year: int, month: int, n: int) -> date:
    d = date(year, month, 1)
    d += timedelta(days=(7 - d.weekday()) % 7)          # Jumatatu ya kwanza
    return d + timedelta(days=7 * (n - 1))


def holidays(year: int) -> set[date]:
    """Sikukuu zote za mwaka mmoja, pamoja na siku za mbadala."""
    out: set[date] = set()

    for m, d, kuanzia, kuishia in _THABITI:
        if kuanzia <= year <= kuishia:
            out.add(date(year, m, d))
    for m, n, kuanzia in _JUMATATU:
        if year >= kuanzia:
            out.add(_nth_jumatatu(year, m, n))
    machi, septemba = _ikwinoksi(year)
    out.add(date(year, 3, machi))
    out.add(date(year, 9, septemba))

    ghairi = _OLIMPIKI.get(year)
    if ghairi:
        for m, d in ghairi["ondoa"]:
            out.discard(date(year, m, d))
        for m, d in ghairi["ongeza"]:
            out.add(date(year, m, d))

    # 振替休日 — sikukuu ikianguka Jumapili, siku inayofuata isiyo sikukuu
    # inafungwa. Sheria inatumika kwa mfululizo (Mei 3–5).
    for siku in sorted(out):
        if siku.weekday() == 6:                          # Jumapili
            mbadala = siku + timedelta(days=1)
            while mbadala in out:
                mbadala += timedelta(days=1)
            out.add(mbadala)

    for m, d in _BENKI:
        out.add(date(year, m, d))
    return out


def holidays_between(start: date, end: date) -> set[date]:
    """Sikukuu zote kati ya tarehe mbili, pamoja na za mwaka uliopita/ujao.

    Miaka ya jirani inaingizwa kwa sababu sikukuu za benki za 31 Desemba na
    1–3 Januari zinapakana na mpaka wa mwaka.
    """
    zote: set[date] = set()
    for year in range(start.year - 1, end.year + 2):
        zote |= holidays(year)
    return {d for d in zote if start <= d <= end}


__all__ = ["holidays", "holidays_between"]
