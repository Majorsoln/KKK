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
    provenance: str = ""
    day: str = ""          # `YYYY-MM-DD` ikiwa njia inaitaja; vinginevyo tupu

    @property
    def order(self) -> tuple[str, str]:
        """Ufunguo wa mpangilio: tarehe kwanza, njia kama mrejeshi."""
        return (self.day or "", str(self.path))

    def to_json(self) -> dict[str, Any]:
        return {"path": str(self.path), "symbol": self.symbol, "size_mb": self.size_mb,
                "provenance": self.provenance, "day": self.day}


@dataclass
class Inventory:
    """Kila kitu kilichopo kwenye diski, kabla chochote hakijasomwa."""

    root: Path
    partitions: list[Partition] = field(default_factory=list)
    isiyotambulika: list[Path] = field(default_factory=list)

    @property
    def symbols(self) -> list[str]:
        return sorted({p.symbol for p in self.partitions})

    def provenances(self, symbol: str) -> list[str]:
        return sorted({p.provenance for p in self.partitions if p.symbol == symbol})

    def raw(self, symbol: str) -> list[Partition]:
        """Partitions zote za symbol bila kizuizi cha provenance — kwa kuripoti.

        `of()` inakataa vyanzo viwili kwa sababu haipaswi kupima data
        iliyochanganywa. Ripoti inapaswa **kuionyesha**, kwa hiyo hii ipo.
        """
        return sorted(
            (p for p in self.partitions if p.symbol == symbol), key=lambda p: p.order
        )

    def of(self, symbol: str) -> list[Partition]:
        """Partitions za symbol, **kwa mpangilio wa tarehe**.

        Kupanga kwa njia ya faili kungetosha kwa chanzo kimoja. Chanzo cha pili
        kinapoingia — `provenance=broker` ikianza kurekodi kando ya
        `provenance=aggregator` — njia inaanza na provenance, kwa hiyo mpangilio
        wa maandishi ungeweka feed nzima ya kwanza kabla ya ya pili, na miaka
        ingerudi nyuma katikati ya mtiririko. Tarehe ndiyo ukweli, si njia.
        """
        mine = [p for p in self.partitions if p.symbol == symbol]
        vyanzo = {p.provenance for p in mine}
        if len(vyanzo) > 1:
            raise LoadError(
                f"{symbol}: provenance zaidi ya moja ({sorted(vyanzo)}). Data ya vyanzo "
                f"viwili haichanganywi chini ya symbol moja (data.yaml §2.2). "
                f"Chagua kimoja: discover(root, provenance=...)"
            )
        return sorted(mine, key=lambda p: p.order)

    def render(self) -> str:
        lines = [
            f"L0 · {self.root}",
            f"   faili {len(self.partitions):,} · symbols {len(self.symbols)} · "
            f"GB {sum(p.size_mb for p in self.partitions) / 1024:.2f}",
        ]
        for symbol in self.symbols:
            mine = [p for p in self.partitions if p.symbol == symbol]
            mb = sum(p.size_mb for p in mine)
            vyanzo = self.provenances(symbol)
            siku = sorted(p.day for p in mine if p.day)
            span = f"{siku[0]} -> {siku[-1]}" if siku else "tarehe haiko kwenye njia"
            alama = " CHANZO ZAIDI YA KIMOJA" if len(vyanzo) > 1 else ""
            lines.append(
                f"   {symbol:<8} faili {len(mine):>6,}  MB {mb:>10,.0f}  "
                f"{'/'.join(v or '-' for v in vyanzo):<12} {span}{alama}"
            )
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


def discover(root: Path | str, *, symbols: Sequence[str] | None = None,
             provenance: str | None = None) -> Inventory:
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
        tags = _tags_from_path(path, root)
        if provenance and tags.get("provenance", "") != provenance:
            continue
        inv.partitions.append(
            Partition(path=path, symbol=symbol,
                      size_mb=round(path.stat().st_size / 1e6, 3),
                      provenance=tags.get("provenance", ""), day=_day_from_tags(tags))
        )
    return inv


def _tags_from_path(path: Path, root: Path) -> dict[str, str]:
    """`key=value` zote zilizo kwenye njia — `provenance=`, `year=`, `month=`, `day=`."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    tags: dict[str, str] = {}
    for piece in rel.parts:
        if "=" in piece:
            key, value = piece.split("=", 1)
            tags[key.strip().lower()] = value.strip()
    return tags


def _day_from_tags(tags: dict[str, str]) -> str:
    """`YYYY-MM-DD` kutoka `year=`/`month=`/`day=`, ikiwa zote zipo."""
    try:
        return "{:04d}-{:02d}-{:02d}".format(
            int(tags["year"]), int(tags["month"]), int(tags["day"])
        )
    except (KeyError, ValueError):
        return ""


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
    """Kusanya partitions hadi mwezi ubadilike, kisha toa.

    Mwezi unatoka kwenye **njia** pale `year=`/`month=` zipo — hakuna faili
    inayosomwa ili kujua ni ya lini. Zisipokuwepo, timestamp ya kwanza
    inatumika, na hapo faili inasomwa mara moja tu.
    """
    import pandas as pd

    buffer: list[Any] = []
    label: str | None = None
    lo, hi = str(stage.window.start), str(stage.window.end)

    for part in inventory.of(symbol):
        # Faili iliyo NJE ya dirisha haifunguliwi kabisa. `clip` bado inaendeshwa
        # baadaye — hii inaondoa kusoma tu, si ukaguzi. Kwa dirisha la utafiti
        # linaloishia 2024-03 wakati diski ina hadi 2026-08, ni robo ya data
        # ambayo ingesomwa kisha kutupwa.
        if part.day and not (lo <= part.day <= hi):
            continue

        frame = read_partition(part.path)
        if frame.empty:
            continue
        mwezi = part.day[:7] if part.day else pd.Timestamp(
            frame["timestamp"].iloc[0]
        ).strftime("%Y-%m")
        if label is not None and mwezi != label and buffer:
            yield label, pd.concat(buffer, ignore_index=True)
            buffer = []
        label = mwezi
        buffer.append(frame)

    if buffer and label is not None:
        yield label, pd.concat(buffer, ignore_index=True)
