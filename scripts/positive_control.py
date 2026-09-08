"""LANGO 1 — je injini inaweza KUONA edge? — DOCTRINE §7.1.

Toleo la kwanza lilikalibrisha kiwango cha kukosea kwa kupitisha na halikuwahi
kupima uwezo wa kuona. Miezi sita ya matokeo ya sifuri, bila njia ya kujua
kama yalimaanisha *"hakuna edge sokoni"* au *"kipimo hakiwezi kuiona"*.

Script hii inajibu swali hilo **kabla ya familia yoyote kujengwa**.

```
ticks → vikapu → KUPANDA EDGE kwenye BEI → RCE → trades → curve → bootstrap
```

Kupanda kunafanywa kwenye ticks, kabla ya uteuzi. Kuongeza pips kwenye P&L ya
trades zilizoshachaguliwa kungepima lango la takwimu pekee, na kuruka spread,
sizing ya RCE, kubana kwa lango, na atomiki ya kikapu.

---

**Kusoma jibu.** Nguzo ya `pengo` ndiyo yenye maana:

```
pengo = nguvu ya kinadharia − iliyopimwa
```

Kinadharia ni `Φ(δ − z_α)` — kikomo cha juu kinachodhania uhuru, normality, na
`σ` inayojulikana. Injini halisi itakuwa chini yake. **Pengo ni upungufu wake.**

Pengo dogo (< 10%) → injini inakaribia kikomo cha kinadharia.
Pengo kubwa → kuna kitu kinachopoteza ushahidi, na lazima kipatikane kabla ya
familia yoyote kujengwa.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.analysis import control as C  # noqa: E402
from src.analysis.probe import ProbeSpec, power_curve  # noqa: E402
from src.rce.config import load_config  # noqa: E402

RIPOTI = REPO / "research" / "reports"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=500)
    ap.add_argument("--grid", type=float, nargs="+",
                    default=[0.0, 1.0, 2.0, 3.0, 5.0, 8.0])
    ap.add_argument("--shapes", nargs="+", default=list(C.SHAPES))
    ap.add_argument("--replicates", type=int, default=20)
    ap.add_argument("--B", type=int, default=500)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    mbaya = [s for s in args.shapes if s not in C.SHAPES]
    if mbaya:
        raise SystemExit(f"maumbo hayajulikani: {mbaya} — ni {C.SHAPES}")

    cfg = load_config(REPO / "config" / "risk.yaml")
    spec = ProbeSpec(n_days=args.days)

    print(f"LANGO 1 — udhibiti chanya")
    print(f"   siku {spec.n_days} · SL {spec.sl_pips} pips · "
          f"spread {spec.spread_pips} pips · σ {spec.sigma_pips_per_hour} pips/saa")
    print(f"   maumbo {' '.join(args.shapes)} · replicates {args.replicates} · "
          f"B {args.B:,} · α {args.alpha}")
    print(f"   gridi {args.grid}\n")

    runs = len(args.shapes) * len(args.grid) * args.replicates
    print(f"   runs {runs:,} zinaanza…\n", flush=True)

    t0 = time.time()
    zote: list[C.PowerPoint] = []
    for shape in args.shapes:
        pointi = power_curve(
            spec, cfg=cfg, grid=args.grid, shape=shape,
            n_replicates=args.replicates, alpha=args.alpha, B=args.B,
            seed=args.seed, progress=print if args.verbose else None,
        )
        zote.extend(pointi)
        print(f"   {shape} imekamilika ({time.time() - t0:.0f}s)", flush=True)

    print("\n" + "=" * 78)
    print(f"{'umbo':<10} {'pips':>6}  {'δ':>7}  {'iliyopimwa':>11} "
          f"{'kinadharia':>11}  {'pengo':>7}  {'siku':>6}")
    print("=" * 78)
    for p in zote:
        print(f"{p.shape:<10} {p.pips:>6.2f}  {p.delta_median:>7.2f}  "
              f"{p.rate:>11.1%} {p.theoretical:>11.1%}  {p.gap:>+7.1%}  "
              f"{p.n_days_median:>6.0f}")

    # Kiwango cha kukosea kinasomwa kwenye `pips = 0`: hapo `H0` ni kweli, kwa
    # hiyo kiwango cha kuona kinapaswa kuwa ~α. Kikiwa kikubwa zaidi, lango
    # lina kasoro ya UKUBWA na hakuna kinachofuata kinachoaminika.
    sifuri = [p for p in zote if p.pips == 0.0]
    if sifuri:
        print(f"\n   KIWANGO CHA KUKOSEA (pips = 0, α = {args.alpha}):")
        for p in sifuri:
            alama = "" if p.rate <= args.alpha * 3 else "   ← KUBWA MNO"
            print(f"      {p.shape:<10} {p.rate:>6.1%}{alama}")

    out_path = Path(args.out) if args.out else (RIPOTI / "positive_control.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "spec": {"n_days": spec.n_days, "sl_pips": spec.sl_pips,
                 "spread_pips": spec.spread_pips,
                 "sigma_pips_per_hour": spec.sigma_pips_per_hour},
        "alpha": args.alpha, "B": args.B, "replicates": args.replicates,
        "seed": args.seed, "points": [p.to_json() for p in zote],
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"\nimeandikwa: {out_path}")
    print(f"muda {time.time() - t0:.0f}s")

    # ---- hukumu ----
    kubwa = [p for p in sifuri if p.rate > args.alpha * 3]
    if kubwa:
        print("\nLANGO 1 HALIJAPITA — kiwango cha kukosea ni kikubwa mno.\n"
              "   `p-value` si kipimo. Hakuna familia inayojengwa.")
        return 2

    # Nguvu inasomwa pale kinadharia inapokuwa ya juu: hapo ndipo pengo lina
    # maana. Ikiwa kinadharia yenyewe ni ndogo, hakuna cha kupoteza.
    zenye_maana = [p for p in zote if p.theoretical > 0.5 and p.pips > 0]
    if not zenye_maana:
        print("\nGRIDI HAIFIKI NGUVU YA KUTOSHA — ongeza `--days` au `--grid`.\n"
              "   Bila nukta yenye nguvu ya kinadharia > 50%, pengo halipimiki.")
        return 3

    pengo = max(p.gap for p in zenye_maana)
    print(f"\n   pengo kubwa kuliko yote (kinadharia > 50%): {pengo:+.1%}")
    if pengo > 0.30:
        print("\nLANGO 1 HALIJAPITA — injini inapoteza ushahidi mwingi mno.\n"
              "   Kabla ya familia yoyote, chanzo cha upotevu lazima kipatikane.")
        return 1
    print("\nLANGO 1 LIMEPITA. Injini inaona edge iliyopandwa kwa kiwango\n"
          "   kinachokaribia kikomo cha kinadharia. Familia zinaweza kujengwa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
