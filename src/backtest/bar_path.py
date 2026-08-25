"""Njia ya bei kutoka BARS — DOCTRINE §4.1, §9.2, §11.

Calibration B (§9.2) inadai kitu kimoja mahususi: **pipeline ile ile** iendeshwe
juu ya data isiyo na edge. Lakini familia tatu za data bandia
(`validation/surrogates.py`) zinatengeneza **bars**, si ticks — na haziwezi
kutengeneza ticks: IAAFT juu ya ticks bilioni 2.7 si polepole, ni isiyowezekana.

Wakati huo huo `backtest/execution.py` inatembea kwenye quotes. Kwa hiyo kuna
njia mbili tu:

1. kuandika kitembezi cha pili kinachofanya kazi kwa bars, au
2. kugeuza bars kuwa quotes na kutumia kitembezi kile kile.

**Njia ya pili ndiyo hii, na sababu ni R12/R19.** Kitembezi cha pili kingekuwa
modeli ya pili ya utekelezaji: gharama, slippage, mpangilio wa SL/TP na
`reconciliation_error` vingekuwa na maandishi mawili yanayoweza kutofautiana
kimya. Sakafu ya kelele iliyopimwa kwa modeli moja isingehukumu candidate
iliyopimwa kwa nyingine — na hilo ndilo lango lote la §9 linalotegemea.

---

**Bar haisemi mpangilio wa `high` na `low`, na tofauti ni SL dhidi ya TP.**

Bar moja inasema bei ilifika juu `high` na chini `low`. Haisemi ipi kwanza. Kwa
trade yenye SL na TP ndani ya masafa hayo, jibu ndilo linaloamua matokeo yote.

Chaguo hapa ni **UBAYA KWANZA, kwa kila upande**:

| direction | mpangilio | maana |
|---|---|---|
| BUY  | `open → low → high → close` | SL inaangaliwa kabla ya TP |
| SELL | `open → high → low → close` | SL inaangaliwa kabla ya TP |

Ndiyo maana `direction` ni parameter na si chaguo la kimya. Mpangilio MMOJA kwa
pande zote mbili — mfano `low` kwanza daima — ungekuwa mbaya kwa BUY na mzuri
kwa SELL, na generator ingependelea SELL kwa sababu ambayo si ya soko bali ya
uwakilishi wa data. Upendeleo huo usingeonekana kwenye kipimo chochote.

Upendeleo wa "ubaya kwanza" unashusha vipimo vya kila candidate — **na vya kila
candidate ya null pia**. Sakafu inashuka pamoja nao, kwa hiyo lango linabaki
sawa. Kilichoepukwa ni upendeleo unaotofautiana kati ya wagombea.

---

**Hiki si ubadala wa ticks.** Ni substrate ya HATUA YA KUTAFUTA, ambapo wagombea
ni maelfu na ticks haziwezekani. Waliobaki wanarudiwa juu ya ticks halisi kabla
ya §13. Sharti pekee lisilovunjika: Calibration B na hatua ya kutafuta zitumie
substrate ILE ILE. Zikitofautiana, sakafu inapima utafutaji mwingine.
"""

from __future__ import annotations

from typing import Any

# Robo za bar: `open` mwanzoni kabisa, `close` robo tatu ndani. `close` haiwekwi
# mwisho kabisa kwa sababu mwisho wa bar hii ni MWANZO wa inayofuata — quote
# mbili kwenye muda mmoja zingefanya `searchsorted` ichague isiyotarajiwa.
ROBO = (0.0, 0.25, 0.50, 0.75)

_OPEN, _CLOSE = "open", "close"


class BarPathError(RuntimeError):
    """Bars haziwezi kugeuzwa kuwa njia ya quotes."""


