"""Sifa za broker kutoka MT5 — DOCTRINE §2, §5.

```
python scripts\\mt5_specs.py
python scripts\\mt5_specs.py --deals-since 2024-01-01
```

**Kwa nini script hii ipo.** `config/broker_costs.yaml` ina
`commission_usd_round_turn: 7.0` kwa kila symbol na `contract_size_confirmed:
false`. Namba hizo hazikutoka kwa broker — zilibuniwa kama chaguo-msingi.
Zimeingia kwenye gharama ya kila familia, na kwenye **kukataliwa kwa Gotobi**
(theluthi mbili ya gharama yake ilikuwa commission). §2 inasema kila namba
inayoingia kwenye uamuzi lazima ipimwe na injini hii kabla ya kutumika.
Hii ndiyo kipimo.

**Vinavyopimwa, na kutoka wapi:**

```
contract_size, point, digits, volume_*, swap_*   symbol_info      — hakika
tick_value  → pip_value ya kweli                 symbol_info      — hakika
commission halisi kwa lot                        history_deals    — kama zipo
spread ya sasa (rejea pekee)                     symbol_info_tick — dakika hii
```

Commission **haipo** kwenye `symbol_info` kwenye MT5. Njia pekee ya
kuipima ni deals zilizotekelezwa. Akaunti mpya isiyo na historia haiwezi
kuipima, na script inasema hivyo waziwazi badala ya kukisia.

**Utambulisho wa akaunti hauandikwi kwenye faili wala hauchapishwi**
(login, server, jina la kampuni). Kinachohitajika ni sifa za symbols, si
wewe ni nani.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

RIPOTI = REPO / "research" / "reports"

# Symbols za `config/broker_costs.yaml`. Broker anaweza kuwa na kiambishi
# (`EURUSD.a`, `EURUSDm`, `EURUSD_raw`) — `tafuta_symbol` inashughulikia.
SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD",
           "NZDUSD", "EURGBP", "EURJPY", "EURCHF", "GBPJPY", "XAUUSD")

# `pip` kwa `point`: FX ya digits 5 na dhahabu ya digits 2 → pip = point × 10;
# JPY ya digits 3 → × 10 pia. Digits 4/2 (broker za zamani) → pip = point.
def pip_from_point(point: float, digits: int) -> float:
    return point * 10.0 if digits in (3, 5) else point


def pip_value_yetu(symbol: str, *, contract: float, pip: float,
                   mid: float, bei: dict[str, float]) -> float | None:
    """`pip_value` kwa akaunti ya USD kwa sheria ZETU (`f1.pip_value`).

    Ipo hapa ili ilinganishwe na `trade_tick_value` ya broker. Ikiwa
    zinatofautiana, mojawapo ni kosa — na `pip_value` isiyo sahihi inatoa
    `commission_pips` isiyo sahihi, kosa linaloonekana kama EV badala ya
    kama kasoro (§13.10).

    ```
    ...USD  (dola ni nukuu)   →  contract × pip
    USD...  (dola ni msingi)  →  contract × pip ÷ bei
    cross   (hakuna dola)     →  contract × pip ÷ bei_ya_kubadilisha
    ```
    """
    if mid <= 0 or contract <= 0:
        return None
    if symbol.endswith("USD"):
        return contract * pip
    if symbol.startswith("USD"):
        return contract * pip / mid
    # Cross: nukuu si USD, kwa hiyo inahitaji bei ya kubadilisha nukuu → USD.
    nukuu = symbol[3:]
    moja_kwa_moja = f"{nukuu}USD"       # GBP → GBPUSD, thamani × bei
    kinyume = f"USD{nukuu}"             # JPY → USDJPY, thamani ÷ bei
    if moja_kwa_moja in bei and bei[moja_kwa_moja] > 0:
        return contract * pip * bei[moja_kwa_moja]
    if kinyume in bei and bei[kinyume] > 0:
        return contract * pip / bei[kinyume]
    return None


def subiri_tick(mt5, jina: str, *, majaribio: int = 25, pumzika: float = 0.2):
    """`symbol_info_tick` baada ya `symbol_select`, ikisubiri quote ifike.

    Symbol iliyoongezwa Market Watch sasa hivi haina quote kwa mara ya
    kwanza, na `trade_tick_value` yake ni **0.0** mpaka ifike — ndiyo maana
    run ya kwanza ilitoa `pip_value 0.00` kwa USDCAD na EURGBP wakati
    EURUSD na USDJPY zilifanya kazi. Kutorudia kungeandika sifuri kwenye
    ripoti kana kwamba ni kipimo.
    """
    import time as _t
    for _ in range(majaribio):
        tick = mt5.symbol_info_tick(jina)
        if tick and tick.bid > 0 and tick.ask > 0:
            return tick
        _t.sleep(pumzika)
    return None


def tafuta_terminal() -> list[Path]:
    """`terminal64.exe` zote zilizosakinishwa kwenye mashine hii.

    `mt5.initialize()` bila `path` inatafuta njia ya **chaguo-msingi pekee**
    (`C:\\Program Files\\MetaTrader 5`). Broker wengi wanasakinisha kwa jina
    lao — `IC Markets MT5`, `Exness MetaTrader 5` — na hapo initialize
    inashindwa kwa `IPC initialize failed` ingawa terminal ipo na
    imefunguliwa.

    Inatafuta kwa **kina cha 3 pekee** kwenye folda za programu na
    `%LOCALAPPDATA%`; kutafuta diski nzima kungechukua dakika.
    """
    mizizi = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs",
        Path.home() / "AppData" / "Roaming",
    ]
    zote: list[Path] = []
    for mzizi in mizizi:
        if not mzizi or not mzizi.is_dir():
            continue
        for kina in ("terminal64.exe", "*/terminal64.exe",
                     "*/*/terminal64.exe"):
            try:
                zote += [p for p in mzizi.glob(kina) if p.is_file()]
            except OSError:
                continue
    # `dict.fromkeys` inaondoa marudio ikihifadhi mpangilio.
    return list(dict.fromkeys(zote))


def anzisha(mt5, path: str | None) -> tuple[bool, str]:
    """`mt5.initialize()`, ikijaribu njia zilizopatikana ikiwa lazima."""
    if path:
        ok = mt5.initialize(path=path)
        return ok, (path if ok else f"{path} → {mt5.last_error()}")
    if mt5.initialize():
        return True, "njia ya chaguo-msingi"

    kwanza = mt5.last_error()
    zilizopatikana = tafuta_terminal()
    if not zilizopatikana:
        return False, (f"chaguo-msingi: {kwanza}\n"
                       "   Hakuna `terminal64.exe` iliyopatikana kwenye "
                       "folda za programu.")
    for p in zilizopatikana:
        if mt5.initialize(path=str(p)):
            return True, str(p)
    orodha = "\n".join(f"      {p}" for p in zilizopatikana)
    return False, (f"chaguo-msingi: {kwanza}\n"
                   f"   Zimepatikana lakini hazikufunguka:\n{orodha}")


def tafuta_symbol(mt5, msingi: str) -> str | None:
    """Jina halisi la broker kwa symbol ya msingi, au `None`.

    Inajaribu jina kamili kwanza, kisha inatafuta lolote lenye msingi ndani
    yake. Ikipata zaidi ya moja inarudisha **fupi kabisa** — kwa kawaida ndiyo
    ya kawaida, si `EURUSD.pro.hedge`.
    """
    if mt5.symbol_info(msingi) is not None:
        return msingi
    zote = mt5.symbols_get(f"*{msingi}*") or ()
    majina = sorted((s.name for s in zote), key=lambda n: (len(n), n))
    return majina[0] if majina else None


def commissions(mt5, tangu: datetime) -> dict[str, dict]:
    """Commission halisi kwa lot, kwa symbol, kutoka deals zilizotekelezwa.

    Deal moja ni **upande mmoja**. `commission` ya MT5 ni hasi (inatolewa),
    na inaweza kutozwa yote kwenye kufungua au nusu-nusu kutegemea broker.
    Kwa hiyo tunajumlisha deals **zote** za symbol na kugawa kwa jumla ya
    volume ya kufungua pekee — hiyo inatoa gharama ya **round-turn kwa lot**
    bila kujali broker anaitoza wapi.
    """
    # `history_deals_get` inachuja kwa saa ya SERVER, si UTC. Server ikiwa
    # UTC+3, deal ya dakika hii ina alama ya saa iliyo masaa matatu mbele ya
    # `datetime.now(timezone.utc)`, na dirisha linaloishia "sasa" linaikosa.
    # Kwa hiyo mwisho ni **siku mbili mbele** — pana kuliko tofauti yoyote ya
    # saa duniani. Dirisha pana halina hasara hapa: tunachambua kwa symbol,
    # si kwa saa.
    mwisho = datetime.now(timezone.utc) + timedelta(days=2)
    deals = mt5.history_deals_get(tangu, mwisho)
    if deals is None:
        return {}
    jumla: dict[str, dict] = defaultdict(
        lambda: {"commission": 0.0, "volume_in": 0.0, "n": 0, "swap": 0.0})
    for d in deals:
        # entry: 0 = IN, 1 = OUT, 2 = INOUT, 3 = OUT_BY. Balance/credit
        # zina `symbol` tupu — hazihusiki.
        if not d.symbol:
            continue
        j = jumla[d.symbol]
        j["commission"] += float(d.commission)
        j["swap"] += float(d.swap)
        j["n"] += 1
        if d.entry in (0, 2):
            j["volume_in"] += float(d.volume)
    out = {}
    for sym, j in jumla.items():
        if j["volume_in"] <= 0:
            continue
        out[sym] = {
            "commission_usd_round_turn": abs(j["commission"]) / j["volume_in"],
            "lots_in": j["volume_in"], "deals": j["n"],
            "swap_total": j["swap"],
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deals-since", default=None,
                    help="YYYY-MM-DD; chaguo-msingi ni miaka 3 iliyopita")
    ap.add_argument("--out", default=str(RIPOTI / "mt5_specs.json"))
    ap.add_argument("--terminal", default=None,
                    help="njia kamili ya terminal64.exe")
    ap.add_argument("--find", action="store_true",
                    help="onyesha terminal zilizopatikana kisha simama")
    args = ap.parse_args()

    if args.find:
        zote = tafuta_terminal()
        print(f"terminal64.exe zilizopatikana: {len(zote)}")
        for p in zote:
            print(f"   {p}")
        if not zote:
            print("   HAKUNA. MT5 haijasakinishwa kwenye njia za kawaida.")
        return 0

    try:
        import MetaTrader5 as mt5                              # noqa: N813
    except ImportError:
        print("MetaTrader5 haijasakinishwa.  pip install MetaTrader5")
        return 2

    ok, chanzo = anzisha(mt5, args.terminal)
    if not ok:
        print(f"mt5.initialize() imeshindwa.\n   {chanzo}")
        print("\nSababu zinazowezekana, kwa mpangilio:")
        print("   1. Terminal ya MT5 haijafunguliwa — ifungue na uingie.")
        print("   2. Imesakinishwa kwa jina la broker — tumia --terminal:")
        print("      python scripts\\mt5_specs.py --find")
        print("      python scripts\\mt5_specs.py --terminal \"<njia>\"")
        biti = 64 if sys.maxsize > 2 ** 32 else 32
        print(f"   3. Python ni {biti}-bit "
              f"({'sawa' if biti == 64 else 'MetaTrader5 INAHITAJI 64-bit'}).")
        print("   4. MT5 haijasakinishwa kabisa kwenye mashine hii.")
        print("\nKama ni (4): commission HAIWEZI kupimwa hapa. `7.0` inabaki")
        print("   ikiwa imeandikwa kama DHANA, na Gotobi inapata `UNCERTAIN`")
        print("   badala ya `COST-FAILED` (§13.2, §13.10).")
        return 2
    print(f"MT5 imefunguliwa kupitia: {chanzo}")

    acc = mt5.account_info()
    if acc is None:
        print(f"account_info() ni tupu: {mt5.last_error()}")
        mt5.shutdown()
        return 2

    # Utambulisho HAUCHAPISHWI: login, server, company hazitoki hapa.
    print("=" * 78)
    print("AKAUNTI (bila utambulisho)")
    print("=" * 78)
    print(f"   sarafu {acc.currency} · leverage 1:{acc.leverage} · "
          f"margin_mode {acc.margin_mode} · trade_mode {acc.trade_mode}")
    print("   (0 = demo, 1 = contest, 2 = real)")

    # ---- pita 1: chagua zote, subiri quotes ----
    # Symbols zote zinachaguliwa KABLA ya kusomwa. `symbol_select` peke yake
    # hairudishi quote papo hapo, na `trade_tick_value` inabaki 0.0 mpaka
    # quote ifike — ndiyo sababu ya `pip_value 0.00` ya run ya kwanza.
    print("\n   inachagua symbols na kusubiri quotes…", flush=True)
    majina, hakuna = {}, []
    for msingi in SYMBOLS:
        jina = tafuta_symbol(mt5, msingi)
        if jina is None:
            hakuna.append(msingi)
            continue
        mt5.symbol_select(jina, True)
        majina[msingi] = jina
    ticks = {m: subiri_tick(mt5, j) for m, j in majina.items()}
    bei = {m: (t.bid + t.ask) / 2 for m, t in ticks.items() if t}

    print("\n" + "=" * 78)
    print("SYMBOLS")
    print("=" * 78)
    print(f"   {'msingi':<8} {'contract':>10} {'point':>9} {'dig':>4} "
          f"{'pip_val MT5':>12} {'pip_val yetu':>13} {'tofauti':>9} "
          f"{'spread':>7}")

    jedwali = {}
    for msingi, jina in majina.items():
        si = mt5.symbol_info(jina)          # baada ya quote — tick_value hai
        tick = ticks[msingi]
        pip = pip_from_point(si.point, si.digits)
        # `trade_tick_value` ni thamani ya tick MOJA kwa lot 1 kwa sarafu ya
        # akaunti. pip_value = tick_value × (pip ÷ tick_size).
        pv_mt5 = (si.trade_tick_value * (pip / si.trade_tick_size)
                  if si.trade_tick_size else float("nan"))
        pv_yetu = pip_value_yetu(msingi, contract=si.trade_contract_size,
                                 pip=pip, mid=bei.get(msingi, 0.0), bei=bei)
        tofauti = ((pv_yetu - pv_mt5) / pv_mt5
                   if pv_yetu is not None and pv_mt5 else None)
        spread_pips = ((tick.ask - tick.bid) / pip) if tick else float("nan")
        jedwali[msingi] = {
            "broker_name": jina,
            "contract_size": si.trade_contract_size,
            "point": si.point, "digits": si.digits, "pip": pip,
            "tick_size": si.trade_tick_size,
            "tick_value": si.trade_tick_value,
            "pip_value_mt5": pv_mt5, "pip_value_yetu": pv_yetu,
            "pip_value_diff": tofauti,
            "mid": bei.get(msingi),
            "volume_min": si.volume_min, "volume_step": si.volume_step,
            "volume_max": si.volume_max,
            "swap_long": si.swap_long, "swap_short": si.swap_short,
            "swap_mode": si.swap_mode,
            "spread_now_pips": spread_pips,
            "quote": tick is not None,
        }
        print(f"   {msingi:<8} {si.trade_contract_size:>10,.0f} "
              f"{si.point:>9.5f} {si.digits:>4} {pv_mt5:>12.3f} "
              f"{(f'{pv_yetu:.3f}' if pv_yetu is not None else '—'):>13} "
              f"{(f'{tofauti:+.2%}' if tofauti is not None else '—'):>9} "
              f"{spread_pips:>7.2f}")

    bila_quote = [m for m, v in jedwali.items() if not v["quote"]]
    if bila_quote:
        print(f"\n   BILA QUOTE (pip_value HAIJATHIBITISHWA): "
              f"{', '.join(bila_quote)}")
        print("   Soko limefungwa, au symbol haipatikani kwa akaunti hii.")
    mbaya = [(m, v["pip_value_diff"]) for m, v in jedwali.items()
             if v["pip_value_diff"] is not None
             and abs(v["pip_value_diff"]) > 0.01]
    sawa = sum(1 for v in jedwali.values()
               if v["pip_value_diff"] is not None
               and abs(v["pip_value_diff"]) <= 0.01)
    print(f"\n   pip_value: {sawa}/{len(jedwali)} zinakubaliana na sheria "
          f"zetu ndani ya 1%")
    if mbaya:
        print("   HAZIKUBALIANI: " + " · ".join(
            f"{m} {d:+.1%}" for m, d in mbaya))

    if hakuna:
        print(f"\n   HAZIPO kwa broker huyu: {', '.join(hakuna)}")

    # ---- commission: kipimo, si dhana ----
    tangu = (datetime.fromisoformat(args.deals_since).replace(tzinfo=timezone.utc)
             if args.deals_since
             else datetime.now(timezone.utc) - timedelta(days=365 * 3))
    kom = commissions(mt5, tangu)

    print("\n" + "=" * 78)
    print(f"COMMISSION HALISI (deals tangu {tangu:%Y-%m-%d})")
    print("=" * 78)
    if not kom:
        print("   HAKUNA DEAL HATA MOJA kwenye dirisha hili.")
        print("   Commission HAIWEZI kupimwa. `broker_costs.yaml` inabaki na")
        print("   DHANA ya 7.0, na kila familia inayokufa kwa gharama inapata")
        print("   alama ya `UNCERTAIN`, si `COST-FAILED` (§13.2).")
        print("\n   Njia ya kuipima: fungua na funga lot 0.01 kwa kila symbol")
        print("   inayohitajika kwenye akaunti hii, kisha endesha tena.")
    else:
        print(f"   {'symbol':<16} {'$/lot RT':>10} {'lots':>9} {'deals':>7}")
        for sym, v in sorted(kom.items()):
            print(f"   {sym:<16} {v['commission_usd_round_turn']:>10.2f} "
                  f"{v['lots_in']:>9.2f} {v['deals']:>7,}")
        print("\n   Ni round-turn kwa lot 1, ikiwa imegawanywa kwa volume ya")
        print("   kufungua — inajumuisha commission ya kufungua NA ya kufunga")
        print("   bila kujali broker anaitoza upande gani.")

    # ---- YAML tayari kubandika ----
    print("\n" + "=" * 78)
    print("BANDIKA HII KWENYE config/broker_costs.yaml")
    print("=" * 78)
    kwa_msingi = {}
    for msingi, v in jedwali.items():
        m = kom.get(v["broker_name"])
        if m:
            kwa_msingi[msingi] = m["commission_usd_round_turn"]
    print("commission_usd_round_turn:")
    print(f"  default:  {7.0 if not kwa_msingi else min(kwa_msingi.values()):.2f}"
          f"{'   # BADO NI DHANA' if not kwa_msingi else '   # imepimwa'}")
    for msingi in SYMBOLS:
        if msingi in kwa_msingi:
            print(f"  {msingi + ':':<9} {kwa_msingi[msingi]:.2f}")
        elif msingi in jedwali:
            print(f"  {msingi + ':':<9} 7.00   # HAIJAPIMWA — hakuna deal")
    print("\ncontract_size:")
    kawaida = {m: v["contract_size"] for m, v in jedwali.items()}
    default = max(set(kawaida.values()), key=list(kawaida.values()).count) \
        if kawaida else 100000
    print(f"  default:  {default:.0f}")
    for msingi, cs in sorted(kawaida.items()):
        if cs != default:
            print(f"  {msingi + ':':<9} {cs:.0f}")
    print(f"\ncontract_size_confirmed: {'true' if jedwali else 'false'}")

    matokeo = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "account": {"currency": acc.currency, "leverage": acc.leverage,
                    "margin_mode": int(acc.margin_mode),
                    "trade_mode": int(acc.trade_mode)},
        "symbols": jedwali, "missing": hakuna,
        "commission": kom,
        "commission_measured": bool(kom),
        "deals_since": tangu.date().isoformat(),
    }
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(matokeo, indent=2, default=str) + "\n",
                    encoding="utf-8", newline="\n")
    print(f"\nimeandikwa: {path}")
    mt5.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
