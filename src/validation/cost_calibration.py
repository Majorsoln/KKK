"""Calibration A — injini inapima gharama yake yenyewe (DOCTRINE §8.3, R5, R16).

Namba mbili, chanzo kimoja:

```
research_cost      = ILIYOTOKEA      — kutoka ticks halisi
live_sizing_cost   = KADIRIO         — kutoka RCE, kihafidhina
```

Kudai kwamba backtest na live zina gharama ile ile ni uongo unaojionyesha kama
faida. Kwa hiyo zote mbili zinapimwa, zinaripotiwa kando, na `live ≥ research`
ni **ukaguzi**, si matumaini (R16).

---

**Kinachopimwa kwenye tick, na jinsi gani**

Kila bar inapofungwa, uamuzi unafanyika. Utekelezaji hauwezi kutokea kwenye
quote ile ile — unatokea kwenye **quote inayofuata**, kwa sababu hiyo ndiyo bei
ya kwanza inayoweza kupatikana. Kwa hiyo:

```
mpaka wa bar  t
   quote ya mwisho KABLA ya t   →  bei ya uamuzi
   quote ya kwanza BAADA ya t   →  bei ya kujaza
   tofauti yao                  →  slippage
   ask − bid kwenye quote hiyo  →  spread
```

Hakuna dhana ya latency hapa. Latency ingekuwa constant, na §2 inakataa constants
zisizopimwa; tick inayofuata ni jibu la data yenyewe.

**Slippage inatozwa kwa ukubwa wake wote.** Bila strategy hakuna mwelekeo, kwa hiyo
haiwezekani kujua kama mwendo ulitusaidia au ulitugharimu. Kuchukua `|Δ|` nzima
kunazidisha gharama ya utafiti — na hilo linafanya ukaguzi wa R16 kuwa **mgumu
zaidi**, si rahisi. Ukaguzi unaoshindwa kwa sauti ni bora kuliko unaopita kimya.
Thamani yenye ishara inapimwa kwa kila trade kwenye `backtest/execution.py`.

---

**Muundo wa gharama: mahali ambapo Doctrine na RCE hazilingani**

§8.1 inaweka slippage **mara mbili** — `ENTRY` na `EXIT`. RCE inaihesabu **mara
moja** (`engine.py`: `spread_effective + slippage_cap + comm + swap`), kwa sababu
`slippage_cap` yake ni cap ya `order.deviation` ya kuingia.

RCE HAIGUSWI (R12). Kwa hiyo namba **tatu** zinaripotiwa, kila moja ikijibu swali
lake:

| namba | inajibu | inatumika wapi |
|---|---|---|
| `research_cost_pips` | *gharama halisi ya kwenda-kurudi ni ipi?* | backtest, `cost_sensitivity` |
| `live_sizing_cost_pips` | *RCE itasizisha lots kwa gharama ipi?* | lango la §8.4 (R20) |
| `live_check_pips` | *ulinganisho wa R16 kwa muundo ULE ULE* | ukaguzi `live ≥ research` |

Kuzichanganya kungeficha kitu kimoja mahususi: **exit slippage ambayo sizing ya
RCE haiihesabu**. Inaonekana kwenye `rce_slippage_gap_pips`, na haifichwi.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from src.data.bars import bar_ends
from src.rce.cost import SymbolSpec, commission_pips, pip_size, slippage_cap_pips, spread_effective
from src.rce.cost import swap_pips as rce_swap_pips

# Dirisha la ATR: bars 14 — `ATR_14` ya §21. Sio namba mpya.
ATR_WINDOW = 14


class CalibrationAError(RuntimeError):
    """Gharama haiwezi kupimwa kwa cell hii."""


@dataclass(frozen=True)
class Broker:
    """Ukweli wa broker kwa symbol moja. Unatoka MT5 na `broker_costs.yaml`.

    Hakuna kinachokadiriwa hapa — kila kimoja kina chanzo cha nje.
    """

    spec: SymbolSpec
    pip_value_acct: float
    commission_round_turn: float
    nights: float = 0.0
    triple_nights: float = 0.0
    direction: str = "BUY"
    order_type: str = "market"

    @property
    def symbol(self) -> str:
        return self.spec.symbol


@dataclass(frozen=True)
class CostRow:
    """Cell moja ya `(pair, TF)` — safu zote mbili, pamoja na ukaguzi wake."""

    symbol: str
    timeframe: str
    n_points: int
    n_dropped_gap: int

    # ---- iliyopimwa (ticks halisi) ----
    spread_mean_pips: float
    spread_p50_pips: float
    spread_p95_pips: float
    slippage_mean_pips: float
    slippage_p95_pips: float

    # ---- vipengele vya RCE ----
    commission_pips: float
    swap_pips: float
    live_spread_pips: float
    live_slippage_cap_pips: float

    # ---- jumla tatu (§8.2) ----
    research_cost_pips: float
    live_sizing_cost_pips: float
    live_check_pips: float

    atr_pips: float

    @property
    def research_cost_atr(self) -> float:
        return self.research_cost_pips / self.atr_pips if self.atr_pips > 0 else float("nan")

    @property
    def live_sizing_cost_atr(self) -> float:
        return self.live_sizing_cost_pips / self.atr_pips if self.atr_pips > 0 else float("nan")

    @property
    def cost_sensitivity(self) -> float:
        """`live ÷ research` (§21). Juu = strategy inategemea gharama kubaki nzuri."""
        base = self.research_cost_pips
        return self.live_sizing_cost_pips / base if base > 0 else float("nan")

    @property
    def rce_slippage_gap_pips(self) -> float:
        """Slippage ya kutoka ambayo sizing ya RCE haiihesabu. Haifichwi."""
        return self.live_check_pips - self.live_sizing_cost_pips

    @property
    def ok(self) -> bool:
        """R16 — `live ≥ research` kwa muundo ULE ULE."""
        return self.live_check_pips >= self.research_cost_pips

    def render(self) -> str:
        alama = "OK " if self.ok else "VUNJIKA"
        pengo = f" -{self.n_dropped_gap:,}" if self.n_dropped_gap else ""
        return (
            f"{self.symbol:<8} {self.timeframe:<4} n {self.n_points:>7,}{pengo:<8}  "
            f"research {self.research_cost_pips:>7.3f} pips ({self.research_cost_atr:>5.3f} ATR)  "
            f"live {self.live_sizing_cost_pips:>7.3f}  "
            f"check {self.live_check_pips:>7.3f}  "
            f"sens {self.cost_sensitivity:>5.2f}×  {alama}"
        )

    def render_detail(self) -> str:
        """Vipengele vinne vya §8.1, kando. Jumla peke yake haisemi kilichovunjika."""
        return (
            f"{'':<14}iliyopimwa: spread {self.spread_mean_pips:>7.3f} "
            f"(p95 {self.spread_p95_pips:>7.3f}) · slip {self.slippage_mean_pips:>6.3f} ×2 "
            f"(p95 {self.slippage_p95_pips:>6.3f}) · comm {self.commission_pips:>6.3f}\n"
            f"{'':<14}RCE       : spread {self.live_spread_pips:>7.3f} · "
            f"cap {self.live_slippage_cap_pips:>6.3f} · comm {self.commission_pips:>6.3f} · "
            f"ATR {self.atr_pips:>8.1f} pips"
        )

    def to_json(self) -> dict[str, Any]:
        payload = {k: v for k, v in self.__dict__.items()}
        payload.update({
            "research_cost_atr": self.research_cost_atr,
            "live_sizing_cost_atr": self.live_sizing_cost_atr,
            "cost_sensitivity": self.cost_sensitivity,
            "rce_slippage_gap_pips": self.rce_slippage_gap_pips,
            "ok": self.ok,
        })
        return payload


@dataclass(frozen=True)
class CostTable:
    """Jedwali kamili, pamoja na tarehe — ushahidi wa R5."""

    rows: tuple[CostRow, ...]
    created_at: str = ""
    source: str = ""
    config_hash: str = ""

    def __getitem__(self, key: tuple[str, str]) -> CostRow:
        symbol, timeframe = key
        for row in self.rows:
            if row.symbol == symbol and row.timeframe == timeframe:
                return row
        raise KeyError(f"hakuna cell ({symbol}, {timeframe})")

    @property
    def broken(self) -> tuple[CostRow, ...]:
        return tuple(row for row in self.rows if not row.ok)

    def broken_at(self, timeframe: str) -> tuple[CostRow, ...]:
        """Cells zilizovunjika kwenye TF ya **utekelezaji** pekee.

        R16 inasimamia gharama ya kutekeleza, na R11 inafunga entry H1. Cell ya
        D1 iliyovunjika inasema kitu cha kweli — mpaka wa D1 ni rollover, na
        spread yake ni mara 1.6–4.4 ya ya H1 kwenye symbols ZOTE 12 — lakini
        haisemi kwamba gharama ya kile tunachokitrade imekadiriwa vibaya.

        Kuchanganya mbili hizo kungefanya kimoja kati ya viwili: kusimamisha
        injini kwa TF isiyotekelezwa, au kulegeza R16 hadi isishike kitu.
        """
        return tuple(r for r in self.broken if r.timeframe == timeframe)

    def assert_ok(self) -> "CostTable":
        """R16 — calibration ikivunjika, injini inasimama. Haiendelei kwa onyo."""
        if self.broken:
            mbaya = ", ".join(f"{r.symbol}/{r.timeframe}" for r in self.broken)
            raise CalibrationAError(
                f"`live < research` kwenye cells: {mbaya} — R16 imevunjika, injini inasimama"
            )
        return self

    def render(self, detail: bool = True) -> str:
        lines = [f"CALIBRATION A · cells {len(self.rows)} · {self.created_at}"]
        for row in self.rows:
            lines.append("   " + row.render())
            if detail or not row.ok:
                lines.append(row.render_detail())
        if self.broken:
            lines.append(f"   VUNJIKA: cells {len(self.broken)} zina `live < research` (R16)")
        pengo = [r for r in self.rows if r.rce_slippage_gap_pips > 0]
        if pengo:
            kubwa = max(r.rce_slippage_gap_pips for r in pengo)
            lines.append(
                f"   KUMBUKA: sizing ya RCE haihesabu slippage ya kutoka "
                f"(hadi pips {kubwa:.2f}); backtest inaihesabu kwenye path"
            )
        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at, "source": self.source,
            "config_hash": self.config_hash,
            "atr_window": ATR_WINDOW,
            "rows": [row.to_json() for row in self.rows],
        }

    def write(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_json(), indent=2, default=str) + "\n",
            encoding="utf-8", newline="\n",
        )
        return path

    @classmethod
    def read(cls, path: Path) -> "CostTable":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        fields = CostRow.__dataclass_fields__
        rows = tuple(
            CostRow(**{k: v for k, v in row.items() if k in fields}) for row in raw["rows"]
        )
        return cls(rows=rows, created_at=raw.get("created_at", ""),
                   source=raw.get("source", ""), config_hash=raw.get("config_hash", ""))


# ===========================================================================
# Kipimo
# ===========================================================================


def execution_samples(ticks, bars, timeframe: str, *, symbol: str,
                      day_tz: str = "UTC", max_gap_seconds: float | None = None):
    """Sampuli ghafi za spread na slippage kwenye kila mpaka wa bar.

    `max_gap_seconds` inatenganisha **utekelezaji** na **soko lililofungwa**.

    Mpaka wa bar unapoangukia Ijumaa usiku, quote inayofuata ni ya Jumapili
    usiku. Tofauti kati yao si slippage — ni pengo la wikendi, na linaweza kuwa
    pips 50. Bila kizuizi, mipaka hiyo (asilimia 1 kwa H1, asilimia 20 kwa D1)
    ingepandisha `slippage_mean` kwa kiasi kikubwa, `research_cost` ingeonekana
    kubwa kuliko ilivyo, na R16 ingevunjika kwa sababu isiyo ya gharama.

    Kizingiti kinatoka `data.yaml: quality.max_gap_seconds` — si kubuniwa hapa.
    """
    import numpy as np
    import pandas as pd

    missing = {"timestamp", "bid", "ask"} - set(ticks.columns)
    if missing:
        raise CalibrationAError(f"ticks hazina {sorted(missing)} — §4.1 inadai bid/ask")
    if len(bars) == 0:
        raise CalibrationAError(f"hakuna bars za {symbol}/{timeframe}")

    stamps = pd.DatetimeIndex(pd.to_datetime(ticks["timestamp"], utc=True)).as_unit("ns")
    stamps_ns = stamps.view("int64")
    bid = ticks["bid"].to_numpy(dtype=float)
    ask = ticks["ask"].to_numpy(dtype=float)
    mid = (bid + ask) / 2.0
    pip = pip_size(symbol)

    ends = pd.DatetimeIndex(bar_ends(bars.index, timeframe, day_tz)).as_unit("ns")
    fill = np.searchsorted(stamps_ns, ends.view("int64"), side="left")

    # Mpaka unaotokea kabla ya tick ya kwanza hauna quote ya uamuzi; unaotokea
    # baada ya ya mwisho hauna quote ya kujaza. Vyote viwili vinatolewa nje —
    # kuvijaza kwa jirani kungebuni bei ambayo haikuwahi kuwepo.
    halali = (fill > 0) & (fill < len(stamps))
    fill = fill[halali]
    if fill.size == 0:
        raise CalibrationAError(
            f"{symbol}/{timeframe}: hakuna mpaka wa bar wenye quote pande zote mbili"
        )

    n_dropped = 0
    if max_gap_seconds is not None:
        gap = (stamps_ns[fill] - stamps_ns[fill - 1]) / 1e9
        ndani = gap <= float(max_gap_seconds)
        n_dropped = int((~ndani).sum())
        fill = fill[ndani]

    spread = (ask[fill] - bid[fill]) / pip
    slippage = np.abs(mid[fill] - mid[fill - 1]) / pip
    return spread, slippage, n_dropped


def summarise(spread, slippage, n_dropped: int = 0) -> dict[str, float]:
    """Sampuli → takwimu za cell."""
    import numpy as np

    spread = np.asarray(spread, dtype=float)
    slippage = np.asarray(slippage, dtype=float)
    if spread.size == 0:
        raise CalibrationAError("hakuna sampuli za kufupisha")
    return {
        "n_points": int(spread.size),
        "n_dropped_gap": int(n_dropped),
        "spread_mean_pips": float(spread.mean()),
        "spread_p50_pips": float(np.quantile(spread, 0.50)),
        "spread_p95_pips": float(np.quantile(spread, 0.95)),
        "slippage_mean_pips": float(slippage.mean()),
        "slippage_p95_pips": float(np.quantile(slippage, 0.95)),
    }


def measure_execution(ticks, bars, timeframe: str, *, symbol: str,
                      day_tz: str = "UTC",
                      max_gap_seconds: float | None = None) -> dict[str, float]:
    """Spread na slippage kwenye kila mpaka wa bar — kutoka ticks, si kudhaniwa."""
    return summarise(
        *execution_samples(ticks, bars, timeframe, symbol=symbol, day_tz=day_tz,
                           max_gap_seconds=max_gap_seconds)
    )


@dataclass
class CellSamples:
    """Mkusanyiko wa sampuli za cell moja, mwezi baada ya mwezi.

    Data ya miaka 10 haiingii kwenye kumbukumbu kwa mara moja. Kwa hiyo kila
    mwezi unapimwa peke yake na sampuli zinakusanywa; takwimu zinahesabiwa
    mwishoni, juu ya sampuli **zote**. Hakuna wastani wa wastani hapa —
    quantile ya quantiles si quantile.
    """

    symbol: str
    timeframe: str
    max_gap_seconds: float | None = None
    n_dropped_gap: int = 0
    n_vipande_tupu: int = 0
    _spread: list = None
    _slippage: list = None
    _atr: list = None

    def __post_init__(self) -> None:
        self._spread, self._slippage, self._atr = [], [], []

    def add(self, ticks, bars, *, day_tz: str = "UTC") -> "CellSamples":
        """Ongeza kipande kimoja.

        Kipande kisicho na mpaka hata mmoja halali **si kosa la kufa nacho**.
        Mwezi mmoja wa D1 unaweza kuwa na mipaka yote ikianguka kwenye pengo la
        feed; kusimamisha run nzima hapo kungetupa saa za kazi kwa taarifa
        ambayo ni ya mwezi mmoja. Inahesabiwa (`n_vipande_tupu`) na kuonekana.
        Kosa linakuja mwishoni ikiwa cell NZIMA haina sampuli.
        """
        spread, slippage, dropped = execution_samples(
            ticks, bars, self.timeframe, symbol=self.symbol, day_tz=day_tz,
            max_gap_seconds=self.max_gap_seconds,
        )
        self.n_dropped_gap += dropped
        if len(spread) == 0:
            self.n_vipande_tupu += 1
            return self
        self._spread.append(spread)
        self._slippage.append(slippage)
        if len(bars) > ATR_WINDOW:
            self._atr.append(atr_pips(bars, self.symbol))
        return self

    @property
    def n_chunks(self) -> int:
        return len(self._spread)

    def stats(self) -> dict[str, float]:
        import numpy as np

        if not self._spread:
            raise CalibrationAError(
                f"{self.symbol}/{self.timeframe}: hakuna sampuli hata moja "
                f"({self.n_vipande_tupu} vipande, mipaka {self.n_dropped_gap} nje ya session)"
            )
        return summarise(np.concatenate(self._spread), np.concatenate(self._slippage),
                         self.n_dropped_gap)

    def atr(self) -> float:
        """Median ya ATR za vipande — kipimo kimoja cha ukubwa wa mwendo."""
        import numpy as np

        if not self._atr:
            raise CalibrationAError(
                f"{self.symbol}/{self.timeframe}: hakuna kipande chenye bars > {ATR_WINDOW}"
            )
        return float(np.median(self._atr))


def atr_pips(bars, symbol: str, window: int = ATR_WINDOW) -> float:
    """Wastani wa `ATR_14` kwa pips (§21) — kipimo cha ukubwa wa mwendo."""
    import numpy as np

    high = bars["high"].to_numpy(dtype=float)
    low = bars["low"].to_numpy(dtype=float)
    close = bars["close"].to_numpy(dtype=float)
    if len(close) <= window:
        raise CalibrationAError(f"bars {len(close)} <= dirisha la ATR {window}")

    prev = close[:-1]
    tr = np.maximum(
        high[1:] - low[1:],
        np.maximum(np.abs(high[1:] - prev), np.abs(low[1:] - prev)),
    )
    # Wastani wa kusonga wa `window`, kisha wastani wake — kipimo kimoja kwa cell.
    kernel = np.ones(window) / window
    atr = np.convolve(tr, kernel, mode="valid")
    return float(np.median(atr) / pip_size(symbol))


def live_spread_median(h1, m5, cfg, *, step: int = 100) -> float:
    """`spread_effective` ya RCE ikitathminiwa mara nyingi kwenye historia.

    RCE inaangalia bars 100 za mwisho za H1 na 288 za mwisho za M5 (`risk.yaml`).
    Kuiita **mara moja** juu ya miaka 9 kungetoa jibu la siku nne za mwisho, na
    jedwali la calibration lingesema "gharama ya live" wakati likimaanisha
    "gharama ya wiki iliyopita".

    Kwa hiyo inaitwa kwenye nanga nyingi na median inachukuliwa. Hesabu bado ni
    ya RCE, kila mara — hakuna inayoandikwa upya hapa (R12).
    """
    import numpy as np
    import pandas as pd

    h1 = pd.Series(h1).dropna()
    m5 = pd.Series(m5).dropna()
    if h1.empty:
        raise CalibrationAError("hakuna spread za H1 — upande wa live hauwezi kupimwa")

    base_window = int(cfg.get("spread_model.base_window", 100))
    anchors = h1.index[base_window::step]
    if len(anchors) == 0:
        anchors = h1.index[-1:]

    values = [
        spread_effective(
            h1.loc[:t].to_list(), m5.loc[:t].to_list() if not m5.empty else [], cfg
        )
        for t in anchors
    ]
    return float(np.median(values))


def calibrate_cell(*, timeframe: str, cfg_risk, broker: Broker,
                   h1_spreads: Sequence[float] = (), m5_spreads: Sequence[float] = (),
                   live_spread: float | None = None,
                   ticks=None, bars=None, samples: "CellSamples | None" = None,
                   m5_slippage_estimate: float | None = None,
                   max_gap_seconds: float | None = None,
                   day_tz: str = "UTC") -> CostRow:
    """Cell moja ya `(pair, TF)`. Upande wa live unatoka RCE, hauhesabiwi hapa (R12).

    Ingizo la kipimo ni **mojawapo**: `ticks` + `bars` (data ndogo, mara moja) au
    `samples` (mkusanyiko wa miezi mingi).
    """
    symbol = broker.symbol
    if samples is not None:
        measured, atr = samples.stats(), samples.atr()
    elif ticks is not None and bars is not None:
        measured = measure_execution(ticks, bars, timeframe, symbol=symbol,
                                     day_tz=day_tz, max_gap_seconds=max_gap_seconds)
        atr = atr_pips(bars, symbol)
    else:
        raise CalibrationAError("toa `ticks` + `bars`, au `samples` — si bila kimoja")

    comm = commission_pips(broker.commission_round_turn, broker.pip_value_acct)
    swap = (
        rce_swap_pips(broker.direction, broker.spec, broker.nights,
                      broker.pip_value_acct, broker.triple_nights)
        if broker.nights > 0 else 0.0
    )

    if live_spread is None:
        live_spread = spread_effective(list(h1_spreads), list(m5_spreads), cfg_risk)
    live_cap = slippage_cap_pips(
        broker.order_type, cfg_risk, m5_slippage_estimate, symbol=symbol
    )

    # §8.1: spread kamili (nusu kuingia + nusu kutoka) + slippage MARA MBILI.
    research = (
        measured["spread_mean_pips"] + 2.0 * measured["slippage_mean_pips"] + comm + swap
    )
    # §8.2: namba ya RCE, kama RCE inavyoihesabu — slippage mara moja.
    live_sizing = live_spread + live_cap + comm + swap
    # R16: ulinganisho wa muundo ULE ULE.
    live_check = live_spread + 2.0 * live_cap + comm + swap

    return CostRow(
        symbol=symbol, timeframe=timeframe,
        n_points=int(measured["n_points"]),
        n_dropped_gap=int(measured.get("n_dropped_gap", 0)),
        spread_mean_pips=measured["spread_mean_pips"],
        spread_p50_pips=measured["spread_p50_pips"],
        spread_p95_pips=measured["spread_p95_pips"],
        slippage_mean_pips=measured["slippage_mean_pips"],
        slippage_p95_pips=measured["slippage_p95_pips"],
        commission_pips=float(comm), swap_pips=float(swap),
        live_spread_pips=float(live_spread), live_slippage_cap_pips=float(live_cap),
        research_cost_pips=float(research),
        live_sizing_cost_pips=float(live_sizing),
        live_check_pips=float(live_check),
        atr_pips=float(atr),
    )


def calibrate(cells: Sequence[dict], *, source: str = "", config_hash: str = "",
              progress=print) -> CostTable:
    """Cells zote. R23 — kila moja inachapishwa inapokamilika."""
    rows = []
    for kw in cells:
        row = calibrate_cell(**kw)
        rows.append(row)
        if progress:
            progress("   " + row.render())
    return CostTable(
        rows=tuple(rows),
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source=source, config_hash=config_hash,
    )
