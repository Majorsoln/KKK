"""Strategy DNA — DOCTRINE §10.1, §10.2, §5.

> **Strategy ni uchambuzi KAMILI: kutoka data ghafi hadi entry NA exit yake.**

Hilo si maelezo; ni muundo. `Strategy` haiwezi kuundwa bila exit, kwa sababu
dataclass inaidai. Entry ile ile yenye exit mbili tofauti inatoa **hash mbili
tofauti**, kwa hiyo zote mbili zinahesabiwa kwenye `variants_tested` (§10.1).
Kama exit ingekuwa ya hiari au ingeongezwa baadaye, ingekuwa rahisi kutafuta
exit bora baada ya kuona matokeo — na hesabu ya multiplicity ingekuwa ndogo
kuliko utafutaji uliofanyika.

---

**AND · OR · NOT bila mti wa expressions.**

§10.3 inadai combinators tatu. Zinatekelezwa kwa **orodha tambarare** yenye
`logic` moja (`AND`/`OR`) na `negate` kwa kila sharti. Sababu ni mbili:

* `complexity` ya §21 ni `len(entry) + len(exit)`. Kwenye mti wenye kina,
  namba hiyo haingekuwa na maana moja.
* Mutation inayohifadhi `max_conditions` (R21) inahesabika kwa urahisi kwenye
  orodha; kwenye mti ingehitaji kuhesabu majani na kufafanua "sharti" ni nini.

Kinachopotea ni masharti yaliyowekwa ndani ya mengine — `(A AND B) OR C`. Kama
yatahitajika, yatakuja kama aina ya `Condition`, si kama kina cha mti.

---

**`variant_hash` haujali mpangilio.** `A AND B` na `B AND A` ni strategy ILE ILE.
Zisipopewa hash moja, generator ingezalisha nakala na `variants_tested`
ingepanda bila utafutaji kupanuka — sakafu ya §9 ingekuwa juu kuliko inavyostahili
kwa sababu ya kuhesabu, si kwa sababu ya kutafuta.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Sequence

AND, OR = "AND", "OR"
LOGIC = (AND, OR)

GT, LT, CROSS_ABOVE, CROSS_BELOW = ">", "<", "cross_above", "cross_below"
OPS = (GT, LT, CROSS_ABOVE, CROSS_BELOW)

# SL/TP: aina zinazoruhusiwa. `parameter` ina maana tofauti kwa kila moja, kwa
# hiyo aina na parameter zinasafiri pamoja daima.
ATR_MULT, FIXED_PIPS, RR = "atr_mult", "fixed_pips", "rr"
SL_TYPES = (ATR_MULT, FIXED_PIPS)
TP_TYPES = (ATR_MULT, FIXED_PIPS, RR)

ANY_REGIME = "ANY"

# §5: kila percentile inatangaza dirisha lake ndani ya JINA lake. Bila hilo,
# `ATR_percentile` ya bar ya 2017 ingeweza kuhesabiwa juu ya sample nzima na
# kubeba taarifa ya 2020 — uvujaji ambao hakuna test itakayouona, na
# utakaojionyesha kama ustadi.
_PERCENTILE = re.compile(r"percentile", re.IGNORECASE)
_DIRISHA = re.compile(r"_\d+[dbm]$")


class DNAError(ValueError):
    """Strategy haiwezi kuundwa kama ilivyoombwa."""


@dataclass(frozen=True)
class Condition:
    """Sharti moja: `feature op ref`.

    `ref` inaweza kuwa namba (kizingiti) au jina la feature nyingine
    (ulinganisho). Kutofautisha kunafanywa na aina, si na mkataba wa majina.
    """

    feature: str
    op: str
    ref: float | str
    negate: bool = False

    def __post_init__(self) -> None:
        if self.op not in OPS:
            raise DNAError(f"op {self.op!r} haijulikani — zinazoruhusiwa {OPS}")
        for name in (self.feature, self.ref):
            if isinstance(name, str):
                _kagua_jina(name)

    @property
    def ref_ni_feature(self) -> bool:
        return isinstance(self.ref, str)

    def render(self) -> str:
        ref = self.ref if self.ref_ni_feature else f"{self.ref:g}"
        msingi = f"{self.feature} {self.op} {ref}"
        return f"NOT({msingi})" if self.negate else msingi

    def key(self) -> tuple:
        """Ufunguo wa kupanga — unafanya hash isijali mpangilio."""
        return (self.feature, self.op, str(self.ref), self.negate)

    def to_json(self) -> dict[str, Any]:
        return {"feature": self.feature, "op": self.op, "ref": self.ref,
                "negate": self.negate}


@dataclass(frozen=True)
class ConditionSet:
    """Masharti na namna yanavyounganishwa. Tupu = 'daima kweli'."""

    conditions: tuple[Condition, ...] = ()
    logic: str = AND

    def __post_init__(self) -> None:
        if self.logic not in LOGIC:
            raise DNAError(f"logic {self.logic!r} — zinazoruhusiwa {LOGIC}")

        # `A AND A` ni `A`. Nakala kamili zinaanguka hapa, si kwenye hash pekee.
        #
        # Zikiachwa, mambo mawili yangetokea: `complexity` ingehesabu masharti
        # ambayo hayabani chochote (na §13 ingeadhibu strategy kwa kitu
        # isichokifanya), na strategy ILE ILE ingepata hash mbili — yaani
        # `variants_tested` ingepanda bila utafutaji kupanuka.
        #
        # Kinachobaki bila kugunduliwa ni **madokezo**: `return_1 < 0` inadokeza
        # `return_1 < 0.01` chini ya AND. Hilo ni gumu zaidi, na kuliacha
        # kunaadhibu strategy kupita kiasi — upande salama.
        pekee: list[Condition] = []
        zilizoonekana: set[tuple] = set()
        for c in self.conditions:
            if c.key() not in zilizoonekana:
                zilizoonekana.add(c.key())
                pekee.append(c)
        if len(pekee) != len(self.conditions):
            object.__setattr__(self, "conditions", tuple(pekee))

    def __len__(self) -> int:
        return len(self.conditions)

    @property
    def tupu(self) -> bool:
        return not self.conditions

    @property
    def features(self) -> tuple[str, ...]:
        out: list[str] = []
        for c in self.conditions:
            out.append(c.feature)
            if c.ref_ni_feature:
                out.append(str(c.ref))
        return tuple(dict.fromkeys(out))

    def render(self) -> str:
        if self.tupu:
            return "(daima)"
        kiungo = f" {self.logic} "
        return kiungo.join(c.render() for c in self.conditions)

    def canonical(self) -> dict[str, Any]:
        """Umbo lisilojali mpangilio — `A AND B` sawa na `B AND A`.

        `AND` na `OR` zote ni commutative kwenye orodha tambarare, kwa hiyo
        kupanga ni salama. Mti wenye kina ungefanya hili lisiwe kweli, na ndiyo
        sababu nyingine ya kuepuka mti.
        """
        return {
            "logic": self.logic,
            "conditions": [c.to_json() for c in sorted(self.conditions, key=Condition.key)],
        }

    def to_json(self) -> dict[str, Any]:
        return {"logic": self.logic, "conditions": [c.to_json() for c in self.conditions]}


@dataclass(frozen=True)
class Strategy:
    """Uchambuzi kamili: entry NA exit, zikitangazwa pamoja (§10.1)."""

    symbol: str
    direction: str                  # BUY / SELL
    entry: ConditionSet
    # ---- exit: kila strategy inayo, hakuna ya hiari ----
    sl_type: str
    sl_param: float
    tp_type: str
    tp_param: float
    time_stop_bars: int
    exit: ConditionSet = field(default_factory=ConditionSet)
    regime: str = ANY_REGIME
    generation: int = 0
    parent_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.direction.upper() not in ("BUY", "SELL"):
            raise DNAError(f"direction {self.direction!r} — BUY au SELL")
        if self.sl_type not in SL_TYPES:
            raise DNAError(f"sl_type {self.sl_type!r} — {SL_TYPES}")
        if self.tp_type not in TP_TYPES:
            raise DNAError(f"tp_type {self.tp_type!r} — {TP_TYPES}")
        if self.sl_param <= 0 or self.tp_param <= 0:
            raise DNAError("sl_param na tp_param lazima ziwe > 0")
        if self.time_stop_bars <= 0:
            raise DNAError("time_stop_bars lazima iwe > 0 — trade isiyo na mwisho si trade")
        if self.entry.tupu:
            raise DNAError("entry haiwezi kuwa tupu — 'ingia daima' si strategy")

    # ---------------- vipimo ----------------

    @property
    def complexity(self) -> int:
        """§21: `len(entry_conditions) + len(exit_conditions)`."""
        return len(self.entry) + len(self.exit)

    @property
    def features_used(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(self.entry.features + self.exit.features))

    # ---------------- utambulisho ----------------

    def canonical(self) -> dict[str, Any]:
        """Kila kinachofanya strategy kuwa YENYEWE — na hakuna kingine.

        `generation` na `parent_ids` HAZIMO: strategy ile ile iliyofikiwa kwa
        njia mbili tofauti ni strategy ile ile, na kuipima mara mbili ni
        kuhesabu utafutaji ambao haukufanyika.
        """
        return {
            "symbol": self.symbol.upper(), "direction": self.direction.upper(),
            "regime": self.regime,
            "entry": self.entry.canonical(), "exit": self.exit.canonical(),
            "sl": [self.sl_type, round(float(self.sl_param), 6)],
            "tp": [self.tp_type, round(float(self.tp_param), 6)],
            "time_stop_bars": int(self.time_stop_bars),
        }

    @property
    def variant_hash(self) -> str:
        raw = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @property
    def strategy_id(self) -> str:
        return f"{self.symbol.upper()}-{self.direction.upper()[:1]}-{self.variant_hash}"

    # ---------------- kuripoti ----------------

    def render(self) -> str:
        return (
            f"{self.strategy_id}  gen {self.generation}  complexity {self.complexity}\n"
            f"   regime  {self.regime}\n"
            f"   ENTRY   {self.entry.render()}\n"
            f"   EXIT    {self.exit.render()}\n"
            f"   SL {self.sl_type}={self.sl_param:g} · TP {self.tp_type}={self.tp_param:g} "
            f"· time_stop {self.time_stop_bars} bars"
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id, "variant_hash": self.variant_hash,
            "symbol": self.symbol, "direction": self.direction, "regime": self.regime,
            "entry": self.entry.to_json(), "exit": self.exit.to_json(),
            "sl_type": self.sl_type, "sl_param": self.sl_param,
            "tp_type": self.tp_type, "tp_param": self.tp_param,
            "time_stop_bars": self.time_stop_bars,
            "complexity": self.complexity, "features_used": list(self.features_used),
            "generation": self.generation, "parent_ids": list(self.parent_ids),
        }


def _kagua_jina(name: str) -> None:
    """§5: percentile bila dirisha kwenye jina HAIRUHUSIWI kuwepo kwenye code."""
    if _PERCENTILE.search(name) and not _DIRISHA.search(name):
        raise DNAError(
            f"feature {name!r} ni percentile bila dirisha kwenye jina lake (§5). "
            f"Tumia mf. `ATR_percentile_252d` — percentile juu ya sample nzima "
            f"ingempa bar ya 2017 taarifa ya 2020"
        )


def strategies_ni_moja(a: Strategy, b: Strategy) -> bool:
    """Strategy mbili ni ile ile ikiwa hash zao zinalingana."""
    return a.variant_hash == b.variant_hash


def unique(items: Sequence[Strategy]) -> list[Strategy]:
    """Ondoa nakala, ukihifadhi mpangilio wa kwanza."""
    seen: set[str] = set()
    out = []
    for s in items:
        if s.variant_hash not in seen:
            seen.add(s.variant_hash)
            out.append(s)
    return out
