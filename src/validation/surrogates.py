"""Familia TATU za data bandia — DOCTRINE §9.2, R15.

Calibration B inaendesha pipeline nzima juu ya data **isiyo na edge**. Kile injini
"inakigundua" pale ndiyo sakafu. Kwa hiyo swali pekee linalohesabika hapa ni:
*data bandia inahifadhi nini, na inavunja nini?*

| familia | inahifadhi | inavunja |
|---|---|---|
| `block_resample` | autocorrelation NDANI ya block | uhusiano KATI ya blocks |
| `regime_shuffle` | urefu na mpangilio wa regimes | mfuatano NDANI ya regime |
| `return_surrogate` | mgawanyo na wigo (spectrum) wa returns | awamu (phase) yote |

**Hakuna hata moja inayovunja kila kitu — na hilo ni kwa makusudi.**

`block_resample` inahifadhi momentum ya bars chache kwa ufafanuzi wake; `return_surrogate`
(IAAFT) inahifadhi autocorrelation nzima ya mstari kwa sababu inahifadhi wigo. Strategy
inayoishi kwa autocorrelation ya mstari itafanya kazi ndani ya familia hizo mbili —
kwa hiyo sakafu inayotoka kwao itakuwa **juu**, na ndiyo bar itakayolazimika kuivuka.

Hiyo ndiyo maana ya `max` (§9.2): sakafu inapanda hasa kwa aina ya edge ambayo null
inaihifadhi. Familia moja ingetoa sakafu ambayo ni nusu tabia ya soko, nusu tabia ya
generator — na hatuwezi kutofautisha mbili hizo kwa kuangalia.

---

**Kinachohifadhiwa daima, familia zote tatu:**

* **saa** — timestamps hazibadilishwi. Sessions, wikendi na mapengo ya kalenda ni
  ya kweli. Tunavunja utabirikaji, si kalenda.
* **spread na row yake** — spread haipangwi upya peke yake. Inasafiri **pamoja na**
  return iliyoandamana nayo, kwa hiyo uhusiano *spread pana ↔ mwendo mkubwa*
  unabaki. Ukivunjwa, gharama ingekuwa nasibu dhidi ya volatility, na kila
  strategy ingeonekana nafuu kuliko ilivyo hasa pale inapoumia zaidi.
* **umbo la bar** — `open/high/low` zinasafiri kama nyongeza za `log` juu ya `close`
  ya row ile ile, kwa hiyo `high ≥ max(open, close)` inabaki kweli bila kuangaliwa.
* **bei chanya** — returns ni za `log`; bei inajengwa kwa `exp`. Bei hasi
  isingekuwa kosa linaloonekana, ingekuwa jibu.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Sequence

BLOCK = "block_resample"
REGIME = "regime_shuffle"
SURROGATE = "return_surrogate"
FAMILIES = (BLOCK, REGIME, SURROGATE)

PRESERVES = {
    BLOCK: "autocorrelation ndani ya block",
    REGIME: "urefu na mpangilio wa regimes",
    SURROGATE: "mgawanyo na wigo wa returns",
}
BREAKS = {
    BLOCK: "uhusiano kati ya blocks",
    REGIME: "mfuatano ndani ya regime",
    SURROGATE: "awamu (phase) yote",
}

LOW, MID, HIGH = "LOW", "MID", "HIGH"

# Dirisha la regime: bars 252 — lile lile la `ATR_percentile_252d` (§21). Si namba
# mpya; ni ile ile iliyofafanuliwa kwenye kamusi ya vipimo.
REGIME_WINDOW = 252

# Dirisha la kusugua volatility: bars 14 — lile lile la `ATR_14` linalotumiwa na
# `ATR_percentile_252d` (§21). Regime inajengwa juu ya volatility iliyosuguliwa,
# si juu ya bar moja; ona `default_regime`.
VOL_WINDOW = 14

# Chini ya hii, `p95`, ACF na wigo vyote vinahesabiwa kwa data isiyotosha kuwapa
# maana. Si upendeleo — ni kwamba mstari mfupi hauna tabia ya kutunza.
MIN_ROWS = 64


class SurrogateError(RuntimeError):
    """Frame haiwezi kugeuzwa kuwa data bandia."""


@dataclass(frozen=True)
class Surrogate:
    """Frame moja bandia, pamoja na kila kitu kinachohitajika kuizalisha upya."""

    family: str
    seed: int
    frame: Any
    n_rows: int
    price_col: str
    block_len: int | None = None
    iaaft_iters: int | None = None

    @property
    def preserves(self) -> str:
        return PRESERVES[self.family]

    @property
    def breaks(self) -> str:
        return BREAKS[self.family]

    def render(self) -> str:
        extra = f" · block {self.block_len}" if self.block_len else ""
        extra += f" · iaaft {self.iaaft_iters}" if self.iaaft_iters else ""
        return (
            f"{self.family:<17} seed {self.seed:<6} rows {self.n_rows:>8,}{extra}\n"
            f"   inahifadhi: {self.preserves}\n"
            f"   inavunja  : {self.breaks}"
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "family": self.family, "seed": self.seed, "n_rows": self.n_rows,
            "price_col": self.price_col, "block_len": self.block_len,
            "iaaft_iters": self.iaaft_iters,
            "preserves": self.preserves, "breaks": self.breaks,
        }


# ===========================================================================
# API
# ===========================================================================


def make(frame, family: str, *, seed: int, block_len: int | None = None,
         regime: Sequence[str] | None = None, iaaft_iters: int = 200) -> Surrogate:
    """Zalisha frame bandia yenye schema ILE ILE ya ingizo.

    Ingizo linaweza kuwa **ticks** (`timestamp`, `bid`, `ask`) au **bars**
    (`open/high/low/close` pamoja na safu za spread). Safu zozote nyingine
    zinasafiri kama zilivyo, zikiwa zimeambatana na row zake.
    """
    import numpy as np

    if family not in FAMILIES:
        raise SurrogateError(f"familia haijulikani: {family!r} — §9.2 ina tatu: {FAMILIES}")
    if len(frame) < MIN_ROWS:
        raise SurrogateError(
            f"rows {len(frame)} < {MIN_ROWS} — mstari mfupi hauna tabia ya kutunza"
        )

    price, rebuild, price_col = _decompose(frame)
    if not np.all(price > 0):
        raise SurrogateError("bei si chanya — returns za log haziwezekani")

    r = np.diff(np.log(price))
    rng = np.random.default_rng(seed)
    used_block = used_iters = None

    if family == BLOCK:
        used_block = int(block_len) if block_len else measure_block_len(r)
        idx = _block_indices(len(r), used_block, rng)
        r_s = r[idx]
    elif family == REGIME:
        labels = list(regime) if regime is not None else default_regime(r)
        if len(labels) != len(r):
            raise SurrogateError(
                f"regime ina {len(labels)} labels lakini returns ni {len(r)}"
            )
        idx = _regime_indices(labels, rng)
        r_s = r[idx]
    else:
        r_s, used_iters = iaaft(r, rng, iters=iaaft_iters)
        # Rows hazipangwi upya hapa — returns zimebadilishwa, si kuhamishwa. Kwa
        # hiyo spread inaambatanishwa kwa **cheo cha |return|**: mwendo mkubwa
        # unapata spread iliyokuwa ikiandamana na mwendo mkubwa. Mgawanyo wa
        # spread unabaki ule ule, na uhusiano wake na volatility pia.
        idx = _rank_map(np.abs(r), np.abs(r_s))

    return Surrogate(
        family=family, seed=int(seed), frame=rebuild(r_s, idx), n_rows=len(frame),
        price_col=price_col, block_len=used_block, iaaft_iters=used_iters,
    )


def measure_block_len(returns) -> int:
    """Urefu wa block unapimwa, haudhaniwi (§2).

    Vipimo viwili, na kikubwa kinashinda:

    * **ACF** — lag ya kwanza ambapo autocorrelation inaingia ndani ya ukanda wa
      kelele nyeupe (`1.96/√n`). Chini ya lag hiyo kuna muundo wa kutunza.
    * **`n^(1/3)`** — kiwango cha kawaida cha block bootstrap. Block lazima ikue
      na sampuli, la sivyo uhusiano wa masafa marefu unapotea kadri data
      inavyoongezeka — na sakafu ingeshuka kwa sababu ya ukubwa wa data pekee.
    """
    import numpy as np

    x = np.asarray(returns, dtype=float)
    n = len(x)
    rate = max(2, math.ceil(n ** (1.0 / 3.0)))

    band = 1.96 / math.sqrt(n)
    xc = x - x.mean()
    denom = float(xc @ xc)
    if denom <= 0:
        return rate

    lag_acf = 1
    for k in range(1, min(n // 10, 200) + 1):
        acf = float(xc[:-k] @ xc[k:]) / denom
        if abs(acf) < band:
            lag_acf = k
            break
        lag_acf = k + 1

    return int(min(max(lag_acf, rate), max(2, n // 4)))


def default_regime(returns, window: int = REGIME_WINDOW,
                   smooth: int = VOL_WINDOW) -> list[str]:
    """Regime kwa percentile ya volatility ndani ya dirisha la nyuma (§21).

    Sio detector kamili ya §6 — ni ya kutosha kwa null: kinachohitajika ni
    mgawanyo wa vipindi tulivu na vya msukosuko, ili shuffle isichanganye
    2020-03 na Agosti tulivu.

    **Volatility inasuguliwa kwanza.** `|return|` ya bar MOJA si regime; ni
    kelele ya kipimo. Ikitumika moja kwa moja, labels zinabadilika karibu kila
    bar, mifululizo inakuwa ya urefu 1 — na familia B **inakuwa ingizo lenyewe**,
    kimya kabisa. Ndiyo maana §21 inajenga `vol_regime_252d` juu ya `ATR_14`,
    si juu ya range ya bar moja: madirisha yote mawili yanatoka pale.

    Mfululizo mfupi kuliko dirisha lililoupima si regime — ni yumbayumba ya
    kipimo, kwa hiyo unaunganishwa na uliotangulia.
    """
    import numpy as np
    import pandas as pd

    absr = pd.Series(np.abs(np.asarray(returns, dtype=float)))
    vol = absr.rolling(smooth, min_periods=1).mean()
    pct = vol.rolling(window, min_periods=1).rank(pct=True).to_numpy()
    labels = np.where(pct < 0.33, LOW, np.where(pct < 0.67, MID, HIGH))
    return _merge_short_runs([str(v) for v in labels], smooth)


def _merge_short_runs(labels: list[str], min_run: int) -> list[str]:
    """Mfululizo mfupi kuliko `min_run` unachukua jina la uliotangulia."""
    if not labels:
        return labels

    runs: list[list] = []
    for lab in labels:
        if runs and runs[-1][0] == lab:
            runs[-1][1] += 1
        else:
            runs.append([lab, 1])

    merged: list[list] = []
    for lab, n in runs:
        if merged and (n < min_run or merged[-1][0] == lab):
            merged[-1][1] += n
        else:
            merged.append([lab, n])
    # Mfululizo wa KWANZA hauna uliotangulia; ukiwa mfupi, unaungana na ufuatao.
    if len(merged) > 1 and merged[0][1] < min_run:
        merged[1][1] += merged[0][1]
        merged.pop(0)

    out: list[str] = []
    for lab, n in merged:
        out.extend([lab] * n)
    return out


def iaaft(x, rng, *, iters: int = 200):
    """Iterative Amplitude Adjusted Fourier Transform.

    Inarudisha mstari wenye **mgawanyo ULE ULE haswa** wa `x` (kwa kupanga upya
    thamani zile zile) na wigo wa nguvu wa karibu sana — lakini awamu ni ya
    nasibu. Kila muundo unaotegemea *lini* jambo linatokea unapotea; kila
    unaotegemea *mara ngapi* unabaki.

    Rudi na idadi ya mizunguko iliyotumika: ikisimama kabla ya `iters`, ranks
    zimeganda na kuendelea hakuna kinachoongeza.
    """
    import numpy as np

    x = np.asarray(x, dtype=float)
    amp = np.abs(np.fft.rfft(x))
    ordered = np.sort(x)
    y = rng.permutation(x)

    prev = None
    used = iters
    for i in range(1, iters + 1):
        phase = np.angle(np.fft.rfft(y))
        y = np.fft.irfft(amp * np.exp(1j * phase), n=len(x))
        ranks = np.argsort(np.argsort(y, kind="stable"), kind="stable")
        y = ordered[ranks]
        if prev is not None and np.array_equal(ranks, prev):
            used = i
            break
        prev = ranks
    return y, used


# ===========================================================================
# Ndani
# ===========================================================================


def _block_indices(m: int, block: int, rng):
    """Blocks za mviringo: mwanzo wa nasibu, urefu thabiti, zinazungushwa mwisho.

    Mviringo (`% m`) inahakikisha kila index ina nafasi SAWA ya kuchaguliwa.
    Bila hiyo, rows za mwanzo zingeonekana mara nyingi zaidi kuliko za mwisho,
    na data bandia ingekuwa na upendeleo wa kipindi — upendeleo ambao
    ungeonekana kama muundo.
    """
    import numpy as np

    n_blocks = math.ceil(m / block)
    starts = rng.integers(0, m, size=n_blocks)
    idx = (starts[:, None] + np.arange(block)[None, :]) % m
    return idx.reshape(-1)[:m]


def _regime_indices(labels: Sequence[str], rng):
    """Panga upya NDANI ya kila mfululizo wa regime; mipaka haiguswi.

    Kinga: labels zinazobadilika kila row zinatoa mifululizo ya urefu 1, na
    familia hii ingekuwa **ingizo lenyewe** — data bandia yenye edge halisi ndani
    yake. Hilo halijitokezi kama kosa; linajitokeza kama sakafu ambayo hakuna
    strategy inayoweza kuivuka.
    """
    import numpy as np

    lab = np.asarray(labels, dtype=object)
    idx = np.arange(len(lab))
    boundaries = np.flatnonzero(lab[1:] != lab[:-1]) + 1

    pieces = np.split(idx, boundaries)
    inayochanganywa = sum(len(p) for p in pieces if len(p) > 1)
    if inayochanganywa < 0.5 * len(lab):
        raise SurrogateError(
            f"regime hazina uendelevu: rows {inayochanganywa:,}/{len(lab):,} pekee ziko "
            f"kwenye mfululizo wenye urefu > 1. Familia B ingekuwa ingizo lenyewe"
        )

    for piece in pieces:
        if len(piece) > 1:
            idx[piece[0]: piece[-1] + 1] = rng.permutation(piece)
    return idx


def _rank_map(orig, sur):
    """Index inayolinganisha cheo cha `sur` na cheo cha `orig`."""
    import numpy as np

    order = np.argsort(np.asarray(orig), kind="stable")
    ranks = np.argsort(np.argsort(np.asarray(sur), kind="stable"), kind="stable")
    return order[ranks]


def _decompose(frame) -> tuple[Any, Callable[[Any, Any], Any], str]:
    """Tenganisha frame kuwa: bei, na namna ya kuijenga upya.

    Kila safu isiyo bei inasafiri **kwa index**, si kwa thamani — kwa hiyo
    safu zisizo za namba (mf. `session`, `symbol`) zinabaki sahihi bila kutajwa.
    """
    import numpy as np

    cols = set(frame.columns)

    if {"bid", "ask"} <= cols:
        bid = frame["bid"].to_numpy(dtype=float)
        ask = frame["ask"].to_numpy(dtype=float)
        price = (bid + ask) / 2.0
        price_col = "mid"
        carried = {"spread": ask - bid}

        def rebuild_derived(price_s, c):
            return {"bid": price_s - c["spread"] / 2.0, "ask": price_s + c["spread"] / 2.0}

    elif "close" in cols:
        close = frame["close"].to_numpy(dtype=float)
        price = close
        price_col = "close"
        # Umbo la bar linahifadhiwa kama nyongeza za `log` juu ya `close` YAKE.
        # Kwa hiyo `high_off ≥ 0 ≥ low_off` na `high_off ≥ open_off`; kuzidisha
        # kwa `close` chanya kunahifadhi mielekeo yote — OHLC inabaki halali
        # bila kukaguliwa.
        carried = {
            name: np.log(frame[name].to_numpy(dtype=float) / close)
            for name in ("open", "high", "low") if name in cols
        }

        def rebuild_derived(price_s, c):
            return {"close": price_s, **{k: price_s * np.exp(v) for k, v in c.items()}}

    else:
        raise SurrogateError(
            "frame haina `bid`/`ask` wala `close` — §4.1 inadai mojawapo"
        )

    # Saa haisafiri. Kila safu ya muda inarudishwa mahali pake baada ya rows
    # kupangwa upya — tunavunja utabirikaji, si kalenda.
    time_cols = [c for c in frame.columns if _ni_muda(frame[c])]

    def rebuild(r_s, idx):
        # Row 0 ni nanga: bei yake, spread yake na umbo lake vinabaki. Returns
        # ni `n−1`, kwa hiyo `idx` inagusa rows 1..n−1 pekee.
        full = np.concatenate([[0], np.asarray(idx, dtype=int) + 1])
        price_s = price[0] * np.exp(np.concatenate([[0.0], np.cumsum(r_s)]))

        out = frame.iloc[full].copy()
        out.index = frame.index
        for name in time_cols:
            out[name] = frame[name].to_numpy()
        for name, values in rebuild_derived(
            price_s, {k: v[full] for k, v in carried.items()}
        ).items():
            out[name] = values
        return out[list(frame.columns)]

    return price, rebuild, price_col


def _ni_muda(series) -> bool:
    import pandas as pd

    return pd.api.types.is_datetime64_any_dtype(series)
