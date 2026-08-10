"""DF-05 — L1: checks 8 za ubora + `quality_report.json` (spec §3).

Kila partition inapita ukaguzi huu. Ikifeli → **haitumiki kwa training**
(`fail_action: exclude`) na ripoti inaandikwa.

| # | Ukaguzi | FAIL reason |
|---|---|---|
| 1 | coverage | `low_coverage` |
| 2 | monotonicity | `bad_timestamps` |
| 3 | gaps ndani ya session | `intrasession_gap` |
| 4 | OHLC sanity | `ohlc_violation` |
| 5 | quote sanity | `quote_violation` |
| 6 | DST/session | `session_mismatch` |
| 7 | clock drift | `clock_drift` |
| 8 | flat bars | `stale_feed` |

**Ukaguzi wa 4 (OHLC) unafanyika L2, si hapa.** L0 ni ticks (uamuzi wa PD
2026-08-04); ticks hazina OHLC. Bars zinapojengwa (L2) ndipo `low ≤ min(open,
close) ≤ max(open, close) ≤ high` inakuwa na maana, na hapo ndipo inakaguliwa
(`bars.py`). Ripoti inaonyesha wazi ukaguzi upi ulifanyika tabaka lipi.

**Sera ya NaN (§3):** hakuna imputation ya kubuni. Tick isiyokamilika inabeba
`is_valid=false`; haifutwi kimya.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Sababu za FAIL — majina yale yale ya spec §3.
FAIL_LOW_COVERAGE = "low_coverage"
FAIL_BAD_TIMESTAMPS = "bad_timestamps"
FAIL_INTRASESSION_GAP = "intrasession_gap"
FAIL_OHLC = "ohlc_violation"
FAIL_QUOTE = "quote_violation"
FAIL_SESSION_MISMATCH = "session_mismatch"
FAIL_CLOCK_DRIFT = "clock_drift"
FAIL_STALE_FEED = "stale_feed"

# Kina cha kila siku — kikubwa, hakiingii git (ona `.gitignore`).
DETAIL_NAME = "quality_detail.json"

# Muundo NA MAANA ya matokeo. 1 = hukumu kwa faili · 2 = kwa siku (2026-08-08)
# · 3 = siku iliyogawanywa kwenye faili mbili inaunganishwa, na `clock_drift`
# inapima siku badala ya `now()` (2026-08-09).
#
# Ripoti inapigwa CHAPA namba hii, na kila msomaji analinganisha na yake. Bila
# hilo, ripoti ya code ya zamani inaonekana sawa kabisa na ya mpya — kipimo cha
# 2026-08-09 kilipoteza saa nane hasa hivyo: matokeo yalikuwa ya zamani, namba
# zilikuwa halali, na hakuna kilichosema tofauti.
CHECK_SCHEMA_VERSION = 3


def schema_warning(report: dict) -> str:
    """Onyo kama ripoti iliandikwa na code ya zamani kuliko hii. Tupu = sawa."""
    stamped = int(report.get("schema", 1))
    if stamped >= CHECK_SCHEMA_VERSION:
        return ""
    return (
        f"ONYO: ripoti hii ina muundo {stamped}, code ina {CHECK_SCHEMA_VERSION}. "
        "Iliandikwa na toleo la zamani la checks — namba hapa chini SI za code "
        "iliyopo sasa. Endesha `scripts\\audit.bat` tena."
    )


@dataclass
class CheckResult:
    """Ukaguzi mmoja: umepita au la, na **namba** iliyosababisha."""

    name: str
    passed: bool
    reason: str = ""
    value: float | None = None
    threshold: float | None = None
    detail: str = ""

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DayQuality:
    """Matokeo ya SIKU moja — hiki ndicho kipimo cha kutumika/kutotumika.

    Malighafi (`observed_minutes` … `last_ts`) inabebwa pamoja na hukumu kwa
    sababu **siku moja inaweza kuwa imegawanywa kwenye partitions mbili**
    (§3 — Toleo B linakata mwezi saa 05:00 UTC, si usiku wa manane). Kipande
    kimoja hakiwezi kuhukumiwa peke yake, na uwiano uliokwishakokotolewa
    hauwezi kuunganishwa; dakika na mipaka ya muda zinaweza.
    """

    day: str
    checks: list[CheckResult] = field(default_factory=list)
    observed_minutes: int = 0
    expected_minutes: int = 0
    first_ts: str = ""
    last_ts: str = ""

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def fail_reasons(self) -> list[str]:
        return [c.reason for c in self.checks if not c.passed and c.reason]

    def to_json(self) -> dict[str, Any]:
        return {
            "day": self.day,
            "passed": self.passed,
            "fail_reasons": self.fail_reasons,
            "observed_minutes": self.observed_minutes,
            "expected_minutes": self.expected_minutes,
            "first_ts": self.first_ts,
            "last_ts": self.last_ts,
            "checks": [c.to_json() for c in self.checks],
        }


@dataclass
class PartitionQuality:
    """Matokeo ya partition moja, yakiwa yamegawanywa kwa SIKU.

    **Kitengo cha hukumu ni siku, si faili** (PD 2026-08-08). Data yetu ina
    miundo miwili: Toleo A linaandika partition kwa SIKU, Toleo B kwa MWEZI.
    Kuhukumu kwa faili kunafanya vitu viwili vibaya kwa wakati mmoja:

    * partition ya mwezi ina siku ~22, kwa hiyo ina nafasi mara 22 zaidi ya
      kukumbana na siku moja mbaya — inafeli mara nyingi zaidi bila kuwa mbovu
      zaidi (ndiyo maana EURCHF/GBPJPY/XAUUSD zilifeli 12 KWA MWAKA, yaani
      partitions ZAO ZOTE);
    * `fail_action: exclude` ingetupa **mwezi mzima kwa siku moja mbaya** —
      symbols tatu za Toleo B zingetoweka kabisa kwenye training.

    Kwa hiyo checks zote saba zinafanyika kwa kila siku, na kinachotolewa nje
    ni **siku**, si faili.
    """

    partition: str
    symbol: str | None
    provenance: str
    rows: int = 0
    days: list[DayQuality] = field(default_factory=list)
    checks: list[CheckResult] = field(default_factory=list)   # zisizo za siku (mf. faili tupu)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks) and all(d.passed for d in self.days)

    @property
    def failed_days(self) -> list[DayQuality]:
        return [d for d in self.days if not d.passed]

    @property
    def usable_days(self) -> list[str]:
        return [d.day for d in self.days if d.passed]

    @property
    def fail_reasons(self) -> list[str]:
        reasons = [c.reason for c in self.checks if not c.passed and c.reason]
        for day in self.failed_days:
            reasons.extend(day.fail_reasons)
        return reasons

    def to_json(self) -> dict[str, Any]:
        return {
            "partition": self.partition,
            "symbol": self.symbol,
            "provenance": self.provenance,
            "rows": self.rows,
            "passed": self.passed,
            "days_total": len(self.days),
            "days_failed": len(self.failed_days),
            "fail_reasons": sorted(set(self.fail_reasons)),
            "checks": [c.to_json() for c in self.checks],
            "days": [d.to_json() for d in self.days],
        }


# --------------------------------------------------------------------------
# Checks (kila moja ni function huru — inajaribika peke yake)
# --------------------------------------------------------------------------


def check_coverage(rows: int, expected_rows: int, min_coverage: float) -> CheckResult:
    """1 — vipande vilivyopo ÷ vinavyotarajiwa (kalenda ya session, si dhana).

    Spec §3 inasema "**bars** zilizopo ÷ bars zinazotarajiwa". Kwenye tabaka la
    ticks kipimo kinacholingana ni **dakika zenye quote** dhidi ya median ya
    dakika za siku kamili za mwezi ule (`SessionCalendar.expected_minutes`).
    Kuhesabu ticks badala ya dakika kungefanya kizingiti kisiwe na maana: idadi
    ya ticks kwa siku inatofautiana mara mbili-tatu kwa kawaida kabisa, wakati
    dakika zenye quote ni thabiti — na pengo la saa mbili linaonekana mara moja.
    """
    if expected_rows <= 0:
        return CheckResult(
            name="coverage",
            passed=True,
            detail="hakuna matarajio ya kalenda kwa siku hii — haijahukumiwa",
        )
    ratio = rows / expected_rows
    return CheckResult(
        name="coverage",
        passed=ratio >= min_coverage,
        reason="" if ratio >= min_coverage else FAIL_LOW_COVERAGE,
        value=round(ratio, 6),
        threshold=min_coverage,
    )


def check_monotonicity(frame: pd.DataFrame, max_duplicate_frac: float = 0.0) -> CheckResult:
    """2 — timestamps zinapanda; duplicate chache za tick feed zinavumiliwa.

    **Kurudi nyuma hakuvumiliwi kamwe** — hakuna feed inayoweza kuzalisha tick
    ya zamani baada ya mpya; hiyo ni saa iliyoharibika au faili lililochanganywa.

    **Duplicate ni jambo lingine kabisa.** MT5 inatoa timestamps za µs/ms; quotes
    mbili zinaweza kutua ndani ya kipimo kile kile. Kwenye ticks bilioni 3.4
    hilo ni la lazima kitakwimu, si kasoro. Kizuizi ni **sehemu** yake
    (`max_duplicate_frac`), si sifuri kamili.

    Kinachohitajika kwa duplicate si kuzifuta bali **mpangilio thabiti**: labels
    za touch (§5) zinatatuliwa kwa mfuatano wa ticks, kwa hiyo ticks zenye
    timestamp ile ile lazima zibaki kwa mpangilio wa kufika. Ndiyo maana kila
    sort kwenye tabaka hili ni stable (`kind="stable"`/`mergesort`).
    """
    ts = frame["timestamp"]
    backwards = int((ts.diff() < pd.Timedelta(0)).sum())
    duplicates = int(ts.duplicated().sum())
    frac = duplicates / len(frame) if len(frame) else 0.0
    passed = backwards == 0 and frac <= max_duplicate_frac
    return CheckResult(
        name="monotonicity",
        passed=passed,
        reason="" if passed else FAIL_BAD_TIMESTAMPS,
        value=float(backwards + duplicates),
        threshold=0.0,
        detail=(
            f"zilizorudi nyuma={backwards} duplicates={duplicates} "
            f"({frac:.6f} ya ticks; kikomo {max_duplicate_frac})"
        ),
    )


def check_gaps(frame: pd.DataFrame, max_gap_seconds: float) -> CheckResult:
    """3 — pengo kubwa zaidi **ndani ya session** (si wikendi/rollover)."""
    if len(frame) < 2:
        return CheckResult(name="gaps", passed=True, detail="ticks chache mno kupima")
    gaps = frame["timestamp"].diff().dt.total_seconds().dropna()
    largest = float(gaps.max()) if len(gaps) else 0.0
    passed = largest <= max_gap_seconds
    return CheckResult(
        name="gaps",
        passed=passed,
        reason="" if passed else FAIL_INTRASESSION_GAP,
        value=round(largest, 3),
        threshold=max_gap_seconds,
        detail=f"pengo kubwa zaidi = {largest / 60:.1f} min",
    )


def check_quote_sanity(
    frame: pd.DataFrame,
    max_spread_pips: float,
    pip: float,
    outlier_mult: float = 0.0,
) -> CheckResult:
    """5 — quote **isiyowezekana**, si quote pana.

    Kipimo cha kwanza (2026-08-08) kilifelisha siku 835 — na `--reason` ilionyesha
    hakuna `crossed` hata moja. Zilikuwa vitu viwili tofauti kabisa:

    * **GBPJPY siku za sikukuu** (24–28 Desemba, 2 Januari) na siku za msukosuko
      (23 Machi 2020, 26 Novemba 2021). Spread inapanuka kwa sababu liquidity
      inatoweka. Hiyo ni **soko**, si data mbovu.
    * **XAUUSD, hasa 2025–2026.** Kizingiti kilikuwa 200 pips = **$2.00 kamili**.
      Dhahabu ilipokuwa $1,200 hiyo ni 16.7 bps; ilipofika $4,000 ni 5.0 bps —
      kizingiti kile kile kinabana **mara tatu zaidi**. Ndiyo maana miaka ya bei
      ya juu ndiyo iliyofeli zaidi. Kizingiti kilikuwa kinapima bei, si ubora.

    **Na jambo zito kuliko yote:** kutoa nje siku zenye spread pana kunaondoa
    hasa siku ambazo gharama ni kubwa. Model ya gharama ingejifunza soko lisilo
    na sikukuu wala msukosuko, na kila EV ingekuwa ya matumaini — upendeleo ule
    ule ambao `cost_stress_mult` ipo kuupinga. Siku hizo ni **data ya thamani**.

    Kwa hiyo sasa:

    | Hali | Uamuzi |
    |---|---|
    | `bid > ask` (crossed) | FAIL — haiwezekani kimwili |
    | `bid == ask` (zero spread) | FAIL — quote ya `mid` iliyoingizwa mahali pa bid/ask |
    | `bid <= 0` au `ask <= 0` | FAIL |
    | spread pana | FAIL **tu** ikizidi kizingiti kamili **NA** `outlier_mult` × median ya SIKU |

    Sharti la mwisho ni la **na**, si la **au**: siku ya Krismasi ina median pana
    yenyewe, kwa hiyo quote ya pana mara mbili haizidi 50× median na inabaki.
    Tick iliyoharibika (mara 1,000 ya median) inazidi vyote viwili.
    """
    """5 — `bid < ask`, `spread > 0`, `spread ≤ max_plausible`.

    `crossed` (`bid > ask`) na `zero_spread` (`bid == ask`) zinahesabiwa
    **kando**. Zote mbili zinafelisha — quote yoyote kati yao haiwezi kutumika
    kwa RCE (§3.1 inatumia spread kama gharama) wala kwa labels za touch (§5,
    `touch_side: trade_price`). Lakini si kitu kimoja: `crossed` ni feed
    iliyoharibika, `zero_spread` mara nyingi ni bei ya `mid` iliyoingizwa
    mahali pa bid/ask. Ripoti inatofautisha ili suluhisho lisiwe la kubahatisha.
    """
    bid, ask = frame["bid"], frame["ask"]
    crossed = int((bid > ask).sum())
    zero_spread = int((bid == ask).sum())
    non_positive = int((bid <= 0).sum() + (ask <= 0).sum())

    spread_pips = (ask - bid) / pip
    day_median = float(spread_pips.median()) if len(spread_pips) else 0.0
    if outlier_mult > 0 and day_median > 0:
        limit = max(max_spread_pips, outlier_mult * day_median)
    else:
        limit = max_spread_pips
    corrupt = int((spread_pips > limit).sum())

    impossible = crossed + zero_spread + non_positive
    bad = impossible + corrupt
    widest = float(spread_pips.max()) if len(spread_pips) else 0.0
    return CheckResult(
        name="quote_sanity",
        passed=bad == 0,
        reason="" if bad == 0 else FAIL_QUOTE,
        value=float(bad),
        threshold=0.0,
        detail=(
            f"crossed={crossed} zero_spread={zero_spread} bei<=0={non_positive} · "
            f"spread>{limit:.0f}pips={corrupt} "
            f"(median ya siku {day_median:.1f} · pana zaidi {widest:.1f})"
        ),
    )


def check_session_match(
    frame: pd.DataFrame,
    expected_open: datetime | None,
    expected_close: datetime | None,
    tolerance_minutes: float,
    hour_step_ok: bool = False,
) -> CheckResult:
    """6 — mipaka ya session inalingana na kalenda (DST inanaswa hapa).

    `hour_step_ok`: hatua ya **saa moja kamili** ni mabadiliko ya DST, si data
    mbovu. Soko linahamia saa moja mara mbili kwa mwaka; kuziita siku hizo
    `session_mismatch` kungetupa siku 24 nzuri kila mwaka bila sababu (§3:
    "weekend, holiday na rollover si gaps — ni kalenda"). Zinaripotiwa kwenye
    `detail` ili DST ilinganishwe na kalenda ya broker, lakini haziondolewi.
    """
    if expected_open is None or expected_close is None:
        return CheckResult(
            name="session_match", passed=True, detail="kalenda haina siku hii — haijahukumiwa"
        )
    first = frame["timestamp"].min().to_pydatetime()
    last = frame["timestamp"].max().to_pydatetime()
    drift_open = abs((first - expected_open).total_seconds()) / 60.0
    drift_close = abs((last - expected_close).total_seconds()) / 60.0
    worst = max(drift_open, drift_close)

    dst_step = hour_step_ok and abs(worst - 60.0) <= tolerance_minutes
    passed = worst <= tolerance_minutes or dst_step
    detail = f"open ±{drift_open:.1f} min · close ±{drift_close:.1f} min"
    if dst_step:
        detail += " — hatua ya saa 1 (DST), si hitilafu"
    return CheckResult(
        name="session_match",
        passed=passed,
        reason="" if passed else FAIL_SESSION_MISMATCH,
        value=round(worst, 2),
        threshold=tolerance_minutes,
        detail=detail,
    )


def check_clock_drift(
    frame: pd.DataFrame, day: date | None = None, max_future_seconds: float = 60.0
) -> CheckResult:
    """7 — tz ni UTC, na hakuna tick inayotoka nje ya siku yake yenyewe.

    **Kipimo cha kwanza kilikuwa kikilinganisha tick ya mwisho na `now()`.**
    Kwenye kumbukumbu ya kihistoria hiyo haina maana: faili ya 2016 inatoa
    −10.6 miaka, p50 ya ripoti nzima ilikuwa −171,679,765 s, na ukaguzi
    haukuweza kufeli kimuundo (kipimo cha 2026-08-09: 0/34,089). Ukaguzi
    usioweza kufeli si ulinzi — ni jina linalotoa hakikisho la uwongo.

    Kinachopimwa sasa ni kitu ambacho **kinaweza** kuwa kibovu kwenye
    kumbukumbu: tick iliyoandikwa nje ya siku ambayo faili linaidai. Saa ya
    server ikipotoka wakati wa kuandika, au faili likachanganywa, tick
    inatokea upande usiofaa wa usiku wa manane. Bila `day`, tunakagua tz
    pekee — nayo ni ukaguzi halisi (inapita 34,089/34,089, na hiyo ni jibu).
    """
    ts = frame["timestamp"]
    tz = getattr(ts.dtype, "tz", None)
    if tz is None or str(tz) != "UTC":
        return CheckResult(
            name="clock_drift",
            passed=False,
            reason=FAIL_CLOCK_DRIFT,
            detail=f"timestamp si UTC (tz={tz})",
        )
    if day is None:
        return CheckResult(
            name="clock_drift", passed=True, detail="tz ni UTC; hakuna siku ya kulinganisha"
        )
    start = pd.Timestamp(day, tz="UTC")
    outside = float(
        max(
            (start - ts.min()).total_seconds(),
            (ts.max() - (start + pd.Timedelta(days=1))).total_seconds(),
            0.0,
        )
    )
    passed = outside <= max_future_seconds
    return CheckResult(
        name="clock_drift",
        passed=passed,
        reason="" if passed else FAIL_CLOCK_DRIFT,
        value=round(outside, 2),
        threshold=max_future_seconds,
        detail=f"tz UTC · nje ya siku {day.isoformat()} kwa {outside:.1f}s",
    )


def check_stale_feed(frame: pd.DataFrame, max_stale_seconds: float) -> CheckResult:
    """8 — feed iliyoganda, ikipimwa kwa **MUDA**, si kwa idadi ya ticks.

    Spec §3 inasema "mfululizo wa **bars** zenye `high==low`" — kipimo cha bars,
    kinachofanyika L2 (`bars.check_flat_bars`), sawa na ukaguzi wa 4. Kwenye
    ticks, kuhesabu mfululizo wa ticks ni kipimo kisicho na maana: dakika moja
    tulivu ya Asia inaweza kuwa na ticks 40 zenye quote ile ile, na hiyo si feed
    iliyoganda — ni soko tulivu.

    Kinachomaanisha kitu ni **muda**: quote ile ile kwa nusu saa wakati session
    iko wazi ni feed iliyoganda, iwe imeleta ticks 5 au 5,000.
    """
    if len(frame) < 2:
        return CheckResult(name="stale_feed", passed=True, detail="ticks chache mno kupima")
    changed = ((frame["bid"].diff() != 0) | (frame["ask"].diff() != 0)).to_numpy()
    edges = np.append(np.flatnonzero(changed), len(frame) - 1)
    if len(edges) < 2:
        return CheckResult(name="stale_feed", passed=True, detail="quote moja tu")

    stamps = frame["timestamp"].to_numpy()[edges]
    durations = np.diff(stamps) / np.timedelta64(1, "s")
    # Ticks zilizofika ndani ya kila dirisha la ukimya — hii ndiyo inayotofautisha
    # feed ILIYOGANDA (ticks zinakuja, quote haibadiliki) na PENGO (hakuna ticks
    # kabisa). Muda peke yake hauwezi kutofautisha, na suluhisho la kila moja ni
    # tofauti: la kwanza ni tatizo la broker/chanzo, la pili ni data iliyokosekana.
    counts = np.diff(edges)
    worst = int(np.argmax(durations))
    longest = float(durations[worst])
    ticks_inside = int(counts[worst]) - 1
    passed = longest <= max_stale_seconds
    aina = "feed imeganda" if ticks_inside > 0 else "hakuna ticks (pengo)"
    return CheckResult(
        name="stale_feed",
        passed=passed,
        reason="" if passed else FAIL_STALE_FEED,
        value=round(longest, 1),
        threshold=float(max_stale_seconds),
        detail=f"quote ile ile kwa dakika {longest / 60:.1f} · ticks {ticks_inside} · {aina}",
    )


# --------------------------------------------------------------------------
# Kuendesha checks kwa partition
# --------------------------------------------------------------------------


def check_partition(
    path: Path,
    cfg,
    calendar=None,
    expected_minutes: int | None = None,
) -> PartitionQuality:
    """Checks zote za L1 kwa partition moja (spec §3).

    Partition inayovuka siku nyingi inahukumiwa kwa **siku mbaya zaidi** kwenye
    coverage: siku moja iliyokatika ndani ya mwezi haipaswi kufichwa na wastani
    wa mwezi mzima.
    """
    from .manifest import provenance_from_path, symbol_from_path
    from .schema import read_quotes

    path = Path(path)
    symbol = symbol_from_path(path, cfg)
    provenance = provenance_from_path(path, cfg)
    frame = read_quotes(path, cfg)

    result = PartitionQuality(
        partition=str(path),
        symbol=symbol,
        provenance=provenance,
        rows=int(len(frame)),
    )
    if frame.empty:
        result.checks.append(
            CheckResult(
                name="coverage",
                passed=False,
                reason=FAIL_LOW_COVERAGE,
                value=0.0,
                detail="partition haina ticks",
            )
        )
        return result

    max_spread = _max_plausible_spread(cfg, symbol)
    pip = _pip_size(symbol)
    max_gap = _per_symbol(cfg, "quality.max_gap_seconds", symbol, 3600.0)
    max_stale = _per_symbol(cfg, "quality.max_stale_seconds", symbol, 1800.0)
    tolerance = float(cfg.get("quality.session_tolerance_minutes", 15))
    min_coverage = float(cfg.get("quality.min_coverage", 0.995))
    max_dup = float(cfg.get("quality.max_duplicate_frac", 0.0))
    outlier_mult = float(cfg.get("quality.spread_outlier_mult", 0.0))

    for day, group in frame.groupby(frame["timestamp"].dt.date):
        blocked = excluded_reason(cfg, symbol, day)
        if blocked:
            # Uamuzi wa PD unatangulia checks: siku haihukumiwi, inatolewa nje
            # na sababu yake inasafiri nayo kwenye ripoti.
            result.days.append(
                DayQuality(
                    day=day.isoformat(),
                    checks=[
                        CheckResult(
                            name="excluded",
                            passed=False,
                            reason=FAIL_EXCLUDED_BY_PD,
                            detail=blocked,
                        )
                    ],
                )
            )
            continue
        expected = int(
            expected_minutes
            if expected_minutes is not None
            else (calendar.expected_minutes(symbol, day) if calendar is not None else 0)
        )
        observed = int(group["timestamp"].dt.floor("min").nunique())
        coverage = check_coverage(observed, expected, min_coverage)
        if expected > 0:
            coverage.detail = f"dakika {observed}/{expected}"

        bounds = calendar.expected_session(symbol, day) if calendar is not None else None
        session = check_session_match(
            group,
            bounds[0] if bounds else None,
            bounds[1] if bounds else None,
            tolerance,
            hour_step_ok=True,  # DST ni kalenda, si data mbovu (§3)
        )

        result.days.append(
            DayQuality(
                day=day.isoformat(),
                observed_minutes=observed,
                expected_minutes=expected,
                first_ts=group["timestamp"].min().isoformat(),
                last_ts=group["timestamp"].max().isoformat(),
                checks=[
                    coverage,
                    check_monotonicity(group, max_dup),
                    check_gaps(group, max_gap),
                    check_quote_sanity(group, max_spread, pip, outlier_mult),
                    session,
                    check_clock_drift(group, day),
                    check_stale_feed(group, max_stale),
                ],
            )
        )
    return result


def merge_split_days(report: "QualityReport", calendar=None, tolerance_minutes: float = 15.0) -> int:
    """Siku iliyogawanywa kwenye partitions mbili inahukumiwa **kama siku moja**.

    Kipimo cha 2026-08-09 kilionyesha EURCHF ikitoa mistari **miwili kwa tarehe
    ile ile** — tarehe 1 ya karibu kila mwezi, kwa miaka yote. Namba zenyewe
    zinaeleza kilichotokea: kipande kimoja kinafunga dakika **1140** kabla ya
    wakati (yaani saa 04:59), kingine kinafunguka dakika **300** baada ya wakati
    (yaani saa 05:00). `1140 + 300 = 1440` — **siku moja kamili**. Toleo B
    linakata mwezi saa 05:00 UTC, si usiku wa manane, kwa hiyo tarehe 1 iko
    nusu kwenye faili ya mwezi uliopita na nusu kwenye ya mwezi huu.

    Kila nusu, ikihukumiwa peke yake, inaonekana imevunjika: coverage yake ni
    5/24 au 19/24, na mipaka yake ya session iko mbali na kalenda. Pamoja, ni
    siku nzima yenye afya. Kwa `fail_action: exclude` hiyo ilikuwa ikitupa
    **tarehe 1 ya kila mwezi** kwa symbols zote tatu za Toleo B — siku ~380 za
    biashara halisi, si kwa kasoro ya data bali ya kipimo changu.

    Hii ni kasoro ile ile ya "kitengo cha hukumu" iliyorekebishwa 2026-08-08,
    ikiwa upande wa pili: wakati ule faili moja ilikuwa na siku nyingi; hapa
    siku moja iko kwenye faili nyingi.

    Kinachounganishwa ni **malighafi**, si majibu: dakika zinajumlishwa, mipaka
    ya muda inachukua mwanzo wa kwanza na mwisho wa mwisho. Uwiano
    uliokwishakokotolewa hauwezi kujumlishwa. Checks zisizotegemea kalenda
    (`gaps`, `monotonicity`, `quote_sanity`, `stale_feed`) zinabaki za kila
    kipande — kasoro ndani ya nusu moja ni kasoro ya siku nzima.

    Inarudisha idadi ya vipande vilivyounganishwa (vilivyoondolewa).
    """
    # PROVENANCE IKO KWENYE UFUNGUO. Siku inagawanywa kati ya faili mbili za
    # CHANZO KIMOJA (miezi miwili mfululizo). Aggregator na broker wakiwa na
    # siku ile ile — ndivyo ilivyo kwenye siku 5 zinazopishana (§2.2) — hizo ni
    # **vipimo viwili huru vya siku moja**, si nusu mbili. Kuviunganisha
    # kungejumlisha dakika za vyanzo viwili (coverage 2.0), kungefuta kimoja
    # kwenye ripoti, na kungeondoa uwezekano wa kuvilinganisha — ambao ndio
    # msingi wa swali kubwa la R0. Alama yake ilikuwa `coverage max = 2.0084`.
    index: dict[tuple[str, str, str], list[tuple[PartitionQuality, DayQuality]]] = {}
    for part in report.partitions:
        for day in part.days:
            index.setdefault((str(part.symbol), str(part.provenance), day.day), []).append(
                (part, day)
            )

    merged = 0
    for (symbol, _provenance, day_key), pieces in index.items():
        if len(pieces) < 2:
            continue
        # Siku iliyotolewa nje na PD haihukumiwi; kuunganisha kungeirudisha.
        if any(FAIL_EXCLUDED_BY_PD in d.fail_reasons for _, d in pieces):
            for part, dayq in pieces[1:]:
                part.days.remove(dayq)
                merged += 1
            continue

        keeper = pieces[0][1]
        keeper.observed_minutes = sum(d.observed_minutes for _, d in pieces)
        keeper.expected_minutes = max(d.expected_minutes for _, d in pieces)
        stamps = [d.first_ts for _, d in pieces if d.first_ts] + [
            d.last_ts for _, d in pieces if d.last_ts
        ]
        keeper.first_ts = min(stamps) if stamps else ""
        keeper.last_ts = max(stamps) if stamps else ""

        others = [c for _, d in pieces[1:] for c in d.checks]
        keeper.checks = [c for c in keeper.checks if c.name not in ("coverage", "session_match")]
        keeper.checks += [c for c in others if c.name not in ("coverage", "session_match")]

        min_coverage = next(
            (c.threshold for _, d in pieces for c in d.checks
             if c.name == "coverage" and c.threshold is not None),
            0.95,
        )
        keeper.checks.insert(
            0, check_coverage(keeper.observed_minutes, keeper.expected_minutes, float(min_coverage))
        )
        bounds = (
            calendar.expected_session(symbol, date.fromisoformat(day_key))
            if calendar is not None
            else None
        )
        if bounds and keeper.first_ts and keeper.last_ts:
            # `format="ISO8601"` si mapambo. `isoformat()` inaacha sehemu ya
            # sekunde ikiwa ni sifuri, kwa hiyo tick ya `00:00:00.070000` na ya
            # `23:59:54` zinatoa maumbo MAWILI tofauti kwenye orodha ile ile.
            # Bila hii, pandas inakisia umbo kutoka kwa kipengele cha KWANZA na
            # kufeli kwa cha pili. Data ya majaribio ilikuwa na precision moja
            # kila wakati; data halisi haina — na saa nane zilikwenda hapo.
            span = pd.DataFrame(
                {
                    "timestamp": pd.to_datetime(
                        [keeper.first_ts, keeper.last_ts], utc=True, format="ISO8601"
                    )
                }
            )
            keeper.checks.append(
                check_session_match(span, bounds[0], bounds[1], tolerance_minutes, hour_step_ok=True)
            )
        for part, dayq in pieces[1:]:
            part.days.remove(dayq)
            merged += 1

    return merged


FAIL_EXCLUDED_BY_PD = "excluded_by_pd"


def excluded_reason(cfg, symbol: str | None, day) -> str:
    """Siku iliyotolewa nje kwa **UAMUZI ULIOANDIKWA**, si kwa check.

    Checks zinakamata siku moja moja. Zinashindwa pale kasoro ni ya **kipindi**:
    kipimo cha 2026-08-08 kilionyesha EURCHF, GBPJPY na XAUUSD — symbols zote
    tatu za Toleo B, yaani chanzo kimoja — zikipoteza saa 1–2 KWA SIKU mwaka
    2023 pekee, kisha kurudi 2024. Gaps check inakamata asilimia 45 ya siku
    hizo; nyingine zinapita ingawa zina kasoro ile ile ndogo zaidi.

    Kipindi kikijulikana, kukiondoa ni **uamuzi wa PD** — unaoandikwa hapa kwa
    sababu yake, unaingia `config_hash`, na hivyo unakuwa sehemu ya `dataset_id`.
    Mtu yeyote atakayeona namba za baadaye ataona pia kilichotolewa na kwa nini.
    """
    if not symbol:
        return ""
    key = day if isinstance(day, str) else day.isoformat()
    for entry in cfg.get("quality.excluded_ranges", []) or []:
        symbols = [s.upper() for s in (entry.get("symbols") or [])]
        if symbols and symbol.upper() not in symbols:
            continue
        if str(entry.get("from", "")) <= key <= str(entry.get("to", "9999-12-31")):
            return str(entry.get("reason", "haijatajwa"))
    return ""


def _per_symbol(cfg, dotted: str, symbol: str | None, default: float) -> float:
    """Kizingiti kinachoweza kuwa namba moja au ramani ya `symbol -> namba`.

    XAUUSD ina **mapumziko ya kila siku** (dhahabu inafunga ~saa 1 kila siku);
    EURUSD haina. Kizingiti kimoja cha `max_gap_seconds` kinamaanisha ama
    kufelisha kila siku ya dhahabu, ama kutokuona pengo la kweli kwenye FX.
    Kigezo kilekile kinaruhusiwa kuwa `{default: X, XAUUSD: Y}`.
    """
    value = cfg.get(dotted, default)
    if isinstance(value, dict):
        if symbol and symbol.upper() in value:
            return float(value[symbol.upper()])
        return float(value.get("default", default))
    return float(value)


def _worst_by_day(frame: pd.DataFrame, check) -> CheckResult:
    """Endesha ukaguzi kwa **kila siku** ndani ya partition, rudisha mbaya zaidi.

    Partition ya mwezi (Toleo B) ina siku ~22. Kuikagua kama kipande kimoja
    kungetoa majibu mawili ya uwongo: pengo la usiku kati ya sessions
    lingehesabiwa kama `intrasession_gap`, na mipaka ya session ingelinganishwa
    na siku ya kwanza pekee. Weekend/rollover si gaps — ni kalenda (§3).
    """
    results = [check(day, group) for day, group in frame.groupby(frame["timestamp"].dt.date)]
    if not results:
        return CheckResult(name="?", passed=True, detail="hakuna siku ya kupima")
    failed = [r for r in results if not r.passed]
    if failed:
        # Mbaya zaidi = thamani mbali zaidi na kizingiti; sifuri isipopimika.
        return max(failed, key=lambda r: abs(r.value if r.value is not None else 0.0))
    return results[0]


def _max_plausible_spread(cfg, symbol: str | None) -> float:
    limits = cfg.get("quality.max_plausible_spread_pips", {}) or {}
    if symbol and symbol in limits:
        return float(limits[symbol])
    return float(limits.get("default", 50.0))


def _pip_size(symbol: str | None) -> float:
    if not symbol:
        return 0.0001
    upper = symbol.upper()
    if upper.startswith(("XAU", "XAG")) or upper[3:6] == "JPY":
        return 0.01
    return 0.0001


# --------------------------------------------------------------------------
# Ripoti
# --------------------------------------------------------------------------


@dataclass
class QualityReport:
    """`quality_report.json` — deliverable ya R0 (spec §3, RS-03)."""

    partitions: list[PartitionQuality] = field(default_factory=list)
    built_at: str = ""
    config_hash: str = ""
    thresholds: dict[str, Any] = field(default_factory=dict)
    calendar_comparison: dict[str, Any] = field(default_factory=dict)
    split_days_merged: int = 0
    code_rev: str = ""
    coverage_by_symbol: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> list[PartitionQuality]:
        return [p for p in self.partitions if p.passed]

    @property
    def failed(self) -> list[PartitionQuality]:
        return [p for p in self.partitions if not p.passed]

    @property
    def total_days(self) -> int:
        return sum(len(p.days) for p in self.partitions)

    @property
    def failed_days(self) -> int:
        return sum(len(p.failed_days) for p in self.partitions)

    def excluded_days(self) -> dict[str, list[str]]:
        """`symbol -> siku zisizoingia training` — hii ndiyo athari halisi ya §3."""
        out: dict[str, list[str]] = {}
        for part in self.partitions:
            if not part.failed_days:
                continue
            out.setdefault(str(part.symbol), []).extend(d.day for d in part.failed_days)
        return {sym: sorted(set(days)) for sym, days in sorted(out.items())}

    def by_symbol_year(self) -> dict[str, dict[str, int]]:
        """Muhtasari kwa symbol/mwaka, ukihesabu **SIKU** — ndivyo R0 inavyoulizwa."""
        summary: dict[str, dict[str, int]] = {}
        for part in self.partitions:
            year = _year_of(part.partition)
            key = f"{part.symbol}/{year}"
            slot = summary.setdefault(
                key, {"days_passed": 0, "days_failed": 0, "partitions": 0, "rows": 0}
            )
            slot["days_passed"] += len(part.days) - len(part.failed_days)
            slot["days_failed"] += len(part.failed_days)
            slot["partitions"] += 1
            slot["rows"] += part.rows
        return dict(sorted(summary.items()))

    def reason_counts(self) -> dict[str, int]:
        """Sababu zikihesabiwa kwa **SIKU** — kitengo cha kutolewa nje."""
        counts: dict[str, int] = {}
        for part in self.partitions:
            for reason in (c.reason for c in part.checks if not c.passed and c.reason):
                counts[reason] = counts.get(reason, 0) + 1
            for day in part.failed_days:
                for reason in day.fail_reasons:
                    counts[reason] = counts.get(reason, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    def to_json(self) -> dict[str, Any]:
        """**Muhtasari** — ndicho kinachopitiwa na PD na kuingia git.

        Kina cha kila siku (checks 7 x siku ~39,000) ni ~34 MB. Kingeingia git
        na kubadilika kila run — repo ingekua kwa GB bila sababu, kwa sababu git
        inahifadhi kila toleo milele. Kwa hiyo kina kinakwenda `quality_detail.json`
        (haipushwi; ona `.gitignore`), na muhtasari huu unabaki mdogo na wa kudumu.
        Vyote viwili vinaandikwa na `save()` kwa wakati mmoja.
        """
        return {
            # Muundo wa ripoti. 2 = hukumu kwa SIKU; 1 = kwa faili (kabla ya
            # 2026-08-08). Wasomaji wanaikagua badala ya kukisia kwa umbo.
            "schema": CHECK_SCHEMA_VERSION,
            "built_at": self.built_at,
            "config_hash": self.config_hash,
            # Commit iliyozalisha namba hizi. `config_hash` inasema vizingiti
            # vilikuwa vipi; hii inasema CODE ilikuwa ipi. Bila zote mbili,
            # ripoti haiwezi kuzalishwa upya wala kukanushwa.
            "code_rev": self.code_rev,
            "thresholds": self.thresholds,
            "totals": {
                "partitions": len(self.partitions),
                "passed": len(self.passed),
                "failed": len(self.failed),
                "days": self.total_days,
                "days_failed": self.failed_days,
                "days_passed": self.total_days - self.failed_days,
                # Vipande vya siku iliyogawanywa kwenye partitions mbili,
                # vilivyounganishwa kabla ya kuhesabu (§3). Sifuri = hakuna
                # partition inayokatiza siku; namba kubwa = Toleo B lipo.
                "split_day_pieces_merged": self.split_days_merged,
            },
            "fail_reasons": self.reason_counts(),
            "by_symbol_year": self.by_symbol_year(),
            "coverage_by_symbol": self.coverage_by_symbol,
            "excluded_days": self.excluded_days(),
            "calendar_comparison": self.calendar_comparison,
            "detail": DETAIL_NAME,
        }

    def to_detail(self) -> dict[str, Any]:
        """Kina cha kila siku — malighafi ya `quality-stats` na `--what-if`."""
        return {
            "schema": CHECK_SCHEMA_VERSION,
            "built_at": self.built_at,
            "config_hash": self.config_hash,
            "partitions": [p.to_json() for p in self.partitions],
        }

    def save(self, path: Path) -> Path:
        """Andika muhtasari (`path`) na kina (`quality_detail.json`) pamoja."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_json(), indent=2) + "\n", encoding="utf-8")
        (path.parent / DETAIL_NAME).write_text(
            json.dumps(self.to_detail()) + "\n", encoding="utf-8"
        )
        return path

    def render(self) -> str:
        lines = [
            f"L1 quality: siku {self.total_days - self.failed_days}/{self.total_days} "
            f"zimepita ({(self.total_days - self.failed_days) / max(self.total_days, 1):.1%}) "
            f"· partitions {len(self.partitions)}"
        ]
        for reason, count in self.reason_counts().items():
            lines.append(f"  ! {reason}: {count}")
        return "\n".join(lines)


