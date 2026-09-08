"""Familia inatangazwa kabla ya kuendeshwa — DOCTRINE §4, §8.1.

Strategy ni **sehemu sita zilizoandikwa** (§4): nanga · mwelekeo · kuingia ·
stop · kutoka · ukubwa. Si code inayozalisha trades — code ni utekelezaji wa
tangazo. Tofauti ni ya msingi: tangazo linaweza ku-hash na kufungwa kabla ya
run, code haiwezi.

```
tangazo  →  fingerprint  →  ledger  →  run  →  matokeo
   ↑                                            │
   └────────── halibadiliki baada ya hapa ──────┘
```

Toleo la kwanza lilishindwa kwa sababu ufafanuzi ulikuwa unakua wakati matokeo
yanaonekana. Kila `Declaration` hapa ina `fingerprint()`; ikiwa fingerprint
imebadilika kati ya run mbili, ni **familia mbili tofauti** na zote mbili
zinahesabika kwenye bajeti ya majaribio (§8.1).

---

**`trials` ni sehemu ya tangazo, si ya ripoti.** Familia inayotangaza jaribio
moja na kisha kuendesha matano imevunja bajeti ya α kabla ya `p` yoyote
kusomwa. Namba hii inaingia kwenye fingerprint ili isije ikaongezwa kimya.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from src.portfolio.regime import REGIMES

# Sehemu sita za §4. Zote ni za lazima; hakuna familia inayoendeshwa ikiwa
# moja haijaandikwa.
FIELDS = ("nanga", "mwelekeo", "kuingia", "stop", "kutoka", "ukubwa")


class FamilyError(RuntimeError):
    """Familia haiwezi kutangazwa au kuendeshwa kama ilivyoombwa."""


@dataclass(frozen=True)
class Declaration:
    """Sehemu sita, pamoja na kila namba inayoziunda."""

    family: str
    symbols: tuple[str, ...]

    nanga: str
    mwelekeo: str
    kuingia: str
    stop: str
    kutoka: str
    ukubwa: str

    mechanism: str                      # §6.1 — sababu ya kiuchumi
    eligible_regimes: tuple[str, ...]
    trials: int
    source: str = ""                    # ushahidi uliochapishwa, kama upo
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.family:
            raise FamilyError("familia haina jina")
        if not self.symbols:
            raise FamilyError(f"{self.family}: hakuna symbol iliyotangazwa")
        tupu = [f for f in FIELDS if not str(getattr(self, f)).strip()]
        if tupu:
            raise FamilyError(
                f"{self.family}: sehemu za §4 hazijaandikwa: {tupu} — "
                f"familia isiyokamilika haiendeshwi"
            )
        if not self.mechanism.strip():
            raise FamilyError(
                f"{self.family}: hakuna mekanizimu (§6.1). Bila sababu ya "
                f"kiuchumi iliyoandikwa, symbol haiwezi kupitishwa"
            )
        mbaya = set(self.eligible_regimes) - set(REGIMES)
        if mbaya:
            raise FamilyError(f"{self.family}: regime hazijulikani: {sorted(mbaya)}")
        if not self.eligible_regimes:
            raise FamilyError(f"{self.family}: hakuna regime iliyotangazwa")
        if self.trials < 1:
            raise FamilyError(f"{self.family}: majaribio ni {self.trials}, si ≥ 1")

    def fingerprint(self) -> str:
        """Alama ya tangazo zima. Ikibadilika, ni familia nyingine."""
        payload = json.dumps({
            "family": self.family,
            "symbols": list(self.symbols),
            **{f: getattr(self, f) for f in FIELDS},
            "mechanism": self.mechanism,
            "eligible_regimes": sorted(self.eligible_regimes),
            "trials": self.trials,
            "params": self.params,
        }, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    def render(self) -> str:
        mistari = [f"{self.family} · {'/'.join(self.symbols)} · "
                   f"majaribio {self.trials} · {self.fingerprint()}",
                   f"   mekanizimu : {self.mechanism}"]
        mistari += [f"   {f:<10} : {getattr(self, f)}" for f in FIELDS]
        mistari.append(f"   regimes    : {', '.join(self.eligible_regimes)}")
        if self.source:
            mistari.append(f"   chanzo     : {self.source}")
        return "\n".join(mistari)

    def to_json(self) -> dict[str, Any]:
        return {
            "family": self.family, "symbols": list(self.symbols),
            **{f: getattr(self, f) for f in FIELDS},
            "mechanism": self.mechanism, "source": self.source,
            "eligible_regimes": list(self.eligible_regimes),
            "trials": self.trials, "params": self.params,
            "fingerprint": self.fingerprint(),
        }


__all__ = ["FIELDS", "FamilyError", "Declaration"]
