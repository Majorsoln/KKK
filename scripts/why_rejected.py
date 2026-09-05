"""Waliokataliwa walikuwa MBALI kiasi gani? — DOCTRINE §9.9, §9.8.

"Hakuna aliyenusurika" ni jibu la ndiyo/hapana, na swali linalofuata daima ni la
**umbali**. Mgombea bora mwenye `T = 0.66` dhidi ya sakafu ya `0.6695` na mmoja
mwenye `T = 0.15` wamekataliwa vilevile, lakini wanaelekeza sehemu tofauti
kabisa: wa kwanza ni suala la kiasi, wa pili ni suala la aina.

Namba yenye mamlaka hapa ni **p-value ya pamoja**:

```
p = (k + 1) / (n + 1)      k = replicates za null zenye T isiyopungua ya halisi
```

Fomu ni ile ile ya §9.8, na inasoma moja kwa moja bila kizingiti kipya chochote.
`K` ya utafutaji ni ile ile pande zote mbili (§9.4), kwa hiyo tatizo la `max` la
§9.1 tayari liko ndani ya null.

---

**Kile script hii HAIFANYI:** kupendekeza sakafu nyingine. Kizingiti kimewekwa
na §9.9 na kimekwisha-thibitishwa dhidi ya null. Kuchagua kingine baada ya kuona
matokeo ni §9.1 kwa ngazi ya mtafiti — na ndiyo hatari ambayo mradi mzima
umejengwa kuizuia. Hapa kuna umbali, si pendekezo.

Inasoma ripoti iliyoandikwa tayari na `discover.py`. Hakuna kinachoendeshwa upya.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.validation.noise_floor import NoiseFloor  # noqa: E402

RIPOTI = REPO / "research" / "reports"


def _asilimia(orodha, q):
    import numpy as np

    return float(np.quantile(orodha, q)) if orodha else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--discovery", required=True)
    ap.add_argument("--noise-floor", default=None)
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args()

    disc_path = Path(args.discovery)
    if not disc_path.exists():
        raise SystemExit(f"ripoti haipo: {disc_path}")
    raw = json.loads(disc_path.read_text(encoding="utf-8"))

    floor_path = Path(args.noise_floor) if args.noise_floor else None
    floor = NoiseFloor.read(floor_path) if floor_path else None
    lango = floor.joint if floor is not None else None

    verdicts = raw.get("screening", {}).get("verdicts", [])
    if not verdicts:
        raise SystemExit("ripoti haina `screening.verdicts` — je ni ya discover.py?")
    if not any(v.get("u") for v in verdicts):
        raise SystemExit(
            "verdicts hazina `u` — ripoti hii ilitokana na kanuni ya kabla ya "
            "§9.9.\n   Endesha `discover.py` upya juu ya jedwali lenye lango la "
            "pamoja."
        )

    kizingiti = verdicts[0].get("joint_floor", float("nan"))
    t_zote = sorted((v["t"] for v in verdicts), reverse=True)
    n = len(t_zote)

    print(f"ripoti: {disc_path.name} · waliopimwa {n}")
    print(f"   T lazima izidi {kizingiti:.4f}\n")

    print("   mgawanyo wa T kwa waliopita §8.4:")
    for jina, q in (("juu kabisa", 1.0), ("p75", 0.75), ("kati", 0.5),
                    ("p25", 0.25), ("chini kabisa", 0.0)):
        print(f"      {jina:<14} {_asilimia(t_zote, q):.4f}")

    juu = t_zote[0]
    print(f"\n   pengo la bora: {juu:.4f} dhidi ya {kizingiti:.4f} "
          f"= {juu - kizingiti:+.4f}")

    # ----- mwelekeo upi ndio kikwazo -----
    metrics = sorted(verdicts[0]["u"])
    print("\n   kwa kila mwelekeo (u ya waliopimwa):")
    print(f"      {'metric':<28} {'juu':>7} {'kati':>7} {'wanaovuka':>11}")
    for m in metrics:
        us = sorted((v["u"].get(m, 0.0) for v in verdicts), reverse=True)
        wanaovuka = sum(1 for x in us if x > kizingiti)
        print(f"      {m:<28} {us[0]:>7.4f} {_asilimia(us, 0.5):>7.4f} "
              f"{wanaovuka:>7}/{n}")

    # ----- bora kadhaa, na p-value yao -----
    kwa_t = sorted(verdicts, key=lambda v: v["t"], reverse=True)[: args.top]
    print(f"\n   bora {len(kwa_t)} kwa T:")
    for v in kwa_t:
        p = lango.p_value(v["values"]) if lango is not None and lango.t_null else None
        pt = "" if p is None else f" · p {p:.3f}"
        dhaifu = min(v["u"], key=lambda k: v["u"][k])
        print(f"      {v['candidate_id']}  T {v['t']:.4f}{pt}  "
              f"dhaifu: {dhaifu} (u {v['u'][dhaifu]:.4f})")
        print("         " + " · ".join(
            f"{k[:12]} {v['u'][k]:.2f}" for k in metrics))

    if lango is None or not lango.t_null:
        print("\n   (p-value inahitaji --noise-floor lenye `t_null`; "
              "lijenge upya kwa `rebuild_floor.py`)")
        return 0

    bora = kwa_t[0]
    p = lango.p_value(bora["values"])
    print(f"\np-VALUE YA PAMOJA YA BORA: {p:.3f}   "
          f"(null {sum(1 for x in lango.t_null if x >= bora['t'])}/"
          f"{len(lango.t_null)} zina T isiyopungua)")

    # §9.1 kwa ngazi ya symbol: kipimo hiki kimefanywa kwa symbols kadhaa.
    print("\n   Hii ni p-value ya symbol MOJA. §9.8 ilionyesha kuwa symbols 12\n"
          "   zikipimwa, matarajio ya kupata p ndogo kwa bahati si sifuri —\n"
          "   `expected_by_chance = N_symbols × p`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
