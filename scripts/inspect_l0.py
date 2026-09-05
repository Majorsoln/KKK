"""Amri 1 — kuangalia data ya L0 KABLA ya kupima chochote.

Haisomi zaidi ya faili chache. Kazi yake ni kujibu maswali manne ambayo, bila
majibu yake, kila kitu kinachofuata ni kudhania:

* muundo wa folda ni upi, na symbol inatambulikaje kutoka njia?
* schema ni ya Toleo A au B, na dtypes ni zipi hasa?
* muda unafunika kipindi gani, na uko UTC?
* faili ni ngapi na GB ngapi — je, kupakia kwa mara moja kunawezekana?

Endesha:

    python scripts/inspect_l0.py
    python scripts/inspect_l0.py --root D:\\elitefx\\research\\data\\L0_raw
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.data.load import discover, normalize, read_partition  # noqa: E402
from src.rce.config import load_config  # noqa: E402
from src.rce.cost import pip_size  # noqa: E402


def _root(arg: str | None) -> Path:
    """Njia ya L0. Mpangilio: `--root`, kisha env, kisha `<repo>/research`.

    Rejea ya mwisho si dhana: inatumika **tu** ikiwa folda ipo kweli, na njia
    iliyochaguliwa inachapishwa. Bila yake, kila terminal mpya inadai
    `call scripts\\env.local.bat` kabla ya chochote — kikwazo kinachojirudia
    bila kulinda kitu.
    """
    if arg:
        return Path(arg)
    env = os.environ.get("ELITEFX_L0_ROOT") or os.environ.get("ELITEFX_RESEARCH_ROOT")
    if env:
        path = Path(env)
        return path if path.name == "L0_raw" else path / "data" / "L0_raw"

    ndani = REPO / "research" / "data" / "L0_raw"
    if ndani.exists():
        return ndani
    raise SystemExit(
        "Data ya L0 haijapatikana. Chagua mojawapo:\n"
        f"   --root <njia>\n"
        "   set ELITEFX_RESEARCH_ROOT=<njia ya research>\n"
        "   call scripts\\env.local.bat\n"
        f"   au weka data kwenye {ndani}"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Angalia L0 kabla ya kupima")
    ap.add_argument("--root", default=None)
    ap.add_argument("--provenance", default=None,
                    help="chagua chanzo kimoja, mf. aggregator au broker")
    ap.add_argument("--peek", type=int, default=2, help="faili ngapi za kusoma kwa undani")
    args = ap.parse_args()

    root = _root(args.root)
    print(f"ROOT: {root}\n")

    inv = discover(root, provenance=args.provenance)
    print(inv.render())

    if not inv.partitions:
        print("\nHAKUNA faili la parquet lililoonekana. Njia si sahihi, au suffix si `.parquet`.")
        return 1

    print("\n" + "=" * 74)
    print("MUUNDO WA NJIA (sampuli)")
    print("=" * 74)
    for part in inv.partitions[:5]:
        print(f"   {part.path.relative_to(root)}   [{part.symbol}]  {part.size_mb:,.1f} MB")

    print("\n" + "=" * 74)
    print("SCHEMA — kama ilivyo kwenye diski, kabla ya normalize")
    print("=" * 74)
    import pandas as pd

    for part in inv.partitions[: args.peek]:
        raw = pd.read_parquet(part.path)
        print(f"\n   {part.path.name}  [{part.symbol}]  rows {len(raw):,}")
        for name, dtype in raw.dtypes.items():
            print(f"      {name:<16} {dtype}")
        print(f"   rows 3 za kwanza:\n{raw.head(3).to_string(max_colwidth=28)}")

        out = normalize(raw, source=str(part.path))
        stamps = out["timestamp"]
        print(f"   baada ya normalize: {list(out.columns)}")
        print(f"      tz {stamps.dt.tz} · {stamps.min()} -> {stamps.max()}")
        print(f"      spread pips (median): "
              f"{((out['ask'] - out['bid']).median() / pip_size(part.symbol)):.2f}")

    print("\n" + "=" * 74)
    print("PROVENANCE — chanzo kwa chanzo, symbol kwa symbol")
    print("=" * 74)
    for symbol in inv.symbols:
        mine = inv.raw(symbol)
        for prov in inv.provenances(symbol):
            zake = [p for p in mine if p.provenance == prov]
            vipindi = [p.period for p in zake if p.period]
            span = (f"{min(vipindi)} -> {max(vipindi)}"
                    if vipindi else "tarehe HAIKO kwenye njia")
            shaka = sum(1 for p in zake if p.shaka)
            if shaka:
                span += f"   TAREHE ISIYOSOMEKA: {shaka}"
            print(f"   {symbol:<8} {prov or '(hakuna)':<12} faili {len(zake):>6,}  "
                  f"MB {sum(p.size_mb for p in zake):>9,.0f}  {span}")
            print(f"      {zake[0].path.relative_to(root)}")
            if len(zake) > 1:
                print(f"      {zake[-1].path.relative_to(root)}")

    pacha = {sym: inv.duplicates(sym) for sym in inv.symbols}
    pacha = {k: v for k, v in pacha.items() if v}
    if pacha or inv.zenye_shaka:
        print("\n" + "=" * 74)
        print("MATATIZO YANAYOZUIA KUPAKIA")
        print("=" * 74)
        for part in inv.zenye_shaka[:20]:
            print(f"   tarehe haisomeki: {part.path.relative_to(root)}")
        for sym, vipindi in pacha.items():
            print(f"   {sym}: vipindi vinajirudia ndani ya chanzo kimoja — "
                  f"{', '.join(vipindi[:5])}")

    mwingiliano = {sym: inv.overlaps(sym) for sym in inv.symbols}
    mwingiliano = {k: v for k, v in mwingiliano.items() if v}
    if mwingiliano:
        print("\n" + "=" * 74)
        print("MWINGILIANO WA VYANZO — si kosa; ni uamuzi")
        print("=" * 74)
        print("   Vipindi vilivyoandikwa na vyanzo VIWILI. Chagua kimoja kwa --provenance;")
        print("   feed mbili haziunganishwi (data.yaml §2.2).")
        for sym, vipindi in mwingiliano.items():
            print(f"   {sym:<8} vipindi {len(vipindi):>3}  "
                  f"{vipindi[0]} -> {vipindi[-1]}")

    print("\n" + "=" * 74)
    print("KIPINDI KWA KILA SYMBOL — kutoka NDANI ya faili ya kwanza na ya mwisho")
    print("(faili zisizo na tarehe kwenye njia zinapangwa mwanzoni)")
    print("=" * 74)
    for symbol in inv.symbols:
        chunks = inv.raw(symbol)
        try:
            kwanza = read_partition(chunks[0].path)["timestamp"]
            mwisho = read_partition(chunks[-1].path)["timestamp"]
            print(f"   {symbol:<8} {kwanza.min()}  ->  {mwisho.max()}   "
                  f"(faili {len(chunks):,})")
        except Exception as exc:
            print(f"   {symbol:<8} KOSA: {exc}")

    print("\n" + "=" * 74)
    print("CONFIG")
    print("=" * 74)
    cfg = load_config(REPO / "config" / "data.yaml")
    for key in ("splits.data_start", "splits.trainval_end", "splits.holdout_start",
                "splits.data_end", "bars.timeframes", "source.symbols"):
        print(f"   {key:<24} {cfg.get(key)}")
    print(f"   config_hash              {cfg.config_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
