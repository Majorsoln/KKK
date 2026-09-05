"""Generator — DOCTRINE §10.3, §10.4, R5, R21.

Inazalisha strategies kutoka **maktaba ya masharti**, si kutoka hypothesis. Hiyo
ndiyo maana: kile injini inachokigundua hakitegemei kile mtu alichokifikiria.

---

**R5 — generator HAIFUNGUKI kabla Calibration A na B.**

`open()` inaita `guard_generator()`, na hiyo inakataa kuendelea bila faili mbili
za ushahidi. Si nidhamu; ni assertion. Generator inayoweza kuendeshwa kabla ya
sakafu kujulikana ni generator inayoweza kutoa "ugunduzi" ambao hakuna
kinachoweza kuupima.

Code yenyewe **ipo** kabla ya B, kwa lazima: §9.2 inadai sakafu ipimwe kwa
kuendesha **pipeline nzima** juu ya data bandia, na pipeline hiyo inajumuisha
utafutaji. Sakafu ya candidate mmoja ingekuwa sakafu ya swali lisilo letu (§9.1).
Kwa hiyo mpangilio ni: `generator inajengwa → B inapima sakafu yake → R5
inafunguka → generator inatumika kwenye data halisi`.

---

**R21 — `max_conditions` ni invariant baada ya KILA mutation, si kizazi cha kwanza.**

Mzazi mwenye masharti 4 na mwenye 4 wanaweza kutoa mtoto mwenye 8. Mtoto huyo
anakataliwa **kabla ya backtest**, anaandikwa kwenye ledger kama
`INVALID_CANDIDATE`, na **hahesabiwi** kwenye `variants_tested` — hakupimwa, kwa
hiyo hakuwahi kupata nafasi ya kuwa na bahati.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence

from src.strategies.dna import (
    AND, ANY_REGIME, ATR_MULT, CROSS_ABOVE, CROSS_BELOW, FIXED_PIPS, GT, LT, OR, RR,
    Condition, ConditionSet, Strategy,
)

from .ledger import INVALID_CANDIDATE, VariantLedger

# §10.3: `max_conditions` = 3–5. Kikomo kigumu, si pendekezo — strategy yenye
# masharti 15 inaweza kuonekana nzuri kwa sababu imekariri historia.
MAX_CONDITIONS_KIKOMO = 5
MIN_CONDITIONS_KIKOMO = 1


class GeneratorError(RuntimeError):
    """Generator imeombwa kufanya kitu kinachovunja mkataba wake."""


@dataclass(frozen=True)
class FeatureSpec:
    """Feature moja pamoja na kile kinachoweza kulinganishwa nayo.

    `thresholds` ni thamani zinazoruhusiwa. Zinatoka kwenye ufafanuzi wa feature
    yenyewe — percentile ni [0,1], RSI ni [0,100] — si kwa kubuni. Feature
    isiyo na kizingiti chenye maana haiingii kwenye maktaba.
    """

    name: str
    thresholds: tuple[float, ...]
    ops: tuple[str, ...] = (GT, LT)
    # Features nyingine ambazo hii inaweza kulinganishwa nazo moja kwa moja.
    peers: tuple[str, ...] = ()


# Maktaba ya masharti — §10.3 (EMA, RSI, ADX, ATR percentile, returns, distance,
# breakout). Majina yanatoka §5, na kila percentile ina dirisha lake ndani ya
# jina lake — `dna._kagua_jina` inaikataa isipokuwa hivyo.
MAKTABA: tuple[FeatureSpec, ...] = (
    FeatureSpec("RSI_14", (20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0)),
    FeatureSpec("ADX_14", (15.0, 20.0, 25.0, 30.0, 40.0)),
    FeatureSpec("ATR_percentile_252d", (0.10, 0.25, 0.50, 0.75, 0.90)),
    FeatureSpec("tick_count_percentile_252d", (0.10, 0.25, 0.50, 0.75, 0.90)),
    FeatureSpec("return_1", (-0.010, -0.005, 0.0, 0.005, 0.010)),
    FeatureSpec("return_5", (-0.020, -0.010, 0.0, 0.010, 0.020)),
    FeatureSpec("return_20", (-0.040, -0.020, 0.0, 0.020, 0.040)),
    FeatureSpec("dist_from_EMA200", (-0.020, -0.005, 0.0, 0.005, 0.020)),
    FeatureSpec("dist_from_high_20", (-0.030, -0.010, -0.002, 0.0)),
    FeatureSpec("dist_from_low_20", (0.0, 0.002, 0.010, 0.030)),
    FeatureSpec("close_pos_in_range", (0.10, 0.25, 0.50, 0.75, 0.90)),
    FeatureSpec("spread_per_atr", (0.02, 0.05, 0.10, 0.20)),
    FeatureSpec("hour", tuple(float(h) for h in range(0, 24, 2))),
    FeatureSpec(
        "EMA_20", (), ops=(CROSS_ABOVE, CROSS_BELOW, GT, LT),
        peers=("EMA_50", "EMA_100", "EMA_200"),
    ),
    FeatureSpec(
        "EMA_50", (), ops=(CROSS_ABOVE, CROSS_BELOW, GT, LT),
        peers=("EMA_100", "EMA_200"),
    ),
)

SL_GRID = ((ATR_MULT, (0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)),
           (FIXED_PIPS, (10.0, 20.0, 30.0, 50.0)))
TP_GRID = ((ATR_MULT, (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0)),
           (RR, (1.0, 1.5, 2.0, 3.0)),
           (FIXED_PIPS, (10.0, 20.0, 40.0, 80.0)))
TIME_STOP_GRID = (6, 12, 24, 48, 96)


@dataclass(frozen=True)
class GeneratorSpec:
    """Mipaka ya utafutaji. Kila kimoja kinaingia kwenye ushahidi."""

    symbols: tuple[str, ...]
    max_conditions: int = 4
    min_conditions: int = 1
    max_exit_conditions: int = 2
    regimes: tuple[str, ...] = (ANY_REGIME,)
    directions: tuple[str, ...] = ("BUY", "SELL")

    def __post_init__(self) -> None:
        if not self.symbols:
            raise GeneratorError("hakuna symbol")
        if not (MIN_CONDITIONS_KIKOMO <= self.max_conditions <= MAX_CONDITIONS_KIKOMO):
            raise GeneratorError(
                f"max_conditions {self.max_conditions} nje ya "
                f"[{MIN_CONDITIONS_KIKOMO}, {MAX_CONDITIONS_KIKOMO}] — §10.3. "
                f"Strategy yenye masharti mengi inaweza kuonekana nzuri kwa sababu "
                f"imekariri historia"
            )
        if self.min_conditions > self.max_conditions:
            raise GeneratorError("min_conditions > max_conditions")

    def to_json(self) -> dict[str, Any]:
        return {
            "symbols": list(self.symbols), "max_conditions": self.max_conditions,
            "min_conditions": self.min_conditions,
            "max_exit_conditions": self.max_exit_conditions,
            "regimes": list(self.regimes), "directions": list(self.directions),
        }


# ===========================================================================
# R5 — mlango
# ===========================================================================


def open_generator(*, noise_floor_path: Path, cost_calibration_path: Path):
    """R5: generator haifunguki bila Calibration A na B zote mbili.

    Inarudisha jedwali la sakafu, kwa sababu kinachofuata kinakihitaji — na kwa
    hiyo hakuna njia ya kufungua mlango kisha kupuuza kilichomo ndani yake.
    """
    from src.validation.noise_floor import guard_generator

    return guard_generator(
        noise_floor_path=noise_floor_path,
        cost_calibration_path=cost_calibration_path,
    )


# ===========================================================================
# Kuzalisha
# ===========================================================================


def condition(rng, spec: FeatureSpec | None = None) -> Condition:
    """Sharti moja la nasibu kutoka maktaba."""
    spec = spec or MAKTABA[int(rng.integers(len(MAKTABA)))]
    op = spec.ops[int(rng.integers(len(spec.ops)))]

    if op in (CROSS_ABOVE, CROSS_BELOW) or (spec.peers and not spec.thresholds):
        if not spec.peers:
            raise GeneratorError(f"{spec.name}: op {op} inahitaji peers")
        ref: float | str = spec.peers[int(rng.integers(len(spec.peers)))]
    else:
        ref = float(spec.thresholds[int(rng.integers(len(spec.thresholds)))])

    return Condition(feature=spec.name, op=op, ref=ref,
                     negate=bool(rng.random() < 0.15))


def condition_set(rng, n: int, *, logic: str | None = None) -> ConditionSet:
    if n <= 0:
        return ConditionSet()
    logic = logic or (AND if rng.random() < 0.75 else OR)
    return ConditionSet(tuple(condition(rng) for _ in range(n)), logic=logic)


def strategy(rng, spec: GeneratorSpec, *, symbol: str | None = None) -> Strategy:
    """Strategy moja ya nasibu — entry NA exit, zikitangazwa pamoja (§10.1)."""
    n_entry = int(rng.integers(spec.min_conditions, spec.max_conditions + 1))
    n_exit = int(rng.integers(0, spec.max_exit_conditions + 1))
    # Jumla ya masharti haizidi kikomo: exit ni sehemu ya strategy, si nyongeza.
    n_exit = min(n_exit, spec.max_conditions - n_entry)

    sl_type, sl_grid = SL_GRID[int(rng.integers(len(SL_GRID)))]
    tp_type, tp_grid = TP_GRID[int(rng.integers(len(TP_GRID)))]

    return Strategy(
        symbol=symbol or spec.symbols[int(rng.integers(len(spec.symbols)))],
        direction=spec.directions[int(rng.integers(len(spec.directions)))],
        entry=condition_set(rng, n_entry),
        exit=condition_set(rng, max(0, n_exit)),
        sl_type=sl_type, sl_param=float(sl_grid[int(rng.integers(len(sl_grid)))]),
        tp_type=tp_type, tp_param=float(tp_grid[int(rng.integers(len(tp_grid)))]),
        time_stop_bars=int(TIME_STOP_GRID[int(rng.integers(len(TIME_STOP_GRID)))]),
        regime=spec.regimes[int(rng.integers(len(spec.regimes)))],
    )


def generate(spec: GeneratorSpec, n: int, *, seed: int) -> Iterator[Strategy]:
    """Strategies `n` za nasibu, zinazozalishika upya kutoka `seed`."""
    import numpy as np

    rng = np.random.default_rng(seed)
    for _ in range(n):
        yield strategy(rng, spec)


# ===========================================================================
# §10.4 — evolution, na R21
# ===========================================================================


def valid(candidate: Strategy, spec: GeneratorSpec) -> bool:
    """R21 — invariant inayokaguliwa baada ya KILA mutation."""
    return candidate.complexity <= spec.max_conditions and len(candidate.entry) >= 1


def mutate(parent: Strategy, spec: GeneratorSpec, rng) -> Strategy:
    """Badilisha kipande KIMOJA. Mabadiliko makubwa ni utafutaji mpya, si kizazi."""
    chaguo = ("entry", "exit", "sl", "tp", "time_stop")
    lipi = chaguo[int(rng.integers(len(chaguo)))]

    entry, exit_, = parent.entry, parent.exit
    sl_type, sl_param = parent.sl_type, parent.sl_param
    tp_type, tp_param = parent.tp_type, parent.tp_param
    time_stop = parent.time_stop_bars

    if lipi == "entry":
        masharti = list(entry.conditions)
        idx = int(rng.integers(len(masharti)))
        masharti[idx] = condition(rng)
        entry = ConditionSet(tuple(masharti), logic=entry.logic)
    elif lipi == "exit":
        masharti = list(exit_.conditions)
        if masharti and rng.random() < 0.5:
            masharti[int(rng.integers(len(masharti)))] = condition(rng)
        else:
            masharti.append(condition(rng))     # inaweza kuvunja R21 — ndiyo maana
        exit_ = ConditionSet(tuple(masharti), logic=exit_.logic)
    elif lipi == "sl":
        sl_type, grid = SL_GRID[int(rng.integers(len(SL_GRID)))]
        sl_param = float(grid[int(rng.integers(len(grid)))])
    elif lipi == "tp":
        tp_type, grid = TP_GRID[int(rng.integers(len(TP_GRID)))]
        tp_param = float(grid[int(rng.integers(len(grid)))])
    else:
        time_stop = int(TIME_STOP_GRID[int(rng.integers(len(TIME_STOP_GRID)))])

    return Strategy(
        symbol=parent.symbol, direction=parent.direction, entry=entry, exit=exit_,
        sl_type=sl_type, sl_param=sl_param, tp_type=tp_type, tp_param=tp_param,
        time_stop_bars=time_stop, regime=parent.regime,
        generation=parent.generation + 1, parent_ids=(parent.strategy_id,),
    )


def recombine(a: Strategy, b: Strategy, rng) -> Strategy:
    """Entry ya mmoja, exit ya mwingine.

    Hapa ndipo R21 inavunjika kwa urahisi zaidi: mzazi mwenye masharti 4 na
    mwenye 4 wanatoa mtoto mwenye 8. Function hii **haizuii** — inaunda mtoto
    kama alivyo, na ukaguzi unafanywa na `spawn()`. Kuficha ukiukaji hapa
    kungefanya R21 isiweze kupimwa.
    """
    if a.symbol != b.symbol:
        raise GeneratorError(f"recombine ya symbols tofauti: {a.symbol} na {b.symbol}")
    return Strategy(
        symbol=a.symbol, direction=a.direction, entry=a.entry, exit=b.exit,
        sl_type=b.sl_type, sl_param=b.sl_param,
        tp_type=b.tp_type, tp_param=b.tp_param,
        time_stop_bars=b.time_stop_bars, regime=a.regime,
        generation=max(a.generation, b.generation) + 1,
        parent_ids=(a.strategy_id, b.strategy_id),
    )


@dataclass
class Spawner:
    """Kizazi kipya, pamoja na ledger inayoshika kila kilichotokea (S1, R21)."""

    spec: GeneratorSpec
    ledger: VariantLedger = field(default_factory=VariantLedger)

    def spawn(self, candidate: Strategy) -> Strategy | None:
        """Andika candidate; rudisha `None` ikiwa haitapimwa.

        Kila candidate inaingia kwenye ledger — hata isiyo halali. `None`
        inamaanisha *"haitaenda kwenye data"*, si *"haikuwahi kuwepo"*.
        """
        sababu = "" if valid(candidate, self.spec) else INVALID_CANDIDATE
        record = self.ledger.generate(candidate, reject_reason=sababu)
        return None if record.reject_reason else candidate

    def spawn_many(self, candidates: Sequence[Strategy]) -> list[Strategy]:
        return [s for s in (self.spawn(c) for c in candidates) if s is not None]

    def next_generation(self, survivors: Sequence[Strategy], *, n: int, rng
                        ) -> list[Strategy]:
        """Mutation na recombination, chini ya bajeti ya `variants_tested`."""
        if not survivors:
            return []
        watoto: list[Strategy] = []
        for _ in range(n):
            if len(survivors) > 1 and rng.random() < 0.4:
                i, j = rng.integers(len(survivors), size=2)
                if survivors[int(i)].symbol != survivors[int(j)].symbol:
                    watoto.append(mutate(survivors[int(i)], self.spec, rng))
                    continue
                watoto.append(recombine(survivors[int(i)], survivors[int(j)], rng))
            else:
                watoto.append(mutate(survivors[int(rng.integers(len(survivors)))],
                                     self.spec, rng))
        return self.spawn_many(watoto)
