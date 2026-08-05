"""DF-01/DF-03 — manifest ya L0: SHA256 kwa kila partition + provenance.

Manifest ndiyo rekodi rasmi ya L0: kila partition ina hash, provenance
(`aggregator` au `broker`, spec §2.2), toleo la schema, na wakati ilipohashiwa.
Sheria ya immutability inatekelezwa hapa:

* partition MPYA → inaongezwa (append-only);
* partition ILIYOPO yenye hash ile ile → sawa;
* partition ILIYOPO yenye hash TOFAUTI → **UKIUKAJI**. Haiandikwi kimya;
  inaripotiwa na `verify` inarudisha FAIL (lango la CI).
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .config import DataConfig
from .hashing import sha256_file

MANIFEST_VERSION = 1
PARTITION_SUFFIXES = (".parquet", ".pq")

PROVENANCE_BROKER = "broker"
PROVENANCE_AGGREGATOR = "aggregator"


class ManifestError(RuntimeError):
    """Manifest imeharibika au inaombwa kufanya jambo linalovunja DF-01."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def code_rev(root: Path | None = None) -> str:
    """git sha ya repo (spec §8: `code_rev`). Isipopatikana → "unknown"."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root or Path(__file__).resolve().parents[2]),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


# --------------------------------------------------------------------------
# Kusoma muundo wa njia ya partition
# --------------------------------------------------------------------------


def _hive_pairs(relpath: Path) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for part in relpath.parts:
        if "=" in part:
            key, _, value = part.partition("=")
            pairs[key.strip().lower()] = value.strip()
    return pairs


def symbol_from_path(path: Path, cfg: DataConfig, root: Path | None = None) -> str | None:
    """Symbol ya partition kutoka kwenye njia (Hive `symbol=XXX` au folda ya kwanza)."""
    try:
        relpath = path.relative_to(root) if root is not None else path
    except ValueError:
        relpath = path
    pairs = _hive_pairs(relpath)
    if "symbol" in pairs:
        return pairs["symbol"]
    known = set(cfg.symbols)
    for part in relpath.parts:
        if part in known:
            return part
    stem_head = relpath.stem.split("_")[0].split("-")[0].upper()
    return stem_head if stem_head in known else None


def provenance_from_path(path: Path, cfg: DataConfig, root: Path | None = None) -> str:
    """Provenance ya partition (spec §2.2). Isipotajwa kwenye njia → default ya config."""
    try:
        relpath = path.relative_to(root) if root is not None else path
    except ValueError:
        relpath = path
    pairs = _hive_pairs(relpath)
    if "provenance" in pairs:
        return pairs["provenance"]
    return cfg.provenance_default


def iter_partitions(root: Path, suffixes: Iterable[str] = PARTITION_SUFFIXES) -> list[Path]:
    """Partitions zote za L0 chini ya `root`, kwa mpangilio thabiti."""
    allowed = {s.lower() for s in suffixes}
    found = [
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in allowed and not p.name.startswith(".")
    ]
    return sorted(found)


# --------------------------------------------------------------------------
# Entries + manifest
# --------------------------------------------------------------------------


@dataclass
class PartitionEntry:
    """Mstari mmoja wa manifest = partition moja ya L0."""

    partition: str
    symbol: str | None
    provenance: str
    sha256: str
    size_bytes: int
    hashed_at: str
    schema_variant: str | None = None
    rows: int | None = None
    first_ts: str | None = None
    last_ts: str | None = None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "PartitionEntry":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in payload.items() if k in known})


@dataclass
class VerifyResult:
    """Matokeo ya ukaguzi wa hashes (lango la CI kwa DF-01)."""

    unchanged: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Kupita = hakuna partition iliyobadilika wala iliyopotea."""
        return not self.changed and not self.missing

    def summary(self) -> str:
        return (
            f"unchanged={len(self.unchanged)} changed={len(self.changed)} "
            f"missing={len(self.missing)} untracked={len(self.untracked)}"
        )


