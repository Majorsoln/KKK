"""Stop kutoka kwenye mwendo uliopita — DOCTRINE §4.2, §5.1.

Kanuni ipo **hapa pekee**. Familia zote zinaiita; hakuna inayoiandika upya.
Kama ingekuwa kwenye kila familia, tofauti ya siku moja kwenye mpaka wa
historia ingebadilisha lots bila kuonekana popote — na familia mbili
zingekuwa zinapima vitu viwili wakati zikiwa zinadai kupima kimoja.

```
mwendo  =  |kutoka − kuingia|  kwa MID          (volatility, si gharama)
stop    =  k × wastani wa mwendo wa vikao k VILIVYOPITA
lots    =  hatari ÷ ((stop + gharama) × thamani ya pip)   ← RCE
```

Matokeo ni `lots ∝ 1/mwendo` — kulenga volatility bila mfumo wa pili wa
ukubwa. `k` ni ya kila familia kwa sababu inategemea urefu wa dirisha na
ukubwa wa spread; kila kitu kingine ni cha pamoja.
"""

from __future__ import annotations

from datetime import date
from typing import Mapping, Sequence

from src.families.base import FamilyError

# `E|X| = σ√(2/π)` kwa mgawanyo wa normal. Inatumika kugeuza mwendo wa wastani
# kuwa `σ` kwa lango la gharama la §6.2, ambalo linadai σ ya DIRISHA.
MOVE_TO_SIGMA = 1.2533141373155003

# Vikao vya nyuma. Ni vya NYUMA pekee — ona `stop_from_moves`.
LOOKBACK_SESSIONS = 20
MIN_SESSIONS = 10


def session_move_pips(ndani, nje, *, pip: float) -> float:
    """`|kutoka − kuingia|` kwa **mid**, katika pips.

    Mid, si bei ya utekelezaji: hiki ni kipimo cha **volatility**, na spread
    si volatility. Kutumia bei ya utekelezaji kungeongeza spread nzima kwenye
    kila kipimo, na stop ingekua kwa gharama badala ya kwa mwendo.
    """
    return abs(nje.mid - ndani.mid) / pip


def stop_from_history(
    history: Sequence[float],
    *,
    lookback: int = LOOKBACK_SESSIONS,
    min_sessions: int = MIN_SESSIONS,
) -> float | None:
    """Wastani wa mwendo kwa vikao `lookback` vya mwisho, au `None`.

    Inarudisha `None` — si namba ya kubuni — pale historia haitoshi. Familia
    inayopokea `None` **hairuki kimya**: haizalishi kikapu, kwa sababu bila
    stop hakuna lots (§5).
    """
    if lookback < 1:
        raise FamilyError(f"lookback ni {lookback}, si ≥ 1")
    if min_sessions < 1 or min_sessions > lookback:
        raise FamilyError(
            f"min_sessions {min_sessions} haiko kati ya 1 na lookback {lookback}")
    if len(history) < min_sessions:
        return None
    teule = list(history[-lookback:])
    return sum(teule) / len(teule)


def stop_from_moves(
    moves: Mapping[tuple[date, str], float],
    *,
    lookback: int = LOOKBACK_SESSIONS,
    min_sessions: int = MIN_SESSIONS,
) -> dict[tuple[date, str], float]:
    """Toleo la batch: `{(siku, leg): mwendo}` → `{(siku, leg): stop}`.

    Jibu la siku fulani linatumia **siku zilizotangulia pekee** — siku yenyewe
    haiingii. Bila hilo, stop ingejua mwendo wa siku ambayo bado haijatokea,
    na ukubwa wa position ungekuwa na lookahead: siku zenye mwendo mkubwa
    zingepewa lots ndogo *kwa sababu* mwendo ulikuwa mkubwa, na curve
    ingeonekana laini kuliko soko lilivyo.
    """
    out: dict[tuple[date, str], float] = {}
    kwa_leg: dict[str, list[float]] = {}
    for (siku, leg) in sorted(moves, key=lambda k: (k[1], k[0])):
        nyuma = kwa_leg.setdefault(leg, [])
        jibu = stop_from_history(nyuma, lookback=lookback,
                                 min_sessions=min_sessions)
        if jibu is not None:
            out[(siku, leg)] = jibu
        thamani = float(moves[(siku, leg)])
        if thamani <= 0:
            raise FamilyError(f"mwendo si chanya: {siku} {leg} → {thamani}")
        nyuma.append(thamani)
    return out


__all__ = ["MOVE_TO_SIGMA", "LOOKBACK_SESSIONS", "MIN_SESSIONS",
           "session_move_pips", "stop_from_history", "stop_from_moves"]
