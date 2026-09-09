"""Pakua kufunga kwa siku kwa faharasa tano — DOCTRINE §11.

```
python scripts/fetch_indices.py
python scripts/fetch_indices.py --dir "C:\\...\\research\\data\\indices"
```

Chanzo ni **Stooq**: CSV moja kwa moja, bure, hakuna akaunti. Faili zinaandikwa
`research/data/indices/*.csv`, ambayo iko kwenye `.gitignore` kama data
nyingine zote.

---

**Kwa nini kuna majina mbadala.** Sikuweza kufikia Stooq kutoka mahali
nilipojenga hii (sera ya mtandao), kwa hiyo **sijathibitisha ticker hata
moja**. Badala ya kubahatisha jina moja na kukuachia 404, kila faharasa ina
orodha ya wagombea; script inajaribu mmoja baada ya mwingine na kuripoti
uliofanya kazi.

Ikishindwa yote, inasema waziwazi ni ipi imekosekana badala ya kuandika faili
tupu. **Faili tupu ingepita kimya hadi kwenye ishara**, ambapo ingeonekana
kama "miezi michache haina data".
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.data.indices import MIN_ROWS, IndexError_, read_csv  # noqa: E402
from src.families.f1_signal import INDEX_FOR, US_INDEX        # noqa: E402

STOOQ = "https://stooq.com/q/d/l/?s={ticker}&i=d"

# Wagombea kwa kila faharasa, kwa mpangilio wa kujaribiwa. Wa kwanza ndiye
# ninayemwamini zaidi; wanaofuata ni majina mengine yanayotumika Stooq.
WAGOMBEA: dict[str, tuple[str, ...]] = {
    "SP500":     ("^spx", "^sp500", "spx"),
    "STOXX50":   ("^stx50", "^sx5e", "^stoxx50e", "^estx50"),
    "FTSE100":   ("^ukx", "^ftse", "^ftse100"),
    "NIKKEI225": ("^nkx", "^nkx225", "^n225", "^nikkei"),
    "TSX":       ("^tsx", "^gsptse", "^tsxc"),
}

MUDA = 40


def pakua(ticker: str) -> bytes | None:
    url = STOOQ.format(ticker=urllib.parse.quote(ticker, safe=""))
    ombi = urllib.request.Request(url, headers={"User-Agent": "elitefx/1.0"})
    try:
        with urllib.request.urlopen(ombi, timeout=MUDA) as jibu:
            return jibu.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def ni_halali(raw: bytes) -> bool:
    """CSV ya kweli, si ukurasa wa kosa.

    Stooq inarudisha HTTP 200 na maandishi kama `"No data"` kwa ticker
    isiyojulikana. Kuangalia code ya HTTP pekee kungeandika faili yenye
    maneno matatu.
    """
    if not raw or len(raw) < 2_000:
        return False
    kichwa = raw[:200].decode("utf-8", "replace").lower()
    return "date" in kichwa and "close" in kichwa


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    ap.add_argument("--sleep", type=float, default=1.5,
                    help="sekunde kati ya maombi — usimlemee mwenyeji")
    args = ap.parse_args()

    folda = Path(args.dir) if args.dir else (
        REPO / "research" / "data" / "indices")
    folda.mkdir(parents=True, exist_ok=True)

    zinazohitajika = sorted(set(INDEX_FOR.values()) | {US_INDEX})
    print(f"Faharasa {len(zinazohitajika)} → {folda}\n")

    mafanikio, mapungufu = {}, []
    for jina in zinazohitajika:
        wagombea = WAGOMBEA.get(jina, ())
        if not wagombea:
            mapungufu.append((jina, "hakuna mgombea"))
            continue
        for i, ticker in enumerate(wagombea):
            if i:
                time.sleep(args.sleep)
            raw = pakua(ticker)
            if raw is None:
                print(f"   {jina:<11} {ticker:<12} haikufikika")
                continue
            if not ni_halali(raw):
                print(f"   {jina:<11} {ticker:<12} si CSV "
                      f"({len(raw):,} bytes)")
                continue
            njia = folda / f"{jina}.csv"
            njia.write_bytes(raw)
            try:
                s = read_csv(njia, name=jina)
            except IndexError_ as exc:
                njia.unlink(missing_ok=True)
                print(f"   {jina:<11} {ticker:<12} imekataliwa: {exc}")
                continue
            print(f"   {jina:<11} {ticker:<12} SAWA · {s.render()}")
            mafanikio[jina] = (ticker, s)
            break
        else:
            mapungufu.append((jina, f"wagombea wote wameshindwa: "
                                    f"{', '.join(wagombea)}"))
        time.sleep(args.sleep)

    print("\n" + "=" * 74)
    if mapungufu:
        print("HAZIJAPATIKANA:")
        for jina, sababu in mapungufu:
            print(f"   {jina:<11} {sababu}")
        print("\nF1 inahitaji ZOTE — kikapu ni cha yote-au-hakuna. Kama Stooq\n"
              "haina jina sahihi, pakua CSV kwa mkono (safu `Date` na `Close`)\n"
              f"na uiweke {folda}\\<JINA>.csv kwa majina haya:\n"
              f"   {', '.join(zinazohitajika)}")
        return 3

    print(f"ZOTE {len(mafanikio)} ZIMEPATIKANA.\n")
    for jina, (ticker, s) in sorted(mafanikio.items()):
        print(f"   {s.render()}   ({ticker})")
    print(f"\nrows chini kabisa zinazokubalika: {MIN_ROWS:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
