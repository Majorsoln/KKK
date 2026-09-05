"""R5 — je mlango wa generator uko wazi? (DOCTRINE §2, §8.3, §9.2)

> Generator haifunguki kabla Calibration A na B hazijakamilika na kuhifadhiwa
> kama ushahidi wenye tarehe.

Script hii haifanyi chochote isipokuwa kuuliza swali hilo na kuonyesha jibu.
Ndiyo ukaguzi ule ule ambao `generator.open_generator()` inaufanya kabla ya
kuzalisha candidate ya kwanza — kwa hiyo kikipita hapa, kitapita huko.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.discovery.generator import open_generator  # noqa: E402
from src.validation.noise_floor import CalibrationError  # noqa: E402

RIPOTI = REPO / "research" / "reports"


def main() -> int:
    cost = RIPOTI / "calibration_a.json"
    floor = RIPOTI / "noise_floor.json"

    for jina, njia in (("Calibration A (§8.3)", cost), ("Calibration B (§9.2)", floor)):
        hali = "ipo" if njia.exists() else "HAIPO"
        print(f"   {jina:<24} {hali:<6} {njia}")
    print()

    try:
        jedwali = open_generator(noise_floor_path=floor, cost_calibration_path=cost)
    except CalibrationError as kosa:
        print(f"R5 IMEFUNGWA\n   {kosa}")
        return 1

    print(f"R5 IMEFUNGUKA · malango {len(jedwali.entries)}")
    print(f"   {jedwali.source}")
    print(f"   imepimwa {jedwali.created_at} · seed {jedwali.seed} · "
          f"replicates {jedwali.n_replicates} × familia {len(jedwali.families)}")
    print(f"   variants_tested: chini {jedwali.variants_tested_min:,} (R6)")
    print()

    for e in jedwali.entries.values():
        dai = f"> {e.floor:,.4f}" if e.higher_is == "better" else f"< {e.floor:,.4f}"
        print(f"   {e.metric:<28} inadai {dai:<18} ←{e.binding_family}")

    if jedwali.without_floor:
        print(f"\n   diagnostic pekee (§1.1): {', '.join(jedwali.without_floor)}")

    # Lango lisilopitika lingefungua R5 kimya kisha kukataa kila kitu (§9.5).
    if jedwali.haipitiki:
        print(f"\n   KOSA: sakafu zisizopitika: {', '.join(jedwali.haipitiki)}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