class L0Manifest:
    """Manifest ya partitions za L0 (spec §2 + §8)."""

    def __init__(
        self,
        path: Path,
        l0_root: Path,
        config_hash: str,
        entries: dict[str, PartitionEntry] | None = None,
        mutation_log: list[dict[str, Any]] | None = None,
        created_at: str | None = None,
    ) -> None:
        self.path = Path(path)
        self.l0_root = Path(l0_root)
        self.config_hash = config_hash
        self.entries: dict[str, PartitionEntry] = entries or {}
        self.mutation_log: list[dict[str, Any]] = mutation_log or []
        self.created_at = created_at or _iso(utcnow())

    # ---------- I/O ----------

    @classmethod
    def load(cls, path: str | Path) -> "L0Manifest":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("manifest_version") != MANIFEST_VERSION:
            raise ManifestError(
                f"manifest_version {payload.get('manifest_version')} haitambuliki "
                f"(inayotarajiwa: {MANIFEST_VERSION})"
            )
        entries = {
            key: PartitionEntry.from_json(value)
            for key, value in payload.get("partitions", {}).items()
        }
        return cls(
            path=Path(path),
            l0_root=Path(payload["l0_root"]),
            config_hash=payload.get("config_hash", ""),
            entries=entries,
            mutation_log=payload.get("mutation_log", []),
            created_at=payload.get("created_at"),
        )

    @classmethod
    def load_or_new(cls, path: str | Path, l0_root: Path, config_hash: str) -> "L0Manifest":
        path = Path(path)
        if path.is_file():
            manifest = cls.load(path)
            manifest.config_hash = config_hash
            return manifest
        return cls(path=path, l0_root=l0_root, config_hash=config_hash)

    def save(self) -> Path:
        """Andika manifest kwa njia ya atomiki (tmp + replace)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "manifest_version": MANIFEST_VERSION,
            "l0_root": str(self.l0_root),
            "config_hash": self.config_hash,
            "code_rev": code_rev(),
            "created_at": self.created_at,
            "updated_at": _iso(utcnow()),
            "partition_count": len(self.entries),
            "provenance_counts": self.provenance_counts(),
            "partitions": {key: entry.to_json() for key, entry in sorted(self.entries.items())},
            "mutation_log": self.mutation_log,
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)
        return self.path

    # ---------- maswali ----------

    def key_for(self, partition_path: Path) -> str:
        path = Path(partition_path)
        try:
            return path.resolve().relative_to(self.l0_root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()

    def provenance_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self.entries.values():
            counts[entry.provenance] = counts.get(entry.provenance, 0) + 1
        return dict(sorted(counts.items()))

    def entries_by_provenance(self, provenance: str) -> list[PartitionEntry]:
        return [e for e in self.entries.values() if e.provenance == provenance]

    def symbols_recorded(self, provenance: str | None = None) -> list[str]:
        symbols = {
            e.symbol
            for e in self.entries.values()
            if e.symbol and (provenance is None or e.provenance == provenance)
        }
        return sorted(symbols)

    # ---------- kuandika ----------

    def record(
        self,
        partition_path: Path,
        cfg: DataConfig,
        provenance: str | None = None,
        schema_variant: str | None = None,
        rows: int | None = None,
        first_ts: str | None = None,
        last_ts: str | None = None,
        allow_mutation: bool = False,
        mutation_reason: str | None = None,
    ) -> PartitionEntry:
        """Ongeza/thibitisha partition. Hash ikibadilika → ManifestError (DF-01)."""
        path = Path(partition_path)
        key = self.key_for(path)
        digest = sha256_file(path)
        size = path.stat().st_size
        existing = self.entries.get(key)
        if existing is not None and existing.sha256 != digest:
            if not allow_mutation:
                raise ManifestError(
                    f"UKIUKAJI WA DF-01: partition `{key}` imebadilika baada ya kuhashiwa "
                    f"({existing.sha256} -> {digest}). L0 ni immutable — badiliko halali ni "
                    "partition MPYA, si kuandika juu ya iliyopo."
                )
            if not mutation_reason:
                raise ManifestError("kuandika juu ya hash iliyopo kunahitaji sababu iliyoandikwa")
            self.mutation_log.append(
                {
                    "partition": key,
                    "old_sha256": existing.sha256,
                    "new_sha256": digest,
                    "reason": mutation_reason,
                    "at": _iso(utcnow()),
                }
            )
        entry = PartitionEntry(
            partition=key,
            symbol=symbol_from_path(path, cfg, self.l0_root),
            provenance=provenance or provenance_from_path(path, cfg, self.l0_root),
            sha256=digest,
            size_bytes=size,
            hashed_at=_iso(utcnow()),
            schema_variant=schema_variant
            if schema_variant is not None
            else (existing.schema_variant if existing else None),
            rows=rows if rows is not None else (existing.rows if existing else None),
            first_ts=first_ts if first_ts is not None else (existing.first_ts if existing else None),
            last_ts=last_ts if last_ts is not None else (existing.last_ts if existing else None),
        )
        self.entries[key] = entry
        return entry

    # ---------- ukaguzi ----------

    def verify(
        self,
        root: Path | None = None,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> VerifyResult:
        """Hesabu **upya** hashes zote na ulinganishe na manifest (lango la CI).

        Tofauti na `hash_l0_tree(resume=True)`, hapa hakuna kuruka: kila
        partition inasomwa na kuhashiwa. Ndiyo maana lango hili linagundua
        mabadiliko ya kimya — na ndiyo maana linachukua muda wa kusoma L0 nzima.
        """
        root = Path(root or self.l0_root)
        result = VerifyResult()
        on_disk = {self.key_for(p): p for p in iter_partitions(root)}
        total = len(self.entries)
        for done, (key, entry) in enumerate(self.entries.items(), start=1):
            path = on_disk.pop(key, None)
            if path is None:
                result.missing.append(key)
            elif sha256_file(path) == entry.sha256:
                result.unchanged.append(key)
            else:
                result.changed.append(key)
            if on_progress:
                on_progress(done, total, key)
        result.untracked.extend(sorted(on_disk))
        return result


# --------------------------------------------------------------------------
# Kuhash L0 nzima (kazi ya 3 ya T0)
# --------------------------------------------------------------------------


@dataclass
class HashRunResult:
    """Muhtasari wa kuhash L0 nzima."""

    scanned: int = 0
    added: int = 0
    confirmed: int = 0
    skipped: int = 0
    mutated: list[str] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)
    manifest_path: str = ""

    @property
    def ok(self) -> bool:
        return not self.mutated and not self.failed


def hash_l0_tree(
    cfg: DataConfig,
    l0_root: Path | None = None,
    manifest_path: Path | None = None,
    read_metadata: bool = True,
    allow_mutation: bool = False,
    mutation_reason: str | None = None,
    resume: bool = True,
    save_every: int = 250,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> tuple[L0Manifest, HashRunResult]:
    """Hash partitions ZOTE za L0 zilizopo + rekodi manifest (DF-01, DF-03).

    `read_metadata=True` inasoma pia rows/first_ts/last_ts/toleo la schema kwa
    kila partition — kutoka **footer ya parquet**, si kwa kusoma ticks
    (`schema.partition_metadata`).

    `resume=True`: partition iliyo kwenye manifest yenye ukubwa na mtime
    visivyobadilika **hairudiwi kuhashiwa**. L0 ni immutable (§2), kwa hiyo
    run ya pili baada ya kukatika inaendelea pale ilipoishia badala ya kuanza
    upya. `verify-l0` ndiyo inayohesabu upya hashes zote (lango la CI).

    `save_every`: manifest inahifadhiwa kila partitions ngapi — run ndefu
    ikikatika, kazi iliyofanyika haipotei.
    """
    root = Path(l0_root or cfg.l0_root)
    mpath = Path(manifest_path or cfg.l0_manifest_path)
    if not root.is_dir():
        raise ManifestError(f"L0 root haipo: {root}")
    manifest = L0Manifest.load_or_new(mpath, root, cfg.config_hash)
    result = HashRunResult(manifest_path=str(mpath))

    partitions = list(iter_partitions(root))
    total = len(partitions)
    since_save = 0

    for path in partitions:
        result.scanned += 1
        key = manifest.key_for(path)
        existing = manifest.entries.get(key)
        was_known = existing is not None

        if resume and existing is not None and existing.size_bytes == path.stat().st_size:
            # Ukubwa haujabadilika na L0 ni immutable — hakuna haja ya kusoma tena.
            result.confirmed += 1
            result.skipped += 1
            if on_progress:
                on_progress(result.scanned, total, key)
            continue

        meta: dict[str, Any] = {}
        if read_metadata:
            try:
                from .schema import partition_metadata  # import wa ndani: pyarrow ni nzito

                described = partition_metadata(path, cfg)
                meta = {
                    "schema_variant": described["schema_variant"],
                    "rows": described["rows"],
                    "first_ts": described["first_ts"],
                    "last_ts": described["last_ts"],
                }
            except Exception as exc:  # partition mbovu haizuii hashing ya nyingine
                result.failed.append({"partition": key, "error": f"{type(exc).__name__}: {exc}"})
        try:
            manifest.record(
                path,
                cfg,
                allow_mutation=allow_mutation,
                mutation_reason=mutation_reason,
                **meta,
            )
        except ManifestError as exc:
            result.mutated.append(key)
            result.failed.append({"partition": key, "error": str(exc)})
            continue
        if was_known:
            result.confirmed += 1
        else:
            result.added += 1

        since_save += 1
        if save_every and since_save >= save_every:
            manifest.save()
            since_save = 0
        if on_progress:
            on_progress(result.scanned, total, key)

    manifest.save()
    return manifest, result