def _year_of(partition: str) -> str:
    """Mwaka wa partition kutoka kwenye njia — miundo yote inayotumika L0.

    Data halisi ina `.../symbol=EURUSD/2026/2026-08-03.parquet` (folda ya mwaka
    si Hive). Kudai `year=` pekee kungefanya ripoti nzima ya R0 iwe `symbol/?`.
    """
    path = Path(partition)
    for part in path.parts:
        if part.startswith("year="):
            return part.split("=", 1)[1]
        if part.startswith("date="):
            return part.split("=", 1)[1][:4]
        if len(part) == 4 and part.isdigit():
            return part
    stem = path.stem
    if len(stem) >= 4 and stem[:4].isdigit():
        return stem[:4]
    return "?"


# --------------------------------------------------------------------------
# Kupanga vizingiti KWA DATA (si kwa kubuni)
# --------------------------------------------------------------------------

# Upande unaofelisha kwa kila ukaguzi: `min` = thamani ndogo ni mbaya
# (coverage); `max` = thamani kubwa ni mbaya (kila kingine).
CHECK_DIRECTION: dict[str, str] = {
    "coverage": "min",
    "monotonicity": "max",
    "gaps": "max",
    "quote_sanity": "max",
    "session_match": "max",
    "clock_drift": "max",
    "stale_feed": "max",
}


