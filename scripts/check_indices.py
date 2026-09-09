"""Kagua faharasa zilizopo na onyesha ishara ya F1 — DOCTRINE §4, §11.

```
python scripts/check_indices.py
```

Inaendeshwa baada ya `fetch_indices.py`, **au baada ya kuweka CSV kwa mkono**.
Chanzo hakijalishi; kinachojalisha ni kwamba faili zina safu `Date` na `Close`
na zinafunika matukio 96 ya F1.

Inaonyesha vitu vitatu:

```
1 · kila faharasa inafunika kipindi gani
2 · matukio mangapi ya F1 yana ishara kamili
3 · ishara zenyewe kwa miezi michache — ili uione mekanizimu ukiwa namba
```

**Hakuna trade inayofanywa. Hakuna `p`. Hakuna α.**
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.data import indices as IX                            # noqa: E402
from src.families import f1                                   # noqa: E402
from src.families import f1_signal as SIG                     # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--sample", type=int, default=6)
    args = ap.parse_args()

    folda = Path(args.dir) if args.dir else (
        REPO / "research" / "data" / "indices")
    zinazohitajika = sorted(set(SIG.INDEX_FOR.values()) | {SIG.US_INDEX})

    print(f"Faharasa ← {folda}\n")
    series, mapungufu = {}, []
    for jina in zinazohitajika:
        njia = folda / f"{jina}.csv"
        if not njia.exists():
            mapungufu.append((jina, "faili haipo"))
            continue
        try:
            s = IX.read_csv(njia, name=jina)
        except IX.IndexError_ as exc:
            mapungufu.append((jina, str(exc)[:80]))
            continue
        series[jina] = s
        muhimu = "" if jina == SIG.US_INDEX else "  ← inaingia kwenye trade"
        print(f"   {s.render()}{muhimu}")

    if mapungufu:
        print("\nHAZIPO au ZIMEKATALIWA:")
        for jina, sababu in mapungufu:
            print(f"   {jina:<11} {sababu}")

    anza, mwisho = date.fromisoformat(args.start), date.fromisoformat(args.end)
    zote, d = [], anza
    while d <= mwisho:
        zote.append(d)
        d += timedelta(days=1)
    siku = f1.eligible_days(zote)
    print(f"\nMatukio ya F1 {anza} → {mwisho}: {len(siku)}")

    inahitajika = {SIG.INDEX_FOR[s] for s in f1.QUALIFIED}
    kwa_trade = {k: v for k, v in series.items() if k in inahitajika}
    if len(kwa_trade) < len(inahitajika):
        pungufu = sorted(inahitajika - set(kwa_trade))
        print(f"\nHAKUNA ISHARA: faharasa {pungufu} hazipo.\n"
              f"F1 ni kikapu cha YOTE-AU-HAKUNA — moja ikikosekana, hakuna "
              f"tukio hata moja.")
        return 3

    print("\n" + "=" * 74)
    for jina, k in sorted(IX.coverage(kwa_trade, siku).items()):
        alama = "" if not k["missing"] else (
            f"  ← {k['missing']} nje ya kipindi (ya kwanza {k['first_missing']})")
        print(f"   {jina:<11} {k['start']} → {k['end']}  rows {k['rows']:>6,}{alama}")

    ishara = SIG.signals(siku, kwa_trade)
    print(f"\n   ishara kamili: {len(ishara)}/{len(siku)} "
          f"({len(ishara) / max(1, len(siku)):.0%})")

    if not ishara:
        print("\nHAKUNA ISHARA HATA MOJA — angalia kipindi cha faharasa.")
        return 3

    print("\n" + "=" * 74)
    print("MFANO WA ISHARA (uzito wa upande wa DOLA: + inauza dola)")
    print("=" * 74)
    hesabu = sorted(ishara)[-args.sample:]
    print(f"   {'tarehe':<12}" + "".join(f"{s:>10}" for s in f1.QUALIFIED))
    for d in hesabu:
        w = ishara[d].weights
        print(f"   {d.isoformat():<12}" +
              "".join(f"{w[s]:>+10.2f}" for s in f1.QUALIFIED))

    print(f"\n   utendaji wa hisa kwa {hesabu[-1]}:")
    r = ishara[hesabu[-1]].meta["returns"]
    for s in f1.QUALIFIED:
        print(f"      {s:<8} {SIG.INDEX_FOR[s]:<11} {r[s]:+7.2%}"
              f"   → uzito {ishara[hesabu[-1]].weights[s]:+.2f}")
    print(f"      (wastani {ishara[hesabu[-1]].meta['mean_return']:+.2%}; "
          f"soko lililofanya vizuri kuliko wastani linauzwa)")

    kamili = len(ishara) == len(siku)
    print(f"\n{'ZOTE ZIPO' if kamili else 'ZIPO KWA SEHEMU'} — "
          f"F1 inaweza kuendeshwa kwa matukio {len(ishara)}.")
    return 0 if kamili else 1


if __name__ == "__main__":
    raise SystemExit(main())
