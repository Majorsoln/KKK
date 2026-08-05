"""DF-02 — normalization ya Toleo A/B kuwa schema MOJA (spec §2.1).

Kanuni mbili zisizovunjwa hapa:

1. **L0 haibadilishwi.** Normalization inafanyika wakati wa KUSOMA. Hakuna
   function ya module hii inayoandika juu ya partition ya L0.
2. **Hakuna usafi wa kubuni.** Hii ni rename + cast pekee: hakuna kupanga upya
   rows, kuondoa duplicates, kujaza NaN wala kukata outliers — hizo ni kazi ya
   L1 (spec §3, term T1). Normalization inayosafisha kimya inaficha hitilafu
   ambazo checks 8 za L1 zinapaswa kuziona.

Schema ya kawaida (spec §2.1): `timestamp[UTC, µs], bid, ask, bid_vol, ask_vol`.
Ramani ya columns inatoka `config/data.yaml` (`source.schema_variants`) kwa
**mpangilio** — Toleo A ndilo lenye majina ya kawaida, kwa hiyo column ya n ya
toleo lolote inalingana na column ya n ya schema ya kawaida.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .config import DataConfig

CANONICAL_COLUMNS: tuple[str, ...] = ("timestamp", "bid", "ask", "bid_vol", "ask_vol")
CANONICAL_TIMESTAMP_DTYPE = "datetime64[us, UTC]"
PRICE_COLUMNS: tuple[str, ...] = ("bid", "ask")
VOLUME_COLUMNS: tuple[str, ...] = ("bid_vol", "ask_vol")

_PRECISION_UNITS = {"us": "us", "ms": "ms", "ns": "ns", "s": "s"}


class SchemaError(ValueError):
    """Partition haifuati toleo lolote la schema lililotangazwa kwenye config."""


@dataclass(frozen=True)
class VariantSpec:
    """Toleo la schema kama lilivyotangazwa kwenye config (spec §2.1)."""

    name: str
    columns: tuple[str, ...]
    precision: str
    symbols: tuple[str, ...]

    @property
    def column_map(self) -> dict[str, str]:
        """Ramani ya `column ya toleo -> column ya kawaida` (kwa mpangilio)."""
        return dict(zip(self.columns, CANONICAL_COLUMNS))

    @property
    def time_unit(self) -> str:
        return _PRECISION_UNITS[self.precision]


def variant_specs(cfg: DataConfig) -> dict[str, VariantSpec]:
    """Matoleo yote ya schema kutoka config, yakiwa yamethibitishwa dhidi ya spec."""
    specs: dict[str, VariantSpec] = {}
    for name, raw in cfg.schema_variants.items():
        columns = tuple(raw["cols"])
        precision = str(raw.get("precision", "us"))
        if len(columns) != len(CANONICAL_COLUMNS):
            raise SchemaError(
                f"Toleo {name} lina columns {len(columns)}; spec §2.1 inataka "
                f"{len(CANONICAL_COLUMNS)} ({', '.join(CANONICAL_COLUMNS)})"
            )
        if precision not in _PRECISION_UNITS:
            raise SchemaError(f"Toleo {name}: precision `{precision}` haijulikani")
        specs[str(name)] = VariantSpec(
            name=str(name),
            columns=columns,
            precision=precision,
            symbols=tuple(raw.get("symbols") or ()),
        )
    canonical_owner = [s for s in specs.values() if s.columns == CANONICAL_COLUMNS]
    if not canonical_owner:
        raise SchemaError(
            "hakuna toleo lenye majina ya schema ya kawaida "
            f"({', '.join(CANONICAL_COLUMNS)}) — config na spec §2.1 zimetofautiana"
        )
    return specs


def detect_variant(columns: list[str] | tuple[str, ...], cfg: DataConfig) -> VariantSpec:
    """Tambua toleo la schema kwa columns zilizopo kwenye partition.

    Partition inaruhusiwa kubeba columns za ziada (mf. `flags` za MT5) — muhimu
    ni kwamba columns zote za toleo zipo.
    """
    present = set(columns)
    matches = [spec for spec in variant_specs(cfg).values() if set(spec.columns) <= present]
    if not matches:
        raise SchemaError(
            f"columns {sorted(present)} hazilingani na toleo lolote la "
            f"`source.schema_variants` ({', '.join(variant_specs(cfg))})"
        )
    if len(matches) > 1:
        # Chagua toleo lenye ulinganifu kamili (bila columns za ziada) ikiwezekana.
        exact = [spec for spec in matches if set(spec.columns) == present]
        if len(exact) != 1:
            raise SchemaError(
                f"columns {sorted(present)} zinalingana na matoleo zaidi ya moja: "
                f"{[m.name for m in matches]}"
            )
        return exact[0]
    return matches[0]


def variant_for(
    columns: list[str] | tuple[str, ...],
    cfg: DataConfig,
    symbol: str | None = None,
) -> VariantSpec:
    """Toleo la schema kwa partition, likikaguliwa dhidi ya matarajio ya symbol."""
    detected = detect_variant(columns, cfg)
    if symbol is not None:
        expected = cfg.variant_of_symbol(symbol)
        if expected is not None and expected != detected.name:
            raise SchemaError(
                f"{symbol}: config inatarajia Toleo {expected}, partition ina Toleo "
                f"{detected.name} — chanzo cha data kimebadilika, ripoti kwa PD kabla ya kuendelea"
            )
    return detected


def _to_utc_microseconds(series: pd.Series, unit: str) -> pd.Series:
    """Timestamps -> UTC µs. Toleo B (ms) linapanda hadi µs bila kupoteza chochote."""
    if pd.api.types.is_datetime64_any_dtype(series):
        stamps = pd.to_datetime(series)
        if getattr(stamps.dtype, "tz", None) is None:
            stamps = stamps.dt.tz_localize("UTC")
        else:
            stamps = stamps.dt.tz_convert("UTC")
    elif pd.api.types.is_integer_dtype(series) or pd.api.types.is_float_dtype(series):
        # Epoch ghafi: unit inatoka kwenye `precision` ya toleo (spec §2.1).
        stamps = pd.to_datetime(series, unit=unit, utc=True)
    elif pd.api.types.is_string_dtype(series) or series.dtype == object:
        stamps = pd.to_datetime(series, utc=True, format="mixed")
    else:
        raise SchemaError(f"dtype ya timestamp `{series.dtype}` haitambuliki")
    return stamps.astype(CANONICAL_TIMESTAMP_DTYPE)


def normalize_frame(
    frame: pd.DataFrame,
    cfg: DataConfig,
    symbol: str | None = None,
    keep_extra_columns: bool = False,
) -> pd.DataFrame:
    """Toleo A au B -> schema MOJA ya kawaida (spec §2.1).

    Input haibadilishwi (frame ya asili inabaki kama ilivyo).
    """
    spec = variant_for(list(frame.columns), cfg, symbol=symbol)
    extras = [c for c in frame.columns if c not in spec.columns]
    ordered = frame.loc[:, list(spec.columns)].rename(columns=spec.column_map)

    out = pd.DataFrame(index=frame.index)
    out["timestamp"] = _to_utc_microseconds(ordered["timestamp"], spec.time_unit)
    for column in PRICE_COLUMNS + VOLUME_COLUMNS:
        out[column] = pd.to_numeric(ordered[column], errors="coerce").astype("float64")
    if keep_extra_columns and extras:
        for column in extras:
            out[column] = frame[column].to_numpy()
    out.attrs["schema_variant"] = spec.name
    out.attrs["source_precision"] = spec.precision
    if symbol is not None:
        out.attrs["symbol"] = symbol
    return out


def read_partition(
    path: str | Path,
    cfg: DataConfig,
    symbol: str | None = None,
    columns: list[str] | None = None,
    keep_extra_columns: bool = False,
) -> pd.DataFrame:
    """Soma partition ya L0 (toleo lolote) na urudishe schema ya kawaida.

    KUSOMA TU — faili la L0 halibadilishwi (spec §2: immutable).

    Ukaguzi wa "symbol hii inatarajiwa Toleo gani" unahusu **data ya aggregator
    pekee**: orodha ya `source.schema_variants[*].symbols` inaelezea data
    iliyopo (spec §2.1). Partitions tunazoandika wenyewe kutoka feed ya broker
    ziko kwenye schema ya kawaida kwa symbols zote, kwa hiyo ukaguzi huo
    haujitokezi kwao.
    """
    from .manifest import provenance_from_path, symbol_from_path  # kuepuka mzunguko wa import

    frame = pd.read_parquet(path, columns=columns)
    inferred = symbol if symbol is not None else symbol_from_path(Path(path), cfg)
    is_source_data = provenance_from_path(Path(path), cfg) == cfg.provenance_default
    return normalize_frame(
        frame,
        cfg,
        symbol=inferred if is_source_data else None,
        keep_extra_columns=keep_extra_columns,
    )


def partition_metadata(path: str | Path, cfg: DataConfig) -> dict[str, Any]:
    """Muhtasari wa partition kutoka **FOOTER** ya parquet — HAISOMI ticks.

    `describe_partition()` inasoma faili nzima; inafaa kwa ukaguzi wa partition
    MOJA. Kwa hashing ya L0 nzima (partitions 21,438 · ticks bilioni 3.4) kusoma
    kila tick ni **saa kadhaa** kwa taarifa zinazopatikana kwenye footer.

    Hapa tunatumia:
      * `metadata.num_rows` — idadi ya rows bila kudecode data
      * statistics za column ya timestamp (min/max kwa kila row group)

    Statistics zisipopatikana, tunasoma **column ya timestamp pekee** — bado ni
    nafuu mara nyingi kuliko kusoma columns zote.
    """
    import pyarrow.parquet as pq

    pfile = pq.ParquetFile(path)
    meta = pfile.metadata
    names = list(pfile.schema_arrow.names)
    spec = detect_variant(names, cfg)
    ts_column = spec.columns[0]  # column ya kwanza ya kila toleo = timestamp

    # Statistics za parquet zinarudisha INTEGER ya epoch kwa unit ya column
    # (si datetime). Bila unit, `pd.Timestamp(int)` inasoma kama nanoseconds →
    # tarehe za 1970. Unit halisi inatoka kwenye arrow schema ya faili.
    ts_type = pfile.schema_arrow.field(ts_column).type
    ts_unit = getattr(ts_type, "unit", None) or spec.time_unit

    first_ts: Any = None
    last_ts: Any = None
    try:
        col_index = meta.schema.names.index(ts_column)
        for rg in range(meta.num_row_groups):
            stats = meta.row_group(rg).column(col_index).statistics
            if stats is None or not stats.has_min_max:
                first_ts = last_ts = None
                break
            lo, hi = stats.min, stats.max
            first_ts = lo if first_ts is None or lo < first_ts else first_ts
            last_ts = hi if last_ts is None or hi > last_ts else last_ts
    except (ValueError, AttributeError):
        first_ts = last_ts = None

    if meta.num_rows and first_ts is None:  # statistics hazipo — soma column MOJA
        series = pq.read_table(path, columns=[ts_column]).column(0).to_pandas()
        if not series.empty:
            first_ts, last_ts = series.min(), series.max()

    def _iso(value: Any) -> str | None:
        if value is None:
            return None
        stamp = pd.Timestamp(value, unit=ts_unit) if isinstance(value, int) else pd.Timestamp(value)
        stamp = stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")
        return stamp.isoformat()

    return {
        "path": str(path),
        "schema_variant": spec.name,
        "rows": int(meta.num_rows),
        "columns": list(CANONICAL_COLUMNS),
        "first_ts": _iso(first_ts),
        "last_ts": _iso(last_ts),
    }


def describe_partition(path: str | Path, cfg: DataConfig) -> dict[str, Any]:
    """Muhtasari wa partition baada ya normalization (kwa ripoti za T0/R0)."""
    frame = read_partition(path, cfg)
    if frame.empty:
        span: dict[str, Any] = {"first_ts": None, "last_ts": None}
    else:
        span = {
            "first_ts": frame["timestamp"].min().isoformat(),
            "last_ts": frame["timestamp"].max().isoformat(),
        }
    return {
        "path": str(path),
        "schema_variant": frame.attrs.get("schema_variant"),
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        **span,
    }
