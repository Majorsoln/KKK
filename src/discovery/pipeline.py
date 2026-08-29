"""Pipeline ya kutafuta — DOCTRINE §3, §8.4, §9.2, §11, R6, R17, S1.

Mnyororo mmoja, kuanzia bars hadi metrics za mgombea bora:

```
bars → features (§5) → generator (§10) → backtest (§11) → LANGO LA UCHUMI (§8.4)
                            │                                      │
                            └──────── VariantLedger (S1) ──────────┘
```

Kazi yake ni **mbili zinazopaswa kuwa moja**:

* **hatua ya kutafuta** juu ya data halisi, na
* **`run_pipeline`** ya Calibration B juu ya data bandia.

Zisipokuwa code ILE ILE, sakafu ya kelele ingepima utafutaji ambao si ule
unaoendeshwa, na §9 nzima ingesimama juu ya ulinganisho usio sawa. Ndiyo maana
`for_calibration()` haiandiki mnyororo mpya — inafunga tu `search()` ile ile.

---

**Ni nani "bora"? Uamuzi mmoja unaobeba uzito wote.**

Calibration B inaomba metrics za mgombea **mmoja** kwa kila replicate. Kwa hiyo
sheria ya kuchagua inakuwa sehemu ya ufafanuzi wa sakafu.

Chaguo hapa ni `net_account_return_month` — PRIMARY yenye mamlaka (R17, §1.2).
Metrics zote za mgombea huyo zinaripotiwa kama zilivyo.

Njia mbadala — kuchukua **kilele cha kila metric peke yake** kwenye run — ni
kali zaidi kwa mtazamo wa kwanza, lakini inavunjika kwa `max_drawdown`: mgombea
mwenye DD ndogo kuliko wote chini ya null ni yule anayetrade mara chache mno,
na sakafu inayotokana naye ingedai kila strategy halisi iwe na DD ndogo kuliko
ya mtu asiyetrade. Hilo si lango kali, ni lango lisilo na maana.

**Sharti linalofanya sakafu iwe halali: sheria ya kuchagua ya Calibration B na
ya hatua ya kutafuta ni MOJA.** `select_by` inaandikwa kwenye ushahidi kwa
sababu hiyo — ikibadilika, sakafu ya zamani haihukumu utafutaji mpya.

---

**Kilichokataliwa bado kimehesabiwa (S1, R6).**

Candidate iliyokataliwa na lango la uchumi imeshagusa data. `variants_tested`
inaihesabu. Kutoihesabu kungeshusha sakafu kwa utafutaji ambao ulifanyika
kweli — upande usio salama kabisa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from src.backtest import economics as ECO
from src.backtest.bar_path import to_path
from src.backtest.engine import BrokerFacts, miezi_ya_dirisha, run
from src.backtest.ledger import Ledger
from src.discovery.evaluate import DEGENERATE, EvaluateError
from src.discovery.generator import GeneratorSpec, generate
from src.discovery.ledger import BACKTEST, VariantLedger
from src.validation.noise_floor import VARIANTS_KEY

# R17/§1.2 — PRIMARY yenye mamlaka. Pesa inaamua, si pips.
SELECT_BY = "net_account_return_month"

# Sababu za kufa kabla ya backtest. Zote zinahesabiwa kwenye `variants_tested`
# ISIPOKUWA zilizokataliwa kabla ya kugusa data (`INVALID_CANDIDATE`,
# `DUPLICATE`) — ledger yenyewe ndiyo inayoamua hilo (S1).
DEGENERATE_ENTRY = "DEGENERATE_ENTRY"
NO_FEATURES = "NO_FEATURES"


class PipelineError(RuntimeError):
    """Pipeline haiwezi kuendeshwa kama ilivyoombwa."""


@dataclass(frozen=True)
class PipelineSpec:
    """Kila kitu kinachofafanua run MOJA ya utafutaji. Chote kinaingia kwenye ushahidi."""

    symbol: str
    timeframe: str
    broker: BrokerFacts
    generator: GeneratorSpec
    n_candidates: int
    hour_tz: str = "UTC"          # §8.6 — si chaguo la kimya
    day_tz: str = "UTC"
    spread_col: str = "spread_p50"
    select_by: str = SELECT_BY

    def __post_init__(self) -> None:
        if self.n_candidates < 2:
            raise PipelineError(
                f"n_candidates {self.n_candidates} < 2 — tatizo la §9.1 ni tabia "
                f"ya `max` ya K, na K=1 haina `max`"
            )
        if self.symbol not in self.generator.symbols:
            raise PipelineError(
                f"symbol {self.symbol!r} haipo kwenye generator.symbols "
                f"{list(self.generator.symbols)}"
            )

    def to_json(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol, "timeframe": self.timeframe,
            "n_candidates": self.n_candidates, "hour_tz": self.hour_tz,
            "day_tz": self.day_tz, "spread_col": self.spread_col,
            "select_by": self.select_by, "generator": self.generator.to_json(),
            "substrate": "bar_path",
        }


@dataclass
class SearchResult:
    """Run moja ya utafutaji: ledger kamili, na bora aliyeibuka."""

    spec: PipelineSpec
    ledger: VariantLedger
    best: Any = None                       # BacktestResult | None
    best_economics: Any = None             # ECO.Economics | None
    best_id: str = ""
    n_passed_economics: int = 0
    by_reason: dict[str, int] = field(default_factory=dict)

    @property
    def variants_tested(self) -> int:
        return self.ledger.variants_tested

    def metrics(self) -> dict[str, float]:
        """Metrics za bora + `variants_tested` — ndicho `calibrate()` inachohitaji.

        Bila bora hata mmoja, metrics ni `NaN`: run ambayo hakuna kilichopita
        haisemi "sifuri", inasema "hakuna". `calibrate()` inaruka `NaN` badala
        ya kuiweka kwenye mgawanyo — na ikiwa `NaN` ni nyingi mno, metric
        inaishia `without_floor` badala ya kupata sakafu ya uongo.
        """
        if self.best is None:
            out = {m: float("nan") for m in (
                "net_pips_month", "net_account_return_month",
                "profitable_month_fraction", "sharpe", "profit_factor",
                "max_drawdown", "fill_rate",
            )}
        else:
            out = {k: v for k, v in self.best.metrics().items()
                   if k not in ("n_trades", "n_months", "path_dependence",
                                VARIANTS_KEY)}
        out[VARIANTS_KEY] = self.variants_tested
        return out

    def render(self) -> str:
        lines = [
            f"UTAFUTAJI · {self.spec.symbol} {self.spec.timeframe} · "
            f"wagombea {self.spec.n_candidates:,} · "
            f"zilizopimwa {self.variants_tested:,} · "
            f"walipita uchumi {self.n_passed_economics:,}",
            f"   bora kwa `{self.spec.select_by}`: "
            f"{self.best_id or '(hakuna)'}",
        ]
        if self.best_economics is not None:
            lines.append(f"   {self.best_economics.render()}")
        for jina, n in sorted(self.by_reason.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"      {jina:<24} {n:>7,}")
        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        return {
            "spec": self.spec.to_json(),
            "variants_tested": self.variants_tested,
            "n_generated": self.ledger.n_generated,
            "n_passed_economics": self.n_passed_economics,
            "by_reason": dict(self.by_reason),
            "best_id": self.best_id,
            "metrics": self.metrics(),
            "economics": (self.best_economics.to_json()
                          if self.best_economics is not None else None),
        }


# ===========================================================================
# Utafutaji
# ===========================================================================


def search(bars, spec: PipelineSpec, *, cfg_risk, seed: int,
           starting_balance: float | None = None,
           progress: Callable[[str], None] | None = None,
           on_pass: Callable[[str, Any, Any], None] | None = None) -> SearchResult:
    """Endesha wagombea `n` juu ya bars zile zile, rudisha bora.

    `seed` inatawala kila kitu cha nasibu hapa. Ikipewa bars zile zile na seed
    ile ile, matokeo ni yale yale — sharti la `calibrate()` (§9.2).

    `on_pass(candidate_id, result, economics)` inaitwa kwa kila aliyepita lango
    la uchumi. `SearchResult` inashikilia bora PEKEE — kwa runs 150 za
    Calibration B, kushikilia kila `BacktestResult` kungejaza kumbukumbu bila
    sababu. Anayehitaji wote (mf. §13) anachukua hapa.
    """
    import math

    from src.data.features import build as build_features

    ledger = VariantLedger()
    out = SearchResult(spec=spec, ledger=ledger)

    feats = build_features(bars, symbol=spec.symbol, hour_tz=spec.hour_tz)

    # Miezi ya dirisha zinahesabiwa MARA MOJA, si kwa kila mgombea. Bars 50,000
    # zikigeuzwa kuwa `PeriodIndex` kwa kila mmoja kati ya 1,000 zinagharimu
    # nusu ya muda wa run — na hazibadiliki hata kidogo.
    miezi = miezi_ya_dirisha(feats)

    # Njia MBILI pekee — moja kwa kila direction — zinajengwa mara moja badala
    # ya kwa kila mgombea. `bar_path` ni deterministic kwa (bars, direction),
    # kwa hiyo hii ni kasi tu, si mabadiliko ya tabia.
    njia = {
        upande: to_path(bars, spec.timeframe, symbol=spec.symbol,
                        direction=upande, day_tz=spec.day_tz,
                        spread_col=spec.spread_col)
        for upande in ("BUY", "SELL")
    }

    bora_thamani = -math.inf
    for candidate in generate(spec.generator, spec.n_candidates, seed=seed):
        record = ledger.generate(candidate)
        if record.reject_reason:
            # `DUPLICATE`/`INVALID_CANDIDATE` — hazijagusa data (S1).
            _hesabu(out.by_reason, record.reject_reason)
            continue

        sababu, result = _pima(candidate, feats, njia, spec, cfg_risk,
                               starting_balance, miezi)
        ledger.advance(record.candidate_id, BACKTEST, reject_reason=sababu)
        _hesabu(out.by_reason, sababu or "SAWA")

        if progress:
            progress(f"   {record.candidate_id}  {sababu or 'SAWA'}")
        if sababu:
            continue

        out.n_passed_economics += 1
        eco = ECO.measure(result)
        if on_pass is not None:
            on_pass(record.candidate_id, result, eco)

        thamani = result.metrics().get(spec.select_by, float("nan"))
        if thamani == thamani and thamani > bora_thamani:      # NaN-safe
            bora_thamani = thamani
            out.best, out.best_id, out.best_economics = result, record.candidate_id, eco

    return out


def for_calibration(spec: PipelineSpec, *, cfg_risk, seed: int,
                    starting_balance: float | None = None
                    ) -> Callable[[Any], Mapping[str, float]]:
    """`run_pipeline` ya `noise_floor.calibrate()`.

    Inafunga `search()` ILE ILE inayoendesha utafutaji halisi. Kuandika mnyororo
    wa pili hapa kungefanya sakafu ipime kitu kingine — na hakuna kipimo
    kinachoweza kuonyesha tofauti hiyo baadaye.

    Seed ni thabiti kwa makusudi: `calibrate()` inabadilisha **data**, si
    generator. Generator ikibadilika kila replicate, mgawanyo ungechanganya
    kelele ya soko na kelele ya utafutaji, na `max` ingekuwa ya vitu viwili.
    """
    def run_pipeline(surrogate_bars) -> Mapping[str, float]:
        return search(surrogate_bars, spec, cfg_risk=cfg_risk, seed=seed,
                      starting_balance=starting_balance).metrics()

    return run_pipeline


# ===========================================================================
# Ndani
# ===========================================================================


def _pima(candidate, feats, njia, spec: PipelineSpec, cfg_risk,
          starting_balance, miezi=None) -> tuple[str, Any]:
    """Mgombea mmoja: backtest kisha lango la uchumi. Rudisha (sababu, matokeo)."""
    from src.discovery.evaluate import signals as tafuta

    try:
        sig = tafuta(candidate, feats, timeframe=spec.timeframe, day_tz=spec.day_tz)
    except EvaluateError:
        # Feature isiyopo kwenye frame hii — mgombea hakuweza kutathminiwa
        # kabisa. Si kufeli kwake; ni kwamba hakugusa data.
        return NO_FEATURES, None
    if sig.degenerate in DEGENERATE:
        return DEGENERATE_ENTRY, None

    # Spreads hazipelekwi hapa: `run()` inazitoa yenyewe kwenye `features`, kwa
    # dirisha linalofuata bei. Kuzipeleka kama orodha moja kutoka hapa
    # kungezifanya zisibadilike kwa run nzima.
    result = run(candidate, feats, njia[candidate.direction.upper()],
                 cfg_risk=cfg_risk, broker=spec.broker, timeframe=spec.timeframe,
                 day_tz=spec.day_tz, starting_balance=starting_balance,
                 months=miezi)
    eco = ECO.measure(result)
    return ("" if eco.passes else eco.reject_reason), result


def _hesabu(mahali: dict[str, int], jina: str) -> None:
    mahali[jina] = mahali.get(jina, 0) + 1


__all__ = [
    "PipelineError", "PipelineSpec", "SearchResult", "SELECT_BY",
    "DEGENERATE_ENTRY", "NO_FEATURES", "search", "for_calibration",
]
