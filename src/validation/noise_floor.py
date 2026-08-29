"""Calibration B — sakafu ya kelele (DOCTRINE §9, R4, R5, R6, R15).

Kadri unavyojaribu strategies nyingi zaidi, ndivyo **bora** kati yao inavyoonekana
nzuri hata kama hakuna hata moja yenye edge. Strategies 100,000 zisizo na thamani
yoyote zinatoa bora yenye miezi 74% yenye faida na Sharpe 1.70 (§9.1). Kizingiti
chochote kilichochaguliwa na binadamu — 50%, 85%, Sharpe 1.0 — hakina kinga dhidi
ya hilo, kwa sababu hakijui utafutaji ulikuwa mkubwa kiasi gani.

Kwa hiyo kizingiti kinapimwa: endesha **pipeline ile ile** juu ya data isiyo na edge,
na kile injini inachokigundua pale ndicho sakafu.

---

**Mambo matatu ambayo moduli hii inayakataa, na kwa nini:**

**1 · Sakafu MOJA kwa vipimo vyote.** `noise_floor` ni **jedwali**, si namba.
Sakafu ya Sharpe haiwezi kuhukumu `net_pips_month` — ni vipimo tofauti vyenye
mgawanyo tofauti chini ya null ILE ILE. Metric isiyo na sakafu yake **haiwezi kuwa
lango** (§1.1); `gate()` inalipuka badala ya kukisia.

**2 · Sakafu kutoka kwa candidate MMOJA.** Tatizo la §9.1 ni tabia ya `max` ya
sampuli `K`. Ikiwa `run_pipeline` inaendesha candidate mmoja kwa kila replicate,
p95 inayotokea ni sakafu ya *"strategy moja ya bahati"* — na kizingiti hicho ni
kidogo kuliko kinachohitajika kwa kiasi kinachoongezeka na `K`. Kwa hiyo callback
**lazima** itangaze `variants_tested`, na moja haitoshi.

**3 · Replicates chache.** `p95` kutoka pointi 20 ni thamani ya pili kwa ukubwa ya
pointi 20 — jina lake ni percentile, tabia yake ni `max`. Kikomo ni
`MIN_REPLICATES`, na hakina njia ya kuzunguka.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from . import surrogates as S

BETTER = "better"
WORSE = "worse"

P_HIGH = 0.95
P_LOW = 0.05

# Replicates chache kuliko hii haziwezi kutoa p95. Pointi 50 zinaweka p95 kati ya
# order statistics 47 na 48 — bado ni ncha, lakini ni ncha inayoungwa mkono na
# pointi kadhaa badala ya moja. Hakuna `allow_thin`: mlango wa dharura kwenye
# kipimo ambacho kila lango linakitegemea ni mlango wa dharura kwenye kila lango.
MIN_REPLICATES = 50

N_BOOTSTRAP = 2000

VARIANTS_KEY = "variants_tested"


class CalibrationError(RuntimeError):
    """Calibration B haiwezi kuendeshwa kama ilivyoombwa."""


class NoFloorError(RuntimeError):
    """Metric imeombwa kama lango bila kuwa na sakafu yake (§1.1)."""


@dataclass(frozen=True)
class MetricSpec:
    """Metric, na **upande gani** wa mgawanyo wa null ni mgumu kuufikia."""

    name: str
    higher_is: str
    # Mipaka ya metric YENYEWE, si ya sakafu. `profitable_month_fraction` haiwezi
    # kuzidi 1.0; `max_drawdown` haiwezi kuwa chini ya 0. Sakafu inayofika mpaka
    # huo ni lango lisilopitika — na hilo linapaswa kuonekana mara moja, si
    # baada ya §13 kubaki tupu kwa miezi.
    lo: float = float("-inf")
    hi: float = float("inf")

    def __post_init__(self) -> None:
        if self.higher_is not in (BETTER, WORSE):
            raise CalibrationError(f"`higher_is` ni {BETTER}/{WORSE}, si {self.higher_is!r}")

    @property
    def tail(self) -> float:
        return P_HIGH if self.higher_is == BETTER else P_LOW


# §9.2 inataja sita; `net_account_return_month` inaongezwa kwa sababu §1.2
# inaifanya kuwa PRIMARY yenye mamlaka — na §1.1 inasema lango lolote linahitaji
# sakafu yake. Mamlaka bila sakafu isingeweza kupitisha chochote.
DEFAULT_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec("net_pips_month", BETTER),
    MetricSpec("net_account_return_month", BETTER),
    MetricSpec("profitable_month_fraction", BETTER, lo=0.0, hi=1.0),
    MetricSpec("sharpe", BETTER),
    MetricSpec("profit_factor", BETTER, lo=0.0),
    MetricSpec("max_drawdown", WORSE, lo=0.0),
)

# `fill_rate` HAIPO hapo juu kwa makusudi (§9.5, 2026-08-26).
#
# Sakafu ya kelele ni marekebisho ya **kutafuta mara nyingi**: inajibu swali
# "utafutaji wa K ulizalisha nini kwa bahati?" Inafanya kazi kwa metric ambazo
# utafutaji unazipandisha — Sharpe, faida, miezi yenye faida. `fill_rate`
# haipandishwi na utafutaji: strategy ya kipuuzi inajaza vizuri kama ya busara,
# kwa sababu kujaza kunategemea spread na mapengo, si ubora wa sheria.
#
# Kuiweka kwenye jedwali kunatoa sakafu ya `p95 = 1.0000`, ambayo inadai mgombea
# ajaze BORA kuliko 95% ya strategies za nasibu — lango lisilopitika kwa
# ufafanuzi. Run ya kwanza (2026-08-26) ilionyesha hilo kwa vitendo.
#
# Ukaguzi wa §16.4 (`fill_rate` ya chini mno = haitradiki) bado ni sahihi, lakini
# msingi wake ni utekelezaji halisi wa ticks — si mgawanyo wa null juu ya
# substrate ya bars, ambapo quotes nne kwa kila bar zinafanya kujaza kuwa rahisi
# kuliko soko lilivyo. Kipimo hicho kinakuja na hatua ya ticks, si hapa.
#
# §1.1 inaruhusu waziwazi: metric isiyo na sakafu inaweza kuwa DIAGNOSTIC pekee.
FILL_RATE_NI_DIAGNOSTIC = "fill_rate"


@dataclass(frozen=True)
class FloorEntry:
    """Sakafu ya metric MOJA, pamoja na ushahidi wa jinsi ilivyopatikana."""

    metric: str
    higher_is: str
    tail: float
    floor: float
    by_family: dict[str, float]
    n_used: dict[str, int]
    ci_low: float
    ci_high: float
    lo: float = float("-inf")
    hi: float = float("inf")

    @property
    def inapitika(self) -> bool:
        """Je kuna thamani YOYOTE halali inayoweza kuvuka sakafu hii?

        Sakafu ya `profitable_month_fraction > 1.0` au `max_drawdown < 0` si
        kali — ni **isiyopitika**, na inakataa kila kitu kimya. Run ya kwanza ya
        Calibration B (§9.5) ilitoa nne kama hizo kati ya saba, na hakuna
        kilichozionyesha hadi zilipohesabiwa kwa mkono.
        """
        if not math.isfinite(self.floor):
            return False
        return self.floor < self.hi if self.higher_is == BETTER else self.floor > self.lo

    @property
    def binding_family(self) -> str:
        """Familia iliyotoa sakafu ngumu zaidi — ndiyo inayotumika (R15)."""
        pick = max if self.higher_is == BETTER else min
        return pick(self.by_family, key=lambda k: self.by_family[k])

    @property
    def uncertainty(self) -> float:
        """Upana wa CI ukilinganishwa na sakafu yenyewe. Kubwa = sakafu tete."""
        base = abs(self.floor)
        return float("inf") if base == 0 else (self.ci_high - self.ci_low) / base

    def passes(self, value: float) -> bool:
        """Kuvuka sakafu ni **kuzidi**, si kufikia. Sawa haipiti."""
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return False
        return value > self.floor if self.higher_is == BETTER else value < self.floor

    def render(self) -> str:
        pct = int(self.tail * 100)
        fam = " · ".join(f"{k[:5]} {v:+.4f}" for k, v in sorted(self.by_family.items()))
        alama = "" if self.inapitika else "  HAIPITIKI"
        return (
            f"{self.metric:<28} p{pct:<3} {self.floor:>+10.4f}  "
            f"[{self.ci_low:+.4f}, {self.ci_high:+.4f}]  "
            f"←{self.binding_family[:5]}   {fam}{alama}"
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "metric": self.metric, "higher_is": self.higher_is, "tail": self.tail,
            "floor": self.floor, "by_family": self.by_family, "n_used": self.n_used,
            "ci_low": self.ci_low, "ci_high": self.ci_high,
            "binding_family": self.binding_family, "uncertainty": self.uncertainty,
            "lo": self.lo, "hi": self.hi, "passable": self.inapitika,
        }


@dataclass(frozen=True)
class NoiseFloor:
    """Jedwali kamili la sakafu, pamoja na ushahidi wenye tarehe (R5)."""

    entries: dict[str, FloorEntry]
    families: tuple[str, ...]
    n_replicates: int
    variants_tested_min: int
    variants_tested_median: float
    without_floor: tuple[str, ...] = ()
    seed: int = 0
    created_at: str = ""
    source: str = ""

    # ---------------- lango ----------------

    def gate(self, metric: str, value: float) -> bool:
        """Pitisha au kataa. Metric isiyo na sakafu **inalipuka**.

        §1.1: *metric isiyokuwa na `noise_floor` yake haiwezi kuwa lango.* Kurudisha
        `True` hapo ingekuwa kupitisha bila kipimo; kurudisha `False` ingekuwa
        kukataa bila kipimo. Zote mbili ni hukumu bila ushahidi.
        """
        entry = self.entries.get(metric)
        if entry is None:
            raise NoFloorError(
                f"`{metric}` haina sakafu — inaweza kuwa DIAGNOSTIC pekee (§1.1). "
                f"Zenye sakafu: {sorted(self.entries)}"
            )
        return entry.passes(value)

    def floor(self, metric: str) -> float:
        entry = self.entries.get(metric)
        if entry is None:
            raise NoFloorError(f"`{metric}` haina sakafu (§1.1)")
        return entry.floor

    def __contains__(self, metric: str) -> bool:
        return metric in self.entries

    @property
    def haipitiki(self) -> tuple[str, ...]:
        """Malango ambayo hakuna thamani halali inayoweza kuyavuka.

        Jedwali lenye hata moja kati ya haya si sakafu — ni mlango uliofungwa.
        §13 ingebaki tupu bila kosa lolote kuonekana (§9.5).
        """
        return tuple(e.metric for e in self.entries.values() if not e.inapitika)

    # ---------------- kuripoti ----------------

    def render(self) -> str:
        lines = [
            f"SAKAFU YA KELELE · replicates {self.n_replicates} kwa kila familia "
            f"({' · '.join(self.families)})",
            f"   variants_tested: chini {self.variants_tested_min:,} · "
            f"kati {self.variants_tested_median:,.0f}   (R6)",
            "",
        ]
        lines += ["   " + e.render() for e in self.entries.values()]
        if self.without_floor:
            lines += ["", "   BILA SAKAFU (diagnostic pekee, §1.1):"]
            lines += [f"      {m}" for m in self.without_floor]
        if self.haipitiki:
            lines += [
                "",
                f"   KOSA · sakafu ZISIZOPITIKA: {', '.join(self.haipitiki)}",
                "      Hakuna thamani halali inayoweza kuzivuka. Malango haya "
                "yatakataa KILA KITU,",
                "      kimya. Ona §9.5 — chanzo cha kawaida ni denominator au "
                "thamani isiyohesabika.",
            ]
        tete = [e.metric for e in self.entries.values() if e.uncertainty > 0.5]
        if tete:
            lines += ["", f"   ONYO · sakafu tete (CI pana kuliko 50%): {', '.join(tete)}"]
        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at,
            "source": self.source,
            "seed": self.seed,
            "families": list(self.families),
            "n_replicates": self.n_replicates,
            "variants_tested_min": self.variants_tested_min,
            "variants_tested_median": self.variants_tested_median,
            "without_floor": list(self.without_floor),
            "entries": {k: v.to_json() for k, v in self.entries.items()},
        }

    def write(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_json(), indent=2, default=str) + "\n",
            encoding="utf-8", newline="\n",
        )
        return path

    @classmethod
    def read(cls, path: Path) -> "NoiseFloor":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = {
            name: FloorEntry(
                metric=e["metric"], higher_is=e["higher_is"], tail=e["tail"],
                floor=e["floor"], by_family=dict(e["by_family"]),
                n_used=dict(e["n_used"]), ci_low=e["ci_low"], ci_high=e["ci_high"],
                lo=float(e.get("lo", float("-inf"))),
                hi=float(e.get("hi", float("inf"))),
            )
            for name, e in raw["entries"].items()
        }
        return cls(
            entries=entries, families=tuple(raw["families"]),
            n_replicates=int(raw["n_replicates"]),
            variants_tested_min=int(raw["variants_tested_min"]),
            variants_tested_median=float(raw["variants_tested_median"]),
            without_floor=tuple(raw.get("without_floor", ())),
            seed=int(raw.get("seed", 0)), created_at=raw.get("created_at", ""),
            source=raw.get("source", ""),
        )


# ===========================================================================
# Calibration B
# ===========================================================================


def calibrate(
    frame,
    run_pipeline: Callable[[Any], Mapping[str, float]],
    *,
    n_replicates: int,
    seed: int,
    metrics: Sequence[MetricSpec] = DEFAULT_METRICS,
    families: Sequence[str] = S.FAMILIES,
    block_len: int | None = None,
    regime: Sequence[str] | None = None,
    source: str = "",
    progress: Callable[[str], None] | None = print,
    checkpoint: "Checkpoint | None" = None,
) -> NoiseFloor:
    """Endesha pipeline juu ya data bandia, rudisha jedwali la sakafu.

    `run_pipeline(surrogate_frame)` inarudisha metrics za **candidate bora**
    aliyeibuka kwenye run ile — pamoja na `variants_tested`. Ndicho kiini: sakafu
    inayohitajika ni ya `max` ya utafutaji, si ya jaribio moja (§9.1).

    Jedwali zima linazalishika upya kutoka `seed` MOJA — kwa sharti moja:
    `run_pipeline` iwe **deterministic** ikipewa frame ile ile. Ikiwa na nasibu
    yake ya ndani isiyofungwa, sakafu itabadilika kila run bila sababu
    inayoonekana, na kizingiti kingekuwa kinatetemeka chini ya kila kitu.

    `checkpoint` inahifadhi matokeo ya kila replicate inapokamilika, na
    inayarudisha bila kuendesha upya. Si ya kasi — ni ya **kuishi**: run ya
    kweli ni masaa mengi, na mashine inayozimika saa ya 40 bila checkpoint
    inapoteza zote. Kwa sababu kila replicate ina seed yake inayotokana na
    `(seed, familia, rep)`, kuendelea kunatoa jedwali LILE LILE.

    R23 — hakuna kinachoendeshwa kimya: kila replicate inachapishwa.
    """
    import numpy as np

    if n_replicates < MIN_REPLICATES:
        raise CalibrationError(
            f"replicates {n_replicates} < {MIN_REPLICATES} — p95 ya pointi chache "
            f"ni `max` yenye jina la percentile"
        )
    fams = tuple(families)
    unknown = set(fams) - set(S.FAMILIES)
    if unknown:
        raise CalibrationError(f"familia hazijulikani: {sorted(unknown)}")
    if len(fams) < 3:
        raise CalibrationError(
            f"familia {len(fams)} < 3 — R15 inadai tatu. Sakafu ya familia moja ni "
            f"nusu tabia ya soko, nusu tabia ya generator, na hazitofautishwi"
        )

    specs = {m.name: m for m in metrics}
    seen: dict[str, dict[str, list[float]]] = {f: {} for f in fams}
    variants: list[int] = []
    extra: set[str] = set()

    for fam in fams:
        for rep in range(n_replicates):
            # Seed ya kila run inatokana na (seed, familia, replicate) — kwa hiyo
            # jedwali zima linazalishika upya kutoka namba MOJA.
            rep_seed = _seed_of(seed, fam, rep)
            # `is not None`, si `if checkpoint`: `__len__` inafanya
            # checkpoint TUPU iwe falsy — yaani ile ya run mpya kabisa,
            # ambayo ndiyo inayohitaji kuandika zaidi kuliko zote.
            result = (checkpoint.get(fam, rep)
                      if checkpoint is not None else None)
            ilihifadhiwa = result is not None
            if result is None:
                sur = S.make(frame, fam, seed=rep_seed,
                             block_len=block_len, regime=regime)
                result = run_pipeline(sur.frame)
                _check_result(result, fam, rep)
                if checkpoint is not None:
                    checkpoint.put(fam, rep, result)
            else:
                _check_result(result, fam, rep)

            variants.append(int(result[VARIANTS_KEY]))
            for name, value in result.items():
                if name == VARIANTS_KEY:
                    continue
                if name not in specs:
                    extra.add(name)
                    continue
                # `isfinite`, si `isnan` pekee. `profit_factor` ni `inf` pale
                # mgombea hana trade hata moja ya hasara — si thamani kubwa, ni
                # thamani isiyohesabika. Ikiingia kwenye `np.quantile`,
                # interpolation inafanya `inf - inf` na sakafu YOTE inakuwa
                # `NaN`. Lango la `> NaN` halipitiki kamwe, na halionyeshi kwa
                # nini. (Calibration B ya kwanza, 2026-08-26.)
                if value is None or not _ni_namba(value):
                    continue
                seen[fam].setdefault(name, []).append(float(value))

            if progress:
                # Idadi ya replicates ZENYE THAMANI, si zilizoendeshwa. Ndiyo
                # inayohesabiwa dhidi ya `MIN_REPLICATES` chini, kwa hiyo ndiyo
                # inayopaswa kuonekana wakati run inaendelea: kujua saa 60
                # baadaye kwamba hazikutosha si kujua, ni kupoteza.
                zilizojaa = min(
                    (len(v) for v in seen[fam].values()), default=0
                ) if seen[fam] else 0
                onyo = "" if zilizojaa >= MIN_REPLICATES else (
                    f"  [zenye thamani {zilizojaa}/{MIN_REPLICATES}]"
                )
                progress(
                    f"   {fam:<17} {rep + 1:>4}/{n_replicates}  "
                    f"variants {result[VARIANTS_KEY]:>6,}  seed {rep_seed}"
                    f"{'  (imehifadhiwa)' if ilihifadhiwa else ''}{onyo}"
                )

    rng = np.random.default_rng(seed)
    entries: dict[str, FloorEntry] = {}
    hafifu: list[str] = []

    for name, spec in specs.items():
        by_family: dict[str, float] = {}
        n_used: dict[str, int] = {}
        for fam in fams:
            values = seen[fam].get(name, [])
            n_used[fam] = len(values)
            if len(values) >= MIN_REPLICATES:
                by_family[fam] = float(np.quantile(values, spec.tail))

        if len(by_family) < len(fams):
            # Metric ambayo pipeline haikuiripoti mara kwa mara haiwezi kuwa lango.
            # Si kosa — ni kwamba haina sakafu, na §1.1 inaamua kilichobaki.
            hafifu.append(name)
            continue

        # R15 — inayotumika ni ngumu ZAIDI, si wastani. Kwa metric ambayo `ndogo ni
        # bora` (mf. `max_drawdown`), ngumu zaidi ni **ndogo** kuliko zote; `max`
        # ya §9.2 imeandikwa kwa metric za p95. Kuchukua `max` kwa p5 kungechukua
        # sakafu RAHISI kuliko zote — kinyume kabisa cha sheria.
        pick = max if spec.higher_is == BETTER else min
        binding = pick(by_family, key=lambda k: by_family[k])
        floor = by_family[binding]

        # CI inatoka kwa familia ILIYOFUNGA sakafu, si kwa zote zilizounganishwa.
        # Ikitoka kwenye pooled, ingeeleza kutokuwa na uhakika kwa namba ambayo
        # HAITUMIKI — na sakafu ingeweza kutua nje ya CI yake yenyewe.
        lo, hi = _bootstrap_ci(seen[binding][name], spec.tail, rng)

        entries[name] = FloorEntry(
            metric=name, higher_is=spec.higher_is, tail=spec.tail, floor=float(floor),
            by_family=by_family, n_used=n_used, ci_low=lo, ci_high=hi,
            lo=spec.lo, hi=spec.hi,
        )

    floor_table = NoiseFloor(
        entries=entries, families=fams, n_replicates=int(n_replicates),
        variants_tested_min=int(min(variants)),
        variants_tested_median=float(_median(variants)),
        without_floor=tuple(sorted(extra | set(hafifu))),
        seed=int(seed),
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source=source,
    )
    if progress:
        progress("")
        progress(floor_table.render())
    return floor_table


@dataclass
class Checkpoint:
    """Matokeo ya kila replicate, yakiandikwa yanapokamilika.

    Run ya kweli ni masaa mengi. Mashine inayozimika saa ya 40 bila hii
    inapoteza zote — na si kupoteza muda pekee, ni kupoteza **ushahidi** ambao
    R5 inaudai.

    ---

    **Fingerprint ndiyo sehemu isiyo ya kawaida.**

    Kuendelea kwenye run yenye vigezo TOFAUTI ni hatari kubwa kuliko kuanza
    upya: jedwali lingechanganya replicates za `K=200` na za `K=1000`, na
    `variants_tested` isingesema ukweli kuhusu utafutaji wowote. Hilo
    lisingeonekana kwenye faili ya mwisho — namba zote zingeonekana halali.

    Kwa hiyo fingerprint inaandikwa kwenye mstari wa kwanza, na kuendelea
    kunakataliwa ikiwa haifanani. Faili inaanza upya badala ya kuchanganya.
    """

    path: Path
    fingerprint: str
    _seen: dict[tuple[str, int], dict] = field(default_factory=dict)

    @classmethod
    def open(cls, path: Path, fingerprint: str,
             progress: Callable[[str], None] | None = None) -> "Checkpoint":
        path = Path(path)
        me = cls(path=path, fingerprint=fingerprint)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({"fingerprint": fingerprint}) + "\n",
                encoding="utf-8", newline="\n",
            )
            return me

        lines = path.read_text(encoding="utf-8").splitlines()
        kichwa = json.loads(lines[0]) if lines else {}
        if kichwa.get("fingerprint") != fingerprint:
            if progress:
                progress(
                    f"   checkpoint ya vigezo TOFAUTI ({path.name}) — inaanza upya."
                )
                for mstari in _tofauti(kichwa.get("fingerprint"), fingerprint):
                    progress(f"      {mstari}")
            path.write_text(
                json.dumps({"fingerprint": fingerprint}) + "\n",
                encoding="utf-8", newline="\n",
            )
            return me

        for line in lines[1:]:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                # Mstari wa mwisho unaweza kukatika mashine ikizimika katikati
                # ya kuandika. Kuurusha ni sahihi: replicate hiyo itaendeshwa
                # upya, na seed yake ni ile ile.
                continue
            me._seen[(row["family"], int(row["rep"]))] = row["result"]
        if progress and me._seen:
            progress(f"   checkpoint: replicates {len(me._seen):,} zimehifadhiwa")
        return me

    def get(self, family: str, rep: int) -> dict | None:
        return self._seen.get((family, rep))

    def put(self, family: str, rep: int, result: Mapping[str, float]) -> None:
        row = {"family": family, "rep": int(rep), "result": dict(result)}
        with self.path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(row, default=float) + "\n")
            fh.flush()
        self._seen[(family, int(rep))] = row["result"]

    def __len__(self) -> int:
        return len(self._seen)


def _tofauti(zamani: Any, sasa: Any) -> list[str]:
    """Vigezo VILIVYOBADILIKA pekee, si fingerprint nzima.

    Kuchapisha JSON mbili ndefu kunaficha kilichobadilika ndani ya kilichobaki
    sawa — na hicho ndicho kinachohitajika kujulikana.
    """
    try:
        a = json.loads(zamani) if isinstance(zamani, str) else dict(zamani or {})
        b = json.loads(sasa) if isinstance(sasa, str) else dict(sasa or {})
    except (json.JSONDecodeError, TypeError, ValueError):
        return [f"zamani: {zamani}", f"sasa  : {sasa}"]
    if not isinstance(a, dict) or not isinstance(b, dict):
        return [f"zamani: {zamani}", f"sasa  : {sasa}"]

    out = []
    for key in sorted(set(a) | set(b)):
        kabla, baada = a.get(key), b.get(key)
        if kabla != baada:
            out.append(f"{key}: {_fupi(kabla)} → {_fupi(baada)}")
    return out or ["(hakuna kigezo kilichobadilika — fingerprint imeharibika?)"]


def _fupi(value: Any, kikomo: int = 60) -> str:
    text = json.dumps(value, sort_keys=True) if not isinstance(value, str) else value
    return text if len(text) <= kikomo else text[: kikomo - 1] + "…"


def code_fingerprint(*roots: Path) -> str:
    """sha256 ya code YOTE inayoathiri matokeo.

    Checkpoint iliyoshika vigezo pekee (`K`, `seed`, bars) ilirudisha replicates
    za **code ya zamani** baada ya kasoro mbili kurekebishwa: vigezo
    havikubadilika, code ilibadilika, na run nzima ilikuwa ni kucheza tena
    matokeo yale yale. Jedwali lililotoka lilionekana halali kabisa.

    Kwa hiyo fingerprint inashika **maudhui ya faili**. Mabadiliko yoyote ya
    code au config yanaifanya checkpoint ianze upya — gharama ya saa nyingi,
    lakini nafuu kuliko sakafu inayodai kupima code isiyokuwa ikiendeshwa.
    """
    import hashlib

    h = hashlib.sha256()
    for root in sorted(Path(r) for r in roots):
        if root.is_file():
            faili = [root]
        else:
            faili = sorted(p for p in root.rglob("*")
                           if p.is_file() and p.suffix in (".py", ".yaml", ".yml"))
        for path in faili:
            h.update(str(path.name).encode("utf-8"))
            h.update(path.read_bytes())
    return h.hexdigest()[:32]


def guard_generator(*, noise_floor_path: Path, cost_calibration_path: Path) -> NoiseFloor:
    """R5 — generator **haifunguki** kabla Calibration A na B hazijahifadhiwa.

    Ni assertion, si nidhamu: generator inaita hii kabla ya kuzalisha candidate ya
    kwanza, na ikikosekana ushahidi, haiendeshi kabisa.
    """
    cost_path = Path(cost_calibration_path)
    if not cost_path.exists():
        raise CalibrationError(
            f"Calibration A (§8.3) haipo: {cost_path} — R5 inazuia generator"
        )
    floor_path = Path(noise_floor_path)
    if not floor_path.exists():
        raise CalibrationError(
            f"Calibration B (§9.2) haipo: {floor_path} — R5 inazuia generator"
        )
    table = NoiseFloor.read(floor_path)
    if not table.entries:
        raise CalibrationError(f"{floor_path} haina sakafu hata moja — R5 inazuia generator")
    return table


# ===========================================================================
# Ndani
# ===========================================================================


def _ni_namba(value: Any) -> bool:
    """Namba halisi inayoweza kuingia kwenye mgawanyo. `NaN`/`inf` si namba."""
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _check_result(result: Any, family: str, rep: int) -> None:
    where = f"({family}, replicate {rep})"
    if not isinstance(result, Mapping):
        raise CalibrationError(f"`run_pipeline` {where} irudishe mapping, si {type(result)}")
    if VARIANTS_KEY not in result:
        raise CalibrationError(
            f"`run_pipeline` {where} haikutangaza `{VARIANTS_KEY}` — S1/R6 inadai "
            f"ihesabiwe daima, na bila yake sakafu haijui utafutaji ulikuwa mkubwa kiasi gani"
        )
    n = int(result[VARIANTS_KEY])
    if n < 2:
        raise CalibrationError(
            f"`{VARIANTS_KEY}` = {n} {where} — sakafu ya candidate MMOJA ni sakafu ya "
            f"swali ambalo hakuna aliyeuliza. Tatizo la §9.1 ni tabia ya `max` ya K"
        )


def _seed_of(seed: int, family: str, rep: int) -> int:
    import hashlib

    digest = hashlib.sha256(f"{seed}:{family}:{rep}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def _bootstrap_ci(values: Iterable[float], tail: float, rng) -> tuple[float, float]:
    """CI ya percentile yenyewe — sakafu ina kutokuwa na uhakika, nayo inaandikwa."""
    import numpy as np

    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return float("nan"), float("nan")
    draws = rng.integers(0, arr.size, size=(N_BOOTSTRAP, arr.size))
    qs = np.quantile(arr[draws], tail, axis=1)
    lo, hi = np.quantile(qs, [0.025, 0.975])
    return float(lo), float(hi)


def _median(values: Sequence[int]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0
