"""Kupakia L0 — partitions za diski hadi frame ya ticks (DOCTRINE §4.1, R18).

Moduli hii **haijui** muundo wa folda zako. Inautafuta.

Sababu si uvivu: muundo uliodhaniwa unashindwa kimya. Njia inayoisha kwa
`symbol=EURUSD/` ikiwa halisi ni `EURUSD/2016/`, glob inarudisha faili sifuri,
na calibration inaripoti "cells 0" badala ya kosa. Kwa hiyo `discover()` inatembea
mti wa faili na kutambua symbol kutoka **njia yenyewe**, na inachapisha
ilichokiona kabla ya chochote kingine kutokea.

---

**Schema mbili, frame moja (§4.1, data.yaml `source.schema_variants`)**

```
Toleo A : timestamp · bid · ask · bid_vol · ask_vol       (µs)
Toleo B : ts        · bid · ask · bid_volume · ask_volume (ms)
```

Zinabadilishwa kuwa schema MOJA hapa. Kila mahali pengine kwenye injini kuna
`timestamp`, `bid`, `ask` — na hakuna sehemu inayohitaji kujua toleo lipi
lilitoka wapi.

**Mpaka unatangazwa, hausahauliki.** `load_ticks` inadai `Stage` — si tarehe
mbili. Kwa hiyo hakuna njia ya kuiita bila kutangaza dirisha, na `clip` (R18)
inatumika kabla ya row yoyote kutoka.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence

from .quality import QualityError, QualityReport, check_ticks
from .window import Stage, clip

# Majina yanayowezekana ya safu ya muda, kwa mpangilio wa kutafutwa.
TIME_COLUMNS = ("timestamp", "ts", "time", "datetime", "date_time")
BID_COLUMNS = ("bid",)
ASK_COLUMNS = ("ask",)
VOLUME_ALIASES = {
    "bid_volume": "bid_vol", "ask_volume": "ask_vol",
    "bidvolume": "bid_vol", "askvolume": "ask_vol",
    "volume_bid": "bid_vol", "volume_ask": "ask_vol",
}

SUFFIXES = (".parquet", ".pq")

# Sarafu zinazotambulika. Orodha ipo kwa sababu **umbo pekee halitoshi**:
# folda iitwayo `symbol=EURUSD` ina neno `SYMBOL` — herufi sita kubwa, sawa
# kabisa na umbo la pair. Bila ukaguzi wa sarafu, kila partition ingewekwa
# chini ya symbol iitwayo "SYMBOL", na calibration ingeripoti cell moja kubwa
# yenye pairs zote ndani yake. Si kosa linaloonekana; ni jedwali lisilo sahihi.
CURRENCIES = frozenset({
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
    "XAU", "XAG", "SEK", "NOK", "DKK", "PLN", "HUF", "CZK",
    "TRY", "ZAR", "MXN", "SGD", "HKD", "CNH", "RUB",
})

_SIX = re.compile(r"[A-Z]{6}")


class LoadError(RuntimeError):
    """Data ya L0 haiwezi kupakiwa kama ilivyoombwa."""


@dataclass(frozen=True)
class Partition:
    """Faili moja ya L0, pamoja na kile kinachojulikana kuihusu kutoka njia yake."""

    path: Path
    symbol: str
    size_mb: float
    provenance: str = ""

    # Kipindi kwa **usahihi ulioandikwa kwenye njia**: `YYYY-MM-DD`, `YYYY-MM`,
    # `YYYY`, au tupu. Partitions za kila siku na za kila mwezi zinaishi pamoja
    # kwenye L0 moja (`day=04/` dhidi ya `ticks-2016-01.parquet`), kwa hiyo
    # kudai usahihi wa siku kwa zote kungefanya nusu yao zionekane hazina tarehe.
    period: str = ""
    shaka: bool = False    # tag ya tarehe ipo lakini haisomeki

    @property
    def order(self) -> tuple[str, str]:
        """Ufunguo wa mpangilio: kipindi kwanza, njia kama mrejeshi."""
        return (self.period or "", str(self.path))

    @property
    def month(self) -> str:
        return self.period[:7] if len(self.period) >= 7 else ""

    def to_json(self) -> dict[str, Any]:
        return {"path": str(self.path), "symbol": self.symbol, "size_mb": self.size_mb,
                "provenance": self.provenance, "period": self.period, "shaka": self.shaka}


@dataclass
class Inventory:
    """Kila kitu kilichopo kwenye diski, kabla chochote hakijasomwa."""

    root: Path
    partitions: list[Partition] = field(default_factory=list)
    isiyotambulika: list[Path] = field(default_factory=list)
    zilizotolewa: list[tuple] = field(default_factory=list)   # (path, Exclusion)

    def matched(self, kifungu: "Exclusion") -> int:
        """Faili ngapi kifungu hiki kimezitoa. Sifuri = kifungu hakifanyi kazi."""
        return sum(1 for _, e in self.zilizotolewa if e is kifungu)

    @property
    def excluded_summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for _, kifungu in self.zilizotolewa:
            out[kifungu.render()] = out.get(kifungu.render(), 0) + 1
        return out

    @property
    def symbols(self) -> list[str]:
        return sorted({p.symbol for p in self.partitions})

    def provenances(self, symbol: str) -> list[str]:
        return sorted({p.provenance for p in self.partitions if p.symbol == symbol})

    def raw(self, symbol: str) -> list[Partition]:
        """Partitions zote za symbol bila kizuizi cha provenance — kwa kuripoti.

        `of()` inakataa vyanzo viwili kwa sababu haipaswi kupima data
        iliyochanganywa. Ripoti inapaswa **kuionyesha**, kwa hiyo hii ipo.
        """
        return sorted(
            (p for p in self.partitions if p.symbol == symbol), key=lambda p: p.order
        )

    def of(self, symbol: str) -> list[Partition]:
        """Partitions za symbol, **kwa mpangilio wa tarehe**.

        Kupanga kwa njia ya faili kungetosha kwa chanzo kimoja. Chanzo cha pili
        kinapoingia — `provenance=broker` ikianza kurekodi kando ya
        `provenance=aggregator` — njia inaanza na provenance, kwa hiyo mpangilio
        wa maandishi ungeweka feed nzima ya kwanza kabla ya ya pili, na miaka
        ingerudi nyuma katikati ya mtiririko. Tarehe ndiyo ukweli, si njia.
        """
        mine = [p for p in self.partitions if p.symbol == symbol]
        vyanzo = {p.provenance for p in mine}
        if len(vyanzo) > 1:
            raise LoadError(
                f"{symbol}: provenance zaidi ya moja ({sorted(vyanzo)}). Data ya vyanzo "
                f"viwili haichanganywi chini ya symbol moja (data.yaml §2.2). "
                f"Chagua kimoja: discover(root, provenance=...)"
            )

        # Faili yenye tarehe isiyosomeka haiwezi kuwekwa kwenye muda, na
        # Calibration A inaweka kila kitu kwenye muda. Karibu daima ni nakala ya
        # siku iliyopo tayari — ikipakiwa, ticks za siku hiyo zinahesabiwa
        # maradufu, na spread yake inapata uzito maradufu bila kosa kuonekana.
        zenye_shaka = [p for p in mine if p.shaka]
        if zenye_shaka:
            orodha = "\n      ".join(str(p.path) for p in zenye_shaka[:10])
            raise LoadError(
                f"{symbol}: faili {len(zenye_shaka)} zina tarehe isiyosomeka kwenye njia:\n"
                f"      {orodha}\n"
                f"   Kwa kawaida ni nakala (`day=29 (1)`). Ziondoe au zitaje upya, "
                f"kisha endesha tena."
            )

        pacha = self.duplicates(symbol)
        if pacha:
            raise LoadError(
                f"{symbol}: vipindi vinajirudia ({', '.join(pacha[:5])}). Partition mbili "
                f"za kipindi kile kile zingehesabu ticks zake maradufu."
            )
        return sorted(mine, key=lambda p: p.order)

    def duplicates(self, symbol: str) -> list[str]:
        """Vipindi vinavyojirudia **ndani ya chanzo kimoja** — partition mbili za siku moja.

        Ndani ya chanzo kimoja, kipindi kinachojirudia ni kosa: ticks za siku
        hiyo zingehesabiwa maradufu. **Kati** ya vyanzo si kosa — ni mwingiliano,
        na unatatuliwa kwa kuchagua chanzo (`overlaps`).
        """
        seen: dict[tuple[str, str], int] = {}
        for p in self.partitions:
            if p.symbol == symbol and p.period:
                key = (p.provenance, p.period)
                seen[key] = seen.get(key, 0) + 1
        return sorted({period for (_, period), n in seen.items() if n > 1})

    def overlaps(self, symbol: str) -> list[str]:
        """Vipindi vilivyopo kwenye vyanzo ZAIDI ya kimoja.

        Si kosa: recorder inapoanza kurekodi wakati aggregator bado inaendelea,
        siku chache zinaandikwa mara mbili kwa vyanzo tofauti. Ni taarifa
        inayohitaji uamuzi — chanzo kipi ndicho ukweli kwa siku hizo.
        """
        kwa_kipindi: dict[str, set[str]] = {}
        for p in self.partitions:
            if p.symbol == symbol and p.period:
                kwa_kipindi.setdefault(p.period, set()).add(p.provenance)
        return sorted(k for k, v in kwa_kipindi.items() if len(v) > 1)

    @property
    def zenye_shaka(self) -> list[Partition]:
        return [p for p in self.partitions if p.shaka]

    def render(self) -> str:
        lines = [
            f"L0 · {self.root}",
            f"   faili {len(self.partitions):,} · symbols {len(self.symbols)} · "
            f"GB {sum(p.size_mb for p in self.partitions) / 1024:.2f}",
        ]
        for symbol in self.symbols:
            mine = [p for p in self.partitions if p.symbol == symbol]
            mb = sum(p.size_mb for p in mine)
            vyanzo = self.provenances(symbol)
            vipindi = sorted(p.period for p in mine if p.period)
            span = f"{vipindi[0]} -> {vipindi[-1]}" if vipindi else "tarehe haiko kwenye njia"
            alama = " CHANZO ZAIDI YA KIMOJA" if len(vyanzo) > 1 else ""
            if any(p.shaka for p in mine):
                alama += " TAREHE ISIYOSOMEKA"
            lines.append(
                f"   {symbol:<8} faili {len(mine):>6,}  MB {mb:>10,.0f}  "
                f"{'/'.join(v or '-' for v in vyanzo):<12} {span}{alama}"
            )
        if self.isiyotambulika:
            lines.append(f"   HAIJATAMBULIKA: faili {len(self.isiyotambulika):,}")
            for path in self.isiyotambulika[:5]:
                lines.append(f"      {path}")
        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "symbols": self.symbols,
            "n_partitions": len(self.partitions),
            "unrecognised": [str(p) for p in self.isiyotambulika[:50]],
        }


@dataclass(frozen=True)
class Exclusion:
    """Kifungu cha `data.yaml: quality.excluded_ranges` — uamuzi wa PD, si check.

    Checks za §4.3 zinakamata siku moja moja; zinashindwa pale kasoro ni ya
    **kipindi**. Kifungu hiki ndicho jibu, na kina sababu iliyoandikwa. Kwa hiyo
    kinaingia `config_hash`, na kupuuza kwake si uzembe — ni kutumia dataset
    tofauti na iliyoidhinishwa.
    """

    symbols: frozenset[str]
    start: str
    end: str
    reason: str = ""

    def covers(self, symbol: str, period: str) -> bool:
        if symbol.upper() not in self.symbols or not period:
            return False
        n = len(period)
        return self.start[:n] <= period <= self.end[:n]

    def render(self) -> str:
        return (f"{'/'.join(sorted(self.symbols))} · {self.start} -> {self.end}"
                f"{' · ' + self.reason.split('.')[0] if self.reason else ''}")


def load_exclusions(cfg) -> list[Exclusion]:
    """Vifungu vya `quality.excluded_ranges`, kama vilivyoandikwa."""
    out = []
    for item in (cfg.get("quality.excluded_ranges", []) or []):
        out.append(Exclusion(
            symbols=frozenset(s.upper() for s in item.get("symbols", [])),
            start=str(item["from"]), end=str(item["to"]),
            reason=str(item.get("reason", "")).strip(),
        ))
    return out


def discover(root: Path | str, *, symbols: Sequence[str] | None = None,
             provenance: str | None = None,
             exclusions: Sequence[Exclusion] = ()) -> Inventory:
    """Tembea mti wa faili, tambua symbol kutoka njia. Hakuna muundo unaodhaniwa."""
    root = Path(root)
    if not root.exists():
        raise LoadError(f"root haipo: {root}")

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
        if provenance and tags.get("provenance", "") != provenance:
            continue
        period, shaka = _period_from_tags(tags)
        kifungu = next((e for e in exclusions if e.covers(symbol, period)), None)
        if kifungu is not None:
            inv.zilizotolewa.append((path, kifungu))
            continue
        inv.partitions.append(
            Partition(path=path, symbol=symbol,
                      size_mb=round(path.stat().st_size / 1e6, 3),
                      provenance=tags.get("provenance", ""), period=period, shaka=shaka)
        )
    return inv


def _tags_from_path(path: Path, root: Path) -> dict[str, str]:
    """`key=value` zote zilizo kwenye njia — `provenance=`, `year=`, `month=`, `day=`."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    tags: dict[str, str] = {}
    for piece in rel.parts:
        if "=" in piece:
            key, value = piece.split("=", 1)
            tags[key.strip().lower()] = value.strip()
    return tags


_ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


def _period_from_tags(tags: dict[str, str]) -> tuple[str, bool]:
    """Kipindi kutoka njia, kwa usahihi wowote uliopo. Rudi na `(kipindi, shaka)`.

    Miundo miwili inaonekana kwenye L0 moja:

    ```
    year=2016/month=01/day=04/ticks.parquet   ->  2016-01-04
    year=2016/month=01/ticks-2016-01.parquet  ->  2016-01
    date=2026-04-27/ticks.parquet             ->  2026-04-27
    ```

    `shaka` inawaka pale tag ipo lakini haisomeki — mf. `day=29 (1)`, ambayo ni
    nakala ya Windows. Faili ya namna hiyo si "isiyo na tarehe"; ni faili ambayo
    tarehe yake **inaonekana lakini si ya kuaminika**, na kwa kawaida ni siku ile
    ile mara mbili. Ikipakiwa kimya, ticks za siku hiyo zinahesabiwa maradufu.
    """
    if "date" in tags:
        value = tags["date"].strip()
        return (value, False) if _ISO_DAY.fullmatch(value) else ("", True)

    pieces: list[str] = []
    for key, width in (("year", 4), ("month", 2), ("day", 2)):
        if key not in tags:
            break
        raw = tags[key].strip()
        if not raw.isdigit():
            return "-".join(pieces), True
        pieces.append(raw.zfill(width))
    return "-".join(pieces), False