def threshold_study(report: dict[str, Any]) -> dict[str, Any]:
    """Mgawanyo wa thamani zilizopimwa + partitions zingefeli kwa kizingiti gani.

    Kizingiti kilichobuniwa mezani ni nadhani; kizingiti kilichotokana na
    mgawanyo wa data ni uamuzi. Kazi hii inasoma `quality_report.json`
    iliyoshaandikwa — **hakuna kusoma parquet tena** — na kuonyesha, kwa kila
    ukaguzi, thamani halisi zilivyotawanyika na ni partitions ngapi zingefeli
    kwa kila kizingiti kinachopendekezwa. PD ndiye anayechagua.
    """
    legacy = int(report.get("schema", 1)) < 2
    stale = schema_warning(report)
    quantiles = [0.001, 0.01, 0.05, 0.10, 0.50, 0.90, 0.95, 0.99, 0.999]
    values: dict[str, list[float]] = {}
    thresholds: dict[str, set[float]] = {}
    offenders: dict[str, dict[str, int]] = {}
    failures: dict[str, int] = {}

    def _units(part: dict[str, Any]):
        """Kila siku ni kipimo kimoja; checks zisizo za siku ni kipimo cha faili."""
        if part.get("days"):
            for day in part["days"]:
                yield day.get("day", "?"), day.get("checks", [])
        else:
            yield "?", part.get("checks", [])

    for part in report.get("partitions", []):
        for _day, checks in _units(part):
          for check in checks:
            name = check.get("name", "?")
            if check.get("value") is None:
                continue
            values.setdefault(name, []).append(float(check["value"]))
            if check.get("threshold") is not None:
                # Vizingiti vinaweza kuwa vya KILA SYMBOL (mf. XAUUSD ina
                # mapumziko ya kila siku). Kuhifadhi kimoja kungeonyesha cha
                # symbol ya mwisho iliyosomwa na kupotosha jedwali zima.
                thresholds.setdefault(name, set()).add(float(check["threshold"]))
            if not check.get("passed", True):
                # Kufeli kunahesabiwa kutoka kwenye JIBU la ukaguzi, si kwa
                # kulinganisha thamani na kizingiti upya. Checks kadhaa zina
                # sheria zaidi ya kizingiti — `session_match` inapitisha hatua
                # ya saa 1 (DST) hata ikizidi uvumilivu. Kuhesabu upya hapa
                # kulikuwa kunaripoti kufeli kusikokuwepo kwenye ripoti yenyewe.
                failures[name] = failures.get(name, 0) + 1
                key = f"{part.get('symbol')}/{_year_of(part.get('partition', ''))}"
                offenders.setdefault(name, {})[key] = offenders.setdefault(name, {}).get(key, 0) + 1

    out: dict[str, Any] = {
        "partitions": len(report.get("partitions", [])),
        "unit": "faili (muundo wa zamani)" if legacy else "siku",
        "legacy": legacy,
        "stale": stale,
        "checks": {},
    }
    for name, series in sorted(values.items()):
        data = pd.Series(series, dtype="float64")
        direction = CHECK_DIRECTION.get(name, "max")
        limits = sorted(thresholds.get(name, ()))
        current = limits[0] if len(limits) == 1 else None
        candidates = (
            [round(float(data.quantile(q)), 4) for q in (0.001, 0.01, 0.05, 0.10)]
            if direction == "min"
            else [round(float(data.quantile(q)), 4) for q in (0.90, 0.95, 0.99, 0.999)]
        )
        shown_limit = (
            str(current)
            if current is not None
            else f"vya symbol: {', '.join(str(v) for v in limits)}"
        )
        failed_now = failures.get(name, 0)
        out["checks"][name] = {
            "direction": direction,
            "measured": len(data),
            "current_threshold": current,
            "thresholds": limits,
            "failing_now": failed_now,
            "quantiles": {f"p{q * 100:g}": round(float(data.quantile(q)), 4) for q in quantiles},
            "min": round(float(data.min()), 4),
            "max": round(float(data.max()), 4),
            # Ukaguzi usiofelisha chochote hauna cha kupangwa upya — chaguo
            # zake zingekuwa kelele (mf. `clock_drift` kwenye data ya kihistoria,
            # ambayo thamani zake ni sekunde milioni nyuma ya sasa).
            "candidates": [
                {
                    "threshold": value,
                    "would_fail": int((data < value).sum())
                    if direction == "min"
                    else int((data > value).sum()),
                }
                for value in sorted(set(candidates))
            ]
            if failed_now
            else [],
            "top_offenders": dict(
                sorted(offenders.get(name, {}).items(), key=lambda kv: -kv[1])[:8]
            ),
        }
    return out


