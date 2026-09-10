"""Pakua kufunga kwa siku kwa faharasa tano — DOCTRINE §11.

```
python scripts/fetch_indices.py
python scripts/fetch_indices.py --show          # onyesha jibu ghafi likikataliwa
python scripts/fetch_indices.py --dir "C:\\...\\research\\data\\indices"
```

Faili zinaandikwa `research/data/indices/<JINA>.csv` kwa umbo moja
(`Date,Close`), bila kujali chanzo. Folda hiyo iko ndani ya `research/data/`,
ambayo haiingii git.

---

**Vyanzo viwili, kwa mpangilio.**

```
1 · Yahoo Finance   JSON, tickers ninazozijua kwa uhakika
2 · Stooq           CSV, tickers ambazo sikuweza kuthibitisha
```

Jaribio la kwanza (Stooq pekee, 2026-09-09) lilirudisha **bytes 796 kwa
majaribio yote 17** — ukubwa ULE ULE kwa kila ticker. Hiyo si "ticker haipo";
ni ukurasa mmoja wa kuzuia. Mabadiliko matatu yametokana na hilo:

1. **Yahoo kwanza**, kwa tickers `^GSPC`, `^FTSE`, `^N225`, `^STOXX50E`,
   `^GSPTSE` — hizi ninazijua, tofauti na za Stooq nilizozibahatisha.
2. **User-Agent ya kivinjari.** Wenyeji wengi wanakataa `python-urllib`.
3. **Jibu lililokataliwa linaonyeshwa.** Toleo la kwanza lilisema *"si CSV
   (796 bytes)"* na kunyamaza — kikataa bila kuonyesha ushahidi. Kosa langu:
   validator inayokataa lazima ionyeshe kile ilichokikataa, vinginevyo
   inakuacha ukikisia.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.data.indices import MIN_ROWS, IndexError_, read_csv  # noqa: E402
from src.families.f1_signal import INDEX_FOR, US_INDEX        # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
MUDA = 45

YAHOO = ("https://query1.finance.yahoo.com/v8/finance/chart/"
         "{ticker}?range=15y&interval=1d")
STOOQ = "https://stooq.com/q/d/l/?s={ticker}&i=d"

# Yahoo: tickers ninazozijua. Stooq: nilizobahatisha.
VYANZO: dict[str, dict[str, tuple[str, ...]]] = {
    "SP500":     {"yahoo": ("^GSPC",), "stooq": ("^spx",)},
    "STOXX50":   {"yahoo": ("^STOXX50E", "^SX5E"), "stooq": ("^stx50",)},
    "FTSE100":   {"yahoo": ("^FTSE",), "stooq": ("^ukx",)},
    "NIKKEI225": {"yahoo": ("^N225",), "stooq": ("^nkx",)},
    "TSX":       {"yahoo": ("^GSPTSE",), "stooq": ("^tsx",)},
}


def fetch(url: str) -> tuple[bytes | None, str]:
    ombi = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(ombi, timeout=MUDA) as jibu:
            return jibu.read(), f"http {jibu.status}"
    except urllib.error.HTTPError as exc:
        return None, f"http {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, f"{type(exc).__name__}: {str(exc)[:60]}"


def kutoka_yahoo(raw: bytes) -> list[tuple[date, float]]:
    """JSON ya Yahoo → `[(siku, kufunga)]`. Inalipuka ikiwa umbo si sahihi."""
    d = json.loads(raw.decode("utf-8"))
    matokeo = (d.get("chart") or {}).get("result") or []
    if not matokeo:
        kosa = (d.get("chart") or {}).get("error")
        raise ValueError(f"hakuna matokeo ({kosa})")
    r = matokeo[0]
    stamps = r.get("timestamp") or []
    quote = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    if not stamps or len(stamps) != len(closes):
        raise ValueError(f"stamps {len(stamps)} dhidi ya closes {len(closes)}")
    out = []
    for t, c in zip(stamps, closes):
        if c is None:
            continue
        out.append((datetime.fromtimestamp(t, tz=timezone.utc).date(), float(c)))
    return out


def kutoka_stooq(raw: bytes) -> list[tuple[date, float]]:
    """CSV ya Stooq → `[(siku, kufunga)]`."""
    import csv
    import io

    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if not rows:
        raise ValueError("haina row hata moja")
    vichwa = {k.strip().lower(): k for k in rows[0] if k}
    if "date" not in vichwa or "close" not in vichwa:
        raise ValueError(f"safu si sahihi: {sorted(vichwa)}")
    out = []
    for r in rows:
        try:
            out.append((datetime.fromisoformat(r[vichwa["date"]][:10]).date(),
                        float(r[vichwa["close"]])))
        except (ValueError, TypeError, KeyError):
            continue
    return out


WACHAMBUZI = {"yahoo": (YAHOO, kutoka_yahoo), "stooq": (STOOQ, kutoka_stooq)}


def andika_csv(path: Path, rows: list[tuple[date, float]]) -> None:
    """Umbo MOJA, bila kujali chanzo: `Date,Close`, zimepangwa, bila marudio."""
    pamoja = {d: c for d, c in rows if c and c > 0}
    mistari = ["Date,Close"]
    mistari += [f"{d.isoformat()},{pamoja[d]}" for d in sorted(pamoja)]
    path.write_text("\n".join(mistari) + "\n", encoding="utf-8", newline="\n")


def onyesha(raw: bytes | None, n: int = 160) -> str:
    if raw is None:
        return "—"
    maandishi = raw[:n].decode("utf-8", "replace")
    return " ".join(maandishi.split())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    ap.add_argument("--sleep", type=float, default=1.5)
    ap.add_argument("--show", action="store_true",
                    help="onyesha mwanzo wa jibu lililokataliwa")
    ap.add_argument("--sources", nargs="+", default=["yahoo", "stooq"],
                    choices=sorted(WACHAMBUZI))
    args = ap.parse_args()

    folda = Path(args.dir) if args.dir else (
        REPO / "research" / "data" / "indices")
    folda.mkdir(parents=True, exist_ok=True)

    zinazohitajika = sorted(set(INDEX_FOR.values()) | {US_INDEX})
    print(f"Faharasa {len(zinazohitajika)} → {folda}")
    print(f"vyanzo: {' → '.join(args.sources)}\n")

    mafanikio, mapungufu = {}, []
    for jina in zinazohitajika:
        kupatikana = False
        for chanzo in args.sources:
            umbo, mchambuzi = WACHAMBUZI[chanzo]
            for ticker in VYANZO.get(jina, {}).get(chanzo, ()):
                url = umbo.format(ticker=urllib.parse.quote(ticker, safe=""))
                raw, hali = fetch(url)
                lebo = f"   {jina:<11} {chanzo:<6} {ticker:<12}"
                if raw is None:
                    print(f"{lebo} {hali}")
                    time.sleep(args.sleep)
                    continue
                try:
                    rows = mchambuzi(raw)
                except Exception as exc:                       # noqa: BLE001
                    print(f"{lebo} {hali} · haisomeki: {str(exc)[:60]}"
                          f" ({len(raw):,} bytes)")
                    if args.show:
                        print(f"        → {onyesha(raw)}")
                    time.sleep(args.sleep)
                    continue

                njia = folda / f"{jina}.csv"
                andika_csv(njia, rows)
                try:
                    s = read_csv(njia, name=jina)
                except IndexError_ as exc:
                    njia.unlink(missing_ok=True)
                    print(f"{lebo} {hali} · imekataliwa: {str(exc)[:70]}")
                    time.sleep(args.sleep)
                    continue
                print(f"{lebo} SAWA · {s.render()}")
                mafanikio[jina] = (chanzo, ticker, s)
                kupatikana = True
                break
            if kupatikana:
                break
        if not kupatikana:
            mapungufu.append(jina)
        time.sleep(args.sleep)

    print("\n" + "=" * 74)
    if mapungufu:
        print(f"HAZIJAPATIKANA: {', '.join(mapungufu)}\n")
        print("F1 inahitaji ZOTE — kikapu ni cha yote-au-hakuna.\n\n"
              "Njia ya mkono: pakua CSV yenye safu `Date` na `Close` (rows\n"
              f"≥ {MIN_ROWS:,}, kuanzia 2017 au mapema) na uiweke:\n")
        for jina in mapungufu:
            print(f"   {folda}\\{jina}.csv")
        print("\nVyanzo vinavyofanya kazi kwenye kivinjari:\n"
              "   investing.com · wsj.com/market-data · au MT5 yako yenyewe\n"
              "   (US500, UK100, JP225, EU50, CA60 kama CFD)\n\n"
              "Ukishaziweka, endesha `python scripts/check_indices.py`.")
        return 3

    print(f"ZOTE {len(mafanikio)} ZIMEPATIKANA.\n")
    for jina, (chanzo, ticker, s) in sorted(mafanikio.items()):
        print(f"   {s.render()}   ({chanzo} {ticker})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