def _symbol_from_path(path: Path, root: Path) -> str | None:
    """Symbol inatoka kwenye njia — folda au jina la faili, chochote kilichopo.

    Kwa `key=value`, thamani pekee ndiyo inayoangaliwa: `symbol=EURUSD` ni
    `EURUSD`, si `SYMBOL`. Na kila mgombea anathibitishwa kuwa **pair halisi**
    kwa kuangalia sarafu zake mbili — hakuna kinachopita kwa umbo pekee.
    """
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    for piece in reversed(rel.parts):
        candidate = piece.split("=", 1)[1] if "=" in piece else piece
        for found in _SIX.finditer(candidate.upper()):
            pair = found.group(0)
            if pair[:3] in CURRENCIES and pair[3:] in CURRENCIES:
                return pair
    return None


def read_partition(path: Path, *, columns: Sequence[str] | None = None):
    """Soma faili MOJA na uinormalize kuwa schema ya §4.1."""
    import pandas as pd

    try:
        frame = pd.read_parquet(path, columns=list(columns) if columns else None)
    except Exception as exc:  # pragma: no cover - inategemea faili halisi
        raise LoadError(f"{path}: haisomeki ({exc})") from exc
    return normalize(frame, source=str(path))


def normalize(frame, *, source: str = ""):
    """Toleo A au B → schema MOJA: `timestamp` (UTC), `bid`, `ask`, volumes.

    Muda unahifadhiwa **UTC** (`data.yaml: timezone.storage_tz`). Faili isiyo na
    tz inachukuliwa kuwa tayari UTC — ndivyo L0 inavyoandikwa; ikiwa si hivyo,
    `quality.timezone` itaikamata, si hapa.
    """
    import pandas as pd

    out = frame.rename(columns={k: v for k, v in VOLUME_ALIASES.items() if k in frame.columns})

    time_col = next((c for c in TIME_COLUMNS if c in out.columns), None)
    if time_col is None:
        raise LoadError(
            f"{source}: hakuna safu ya muda kati ya {TIME_COLUMNS} "
            f"(zilizopo: {list(out.columns)})"
        )
    if time_col != "timestamp":
        out = out.rename(columns={time_col: "timestamp"})

    for name, options in (("bid", BID_COLUMNS), ("ask", ASK_COLUMNS)):
        if name not in out.columns:
            alt = next((c for c in options if c in out.columns), None)
            if alt is None:
                raise LoadError(
                    f"{source}: hakuna safu `{name}` — §4.1 inadai bid NA ask "
                    f"(zilizopo: {list(out.columns)})"
                )
            out = out.rename(columns={alt: name})

    stamps = pd.to_datetime(out["timestamp"], utc=True)
    out = out.assign(timestamp=stamps, bid=out["bid"].astype(float),
                     ask=out["ask"].astype(float))

    ordered = ["timestamp", "bid", "ask"]
    ordered += [c for c in ("bid_vol", "ask_vol") if c in out.columns]
    ordered += [c for c in out.columns if c not in ordered]
    return out[ordered]


