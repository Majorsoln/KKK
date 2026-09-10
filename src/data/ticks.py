"""Kusoma ticks kwa MADIRISHA pekee — DOCTRINE §7.4.

F0 inasoma sekunde 300 kwenye kila ncha ya kila leg: **dakika 20 kwa siku kati
ya 1,440**. Kupakia siku nzima kungekuwa mara 72 ya kile kinachotumika, na kwa
miaka minane ya ticks hiyo ni tofauti kati ya dakika na masaa — au kati ya
jibu na mashine iliyosimama.

```
discover(root)  →  partitions  →  read_windows(mahitaji)  →  ticks za ncha
```

---

**Muundo wa folda hauwaziwi — unatafutwa.** Njia inayoisha kwa `symbol=EURUSD/`
ikiwa halisi ni `EURUSD/2016/` inarudisha faili sifuri, na ripoti inasema
"cells 0" badala ya kosa. Kwa hiyo `discover` inatembea mti wa faili, inatambua
symbol kutoka **njia yenyewe**, na inachapisha ilichokiona kabla ya chochote
kingine kutokea.

**Schema mbili, frame moja** (`data.yaml: source.schema_variants`):

```
Toleo A : timestamp · bid · ask · bid_vol · ask_vol       (µs)
Toleo B : ts        · bid · ask · bid_volume · ask_volume (ms)
```

Zinabadilishwa kuwa schema MOJA hapa. Kila mahali pengine kwenye injini kuna
`timestamp`, `bid`, `ask` — na hakuna sehemu inayohitaji kujua toleo lipi
lilitoka wapi.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Sequence

TIME_COLUMNS = ("timestamp", "ts", "time", "datetime", "date_time")
VOLUME_ALIASES = {
    "bid_volume": "bid_vol", "ask_volume": "ask_vol",
    "bidvolume": "bid_vol", "askvolume": "ask_vol",
    "volume_bid": "bid_vol", "volume_ask": "ask_vol",
}
SUFFIXES = (".parquet", ".pq")

# Sarafu zinazotambulika. Orodha ipo kwa sababu **umbo pekee halitoshi**:
# folda iitwayo `symbol=EURUSD` ina neno `SYMBOL` — herufi sita kubwa, sawa
# kabisa na umbo la pair. Bila ukaguzi wa sarafu, kila partition ingewekwa
# chini ya symbol iitwayo "SYMBOL".
CURRENCIES = frozenset({
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
    "XAU", "XAG", "SEK", "NOK", "DKK", "PLN", "HUF", "CZK",
    "TRY", "ZAR", "MXN", "SGD", "HKD", "CNH", "RUB",
})

_SIX = re.compile(r"[A-Z]{6}")
_ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


class TickError(RuntimeError):
    """Ticks haziwezi kupakiwa kama zilivyoombwa."""


# ===========================================================================
# Kile kilichopo kwenye diski
# ===========================================================================


@dataclass(frozen=True)
class Partition:
    """Faili moja ya L0, pamoja na kile kinachojulikana kutoka njia yake."""

    path: Path
    symbol: str
    size_mb: float
    provenance: str = ""
    # Kipindi kwa **usahihi ulioandikwa kwenye njia**: `YYYY-MM-DD`, `YYYY-MM`,
    # `YYYY`, au tupu. Partitions za kila siku na za kila mwezi zinaishi pamoja
    # kwenye L0 moja, kwa hiyo kudai usahihi wa siku kwa zote kungefanya nusu
    # yao zionekane hazina tarehe.
    period: str = ""
    shaka: bool = False                 # tag ya tarehe ipo lakini haisomeki

    def covers(self, day: date) -> bool:
        """Je siku hii inaweza kuwa ndani ya partition hii?

        Partition isiyo na kipindi kwenye njia **inachukuliwa kuwa inaweza
        kuwa na chochote**. Ni jibu la tahadhari: kuruka faili kwa sababu
        haijatajwa tarehe kungefanya siku zikose ticks kimya.
        """
        return not self.period or day.isoformat().startswith(self.period)

    def to_json(self) -> dict[str, Any]:
        return {"path": str(self.path), "symbol": self.symbol,
                "size_mb": self.size_mb, "provenance": self.provenance,
                "period": self.period, "shaka": self.shaka}


@dataclass
class Inventory:
    """Kila kitu kilichopo kwenye diski, kabla chochote hakijasomwa."""

    root: Path
    partitions: list[Partition] = field(default_factory=list)
    isiyotambulika: list[Path] = field(default_factory=list)

    @property
    def symbols(self) -> list[str]:
        return sorted({p.symbol for p in self.partitions})

    def provenances(self, symbol: str) -> list[str]:
        return sorted({p.provenance for p in self.partitions if p.symbol == symbol})

    def of(self, symbol: str) -> list[Partition]:
        """Partitions za symbol, kwa mpangilio wa tarehe, zikiwa zimekaguliwa."""
        mine = [p for p in self.partitions if p.symbol == symbol]
        if not mine:
            raise TickError(f"{symbol}: hakuna partition kwenye {self.root}")

        vyanzo = {p.provenance for p in mine}
        if len(vyanzo) > 1:
            raise TickError(
                f"{symbol}: provenance zaidi ya moja ({sorted(vyanzo)}). Data "
                f"ya vyanzo viwili haichanganywi chini ya symbol moja "
                f"(data.yaml §2.2). Chagua kimoja: discover(root, provenance=…)"
            )

        # Faili yenye tarehe isiyosomeka (`day=29 (1)` — nakala ya Windows) ni
        # kwa kawaida siku ile ile mara mbili. Ikipakiwa kimya, ticks za siku
        # hiyo zinahesabiwa maradufu na spread yake inapata uzito maradufu.
        shaka = [p for p in mine if p.shaka]
        if shaka:
            orodha = "\n      ".join(str(p.path) for p in shaka[:10])
            raise TickError(
                f"{symbol}: faili {len(shaka)} zina tarehe isiyosomeka:\n"
                f"      {orodha}\n   Ziondoe au zitaje upya, kisha endesha tena."
            )

        pacha = self.duplicates(symbol)
        if pacha:
            raise TickError(
                f"{symbol}: vipindi vinajirudia ({', '.join(pacha[:5])}). "
                f"Partition mbili za kipindi kimoja zingehesabu ticks maradufu."
            )
        return sorted(mine, key=lambda p: (p.period or "", str(p.path)))

    def duplicates(self, symbol: str) -> list[str]:
        seen: dict[tuple[str, str], int] = {}
        for p in self.partitions:
            if p.symbol == symbol and p.period:
                key = (p.provenance, p.period)
                seen[key] = seen.get(key, 0) + 1
        return sorted({kipindi for (_, kipindi), n in seen.items() if n > 1})

    def render(self) -> str:
        mistari = [
            f"L0 · {self.root}",
            f"   faili {len(self.partitions):,} · symbols {len(self.symbols)} · "
            f"GB {sum(p.size_mb for p in self.partitions) / 1024:.2f}",
        ]
        for symbol in self.symbols:
            mine = [p for p in self.partitions if p.symbol == symbol]
            vipindi = sorted(p.period for p in mine if p.period)
            span = f"{vipindi[0]} → {vipindi[-1]}" if vipindi else "hakuna tarehe"
            mistari.append(
                f"   {symbol:<8} faili {len(mine):>6,}  "
                f"MB {sum(p.size_mb for p in mine):>10,.0f}  "
                f"{'/'.join(v or '-' for v in self.provenances(symbol)):<12} {span}")
        if self.isiyotambulika:
            mistari.append(f"   HAIJATAMBULIKA: faili {len(self.isiyotambulika):,}")
            for path in self.isiyotambulika[:5]:
                mistari.append(f"      {path}")
        return "\n".join(mistari)


def discover(root: Path | str, *, symbols: Sequence[str] | None = None,
             provenance: str | None = None) -> Inventory:
    """Tembea mti wa faili, tambua symbol kutoka njia. Hakuna muundo unaodhaniwa."""
    root = Path(root)
    if not root.exists():
        raise TickError(f"root haipo: {root}")

    inv = Inventory(root=root)
    ruhusa = {s.upper() for s in symbols} if symbols else None

    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in SUFFIXES or not path.is_file():
            continue
        symbol = _symbol_from_path(path, root)
        if symbol is None:
            inv.isiyotambulika.append(path)
            continue
        if ruhusa and symbol not in ruhusa:
            continue
        tags = _tags_from_path(path, root)
        if provenance is not None and tags.get("provenance", "") != provenance:
            continue
        kipindi, shaka = _period_from_tags(tags)
        inv.partitions.append(Partition(
            path=path, symbol=symbol,
            size_mb=round(path.stat().st_size / 1e6, 3),
            provenance=tags.get("provenance", ""), period=kipindi, shaka=shaka))
    return inv


def _tags_from_path(path: Path, root: Path) -> dict[str, str]:
    """`key=value` zote zilizo kwenye njia — `provenance=`, `year=`, `day=`…"""
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    tags: dict[str, str] = {}
    for kipande in rel.parts:
        if "=" in kipande:
            key, value = kipande.split("=", 1)
            tags[key.strip().lower()] = value.strip()
    return tags


def _period_from_tags(tags: dict[str, str]) -> tuple[str, bool]:
    """Kipindi kutoka njia, kwa usahihi wowote uliopo → `(kipindi, shaka)`.

    ```
    year=2016/month=01/day=04/ticks.parquet   →  2016-01-04
    year=2016/month=01/ticks-2016-01.parquet  →  2016-01
    date=2026-04-27/ticks.parquet             →  2026-04-27
    ```
    """
    if "date" in tags:
        value = tags["date"].strip()
        return (value, False) if _ISO_DAY.fullmatch(value) else ("", True)

    vipande: list[str] = []
    for key, upana in (("year", 4), ("month", 2), ("day", 2)):
        if key not in tags:
            break
        raw = tags[key].strip()
        if not raw.isdigit():
            return "-".join(vipande), True
        vipande.append(raw.zfill(upana))
    return "-".join(vipande), False


def _symbol_from_path(path: Path, root: Path) -> str | None:
    """Symbol kutoka njia — folda au jina la faili, chochote kilichopo.

    Kwa `key=value`, thamani pekee ndiyo inayoangaliwa: `symbol=EURUSD` ni
    `EURUSD`, si `SYMBOL`. Na kila mgombea anathibitishwa kuwa **pair halisi**
    kwa sarafu zake mbili — hakuna kinachopita kwa umbo pekee.
    """
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    for kipande in reversed(rel.parts):
        mgombea = kipande.split("=", 1)[1] if "=" in kipande else kipande
        for found in _SIX.finditer(mgombea.upper()):
            pair = found.group(0)
            if pair[:3] in CURRENCIES and pair[3:] in CURRENCIES:
                return pair
    return None


# ===========================================================================
# Kusoma
# ===========================================================================


def normalize(frame, *, source: str = ""):
    """Toleo A au B → schema MOJA: `timestamp` (UTC) · `bid` · `ask`.

    Muda unahifadhiwa **UTC**. Faili isiyo na tz inachukuliwa kuwa tayari UTC —
    ndivyo L0 inavyoandikwa.
    """
    import pandas as pd

    out = frame.rename(columns={k: v for k, v in VOLUME_ALIASES.items()
                                if k in frame.columns})
    safu = next((c for c in TIME_COLUMNS if c in out.columns), None)
    if safu is None:
        raise TickError(f"{source}: hakuna safu ya muda kati ya {TIME_COLUMNS} "
                        f"(zilizopo: {list(out.columns)})")
    if safu != "timestamp":
        out = out.rename(columns={safu: "timestamp"})

    for jina in ("bid", "ask"):
        if jina not in out.columns:
            raise TickError(f"{source}: hakuna safu `{jina}` — §7.4 inadai bid "
                            f"NA ask (zilizopo: {list(out.columns)})")

    out = out.assign(timestamp=pd.to_datetime(out["timestamp"], utc=True),
                     bid=out["bid"].astype(float), ask=out["ask"].astype(float))
    mpangilio = ["timestamp", "bid", "ask"]
    mpangilio += [c for c in ("bid_vol", "ask_vol") if c in out.columns]
    return out[mpangilio]


def read_windows(
    inventory: Inventory,
    symbol: str,
    requests: Sequence[tuple[datetime, int]],
    *,
    partitions: Sequence[Partition] | None = None,
):
    """Ticks za madirisha yaliyoombwa PEKEE — `[mwanzo, mwanzo + sekunde)`.

    Partitions zinazosomwa ni zile zinazogusa siku za madirisha. Kila faili
    inasomwa **mara moja**, kisha rows zinakatwa kwa `searchsorted` kwa kila
    dirisha — si mask kwa kila dirisha, ambayo ingekuwa mara `k` ya kupita
    kwenye rows milioni.

    Dirisha lisilo na tick hata moja **halikosewi hapa**: `clock.vwap`
    ndiyo inayolipuka, ikiwa na tarehe. Hapa tunarudisha kilichopo.
    """
    import numpy as np
    import pandas as pd

    if not requests:
        return normalize(pd.DataFrame({"timestamp": [], "bid": [], "ask": []}))

    zote = list(partitions) if partitions is not None else inventory.of(symbol)
    siku = set()
    for start, sekunde in requests:
        mwisho = start + timedelta(seconds=sekunde)
        siku.add(start.astimezone(_utc()).date())
        siku.add(mwisho.astimezone(_utc()).date())

    teule = [p for p in zote if any(p.covers(d) for d in siku)]
    if not teule:
        raise TickError(
            f"{symbol}: hakuna partition inayogusa siku {min(siku)}→{max(siku)}")

    # Mipaka mara moja, si kwa kila faili.
    mipaka = [(_naive(start), _naive(start + timedelta(seconds=sekunde)))
              for start, sekunde in requests]

    vipande, tupu = [], None
    for p in teule:
        try:
            frame = pd.read_parquet(p.path)
        except Exception as exc:                       # noqa: BLE001
            raise TickError(f"{p.path}: haisomeki ({exc})") from exc
        frame = normalize(frame, source=str(p.path))
        frame = frame.sort_values("timestamp", kind="stable")
        tupu = frame.iloc[0:0] if tupu is None else tupu
        # `tz_localize(None)` inatoa datetime64 halisi; `to_numpy()` kwenye
        # safu yenye tz inarudisha object dtype kwenye pandas nyingine, na
        # `searchsorted` juu ya object ni polepole na isiyo na uhakika.
        t = frame["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None).to_numpy()

        for a, b in mipaka:
            i = np.searchsorted(t, a, side="left")
            j = np.searchsorted(t, b, side="left")
            if j > i:
                vipande.append(frame.iloc[i:j])

    if not vipande:
        return tupu
    out = pd.concat(vipande, ignore_index=True)
    out = out.sort_values("timestamp", kind="stable")
    out = out.drop_duplicates(subset=["timestamp", "bid", "ask"])
    return out.reset_index(drop=True)


def _utc():
    from zoneinfo import ZoneInfo
    return ZoneInfo("UTC")


def _naive(moment: datetime):
    """UTC bila tz, kwa `numpy.datetime64[ns]` — kipimo cha `searchsorted`."""
    import numpy as np
    import pandas as pd

    ts = pd.Timestamp(moment)
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    return np.datetime64(ts.tz_localize(None).to_datetime64(), "ns")


__all__ = ["TickError", "Partition", "Inventory", "discover", "normalize",
           "read_windows", "CURRENCIES"]
