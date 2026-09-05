"""Mkataba wa kufikia data — DOCTRINE §16.1, R18.

Holdout si labels pekee. Spread ya 2025, volatility ya 2025, mgawanyo wa 2025 —
vikiingia kwenye calibration inayosaidia kuchagua strategy, holdout imeshaathiri
uteuzi hata kama hakuna `future_return` iliyoangaliwa.

Kwa hiyo kizuizi hakiwezi kuwa maandishi. Ni **saini ya function**:

    calibrate_cost(all_ticks)        # HAPANA — inaona kila kitu
    calibrate_cost(window)           # NDIYO  — haiwezi kuona isiyopewa

Moduli hii inatoa `Window` isiyoweza kubadilishwa, `Stage` inayotangaza kusudi
lake, na `clip()` inayoheshimu mpaka. Function inayopokea `Stage` badala ya path
haiwezi kusoma nje ya dirisha lake bila kuandika code inayoonekana ya ajabu.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

# Aina za dirisha. `HOLDOUT` ni ya pekee: inahitaji `open_holdout()` na inatumika
# MARA MOJA kwa maisha ya mradi (R9).
RESEARCH = "research"
HOLDOUT = "holdout"


class WindowError(RuntimeError):
    """Dirisha limevuka mpaka, au holdout imeombwa kinyume na sheria."""


@dataclass(frozen=True)
class Window:
    """Kipande cha muda, mipaka yote miwili IKIWA NDANI (inclusive)."""

    start: date
    end: date
    kind: str = RESEARCH

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise WindowError(f"dirisha limegeuzwa: {self.start} → {self.end}")
        if self.kind not in (RESEARCH, HOLDOUT):
            raise WindowError(f"aina ya dirisha isiyojulikana: {self.kind!r}")

    def contains(self, moment: date | datetime) -> bool:
        day = moment.date() if isinstance(moment, datetime) else moment
        return self.start <= day <= self.end

    def to_json(self) -> dict[str, str]:
        return {"start": self.start.isoformat(), "end": self.end.isoformat(),
                "kind": self.kind}


@dataclass(frozen=True)
class Stage:
    """Hatua inayosoma data, ikitangaza dirisha na kusudi lake (§16.1).

    Ni `frozen` kwa makusudi: hatua ikishatangazwa, haiwezi kupanuliwa katikati
    ya run. Kupanua kunahitaji kutangaza hatua nyingine, ambayo inaonekana
    kwenye ushahidi.
    """

    name: str
    window: Window
    purpose: str

    def to_json(self) -> dict[str, Any]:
        return {"stage": self.name, "purpose": self.purpose, **self.window.to_json()}


# --------------------------------------------------------------------------
# Mipaka inatoka CONFIG, si kwenye code
# --------------------------------------------------------------------------


def _day(value: Any, field: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:  # pragma: no cover — ujumbe ndio wa maana
        raise WindowError(f"`splits.{field}` si tarehe ya ISO: {value!r}") from exc


def holdout_start(cfg) -> date:
    """Siku ya KWANZA ya holdout. Hakuna hatua ya utafiti inayoifikia."""
    return _day(cfg.get("splits.holdout_start"), "holdout_start")


def research_window(cfg) -> Window:
    """`data_start … trainval_end` — kila kitu kabla ya holdout."""
    start = _day(cfg.get("splits.data_start"), "data_start")
    end = _day(cfg.get("splits.trainval_end"), "trainval_end")
    return guard(Window(start, end, RESEARCH), cfg=cfg)


def holdout_window(cfg) -> Window:
    """`holdout_start … data_end`. Kuipata si kuifungua — tazama `open_holdout`."""
    return Window(
        holdout_start(cfg), _day(cfg.get("splits.data_end"), "data_end"), HOLDOUT
    )


# --------------------------------------------------------------------------
# R18 — assertion, si nidhamu
# --------------------------------------------------------------------------


def guard(window: Window, *, cfg=None, boundary: date | None = None) -> Window:
    """Dirisha la utafiti LAZIMA liishie kabla ya holdout kuanza.

    Hii ndiyo assertion ya R18. Inaitwa na kila function inayojenga dirisha la
    utafiti, si na mtumiaji — mtumiaji anayeikumbuka si ulinzi.
    """
    if window.kind == HOLDOUT:
        return window
    if boundary is None and cfg is None:
        raise WindowError("`guard` inahitaji `cfg` au `boundary` — mpaka hauwezi kudhaniwa")
    limit = boundary if boundary is not None else holdout_start(cfg)
    if window.end >= limit:
        raise WindowError(
            f"dirisha la utafiti linaishia {window.end}, ambayo si kabla ya "
            f"holdout ({limit}). DOCTRINE §16.1 / R18: hakuna hatua ya utafiti "
            f"inayofikia holdout."
        )
    return window


def declare(name: str, purpose: str, window: Window, *, cfg=None) -> Stage:
    """Tangaza hatua inayosoma data. Dirisha linakaguliwa hapa, si baadaye."""
    guard(window, cfg=cfg)
    return Stage(name=name, window=window, purpose=purpose)


# --------------------------------------------------------------------------
# Kukata data kwa dirisha
# --------------------------------------------------------------------------


def clip(frame, stage: Stage, column: str = "timestamp"):
    """Rudisha rows za `frame` zilizo NDANI ya dirisha la `stage`, pekee.

    Function inayopokea `Stage` na kuita `clip()` haiwezi kusoma nje ya dirisha
    lake. Ndiyo maana `clip` inachukua `Stage` na si `Window`: kusudi
    linasafiri pamoja na mpaka, na linaingia kwenye ushahidi.
    """
    import pandas as pd

    if column not in frame.columns:
        raise WindowError(f"safu `{column}` haipo — clip() haiwezi kukagua mpaka")
    stamps = pd.to_datetime(frame[column], utc=True)
    lo = pd.Timestamp(stage.window.start, tz="UTC")
    hi = pd.Timestamp(stage.window.end, tz="UTC") + pd.Timedelta(days=1)
    return frame[(stamps >= lo) & (stamps < hi)]


# --------------------------------------------------------------------------
# R9 — holdout inafunguliwa MARA MOJA
# --------------------------------------------------------------------------


def open_holdout(cfg, *, rule_path: Path, ledger: Path) -> Stage:
    """Fungua holdout. Inafanikiwa MARA MOJA kwa maisha ya mradi.

    `rule_path` ni faili la sheria ya uteuzi iliyoandikwa **kabla**. Bila hilo,
    holdout inaweza kuhukumiwa kwa sheria iliyotungwa baada ya kuona jibu — na
    hapo imepotea bure.

    `ledger` inarekodi ufunguzi: tarehe, sha256 ya sheria, na dirisha. Ipo
    tayari → `WindowError`. Ndiyo R9, ikiwa imetekelezwa badala ya kuombwa.
    """
    import hashlib

    if ledger.is_file():
        prior = json.loads(ledger.read_text(encoding="utf-8"))
        raise WindowError(
            f"holdout ilishafunguliwa {prior.get('opened_at')} kwa sheria "
            f"{str(prior.get('rule_sha256'))[:16]}. R9: inafunguliwa MARA MOJA. "
            f"Kuifungua tena kungefanya kila namba iliyofuata iwe ya baada ya ukweli."
        )
    if not rule_path.is_file():
        raise WindowError(
            f"sheria ya uteuzi haipo: {rule_path}. Holdout haifunguliwi bila "
            f"sheria iliyoandikwa KABLA (DOCTRINE §16)."
        )

    payload = rule_path.read_bytes()
    stage = Stage(
        name="holdout",
        window=holdout_window(cfg),
        purpose=f"uthibitisho wa mwisho kwa sheria ya {rule_path.name}",
    )
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        json.dumps(
            {
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "rule_file": str(rule_path),
                "rule_sha256": hashlib.sha256(payload).hexdigest(),
                **stage.to_json(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return stage