def load_ticks(inventory: Inventory, symbol: str, stage: Stage, *,
               max_spread_pips: float | None = None, pip: float | None = None,
               strict: bool = True) -> tuple[Any, QualityReport]:
    """Ticks zote za `symbol` ndani ya dirisha la `stage`, zikiwa zimekaguliwa.

    Hatua ni **za mpangilio huu kwa makusudi**: soma → panga → kata → kagua.
    Kukagua kabla ya kukata kungeripoti kasoro za data ambayo hatua hii
    haitakayoiona kamwe; kukata kabla ya kupanga kungeacha rows za mpakani
    kutoka faili zisizopangwa.
    """
    import pandas as pd

    chunks = [read_partition(p.path) for p in inventory.of(symbol)]
    if not chunks:
        raise LoadError(f"{symbol}: hakuna partition kwenye {inventory.root}")

    frame = pd.concat(chunks, ignore_index=True)
    frame = frame.sort_values("timestamp", kind="stable").reset_index(drop=True)
    frame = clip(frame, stage).reset_index(drop=True)
    frame.attrs["symbol"] = symbol

    report = check_ticks(frame, stage, max_spread_pips=max_spread_pips, pip=pip)
    if strict and not report.passed:
        raise QualityError(f"{symbol}: ukaguzi wa §4.3 umeshindwa\n{report.render()}")
    return frame, report