def to_path(bars, timeframe: str, *, symbol: str, direction: str,
            day_tz: str = "UTC", spread_col: str = "spread_p50"):
    """Bars → frame ya `timestamp/bid/ask` yenye quotes NNE kwa kila bar.

    Quote ya `open` inakaa kwenye **mwanzo kamili** wa bar. Hilo si la mapambo:
    signal ya bar `i` inatokea mwisho wake (R11), ambao ni mwanzo wa bar `i+1`,
    kwa hiyo `execution` inajaza kwenye `open` ya bar inayofuata na bei
    iliyoombwa ni `close` ya bar iliyotoa signal. Ndiyo mfuatano wa kweli wa
    uamuzi, na tofauti kati yao ni slippage halisi ya bar moja.
    """
    import numpy as np
    import pandas as pd

    from src.data.bars import bar_ends
    from src.rce.cost import pip_size

    hazipo = {_OPEN, "high", "low", _CLOSE} - set(bars.columns)
    if hazipo:
        raise BarPathError(f"safu za OHLC hazipo: {sorted(hazipo)}")
    if len(bars) == 0:
        raise BarPathError("hakuna bars")
    if spread_col not in bars.columns:
        raise BarPathError(
            f"safu ya spread `{spread_col}` haipo — bila spread, gharama "
            f"ingekuwa sifuri na kila candidate ingeonekana na faida"
        )

    upande = direction.upper()
    if upande not in ("BUY", "SELL"):
        raise BarPathError(f"direction ni BUY/SELL, si {direction!r}")

    o = bars[_OPEN].to_numpy(dtype=float)
    h = bars["high"].to_numpy(dtype=float)
    l = bars["low"].to_numpy(dtype=float)
    c = bars[_CLOSE].to_numpy(dtype=float)

    # UBAYA KWANZA — ona maelezo ya juu.
    kwanza, pili = (l, h) if upande == "BUY" else (h, l)
    mids = np.column_stack([o, kwanza, pili, c]).reshape(-1)

    # `as_unit("ns")` kabla ya `view`: kwenye pandas 3, DatetimeIndex inaweza
    # kuhifadhiwa kwa µs, na `view("int64")` inatoa µs kimya wakati kila hesabu
    # nyingine ya muda hapa ni ya ns. Tofauti haingelipuka — ingehamisha kila
    # quote kwenda 1970.
    anza = pd.DatetimeIndex(bars.index)
    if anza.tz is None:
        anza = anza.tz_localize("UTC")           # §4.1 — bars ni za UTC
    anza = anza.as_unit("ns")
    mwisho = pd.DatetimeIndex(bar_ends(anza, timeframe, day_tz)).as_unit("ns")
    urefu = (mwisho.view("int64") - anza.view("int64")).astype("float64")
    stamps = np.column_stack(
        [anza.view("int64") + (urefu * frac).astype("int64") for frac in ROBO]
    ).reshape(-1)

    # Spread ya bar inatumika kwa quotes zote NNE za bar hiyo. Spread ni ya pips
    # tangu `data/bars.py`; hapa inarudishwa kwenye vipimo vya bei.
    nusu = np.repeat(
        bars[spread_col].to_numpy(dtype=float) * pip_size(symbol) / 2.0, len(ROBO)
    )

    out = pd.DataFrame({
        "timestamp": pd.DatetimeIndex(stamps.astype("datetime64[ns]")).tz_localize("UTC"),
        "bid": mids - nusu,
        "ask": mids + nusu,
    })
    # Bar yenye spread isiyojulikana haina quote inayoweza kutumika: bei bila
    # gharama ingekuwa zawadi, si data.
    out = out[np.isfinite(out["bid"]) & np.isfinite(out["ask"])].reset_index(drop=True)
    if len(out) == 0:
        raise BarPathError(f"hakuna bar yenye `{spread_col}` inayojulikana")
    out.attrs["symbol"] = symbol
    out.attrs["direction"] = upande
    out.attrs["source"] = "bar_path"
    return out


def spreads_for_rce(bars, *, spread_col: str = "spread_p50") -> list[float]:
    """Spreads za RCE (`h1_spreads`/`m5_spreads`) kutoka bars zile zile.

    RCE ina lango lake la spread (`max_spread`). Kulipa orodha bandia
    kungelizima kimya — na lango lililozimwa halionekani kwenye ledger.
    """
    import numpy as np

    thamani = bars[spread_col].to_numpy(dtype=float)
    return [float(x) for x in thamani[np.isfinite(thamani)]]


def describe(bars, timeframe: str) -> dict[str, Any]:
    return {
        "substrate": "bar_path", "timeframe": timeframe,
        "n_bars": int(len(bars)), "quotes_per_bar": len(ROBO),
        "intrabar_order": "adverse_first",
    }
