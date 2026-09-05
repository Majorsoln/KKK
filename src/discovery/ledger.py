"""Ledger ya variants — DOCTRINE §9.3 (S1), §10.4, R6, R21.

> **S1** — `variants_tested` inahesabiwa daima, ikiwemo waliokufa mapema.
> Si namba inayotolewa na generator (`len(walionusurika)` si hesabu — ni matokeo).
> Ni **ledger ya matukio isiyofutika**, row moja kwa kila candidate iliyowahi
> kuzalishwa.

Swali linalopaswa kujibika kwa ushahidi, si kwa kumbukumbu:

> *"Strategy hii ilichaguliwa baada ya kujaribu variants ngapi?"*

---

**Kuzalishwa si kupimwa, na tofauti ni ya lazima.**

`n_generated` ni kila candidate iliyowahi kutokea. `variants_tested` ni zile
zilizofika kwenye **data**. Mbili hizo hazilingani, na kuzichanganya kunapotosha
sakafu ya §9 kwa pande **zote mbili**:

| aina | inaingia `variants_tested`? | kwa nini |
|---|---|---|
| iliyopimwa (yoyote hatua) | **ndio** | iligusa data — inaweza kuwa na bahati |
| `INVALID_CANDIDATE` (R21) | hapana | haikupimwa; masharti yalizidi kabla ya backtest |
| `DUPLICATE` | hapana | hash ile ile; si sampuli mpya kutoka null |

Kuhesabu `INVALID` kungepandisha sakafu kwa candidates ambazo hazikuwahi kupata
nafasi ya kuwa na bahati. Kutohesabu iliyopimwa kisha kukataliwa mapema
kungeishusha — na hiyo ndiyo hatari kubwa zaidi, kwa sababu inaonekana kama
usafi wa mchakato.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# Hatua ambazo candidate inaweza kufikia. Mpangilio ni wa maana: kila moja
# inamaanisha "ilipita zilizotangulia".
GENERATED = "GENERATED"        # imezalishwa, bado haijapimwa
BACKTEST = "BACKTEST"
VALIDATION = "VALIDATION"
NOISE_FLOOR = "NOISE_FLOOR"
SURVIVOR = "SURVIVOR"

HATUA_ZILIZOPIMWA = (BACKTEST, VALIDATION, NOISE_FLOOR, SURVIVOR)

# Sababu za kufa KABLA ya kupimwa — hazihesabiwi kwenye `variants_tested`.
INVALID_CANDIDATE = "INVALID_CANDIDATE"   # R21: masharti yamezidi max_conditions
DUPLICATE = "DUPLICATE"                   # hash ile ile imeshaonekana


class LedgerError(RuntimeError):
    """Ledger imeombwa kufanya kitu kinachovunja uadilifu wake."""


@dataclass(frozen=True)
class VariantRecord:
    """Row moja, isiyofutika, kwa kila candidate iliyowahi kuzalishwa."""

    candidate_id: str
    variant_hash: str
    generation: int
    parent_ids: tuple[str, ...]
    tested_at: str
    stage_reached: str
    reject_reason: str = ""
    symbol: str = ""
    complexity: int = 0

    @property
    def ilipimwa(self) -> bool:
        """Iligusa data? Ndilo swali pekee linalohesabika kwa §9."""
        return self.stage_reached in HATUA_ZILIZOPIMWA

    def to_json(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id, "variant_hash": self.variant_hash,
            "generation": self.generation, "parent_ids": list(self.parent_ids),
            "tested_at": self.tested_at, "stage_reached": self.stage_reached,
            "reject_reason": self.reject_reason, "symbol": self.symbol,
            "complexity": self.complexity, "ilipimwa": self.ilipimwa,
        }


@dataclass
class VariantLedger:
    """Kila candidate iliyowahi kuzalishwa, kwa mpangilio wa kuzalishwa.

    Rows hazibadilishwi baada ya kuandikwa — `advance()` inaandika hali mpya
    ikibadilisha row iliyopo, kwa sababu candidate ni **kitu kimoja** kinachopita
    hatua kadhaa. Kinachozuiliwa ni kufuta na kurudi nyuma.
    """

    records: list[VariantRecord] = field(default_factory=list)
    _kwa_hash: dict[str, int] = field(default_factory=dict)
    _kwa_id: dict[str, int] = field(default_factory=dict)

    # ---------------- kuandika ----------------

    def generate(self, strategy, *, reject_reason: str = "") -> VariantRecord:
        """Andika candidate mpya. Nakala inaandikwa pia — lakini kama `DUPLICATE`.

        Nakala **haifutwi kimya**. Ikifutwa, ledger ingekuwa inasema utafutaji
        ulikuwa mdogo kuliko ulivyokuwa, na kupanga kwa generator kusingeweza
        kuchunguzwa baadaye.
        """
        h = strategy.variant_hash
        sababu = reject_reason
        if not sababu and h in self._kwa_hash:
            sababu = DUPLICATE

        record = VariantRecord(
            candidate_id=f"{len(self.records):07d}-{h}",
            variant_hash=h,
            generation=int(getattr(strategy, "generation", 0)),
            parent_ids=tuple(getattr(strategy, "parent_ids", ())),
            tested_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            stage_reached=GENERATED,
            reject_reason=sababu,
            symbol=getattr(strategy, "symbol", ""),
            complexity=int(getattr(strategy, "complexity", 0)),
        )
        self._kwa_id[record.candidate_id] = len(self.records)
        self._kwa_hash.setdefault(h, len(self.records))
        self.records.append(record)
        return record

    def advance(self, candidate_id: str, stage: str, *,
                reject_reason: str = "") -> VariantRecord:
        """Sogeza candidate mbele. Kurudi nyuma HAKURUHUSIWI."""
        if candidate_id not in self._kwa_id:
            raise LedgerError(f"candidate {candidate_id!r} haipo kwenye ledger")
        idx = self._kwa_id[candidate_id]
        sasa = self.records[idx]

        mpangilio = (GENERATED, *HATUA_ZILIZOPIMWA)
        if stage not in mpangilio:
            raise LedgerError(f"hatua {stage!r} haijulikani — {mpangilio}")
        if mpangilio.index(stage) < mpangilio.index(sasa.stage_reached):
            raise LedgerError(
                f"{candidate_id}: {sasa.stage_reached} -> {stage} ni kurudi nyuma. "
                f"Candidate iliyofika hatua haiwezi kuirudia — ledger ingekuwa "
                f"inaandika historia upya"
            )

        mpya = VariantRecord(
            candidate_id=sasa.candidate_id, variant_hash=sasa.variant_hash,
            generation=sasa.generation, parent_ids=sasa.parent_ids,
            tested_at=sasa.tested_at, stage_reached=stage,
            reject_reason=reject_reason or sasa.reject_reason,
            symbol=sasa.symbol, complexity=sasa.complexity,
        )
        self.records[idx] = mpya
        return mpya

    # ---------------- kuhesabu ----------------

    @property
    def n_generated(self) -> int:
        return len(self.records)

    @property
    def variants_tested(self) -> int:
        """Zilizogusa data. Ndiyo namba inayoingia kwenye sakafu ya §9 (R6)."""
        return sum(1 for r in self.records if r.ilipimwa)

    @property
    def n_invalid(self) -> int:
        return sum(1 for r in self.records if r.reject_reason == INVALID_CANDIDATE)

    @property
    def n_duplicate(self) -> int:
        return sum(1 for r in self.records if r.reject_reason == DUPLICATE)

    @property
    def survivors(self) -> tuple[VariantRecord, ...]:
        return tuple(r for r in self.records if r.stage_reached == SURVIVOR)

    def by_stage(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.records:
            out[r.stage_reached] = out.get(r.stage_reached, 0) + 1
        return dict(sorted(out.items()))

    def by_reject_reason(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.records:
            if r.reject_reason:
                out[r.reject_reason] = out.get(r.reject_reason, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))

    def of_hash(self, variant_hash: str) -> tuple[VariantRecord, ...]:
        return tuple(r for r in self.records if r.variant_hash == variant_hash)

    # ---------------- kuripoti ----------------

    def render(self) -> str:
        lines = [
            f"VARIANTS · zilizozalishwa {self.n_generated:,} · "
            f"ZILIZOPIMWA {self.variants_tested:,}  (R6)",
        ]
        pengo = self.n_generated - self.variants_tested
        if pengo:
            lines.append(
                f"   hazikupimwa {pengo:,}: invalid {self.n_invalid:,} · "
                f"duplicate {self.n_duplicate:,}"
            )
        for stage, n in self.by_stage().items():
            lines.append(f"   {stage:<16} {n:>8,}")
        sababu = self.by_reject_reason()
        if sababu:
            lines.append("   sababu za kukataliwa:")
            for jina, n in sababu.items():
                lines.append(f"      {jina:<28} {n:>8,}")
        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        return {
            "n_generated": self.n_generated,
            "variants_tested": self.variants_tested,
            "n_invalid": self.n_invalid,
            "n_duplicate": self.n_duplicate,
            "by_stage": self.by_stage(),
            "by_reject_reason": self.by_reject_reason(),
            "records": [r.to_json() for r in self.records],
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
    def read(cls, path: Path) -> "VariantLedger":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        led = cls()
        for row in raw["records"]:
            record = VariantRecord(
                candidate_id=row["candidate_id"], variant_hash=row["variant_hash"],
                generation=int(row["generation"]), parent_ids=tuple(row["parent_ids"]),
                tested_at=row["tested_at"], stage_reached=row["stage_reached"],
                reject_reason=row.get("reject_reason", ""),
                symbol=row.get("symbol", ""), complexity=int(row.get("complexity", 0)),
            )
            led._kwa_id[record.candidate_id] = len(led.records)
            led._kwa_hash.setdefault(record.variant_hash, len(led.records))
            led.records.append(record)
        return led


def extend(ledger: VariantLedger, strategies: Iterable) -> list[VariantRecord]:
    return [ledger.generate(s) for s in strategies]