def what_if(report: dict[str, Any], proposals: dict[str, float]) -> dict[str, Any]:
    """Kizingiti kikiwa X, siku ngapi zingefeli — kwa namba, si kwa kukisia.

    Inasoma ripoti iliyoshaandikwa. Inatoa athari ya **kila kizingiti peke yake**
    na ya **vyote pamoja** (siku moja inaweza kufeli kwa sababu mbili; jumla ya
    sababu si sawa na idadi ya siku).
    """
    if int(report.get("schema", 1)) < 2:
        raise ValueError(
            "ripoti hii ni ya muundo wa zamani (hukumu kwa FAILI, si kwa siku). "
            "`--what-if` ingehesabu siku 0 kimya. Endesha `check-l1` tena — cache "
            "imeshajitupa yenyewe kwa sababu muundo umebadilika."
        )
    per_check: dict[str, int] = {name: 0 for name in proposals}
    days_total = 0
    days_failed_now = 0
    days_failed_after = 0

    for part in report.get("partitions", []):
        for day in part.get("days", []):
            days_total += 1
            if not day.get("passed", True):
                days_failed_now += 1
            fails_after = False
            for check in day.get("checks", []):
                name = check.get("name", "?")
                value = check.get("value")
                if name in proposals and value is not None:
                    limit = proposals[name]
                    bad = (
                        value < limit
                        if CHECK_DIRECTION.get(name, "max") == "min"
                        else value > limit
                    )
                    if bad:
                        per_check[name] += 1
                        fails_after = True
                elif not check.get("passed", True):
                    fails_after = True   # ukaguzi usiobadilishwa bado unafelisha
            if fails_after:
                days_failed_after += 1

    return {
        "days": days_total,
        "failing_now": days_failed_now,
        "failing_after": days_failed_after,
        "recovered": days_failed_now - days_failed_after,
        "per_check": per_check,
        "proposals": proposals,
    }


