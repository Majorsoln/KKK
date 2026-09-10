"""Lango la §6.2 pekee — je familia INAWEZA kupimika? — DOCTRINE §6.

```
python scripts/gate_probe.py --family f1 --root <L0> --provenance aggregator
```

Inasoma **ncha mbili pekee** za kila tukio na kupima vitu viwili:

```
σ  =  stdev ya (kutoka − kuingia)                 (volatility ya dirisha)
gharama  =  nusu-spread ya kuingia + nusu ya kutoka + commission
```

`σ` **inapimwa**, haigeuzwi kutoka `E|X|` kwa kigezo cha normal (§13.10).
Namba ya normal (`1.2533 × E|X|`) inachapishwa pembeni kama rejea, ili
kiasi cha mikia minene kionekane.

Kisha `gharama / σ` dhidi ya bajeti ya **8%**.

**Hakuna strategy inayoendeshwa. Hakuna `p`. Hakuna α inayotumika.** Ndiyo
maana chombo hiki kipo: baada ya F0 na Gotobi, swali la kwanza kuhusu familia
yoyote mpya si *"ina edge?"* bali ***"tunaweza kuipima kabisa?"*** — na jibu
lake linagharimu dakika chache za diski badala ya jaribio.

Gotobi ilikwama hapa kwa 9.3% dhidi ya 8%, na sehemu kubwa ya gharama yake
ilikuwa **commission**, si spread. Kwa dirisha fupi, `σ` inakua kwa `√muda`
lakini commission haipungui hata kidogo.

---

**Kikomo kimoja kilichoandikwa.** Familia yenye legs za urefu TOFAUTI (F0:
masaa 9 na 4.4) inapimwa hapa kwa **kuchanganya** — kipimo kinakuwa cha
wastani, si cha leg mbaya. Kwa `σ` ni mbaya zaidi: mchanganyiko wa madirisha
mawili yenye `σ` tofauti una mtawanyiko mkubwa kuliko lolote kati yao, kwa
hiyo `σ` inapanuka na lango linalegea. Kwa familia hizo, namba ya uamuzi ni ile ya
`family_run.py`, inayoripoti kwa kila leg. Gotobi na F1 zina dirisha MOJA,
kwa hiyo kwao chombo hiki ni sahihi kabisa.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys
import time
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.backtest.driver import chunks                         # noqa: E402
from src.backtest.driver import commission_usd as D_commission  # noqa: E402
from src.data import ticks as TK                               # noqa: E402
from src.events.clock import quotes                            # noqa: E402
from src.families import f0, f1, gotobi                        # noqa: E402
from src.families.qualify import COST_BUDGET                   # noqa: E402
from src.families.stops import MOVE_TO_SIGMA                   # noqa: E402

FAMILIES = {"f0": f0, "gotobi": gotobi, "f1": f1}
RIPOTI = REPO / "research" / "reports"


def symbols_of(fam) -> tuple[str, ...]:
    return getattr(fam, "SYMBOLS", (getattr(fam, "SYMBOL", ""),))


def pip_of(fam, symbol: str) -> float:
    pips = getattr(fam, "PIPS", None)
    return pips[symbol] if pips else fam.PIP


def pip_value_of(fam, symbol: str, mid: float) -> float:
    try:
        return fam.pip_value(symbol, mid)
    except TypeError:
        return fam.pip_value(mid)


def probe(fam, inv, symbol: str, days, *, commission: float, verbose=False):
    """Mwendo na gharama kwa symbol moja, kwenye dirisha lililotangazwa."""
    pip = pip_of(fam, symbol)
    partitions = inv.of(symbol)
    mwendo, ishara, gharama, kukosekana = [], [], [], 0

    for kundi in chunks(days, size=20):
        maombi = []
        for d in kundi:
            for s in fam.sessions_for(d):
                maombi.append((s.entry_at, fam.WINDOW_SECONDS))
                maombi.append((s.exit_at, fam.WINDOW_SECONDS))
        frame = TK.read_windows(inv, symbol, maombi, partitions=partitions)

        for d in kundi:
            for s in fam.sessions_for(d):
                try:
                    ndani = quotes(frame, s.entry_at, fam.WINDOW_SECONDS)
                    nje = quotes(frame, s.exit_at, fam.WINDOW_SECONDS)
                except Exception:                              # noqa: BLE001
                    kukosekana += 1
                    continue
                mwendo.append(abs(nje.mid - ndani.mid) / pip)
                ishara.append((nje.mid - ndani.mid) / pip)
                # Spread iliyolipwa kwenda-na-kurudi ni nusu kila ncha.
                spread = (ndani.spread_pips(pip) + nje.spread_pips(pip)) / 2
                # §13.10: commission ni ya sarafu ya MSINGI.
                comm = (D_commission(symbol, ndani.mid, commission)
                        / pip_value_of(fam, symbol, ndani.mid))
                gharama.append(spread + comm)
        if verbose:
            print(f"      {symbol} {kundi[0]:%Y-%m}  n {len(mwendo):>5,}",
                  flush=True)

    if not mwendo:
        return None
    w = st.fmean(mwendo)
    g = st.fmean(gharama)
    # §13.10: `σ` inapimwa kutoka mwendo wenye ishara. `MOVE_TO_SIGMA`
    # inabaki kama rejea ya kulinganisha pekee, si kwa lango.
    sigma = st.stdev(ishara) if len(ishara) > 1 else float("nan")
    sigma_normal = w * MOVE_TO_SIGMA
    return {"symbol": symbol, "n": len(mwendo), "missing": kukosekana,
            "move_pips": w, "sigma_pips": sigma,
            "sigma_normal_pips": sigma_normal,
            "kurtosis_hint": sigma / sigma_normal,
            "drift_pips": st.fmean(ishara),
            "cost_pips": g, "ratio": g / sigma,
            "ratio_normal": g / sigma_normal}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True, choices=sorted(FAMILIES))
    ap.add_argument("--root", default=None)
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--provenance", default=None)
    ap.add_argument("--commission", type=float, default=7.0,
                    help="round-turn kwa lot kwa sarafu ya MSINGI")
    ap.add_argument("--out", default=None)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    fam = FAMILIES[args.family]
    root = args.root or os.path.join(
        os.environ.get("ELITEFX_RESEARCH_ROOT", str(REPO / "research")),
        "data", "L0_raw")

    anza, mwisho = date.fromisoformat(args.start), date.fromisoformat(args.end)
    zote, d = [], anza
    while d <= mwisho:
        zote.append(d)
        d += timedelta(days=1)
    siku = fam.eligible_days(zote)
    if not siku:
        print("HAKUNA SIKU INAYOSTAHILI.")
        return 2
    s0, = fam.sessions_for(siku[0])[:1]
    saa = (s0.exit_at - s0.entry_at).total_seconds() / 3600.0

    print(f"LANGO LA §6.2 — {fam.FAMILY}")
    print(f"   matukio {len(siku):,} · dirisha saa {saa:.2f} · "
          f"commission ${args.commission}/lot · bajeti {COST_BUDGET:.0%}")
    print(f"   HAKUNA strategy inayoendeshwa · HAKUNA `p` · HAKUNA α\n")

    zote_symbols = symbols_of(fam)
    inv = TK.discover(root, symbols=list(zote_symbols),
                      provenance=args.provenance)
    print(inv.render() + "\n")

    t0 = time.time()
    matokeo = []
    for symbol in zote_symbols:
        try:
            r = probe(fam, inv, symbol, siku, commission=args.commission,
                      verbose=args.verbose)
        except TK.TickError as exc:
            print(f"   {symbol:<8} HAIPO: {exc}")
            continue
        if r is None:
            print(f"   {symbol:<8} hakuna tick hata moja")
            continue
        matokeo.append(r)

    print("=" * 74)
    print(f"   {'symbol':<9}{'n':>6}{'kukosa':>8}{'mwendo':>9}{'σ':>8}"
          f"{'σ norm':>8}{'gharama':>9}{'gh/σ':>8}{'gh/σn':>8}  jibu")
    print("=" * 74)
    for r in matokeo:
        jibu = "PITA" if r["ratio"] <= COST_BUDGET else "KATAA"
        print(f"   {r['symbol']:<9}{r['n']:>6,}{r['missing']:>8,}"
              f"{r['move_pips']:>9.2f}{r['sigma_pips']:>8.2f}"
              f"{r['sigma_normal_pips']:>8.2f}{r['cost_pips']:>9.2f}"
              f"{r['ratio']:>7.1%}{r['ratio_normal']:>8.1%}  {jibu}")

    if not matokeo:
        print("\nHAKUNA KIPIMO.")
        return 2

    mbaya = max(matokeo, key=lambda r: r["ratio"])
    print(f"\n   leg mbaya kabisa: {mbaya['symbol']} kwa {mbaya['ratio']:.1%}"
          f"  (σ iliyopimwa ÷ σ ya normal = {mbaya['kurtosis_hint']:.3f})")
    if mbaya["ratio"] > COST_BUDGET:
        # Dirisha linalohitajika: σ ∝ √muda.
        inahitajika = mbaya["cost_pips"] / COST_BUDGET
        saa2 = saa * (inahitajika / mbaya["sigma_pips"]) ** 2
        print(f"   σ inayohitajika {inahitajika:.2f} pips → dirisha saa "
              f"{saa2:.2f} (sasa {saa:.2f})")

    print(f"\n   muda {time.time() - t0:.0f}s")
    hukumu = all(r["ratio"] <= COST_BUDGET for r in matokeo)
    print(f"\n{fam.FAMILY}: LANGO {'LIMEFUNGUKA' if hukumu else 'LIMEKATAA'}"
          f" — {'inaweza kupimika' if hukumu else 'haiwezi kupimika'}"
          f" kwa gharama hii.")

    path = Path(args.out) if args.out else (
        RIPOTI / f"gate_{fam.FAMILY.lower()}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(
        {"family": fam.FAMILY, "window_hours": saa, "events": len(siku),
         "commission": args.commission, "budget": COST_BUDGET,
         "per_symbol": matokeo, "passed": hukumu}, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    print(f"imeandikwa: {path}")
    return 0 if hukumu else 3


if __name__ == "__main__":
    raise SystemExit(main())
