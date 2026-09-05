"""Je sakafu inaweza kupitisha wagombea WALIOIJENGA? — DOCTRINE §9.2, §9.3.

Discovery ya GBPUSD ilikataliwa 84/84, na malango matatu yalikataa kwa kauli
moja. Kipimo cha `signal_rate.py` kilionyesha kwamba null na soko halisi zina
**nafasi za kutrade zinazolingana** (1.02×) — kwa hiyo si mzunguko.

Shaka iliyobaki iko kwenye **jinsi sakafu inavyojengwa**:

```
noise_floor[metric] = p95 ya metric hiyo, KWA KILA METRIC PEKE YAKE
lango                = mgombea lazima avuke ZOTE kwa wakati mmoja
```

`p95` ya `net_pips_month` inatoka kwa replicate fulani; `p95` ya `sharpe`
inatoka kwa nyingine; `p5` ya `max_drawdown` kwa ya tatu. **Hakuna mgombea
mmoja wa null aliyelazimika kuvuka zote** — lakini mgombea halisi analazimika.

Kama vipimo ni huru, nafasi ya kuvuka sita kwa wakati mmoja ni `0.05⁶` —
karibu sifuri. Hata vikiwa na uhusiano mkubwa, ni kidogo sana.

---

**Kipimo:** chukua washindi 150 wa null wenyewe — wale walioijenga sakafu — na
uwapime dhidi yake. Kama ~5% wanapita, lango limejengwa vizuri: `p95` inamaanisha
"bora kuliko 95%". Kama ~0% wanapita, lango ni **kali kuliko sehemu zake**, na
84/84 haikuwa hukumu kuhusu GBPUSD — ilikuwa hukumu kuhusu ujenzi wa lango.

Hakuna kinachoendeshwa upya. Checkpoint ya Calibration B ina metrics za kila
replicate; sakafu iko kwenye faili lake. Ni sekunde.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.discovery import survivors as SV  # noqa: E402
from src.validation.noise_floor import NoiseFloor  # noqa: E402

RIPOTI = REPO / "research" / "reports"


def _soma_checkpoint(path: Path) -> list[tuple[str, int, dict]]:
    """(familia, replicate, metrics) kwa kila replicate iliyohifadhiwa."""
    if not path.exists():
        raise SystemExit(
            f"checkpoint haipo: {path}\n"
            f"   Ni faili ya Calibration B (`*_checkpoint.jsonl`). Bila yake,\n"
            f"   washindi wa null hawapatikani na kipimo hiki hakiwezekani."
        )
    out = []
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        out.append((row["family"], int(row["rep"]), row["result"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--noise-floor", default=None)
    ap.add_argument("--checkpoint", default=None)
    args = ap.parse_args()

    floor_path = Path(args.noise_floor) if args.noise_floor else (
        RIPOTI / "noise_floor.json")
    ck_path = Path(args.checkpoint) if args.checkpoint else (
        floor_path.with_name(floor_path.stem + "_checkpoint.jsonl"))

    floor = NoiseFloor.read(floor_path)
    washindi = _soma_checkpoint(ck_path)

    print(f"sakafu: {floor_path.name} · malango {len(floor.entries)}")
    print(f"washindi wa null: {len(washindi)} (kutoka {ck_path.name})")
    print(f"chanzo: {floor.source}\n")

    uchujaji = SV.Screening()
    kwa_familia: dict[str, list[bool]] = {}
    for familia, rep, metrics in washindi:
        uamuzi = SV.screen(f"{familia}-{rep:03d}", "", metrics, floor)
        uchujaji.add(uamuzi)
        kwa_familia.setdefault(familia, []).append(uamuzi.passed)

    n = uchujaji.n_screened
    walipita = sum(1 for v in uchujaji.verdicts if v.passed)
    print(f"WASHINDI WA NULL DHIDI YA SAKAFU YAO WENYEWE: "
          f"{walipita}/{n} = {walipita / n:.1%}\n")

    print("   lango lililokata:")
    for jina, idadi in uchujaji.by_failed_metric().items():
        e = floor.entries[jina]
        ishara = ">" if e.higher_is == "better" else "<"
        print(f"      {jina:<28} {idadi:>4}/{n}  ({idadi / n:>5.1%})  "
              f"dai {ishara} {e.floor:,.4f}")

    print("\n   kwa familia:")
    for familia, matokeo in sorted(kwa_familia.items()):
        k = sum(matokeo)
        print(f"      {familia:<20} {k:>3}/{len(matokeo)}")

    # Kila metric ILIYOJENGWA kama p95 inapaswa kupitisha ~5% ikipimwa peke
    # yake. Tofauti kati ya hiyo na kupita KWA PAMOJA ndiyo gharama ya kudai
    # malango yote kwa wakati mmoja.
    print("\n   kila lango PEKE YAKE (kinadharia ~5%):")
    for jina, e in floor.entries.items():
        peke = sum(1 for _, _, m in washindi if e.passes(m.get(jina)))
        print(f"      {jina:<28} {peke:>4}/{n}  ({peke / n:>5.1%})")

    print()
    if walipita == 0:
        print("SAKAFU HAIWEZI KUPITISHA WAGOMBEA WALIOIJENGA.\n"
              "   Kila lango ni `p95` ya metric YAKE, kutoka replicate yake.\n"
              "   Hakuna mgombea wa null aliyelazimika kuvuka zote kwa wakati\n"
              "   mmoja — lakini mgombea halisi analazimika. Lango ni KALI\n"
              "   KULIKO SEHEMU ZAKE, na kukataa kwa 84/84 hakukuwa hukumu\n"
              "   kuhusu GBPUSD; kulikuwa hukumu kuhusu ujenzi wa lango.")
        return 2
    if walipita / n < 0.01:
        print(f"SAKAFU INAPITISHA {walipita / n:.2%} PEKEE ya wagombea "
              f"walioijenga.\n"
              f"   `p95` kwa kila metric inatarajiwa kupitisha ~5%; kudai zote\n"
              f"   kwa pamoja kunashusha hilo kwa kiasi kikubwa.")
        return 1
    print(f"SAKAFU INAPITISHA {walipita / n:.1%} ya wagombea walioijenga.\n"
          f"   Lango limejengwa vizuri: `p95` inamaanisha 'bora kuliko 95%',\n"
          f"   na kukataa kwa data halisi ni hukumu kuhusu data hiyo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
