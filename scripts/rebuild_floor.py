"""Jenga jedwali la sakafu UPYA kutoka checkpoint — bila kuendesha chochote.

Calibration B ni masaa mengi, lakini gharama hiyo ni ya **kuendesha pipeline
juu ya replicates 150**. Matokeo yake tayari yako kwenye checkpoint. Pale kanuni
ya lango inapobadilika (§9.9), hakuna sababu ya kulipa gharama ile tena: safu
zilezile zinapita kwenye `floor_from_rows()` ile ile inayotumiwa na `calibrate()`,
na jedwali linalotoka ni lile lile hasa lingelitoka kwenye run.

Kinachobadilika ni `created_at` pekee — pamoja na `joint`, ambalo halikuwepo.

---

**Kile script hii HAIWEZI kufanya:** kubadilisha replicates. Checkpoint ina
matokeo ya code iliyokuwa ikiendeshwa wakati ule, na fingerprint yake iko kwenye
mstari wa kwanza. Ikiwa pipeline yenyewe imebadilika, jedwali linalojengwa upya
linaelezea code ya zamani — na hilo linaandikwa kwenye `source`, si kufichwa.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.validation import noise_floor as NF  # noqa: E402

RIPOTI = REPO / "research" / "reports"


def soma_safu(path: Path) -> tuple[str, dict[str, list[dict]]]:
    """(fingerprint, {familia: [matokeo, ...]}) kwa mpangilio wa replicate."""
    if not path.exists():
        raise SystemExit(f"checkpoint haipo: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise SystemExit(f"checkpoint tupu: {path}")

    kichwa = json.loads(lines[0]).get("fingerprint", "")
    kwa_rep: dict[str, dict[int, dict]] = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        kwa_rep.setdefault(row["family"], {})[int(row["rep"])] = row["result"]

    return kichwa, {
        fam: [reps[k] for k in sorted(reps)] for fam, reps in kwa_rep.items()
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out", default=None,
                    help="chaguo-msingi: jedwali lililo pembeni ya checkpoint")
    ap.add_argument("--seed", type=int, default=None,
                    help="chaguo-msingi: seed ya jedwali la zamani")
    args = ap.parse_args()

    ck_path = Path(args.checkpoint)
    out_path = Path(args.out) if args.out else Path(
        str(ck_path).replace("_checkpoint.jsonl", ".json"))

    fingerprint, rows = soma_safu(ck_path)
    fams = tuple(sorted(rows))
    idadi = {f: len(r) for f, r in rows.items()}
    n_rep = min(idadi.values())

    # Seed na chanzo vinatoka kwenye jedwali la zamani ikiwa lipo: bootstrap CI
    # inategemea seed, na kuibuni hapa kungebadilisha namba ambazo hazikubadilika
    # kwa sababu yoyote ya kipimo.
    zamani = NF.NoiseFloor.read(out_path) if out_path.exists() else None
    seed = args.seed if args.seed is not None else (zamani.seed if zamani else 0)
    chanzo = zamani.source if zamani else str(ck_path)

    print(f"checkpoint: {ck_path.name}")
    print(f"   fingerprint {fingerprint[:16]}…")
    print(f"   replicates  {' · '.join(f'{f} {n}' for f, n in sorted(idadi.items()))}")
    if zamani is not None:
        print(f"   jedwali la zamani: malango {len(zamani.entries)} · "
              f"pamoja {'lipo' if zamani.joint else 'HALIPO'} · seed {seed}")
    print()

    if n_rep < NF.MIN_REPLICATES:
        print(f"replicates {n_rep} < {NF.MIN_REPLICATES} — checkpoint haijakamilika.")
        return 2

    variants = [int(r.get(NF.VARIANTS_KEY, 0)) for rs in rows.values() for r in rs]
    mpya = NF.floor_from_rows(
        rows, metrics=NF.DEFAULT_METRICS, families=fams, n_replicates=n_rep,
        variants=variants, seed=seed, source=chanzo,
    )
    print(mpya.render())

    # Sakafu za kila metric HAZIPASWI kubadilika — data ni ileile. Zikibadilika,
    # ni `floor_from_rows` iliyoharibika, si sakafu iliyoboreshwa, na hilo lazima
    # lionekane kabla ya kuandika.
    if zamani is not None:
        tofauti = [
            f"{jina}: {e.floor:,.6f} → {mpya.entries[jina].floor:,.6f}"
            for jina, e in zamani.entries.items()
            if jina in mpya.entries and abs(e.floor - mpya.entries[jina].floor) > 1e-9
        ]
        kukosekana = sorted(set(zamani.entries) ^ set(mpya.entries))
        if tofauti or kukosekana:
            print("\nKOSA · sakafu za metric zimebadilika ingawa data ni ileile:")
            for m in tofauti:
                print(f"      {m}")
            for m in kukosekana:
                print(f"      {m}: lipo upande mmoja pekee")
            print("   Jedwali HALIJAANDIKWA.")
            return 3

    mpya.write(out_path)
    print(f"\nimeandikwa: {out_path}")
    if mpya.joint is not None:
        print(f"   null inayopita lango la pamoja: {mpya.joint.null_pass_rate:.2%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
