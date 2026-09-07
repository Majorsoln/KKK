"""Je vipimo vinapima UBORA au MZUNGUKO? — DOCTRINE §9.2, §9.4, §2.

Hoja ya PD (2026-09-07): *huwezi kukagua trade 200 kwa style moja wakati mbinu
ni tofauti.*

Mahali inapouma ni hapa. Calibration B inachukua **mshindi mmoja** kwa kila run
ya data bandia, na anayechaguliwa ni mwenye `net_account_return_month` kubwa
zaidi (§9.4, `select_by`). Vipimo vyake VYOTE vinakuwa sakafu:

```
mshindi wa null → sharpe, pmf, net_pips, DD  →  bar kwa KILA mgombea halisi
```

Kama mshindi huyo alikuwa wa mzunguko wa juu — trades 300 — sakafu yake ya
`sharpe` na `profitable_month_fraction` ni ya **style yake**. Trend-follower
mwenye trades 38 anapimwa dhidi ya bar ya scalper. Hizo si strategy mbili
zinazoshindana; ni mbinu mbili tofauti.

---

**Swali linalopimika:** je vipimo vinategemea mzunguko?

Kama `sharpe` na `pmf` zinapanda pamoja na `n_trades`, sakafu iliyojengwa
kutoka kwa mshindi ni **dai la mzunguko lililovaa nguo ya ubora**, na
kulinganisha mbinu tofauti kwa bar moja ni kosa la kipimo, si ukali.

Kama hazitegemei, mbinu zinalinganishika kwenye vipimo hivi, na hoja
haitumiki hapa hata kama ni sahihi kwa ujumla.

---

**Jinsi jibu litakavyosomwa — imeandikwa KABLA ya kuliona (§9.10).**

* `|rho| > 0.5` kwenye vipimo vya ubora (`sharpe`, `pmf`) → uhusiano ni wa
  kweli. Lango linahitaji kulinganisha mgombea na null **za mzunguko
  unaofanana**, si na zote.
* `|rho| < 0.3` → mbinu zinalinganishika. Hoja haitumiki hapa.
* Kati → jedwali la tertile linaamua: tofauti ya wastani kati ya mzunguko wa
  chini na wa juu ndiyo ukubwa halisi, si `rho` peke yake.

Uhusiano unapimwa kwenye **substrate zote nne**. Ukiwepo kwenye data halisi
pekee, ni sifa ya soko; ukiwepo kwenye zote, ni sifa ya **vipimo vyenyewe** —
na ndiyo inayohusu sakafu.

Spearman, si Pearson: vipimo vya strategy vina mikia mizito, na `net_pips_month`
moja ya 5,000 ingetawala jibu lote (`src/stats.py`).

---

Inasoma `month_structure_<symbol>_<tf>.json` iliyoandikwa tayari. Hakuna
kinachoendeshwa upya.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.stats import spearman  # noqa: E402

RIPOTI = REPO / "research" / "reports"

MZUNGUKO = "n_trades"
UBORA = ("sharpe", "profitable_month_fraction")
VINGINE = ("net_pips_month", "net_account_return_month", "max_drawdown")


def _kati(x):
    import numpy as np

    a = np.asarray([v for v in x if v == v], dtype=float)
    return float(np.median(a)) if a.size else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=None)
    ap.add_argument("--symbol", default="GBPUSD")
    ap.add_argument("--tf", default="H1")
    args = ap.parse_args()

    path = Path(args.report) if args.report else (
        RIPOTI / f"month_structure_{args.symbol}_{args.tf}.json")
    if not path.exists():
        raise SystemExit(
            f"ripoti haipo: {path}\n"
            f"   Inatoka `scripts/month_structure.py`."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    paired = raw.get("paired", {})
    if not paired:
        raise SystemExit("ripoti haina `paired` — je ni ya month_structure.py?")

    substrates = sorted({s for v in paired.values() for s in v})
    wagombea = sorted(paired)
    vipimo = UBORA + VINGINE

    print(f"ripoti: {path.name} · wagombea {len(wagombea)} · "
          f"substrate {len(substrates)}")
    print(f"   {args.symbol} {args.tf} · dirisha {raw['window']['start']} → "
          f"{raw['window']['end']}\n")

    print("UHUSIANO WA CHEO na `n_trades` (Spearman rho)")
    print(f"   {'metric':<28}" + "".join(f"{s[:8]:>10}" for s in substrates))
    rho_zote: dict[str, dict[str, float]] = {}
    for m in vipimo:
        safu = ""
        rho_zote[m] = {}
        for s in substrates:
            n = [paired[c][s].get(MZUNGUKO) for c in wagombea]
            v = [paired[c][s].get(m) for c in wagombea]
            r = spearman(n, v)
            rho_zote[m][s] = r
            safu += f"{r:>10.3f}"
        alama = "  ←ubora" if m in UBORA else ""
        print(f"   {m:<28}{safu}{alama}")

    # Tertile: rho inasema mwelekeo, jedwali linasema UKUBWA. Uhusiano wa 0.6
    # unaweza kuwa tofauti ndogo isiyo na maana kwa lango, au kubwa kabisa.
    print("\nWASTANI KWA UTATU WA MZUNGUKO (data halisi)")
    halisi = "halisi" if "halisi" in substrates else substrates[0]
    kwa_n = sorted(wagombea, key=lambda c: paired[c][halisi].get(MZUNGUKO, 0.0))
    k = max(1, len(kwa_n) // 3)
    makundi = (("chini", kwa_n[:k]), ("kati", kwa_n[k:-k] or kwa_n[k:]),
               ("juu", kwa_n[-k:]))
    print(f"   {'kundi':<8}{'n_trades':>10}" + "".join(f"{m[:14]:>16}"
                                                       for m in vipimo))
    for jina, kundi in makundi:
        safu = "".join(
            f"{_kati([paired[c][halisi].get(m) for c in kundi]):>16.4f}"
            for m in vipimo)
        print(f"   {jina:<8}"
              f"{_kati([paired[c][halisi].get(MZUNGUKO) for c in kundi]):>10.0f}"
              f"{safu}")

    # Hukumu inasomwa kwenye vipimo vya UBORA pekee, na kwenye substrate ZOTE:
    # uhusiano wa data halisi peke yake ungekuwa sifa ya soko, si ya vipimo.
    kwa_ubora = [abs(rho_zote[m][s]) for m in UBORA for s in substrates
                 if rho_zote[m][s] == rho_zote[m][s]]
    if not kwa_ubora:
        print("\nHAKUNA UHUSIANO ULIOPIMIKA — vipimo havikuhesabika.")
        return 2

    kubwa = max(kwa_ubora)
    kati_ubora = sorted(kwa_ubora)[len(kwa_ubora) // 2]
    print(f"\n   |rho| ya vipimo vya ubora: kubwa {kubwa:.3f} · "
          f"kati {kati_ubora:.3f}")

    if kati_ubora > 0.5:
        print("\nVIPIMO VYA UBORA VINATEGEMEA MZUNGUKO.\n"
              "   Sakafu iliyojengwa kutoka kwa mshindi mmoja (§9.4 `select_by`)\n"
              "   ni dai la mzunguko lililovaa nguo ya ubora. Kulinganisha mbinu\n"
              "   zenye mizunguko tofauti kwa bar moja ni kosa la kipimo.")
        return 1
    if kati_ubora < 0.3:
        print("\nVIPIMO HAVITEGEMEI MZUNGUKO kwa kiasi kinachohusu lango.\n"
              "   Mbinu zenye mizunguko tofauti zinalinganishika kwenye vipimo\n"
              "   hivi. Hoja ya kuoanisha style haitumiki hapa.")
        return 0
    print("\n   Uhusiano ni wa katikati — jedwali la utatu ndilo linaloamua,\n"
          "   si `rho`. Angalia tofauti halisi ya wastani kati ya `chini` na "
          "`juu`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
