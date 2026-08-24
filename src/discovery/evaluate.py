"""Kutathmini strategy juu ya features — DOCTRINE §10.2, §5, R11.

Kiungo kati ya `Strategy` (maandishi) na bars (namba). Inatoa **signals**: nyakati
ambazo strategy inasema "ingia". Kinachofuata baada ya hapo ni RCE (§11.1) na
kisha path ya ticks — si hapa.

---

**Feature isiyojulikana si `False`; ni "hakuna signal".**

Wakati wa warmup, `EMA_200` ni `NaN` kwa bars 200 za kwanza. Kwenye pandas,
`NaN > 5` ni `False` — inaonekana salama. Lakini `NOT(NaN < 5)` ni `NOT(False)`,
yaani **`True`**: sharti lililokanushwa lingewaka kwa bar ambayo feature yake
haijulikani kabisa, na strategy ingeanza kutrade kabla ya kujua chochote.

Kwa hiyo `valid` inahesabiwa kando: bar yenye feature yoyote inayohitajika ikiwa
`NaN` **haitoi signal**, bila kujali masharti yanasemaje. Ndiyo `nan_policy:
invalidate` ya `data.yaml` ikiwa code.

---

**Signal ni mwisho wa bar, si mwanzo wake (R11, R1).**

Bars zina index ya **mwanzo**. Uamuzi unafanyika bar inapofungwa, kwa hiyo muda
wa signal ni `bar_ends(index)`. Kutumia index moja kwa moja kungeweka uamuzi saa
moja kabla ya taarifa iliyousababisha kuwepo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.data.bars import bar_ends
from src.strategies.dna import (
    AND, CROSS_ABOVE, CROSS_BELOW, GT, LT, Condition, ConditionSet, Strategy,
)


# Sababu za kufa BAADA ya kugusa data. Zinahesabiwa kwenye `variants_tested`:
# candidate iliyotathminiwa iligusa bars, kwa hiyo ilikuwa sehemu ya utafutaji.
# Kutozihesabu kungeshusha sakafu ya §9 — upande usio salama.
NO_VALID_BARS = "NO_VALID_BARS"
NO_SIGNALS = "NO_SIGNALS"
ALWAYS_IN = "ALWAYS_IN"

DEGENERATE = (NO_VALID_BARS, NO_SIGNALS, ALWAYS_IN)


class EvaluateError(RuntimeError):
    """Strategy haiwezi kutathminiwa juu ya features zilizotolewa."""


@dataclass(frozen=True)
class Signals:
    """Signals za strategy moja, pamoja na kwa nini nyingine hazikutokea."""

    strategy_id: str
    times: Any                 # DatetimeIndex ya nyakati za uamuzi
    n_bars: int
    n_valid: int               # bars zenye features zote zinazohitajika
    n_signals: int

    @property
    def signal_rate(self) -> float:
        """`signals ÷ bars HALALI`. Denominator si bars zote.

        Bars za warmup hazikuwahi kuwa nafasi ya kutrade; kuziweka kwenye
        denominator kungeshusha kiwango kwa sababu isiyo ya strategy.
        """
        return self.n_signals / self.n_valid if self.n_valid else float("nan")

    @property
    def degenerate(self) -> str:
        """Sababu ikiwa entry haikuchagua chochote. Tupu ikiwa ni strategy.

        Mipaka miwili pekee, na si vizingiti: ni **mipaka ya ufafanuzi**.

        * `signals = 0` — hakuna cha kupima. Si strategy mbaya; si strategy.
        * `signals = bars zote` — entry haikuchagua **chochote**. Tautolojia kama
          `A > x OR A < x` inatoa hii, na vivyo hivyo kizingiti kilicho nje ya
          masafa ya data kabisa. "Kuwa sokoni daima" si sheria ya kuingia.

        Kati yao, kiwango ni **taarifa** kwa §13 na §21 — si lango. Kuweka
        kizingiti hapo (mf. "chini ya 1%") kungekuwa constant isiyopimwa, na §2
        inaikataa.
        """
        if self.n_valid == 0:
            return NO_VALID_BARS
        if self.n_signals == 0:
            return NO_SIGNALS
        if self.n_signals == self.n_valid:
            return ALWAYS_IN
        return ""

    def render(self) -> str:
        alama = f"  {self.degenerate}" if self.degenerate else ""
        return (
            f"{self.strategy_id}  bars {self.n_bars:,} · halali {self.n_valid:,} · "
            f"signals {self.n_signals:,} ({self.signal_rate:.2%}){alama}"
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id, "n_bars": self.n_bars,
            "n_valid": self.n_valid, "n_signals": self.n_signals,
            "signal_rate": self.signal_rate, "degenerate": self.degenerate,
        }


def features_required(cset: ConditionSet) -> tuple[str, ...]:
    return cset.features


def evaluate_condition(cond: Condition, features):
    """Sharti moja → mfululizo wa `bool`. `NaN` inatoa `False` kabla ya kukanusha."""
    import numpy as np

    if cond.feature not in features.columns:
        raise EvaluateError(f"feature {cond.feature!r} haipo kwenye frame")
    left = features[cond.feature]

    if cond.ref_ni_feature:
        if cond.ref not in features.columns:
            raise EvaluateError(f"feature {cond.ref!r} haipo kwenye frame")
        right = features[str(cond.ref)]
    else:
        right = float(cond.ref)

    if cond.op == GT:
        out = left > right
    elif cond.op == LT:
        out = left < right
    elif cond.op in (CROSS_ABOVE, CROSS_BELOW):
        prev_left = left.shift(1)
        prev_right = right.shift(1) if cond.ref_ni_feature else right
        if cond.op == CROSS_ABOVE:
            out = (left > right) & (prev_left <= prev_right)
        else:
            out = (left < right) & (prev_left >= prev_right)
    else:  # pragma: no cover — `dna.Condition` inakagua tayari
        raise EvaluateError(f"op {cond.op!r} haijulikani")

    out = out.fillna(False).astype(bool)
    return ~out if cond.negate else out


def valid_mask(cset: ConditionSet, features):
    """Bars zenye kila feature inayohitajika ikijulikana.

    Hii ndiyo inayozuia `NOT(NaN < x)` kuwaka wakati wa warmup — kosa ambalo
    lingefanya strategy ianze kutrade kabla haijajua chochote.
    """
    import pandas as pd

    if cset.tupu:
        return pd.Series(True, index=features.index)
    zinazohitajika = list(cset.features)
    hazipo = [f for f in zinazohitajika if f not in features.columns]
    if hazipo:
        raise EvaluateError(f"features hazipo: {hazipo}")
    return features[zinazohitajika].notna().all(axis=1)


def evaluate_set(cset: ConditionSet, features):
    """Masharti yote + `valid` → mfululizo mmoja wa `bool`."""
    import pandas as pd

    halali = valid_mask(cset, features)
    if cset.tupu:
        return halali

    matokeo = [evaluate_condition(c, features) for c in cset.conditions]
    pamoja = matokeo[0]
    for m in matokeo[1:]:
        pamoja = (pamoja & m) if cset.logic == AND else (pamoja | m)
    return pamoja & halali


def signals(strategy: Strategy, features, *, timeframe: str,
            day_tz: str = "UTC") -> Signals:
    """Nyakati za uamuzi ambapo entry ya strategy inawaka.

    Muda unaorudishwa ni **mwisho wa bar** — ndipo uamuzi unapofanyika (R11).
    """
    import pandas as pd

    if len(features) == 0:
        raise EvaluateError("hakuna features")

    halali = valid_mask(strategy.entry, features)
    waka = evaluate_set(strategy.entry, features)
    mwisho = pd.DatetimeIndex(bar_ends(features.index, timeframe, day_tz))

    return Signals(
        strategy_id=strategy.strategy_id,
        times=mwisho[waka.to_numpy()],
        n_bars=len(features),
        n_valid=int(halali.sum()),
        n_signals=int(waka.sum()),
    )


def exit_signals(strategy: Strategy, features, *, timeframe: str,
                 day_tz: str = "UTC"):
    """Nyakati ambazo sheria ya exit inawaka. Tupu ikiwa strategy haina sheria.

    SL/TP/time_stop ziko kwenye path ya ticks (`backtest/execution.py`); hizi ni
    za ziada, si mbadala.
    """
    import pandas as pd

    if strategy.exit.tupu:
        return pd.DatetimeIndex([], tz="UTC")
    waka = evaluate_set(strategy.exit, features)
    mwisho = pd.DatetimeIndex(bar_ends(features.index, timeframe, day_tz))
    return mwisho[waka.to_numpy()]