def iter_months(inventory: Inventory, symbol: str, stage: Stage, *,
                max_spread_pips: float | None = None, pip: float | None = None,
                strict: bool = False) -> Iterator[tuple[Any, Any, QualityReport]]:
    """Toa ticks **mwezi kwa mwezi** — kwa data isiyotoshea kwenye kumbukumbu.

    Miaka 10 ya ticks za symbol moja ni rows milioni mia kadhaa. Kuzipakia zote
    kwa mara moja kunasimamisha mashine, na mashine iliyosimama haitoi jibu
    lolote — wala si la kukosea.

    Gharama ya kupasua ni **bar ya mwisho ya kila mwezi** (`bars.build` haitoi
    bar isiyofungwa). Ni bar 1 kati ya ~500 kwa H1: haibadilishi mgawanyo,
    na inaonekana hapa badala ya kufichwa.
    """
    import pandas as pd

    for path, chunk in _grouped_by_month(inventory, symbol, stage):
        chunk = chunk.sort_values("timestamp", kind="stable").reset_index(drop=True)
        chunk = clip(chunk, stage).reset_index(drop=True)
        if chunk.empty:
            continue
        chunk.attrs["symbol"] = symbol
        report = check_ticks(chunk, stage, max_spread_pips=max_spread_pips, pip=pip)
        if strict and not report.passed:
            raise QualityError(f"{symbol} {path}: ukaguzi wa §4.3 umeshindwa\n{report.render()}")
        yield path, chunk, report


def _grouped_by_month(inventory: Inventory, symbol: str, stage: Stage):
    """Kusanya partitions hadi mwezi ubadilike, kisha toa.

    Mwezi unatoka kwenye **njia** pale `year=`/`month=` zipo — hakuna faili
    inayosomwa ili kujua ni ya lini. Zisipokuwepo, timestamp ya kwanza
    inatumika, na hapo faili inasomwa mara moja tu.
    """
    import pandas as pd

    buffer: list[Any] = []
    label: str | None = None
    lo, hi = str(stage.window.start), str(stage.window.end)

    for part in inventory.of(symbol):
        # Faili iliyo NJE ya dirisha haifunguliwi kabisa. `clip` bado inaendeshwa
        # baadaye — hii inaondoa kusoma tu, si ukaguzi. Kwa dirisha la utafiti
        # linaloishia 2024-03 wakati diski ina hadi 2026-08, ni robo ya data
        # ambayo ingesomwa kisha kutupwa.
        #
        # Ulinganisho ni kwa **usahihi wa kipindi chenyewe**: faili ya mwezi
        # `2024-03` inalinganishwa na `2024-03`, si na `2024-03-31`. Kudai
        # usahihi wa siku kungetupa mwezi mzima wa mwisho wa dirisha.
        if part.period:
            n = len(part.period)
            if not (lo[:n] <= part.period <= hi[:n]):
                continue

        frame = read_partition(part.path)
        if frame.empty:
            continue
        mwezi = part.month or pd.Timestamp(
            frame["timestamp"].iloc[0]
        ).strftime("%Y-%m")
        if label is not None and mwezi != label and buffer:
            yield label, pd.concat(buffer, ignore_index=True)
            buffer = []
        label = mwezi
        buffer.append(frame)

    if buffer and label is not None:
        yield label, pd.concat(buffer, ignore_index=True)
