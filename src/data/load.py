"""Kupakia L0 — partitions za diski hadi frame ya ticks (DOCTRINE §4.1, R18).

Moduli hii **haijui** muundo wa folda zako. Inautafuta.

Sababu si uvivu: muundo uliodhaniwa unashindwa kimya. Njia inayoisha kwa
`symbol=EURUSD/` ikiwa halisi ni `EURUSD/2016/`, glob inarudisha faili sifuri,
na calibration inaripoti "cells 0" badala ya kosa. Kwa hiyo `discover()` inatembea
mti wa faili na kutambua symbol kutoka **njia yenyewe**, na inachapisha
ilichokiona kabla ya chochote kingine kutokea.

---

**Schema mbili, frame moja (§4.1, data.yaml `source.schema_variants`)**

```
Toleo A : timestamp · bid · ask · bid_vol · ask_vol       (µs)
Toleo B : ts        · bid · ask · bid_volume · ask_volume (ms)
```

Zinabadilishwa kuwa schema MOJA hapa. Kila mahali pengine kwenye injini kuna
`timestamp`, `bid`, `ask` — na hakuna sehemu inayohitaji kujua toleo lipi
lilitoka wapi.

**Mpaka unatangazwa, hausahauliki.** `load_ticks` inadai `Stage` — si tarehe
mbili. Kwa hiyo hakuna njia ya kuiita bila kutangaza dirisha, na `clip` (R18)
inatumika kabla ya row yoyote kutoka.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence

from .quality import QualityError, QualityReport, check_ticks
from .window import Stage, clip

# Majina yanayowezekana ya safu ya muda, kwa mpangilio wa kutafutwa.
TIME_COLUMNS = ("timestamp", "ts", "time", "datetime", "date_time")
BID_COLUMNS = ("bid",)
ASK_COLUMNS = ("ask",)
VOLUME_ALIASES = {
    "bid_volume": "bid_vol", "ask_volume": "ask_vol",
    "bidvolume": "bid_vol", "askvolume": "ask_vol",
    "volume_bid": "bid_vol", "volume_ask": "ask_vol",
}

SUFFIXES = (".parquet", ".pq")

# Sarafu zinazotambulika. Orodha ipo kwa sababu **umbo pekee halitoshi**:
# folda iitwayo `symbol=EURUSD` ina neno `SYMBOL` — herufi sita kubwa, sawa
# kabisa na umbo la pair. Bila ukaguzi wa sarafu, kila partition ingewekwa
# chini ya symbol iitwayo "SYMBOL", na calibration ingeripoti cell moja kubwa
# yenye pairs zote ndani yake. Si kosa linaloonekana; ni jedwali lisilo sahihi.
CURRENCIES = frozenset({
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
    "XAU", "XAG", "SEK", "NOK", "DKK", "PLN", "HUF", "CZK",
    "TRY", "ZAR", "MXN", "SGD", "HKD", "CNH", "RUB",
})

_SIX = re.compile(r"[A-Z]{6}")


class LoadError(RuntimeError):
    """Data ya L0 haiwezi kupakiwa kama ilivyoombwa."""


@dataclass(frozen=True)
class Partition:
    """Faili moja ya L0, pamoja na kile kinachojulikana kuihusu kutoka njia yake."""

    path: Path
    symbol: str
    size_mb: float

    def to_json(self) -> dict[str, Any]:
        return {"path": str(self.path), "symbol": self.symbol, "size_mb": self.size_mb}


@dataclass
class Inventory:
    """Kila kitu kilichopo kwenye diski, kabla chochote hakijasomwa."""

    root: Path
    partitions: list[Partition] = field(default_factory=list)
    isiyotambulika: list[Path] = field(default_factory=list)

    @property
    def symbols(self) -> list[str]:
        return sorted({p.symbol for p in self.partitions})

    def of(self, symbol: str) -> list[Partition]:
        return sorted(
            (p for p in self.partitions if p.symbol == symbol), key=lambda p: str(p.path)
        )

    def render(self) -> str:
        lines = [
            f"L0 · {self.root}",
            f"   faili {len(self.partitions):,} · symbols {len(self.symbols)} · "
            f"GB {sum(p.size_mb for p in self.partitions) / 1024:.2f}",
        ]
        for symbol in self.symbols:
            chunks = self.of(symbol)
            mb = sum(p.size_mb for p in chunks)
            lines.append(f"   {symbol:<8} faili {len(chunks):>6,}  MB {mb:>10,.0f}")
        if self.isiyotambulika:
            lines.append(f"   HAIJATAMBULIKA: faili {len(self.isiyotambulika):,}")
            for path in self.isiyotambulika[:5]:
                lines.append(f"      {path}")
        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "symbols": self.symbols,
            "n_partitions": len(self.partitions),
            "unrecognised": [str(p) for p in self.isiyotambulika[:50]],
        }


def discover(root: Path | str, *, symbols: Sequence[str] | None = None) -> Inventory:
    """Tembea mti wa faili, tambua symbol kutoka njia. Hakuna muundo unaodhaniwa."""
    root = Path(root)
    if not root.exists():
        raise LoadError(f"root haipo: {root}")

    inv = Inventory(root=root)
    ruhusa = {s.upper() for s in symbols} if symbols else None

    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in SUFFIXES or not path.is_file():
            continue
        symbol = _symbol_from_path(path, root)
        if symbol is None:
            inv.isiyotambulika.append(path)
            continue
        if ruhusa and symbol not in ruhusa:
            continue
        inv.partitions.append(
            Partition(path=path, symbol=symbol,
                      size_mb=round(path.stat().st_size / 1e6, 3))
        )
    return inv


def _symbol_from_path(path: Path, root: Path) -> str | None:
    """Symbol inatoka kwenye njia — folda au jina la faili, chochote kilichopo.

    Kwa `key=value`, thamani pekee ndiyo inayoangaliwa: `symbol=EURUSD` ni
    `EURUSD`, si `SYMBOL`. Na kila mgombea anathibitishwa kuwa **pair halisi**
    kwa kuangalia sarafu zake mbili — hakuna kinachopita kwa umbo pekee.
    """
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    for piece in reversed(rel.parts):
        candidate = piece.split("=", 1)[1] if "=" in piece else piece
        for found in _SIX.finditer(candidate.upper()):
            pair = found.group(0)
            if pair[:3] in CURRENCIES and pair[3:] in CURRENCIES:
                return pair
    return None


def read_partition(path: Path, *, columns: Sequence[str] | None = None):
    """Soma faili MOJA na uinormalize kuwa schema ya §4.1."""
    import pandas as pd

    try:
        frame = pd.read_parquet(path, columns=list(columns) if columns else None)
    except Exception as exc:  # pragma: no cover - inategemea faili halisi
        raise LoadError(f"{path}: haisomeki ({exc})") from exc
    return normalize(frame, source=str(path))


def normalize(frame, *, source: str = ""):
    """Toleo A au B → schema MOJA: `timestamp` (UTC), `bid`, `ask`, volumes.

    Muda unahifadhiwa **UTC** (`data.yaml: timezone.storage_tz`). Faili isiyo na
    tz inachukuliwa kuwa tayari UTC — ndivyo L0 inavyoandikwa; ikiwa si hivyo,
    `quality.timezone` itaikamata, si hapa.
    """
    import pandas as pd

    out = frame.rename(columns={k: v for k, v in VOLUME_ALIASES.items() if k in frame.columns})

    time_col = next((c for c in TIME_COLUMNS if c in out.columns), None)
    if time_col is None:
        raise LoadError(
            f"{source}: hakuna safu ya muda kati ya {TIME_COLUMNS} "
            f"(zilizopo: {list(out.columns)})"
        )
    if time_col != "timestamp":
        out = out.rename(columns={time_col: "timestamp"})

    for name, options in (("bid", BID_COLUMNS), ("ask", ASK_COLUMNS)):
        if name not in out.columns:
            alt = next((c for c in options if c in out.columns), None)
            if alt is None:
                raise LoadError(
                    f"{source}: hakuna safu `{name}` — §4.1 inadai bid NA ask "
                    f"(zilizopo: {list(out.columns)})"
                )
            out = out.rename(columns={alt: name})

    stamps = pd.to_datetime(out["timestamp"], utc=True)
    out = out.assign(timestamp=stamps, bid=out["bid"].astype(float),
                     ask=out["ask"].astype(float))

    ordered = ["timestamp", "bid", "ask"]
    ordered += [c for c in ("bid_vol", "ask_vol") if c in out.columns]
    ordered += [c for c in out.columns if c not in ordered]
    return out[ordered]


def load_ticks(inventory: Inventory, symbol: str, stage: Stage, *,
               max_spread_pips: float | None = None, pip: float | None = None,
               strict: bool = True) -> tuple[Any, QualityReport]:
    """Ticks zote za `symbol` ndani ya dirisha la `stage`, zikiwa zimekaguliwa.

    Hatua ni **za mpangilio huu kwa makusudi**: soma → panga → kata → kagua.
    Kukagua kabla ya kukata kungeripoti kasoro za data ambayo hatua hii
    haitakayoiona kamwe; kukata kabla ya kupanga kungeacha rows za mpakani
    kutoka faili zisizopangwa.
    """
    import pandas as pd

    chunks = [read_partition(p.path) for p in inventory.of(symbol)]
    if not chunks:
        raise LoadError(f"{symbol}: hakuna partition kwenye {inventory.root}")

    frame = pd.concat(chunks, ignore_index=True)
    frame = frame.sort_values("timestamp", kind="stable").reset_index(drop=True)
    frame = clip(frame, stage).reset_index(drop=True)
    frame.attrs["symbol"] = symbol

    report = check_ticks(frame, stage, max_spread_pips=max_spread_pips, pip=pip)
    if strict and not report.passed:
        raise QualityError(f"{symbol}: ukaguzi wa §4.3 umeshindwa\n{report.render()}")
    return frame, report


def iter_months(inventory: Inventory, symbol: str, stage: Stage, *,
                max_spread_pips: float | None = None, pip: float | None = None,
                strict: bool = False) -> Iterator[tuple[Any, Any, QualityReport]]:
    """Toa ticks **mwezi kwa mwezi** — kwa data isiyotoshea kwenye kumbukumbu.

    Miaka 10 ya ticks za symbol moja ni rows milioni mia kadhaa. Kuzipakia zote
    kwa mara moja kunasimamisha mashine, na mashine iliyosimama haitoi jibu
    lolote — wala si la kukosea.

    Gharama ya kupasua ni **bar ya mwisho ya kila mwezi** (`bars.build` haitoi
    bar isiyofungwa). Ni bar 1 kati ya ~500 kwa H1: haibadilishi mgawanyo,
    na inaonekana hapa badala ya kufichwa.
    """
    import pandas as pd

    for path, chunk in _grouped_by_month(inventory, symbol, stage):
        chunk = chunk.sort_values("timestamp", kind="stable").reset_index(drop=True)
        chunk = clip(chunk, stage).reset_index(drop=True)
        if chunk.empty:
            continue
        chunk.attrs["symbol"] = symbol
        report = check_ticks(chunk, stage, max_spread_pips=max_spread_pips, pip=pip)
        if strict and not report.passed:
            raise QualityError(f"{symbol} {path}: ukaguzi wa §4.3 umeshindwa\n{report.render()}")
        yield path, chunk, report


def _grouped_by_month(inventory: Inventory, symbol: str, stage: Stage):
    """Kusanya partitions hadi mwezi ubadilike, kisha toa."""
    import pandas as pd

    buffer: list[Any] = []
    label: str | None = None

    for part in inventory.of(symbol):
        frame = read_partition(part.path)
        if frame.empty:
            continue
        mwezi = pd.Timestamp(frame["timestamp"].iloc[0]).strftime("%Y-%m")
        if label is not None and mwezi != label and buffer:
            yield label, pd.concat(buffer, ignore_index=True)
            buffer = []
        label = mwezi
        buffer.append(frame)

    if buffer and label is not None:
        yield label, pd.concat(buffer, ignore_index=True)