def render_threshold_study(study: dict[str, Any]) -> str:
    lines = [f"partitions zilizopimwa: {study['partitions']} · kitengo: {study.get('unit', 'siku')}"]
    if study.get("legacy"):
        lines.append(
            "  ONYO: ripoti ni ya muundo wa zamani (hukumu kwa FAILI). Partition ya mwezi "
            "inahesabiwa mara moja ingawa ina siku ~22 — namba hapa chini zina upendeleo "
            "dhidi ya Toleo B. Endesha `check-l1` tena."
        )
    elif study.get("stale"):
        lines.append(f"  {study['stale']}")
    lines.append("")
    for name, entry in study["checks"].items():
        arrow = "chini ni mbaya" if entry["direction"] == "min" else "juu ni mbaya"
        lines.append(
            f"{name}  ({arrow}) · kizingiti = "
            f"{entry['current_threshold'] if entry['current_threshold'] is not None else 'vya symbol ' + str(entry.get('thresholds'))} "
            f"→ zinafeli {entry['failing_now']}/{entry['measured']}"
        )
        q = entry["quantiles"]
        lines.append(
            f"   p1={q['p1']} p5={q['p5']} p10={q['p10']} p50={q['p50']} "
            f"p90={q['p90']} p95={q['p95']} p99={q['p99']}  [min={entry['min']} max={entry['max']}]"
        )
        if entry["candidates"]:
            picks = " · ".join(
                f"{c['threshold']}→{c['would_fail']}" for c in entry["candidates"]
            )
            lines.append(f"   chaguo (kizingiti→zitakazofeli): {picks}")
        if entry["top_offenders"]:
            top = " · ".join(f"{k}={v}" for k, v in entry["top_offenders"].items())
            lines.append(f"   zinazoongoza kufeli: {top}")
        lines.append("")
    return "\n".join(lines)


def new_report(cfg) -> QualityReport:
    # Vizingiti VYOTE vya `quality:`, si vilivyochaguliwa. R0 inaulizwa "dhidi ya
    # vizingiti vya data.yaml" — ripoti isiyoonyesha kizingiti kimoja
    # kilichotumika ni ripoti isiyoweza kukaguliwa.
    from .manifest import code_rev

    return QualityReport(
        built_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        config_hash=getattr(cfg, "config_hash", ""),
        code_rev=code_rev(),
        thresholds=dict(cfg.get("quality", {}) or {}),
    )
