"""Mifumo ya kalenda — DOCTRINE §6, §11.

Siku ya mwisho wa mwezi si siku ya kawaida. Ina mtiririko wa taasisi
unaojulikana — wanao-hedge hisa wakisawazisha kwenye fix — na huo ndio
mekanizimu wa F1 wenyewe.

Kwa hiyo F0 kutokuendeshwa siku hiyo si **kuzunguka lango**. Ni ufafanuzi:

```
F0 = mtiririko wa saa za kawaida za biashara
     → siku ya fix ya mwisho wa mwezi si siku ya kawaida
```

Tofauti hiyo ni ya msingi kwa uadilifu wa utafiti. Kutangaza kabla:

    F0 inastahili:  siku ya kazi  NA  regime == NORMAL

ni sehemu ya ufafanuzi wa F0. Kugundua baadaye kwamba *"F0 inaonekana bora
ukiondoa mwisho wa mwezi"* ingekuwa **uamuzi wa utafiti**, na ungehesabika
kwenye bajeti ya majaribio.

---

Mifumo inaandikwa hapa kama seti **iliyofungwa**. Familia inatangaza
inayostahili; isiyotangazwa haiendeshwi. Chaguo-msingi ni `NORMAL` pekee —
familia inayotaka kuendesha siku ya tukio lazima iseme hivyo waziwazi.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable

from src.events.clock import ni_gotobi, ni_siku_ya_kazi, ni_siku_ya_mwisho_ya_mwezi

# Seti iliyofungwa. Kuongeza regime ni mabadiliko ya doctrine, si ya code.
NORMAL = "NORMAL"
MONTH_END_FIX = "MONTH_END_FIX"
CB_EVENT = "CB_EVENT"
HOLIDAY = "HOLIDAY"
TURN_OF_YEAR = "TURN_OF_YEAR"

REGIMES = (NORMAL, MONTH_END_FIX, CB_EVENT, HOLIDAY, TURN_OF_YEAR)


class RegimeError(RuntimeError):
    """Regime haiwezi kubainishwa kama ilivyoombwa."""


def regime_of(
    day: date,
    *,
    holidays: Iterable[date] = (),
    cb_days: Iterable[date] = (),
) -> str:
    """Regime ya siku hii. **Moja pekee** — mifumo haiingiliani.

    Mpangilio wa kipaumbele umewekwa hapa mara moja, na ni wa kudumu:

    ```
    HOLIDAY  >  TURN_OF_YEAR  >  MONTH_END_FIX  >  CB_EVENT  >  NORMAL
    ```

    `MONTH_END_FIX` iko juu ya `CB_EVENT` kwa sababu mtiririko wa hedge ni wa
    **lazima** — wanao-hedge hawana chaguo. Tukio la benki kuu ni la habari;
    mtiririko wa mwisho wa mwezi ni wa mkataba.

    Mpangilio huu unaandikwa kwenye ledger kama sehemu ya sera ya uamuzi.
    """
    zilizofungwa = set(holidays)
    if not ni_siku_ya_kazi(day, zilizofungwa):
        return HOLIDAY
    # 22 Des – 3 Jan: ukwasi mdogo, spread pana, mtiririko wa mwisho wa mwaka.
    if (day.month == 12 and day.day >= 22) or (day.month == 1 and day.day <= 3):
        return TURN_OF_YEAR
    if ni_siku_ya_mwisho_ya_mwezi(day, zilizofungwa):
        return MONTH_END_FIX
    if day in set(cb_days):
        return CB_EVENT
    return NORMAL


def ni_gotobi_halali(day: date, *, holidays: Iterable[date] = (),
                     cb_days: Iterable[date] = ()) -> bool:
    """Gotobi inayostahili: siku ya Gotobi **na** regime inayoruhusiwa.

    Gotobi haigongani na F1 kwa muda (inafunga 00:55 UTC, F1 inafunguka
    14:00), lakini inatangaza `NORMAL` pekee kama familia nyingine zote —
    ili sheria iwe moja kwa zote badala ya kila familia kuwa na yake.
    """
    return (ni_gotobi(day, holidays)
            and regime_of(day, holidays=holidays, cb_days=cb_days) == NORMAL)


__all__ = ["NORMAL", "MONTH_END_FIX", "CB_EVENT", "HOLIDAY", "TURN_OF_YEAR",
           "REGIMES", "RegimeError", "regime_of", "ni_gotobi_halali"]
