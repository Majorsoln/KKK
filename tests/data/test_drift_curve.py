"""`drift-curve` na `cost-audit --by-symbol` — vipimo viwili vya mapitio ya nje.

Mtaalamu wa pili aliomba viwili: **muundo wa muda wa drift** (kuna drift kabisa,
na iko wapi?) na **mgawanyo wa cell kwa symbol kuwa gharama dhidi ya gross**
(je kuondoa symbol ilikuwa sheria au uteuzi?).

Tests hizi hazipimi kuwa amri zinaendesha. Zinapima kuwa **zinajibu swali
lililoulizwa**: kwamba drift ya kweli inaonekana kama drift, kwamba kutokuwepo
kwake kunaonekana kama sifuri, kwamba gharama inatozwa mara moja na si kwa kila
horizon, na kwamba symbol iliyo hasi kwa gharama inatofautishwa na iliyo hasi
kwa gross. Kila moja ya hizo ni namba ambayo hitimisho linaitegemea.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.cli import main
from src.data.labels import SL_FIRST, TIMEOUT, TP_FIRST
from tests.conftest import REPO_ROOT

CONFIG = str(REPO_ROOT / "config" / "data.yaml")
ATR_PRICE = 0.0030
ATR_PIPS = 30.0
N_BARS = 3_000
FIRST = 300      # bar ya kwanza yenye decision point
EVERY = 40       # nafasi kati ya points — hakuna mwingiliano hadi bars 40


def _tree(
    root: Path,
    step: float,
    *,
    symbols: tuple[str, ...] = ("EURUSD",),
    front_load: float | None = None,
    spread_pips: float = 0.6,
    every: int = EVERY,
) -> dict[str, np.ndarray]:
    """L2 bars + L4 points, kwa njia ya bei INAYOJULIKANA.

    `step` ni mwendo wa bei kwa kila bar (units za bei). `front_load` ikitolewa,
    bei inaruka mara moja tu baada ya kuingia kisha inatuama — ndio umbo la
    "drift imejikita mbele" ambalo mtaalamu wa pili anasema lingegeuza ushauri
    wake wa horizon ndefu.
    """
    truth: dict[str, np.ndarray] = {}
    index = pd.date_range("2016-01-04", periods=N_BARS, freq="1h", tz="UTC")
    anchors = np.arange(FIRST, N_BARS - 400, every)

    for i, symbol in enumerate(symbols):
        # Spread inatofautiana kwa symbol — vinginevyo `spread/ATR` ingekuwa
        # constant na ρ isingekuwa na maana wala isingehesabika.
        spread_here = spread_pips * (1.0 + 0.5 * i)
        close = np.full(N_BARS, 1.10)
        if front_load is None:
            close = 1.10 + step * np.arange(N_BARS)
        else:
            # Tuama kila mahali; ruka `front_load` kwenye bar inayofuata point.
            bump = np.zeros(N_BARS)
            bump[anchors + 1] = front_load
            close = 1.10 + np.cumsum(bump)

        bars = pd.DataFrame(
            {
                "open": close, "high": close + 0.0002, "low": close - 0.0002,
                "close": close, "spread_p50": 0.8, "is_valid": True,
            },
            index=index,
        )
        bars.index.name = "timestamp"
        target = root / "data" / "L2_bars" / f"symbol={symbol}" / "tf=H1" / "bars.parquet"
        target.parent.mkdir(parents=True, exist_ok=True)
        bars.reset_index().to_parquet(target, index=False)

        entry_mid = close[anchors]
        # `terminal_atr` kama labeller ingeirekodi kutoka TICKS kwa h = 24,
        # kwa mpangilio `pos+h`. Uhakiki wa amri unapaswa kuipata sawasawa.
        terminal = (close[anchors + 24] - entry_mid) / ATR_PRICE
        truth[symbol] = terminal

        n = len(anchors)
        points = pd.DataFrame({
            "symbol": symbol,
            "decision_time": index[anchors],
            "bar_open": index[anchors],
            "direction": 1,
            "is_setup": True,
            "is_control": False,
            "entry_mid": entry_mid,
            "atr_price": ATR_PRICE,
            "atr_pips": ATR_PIPS,
            "spread_entry_pips": spread_here,
            "spread_exit_pips": spread_here,
            "terminal_atr": terminal,
        })
        folder = root / "data" / "L4_labels" / "labels" / f"symbol={symbol}"
        folder.mkdir(parents=True, exist_ok=True)
        points.to_parquet(folder / "points-2016.parquet", index=False)

        rng = np.random.RandomState(abs(hash(symbol)) % 2**31)
        outcome = rng.choice([TP_FIRST, SL_FIRST, TIMEOUT], size=n, p=[0.3, 0.3, 0.4])
        pd.DataFrame({
            "symbol": symbol,
            "decision_time": index[anchors],
            "sl_atr": 3.0, "tp_atr": 6.0,
            "sl_pips": 3.0 * ATR_PIPS, "tp_pips": 6.0 * ATR_PIPS,
            "outcome": outcome,
            "touch_past_pips": np.where(outcome == SL_FIRST, 1.0, 0.0),
            "timeout_return_r": np.zeros(n),
        }).to_parquet(folder / "barriers-2016.parquet", index=False)
    return truth


@pytest.fixture
def tree(monkeypatch, tmp_path):
    root = tmp_path / "research"
    monkeypatch.setenv("ELITEFX_RESEARCH_ROOT", str(root))
    monkeypatch.setenv("ELITEFX_HOLDOUT_ROOT", str(root / "_holdout"))

    def build(**kwargs):
        _tree(root, **kwargs)
        return root

    return build


def _curve(root: Path) -> dict[int, dict]:
    payload = json.loads((root / "reports" / "r1" / "drift_curve.json").read_text())
    return {int(r["h"]): r for r in payload["curve"]}


# ===========================================================================
# drift-curve — umbo
# ===========================================================================


def test_drift_ya_kweli_inaonekana_kama_drift(tree, capsys):
    """Bei inayopanda kwa `step` kila bar ⇒ gross inapanda KWA MSTARI kwa h."""
    root = tree(step=ATR_PRICE / 100.0)   # 0.01 ATR kwa bar
    assert main(["--config", CONFIG, "drift-curve", "--symbols", "EURUSD",
                 "--horizons", "3,6,12,24,48"]) == 0
    curve = _curve(root)
    for h in (3, 6, 12, 24, 48):
        assert curve[h]["gross_atr"] == pytest.approx(0.01 * h, abs=1e-6)
    # Mstari, si mkunjo: nyongeza kati ya horizons ni sawa kwa uwiano.
    assert curve[48]["gross_atr"] / curve[24]["gross_atr"] == pytest.approx(2.0, abs=1e-6)


def test_drift_isipokuwepo_gross_ni_sifuri_kila_mahali(tree):
    """Bei tuli ⇒ gross ni sifuri kwa horizon YOYOTE — hakuna mkunjo wa kutafsiri."""
    root = tree(step=0.0)
    assert main(["--config", CONFIG, "drift-curve", "--symbols", "EURUSD",
                 "--horizons", "3,24,240"]) == 0
    curve = _curve(root)
    for h in (3, 24, 240):
        assert curve[h]["gross_atr"] == pytest.approx(0.0, abs=1e-9)


def test_drift_iliyojikita_mbele_inatuama(tree):
    """Kuruka mara moja kisha kutuama ⇒ gross ni ILE ILE kuanzia h = 1.

    Hili ndilo umbo ambalo mtaalamu wa pili anasema lingegeuza ushauri wake:
    barriers zingeikamata mapema, na horizon ndefu isingeongeza chochote.
    """
    # Nafasi kubwa kati ya points: horizon ya 120 isivuke point inayofuata,
    # vinginevyo ingekusanya mruko wa trade NYINGINE — na jedwali lingesoma
    # kama drift iliyojikita nyuma wakati si kweli.
    root = tree(step=0.0, front_load=ATR_PRICE * 0.05, every=400)
    assert main(["--config", CONFIG, "drift-curve", "--symbols", "EURUSD",
                 "--horizons", "3,24,120"]) == 0
    curve = _curve(root)
    assert curve[3]["gross_atr"] == pytest.approx(0.05, abs=1e-6)
    assert curve[24]["gross_atr"] == pytest.approx(curve[3]["gross_atr"], abs=1e-6)
    assert curve[120]["gross_atr"] == pytest.approx(curve[3]["gross_atr"], abs=1e-6)


def test_gharama_inatozwa_mara_moja_si_kwa_kila_horizon(tree):
    """Trade ni MOJA. Gharama kwa ATR ni ile ile kwa horizons zote.

    Hii ndiyo inayofanya hoja ya mtaalamu wa pili ya `1/√h` iwe na maana:
    return inakua kwa horizon, gharama haikui. Ikitozwa kwa kila horizon,
    hoja nzima ingekuwa batili — na jedwali lingeificha.
    """
    root = tree(step=ATR_PRICE / 100.0)
    assert main(["--config", CONFIG, "drift-curve", "--symbols", "EURUSD",
                 "--horizons", "3,24,240"]) == 0
    curve = _curve(root)
    expected = (0.6 + 0.7) / ATR_PIPS
    for h in (3, 24, 240):
        assert curve[h]["cost_atr"] == pytest.approx(expected, abs=1e-9)
        assert curve[h]["net_atr"] == pytest.approx(
            curve[h]["gross_atr"] - expected, abs=1e-9
        )


# ===========================================================================
# drift-curve — uhakiki wa bars dhidi ya ticks
# ===========================================================================


def test_uhakiki_unalinganisha_bars_na_terminal_atr(tree, capsys):
    """Njia mbili tofauti za kufika namba ile ile lazima zikubaliane.

    `terminal_atr` inatoka kwenye TICKS; safu ya `gross` kwa h = 24 inatoka
    kwenye H1 close. Zisipolingana, mojawapo ina kasoro — ndiyo namna kasoro
    ya labelling ilivyopatikana wiki hii.
    """
    root = tree(step=ATR_PRICE / 100.0)
    assert main(["--config", CONFIG, "drift-curve", "--symbols", "EURUSD",
                 "--horizons", "24"]) == 0
    out = capsys.readouterr().out
    assert "UHAKIKI kwa h = 24" in out
    payload = json.loads((root / "reports" / "r1" / "drift_curve.json").read_text())
    exact = [r for r in payload["reconciliation"] if r["tag"] == "pos+h"]
    assert exact and all(
        r["bars"] == pytest.approx(r["ticks"], abs=1e-9) for r in exact
    )


def test_uhakiki_unapiga_kelele_mpangilio_ukiwa_na_kosa_la_bar_moja(tree, capsys):
    """`terminal_atr` ikitoka bar moja mapema, amri lazima ISEME hivyo.

    Kosa la bar moja ni dogo kwenye macho na kubwa kwenye hitimisho. Uhakiki
    usioweza kuligundua si uhakiki.
    """
    root = tree(step=ATR_PRICE / 100.0)
    folder = root / "data" / "L4_labels" / "labels" / "symbol=EURUSD"
    points = pd.read_parquet(folder / "points-2016.parquet")
    points["terminal_atr"] = points["terminal_atr"] - 0.01   # bar moja pungufu
    points.to_parquet(folder / "points-2016.parquet", index=False)

    assert main(["--config", CONFIG, "drift-curve", "--symbols", "EURUSD",
                 "--horizons", "24"]) == 0
    assert "ONYO" in capsys.readouterr().out


# ===========================================================================
# cost-audit --by-symbol
# ===========================================================================


def test_by_symbol_inatenganisha_hasi_ya_gharama_na_hasi_ya_gross(tree, capsys):
    """Swali linaloamua kama kuondoa symbol ni sheria au uteuzi.

    Symbol mbili zenye matokeo yale yale ya barrier, lakini spread tofauti.
    Iliyo na spread kubwa inapaswa kuonekana ikiwa hasi kwa EV net **bila**
    kuwa hasi kwa gross — na hiyo ndiyo inayoweza kuondolewa kwa sheria isiyo
    na label.
    """
    root = tree(step=ATR_PRICE / 100.0, symbols=("EURUSD", "GBPUSD"))
    assert main(["--config", CONFIG, "cost-audit", "--cell", "3.0/6.0",
                 "--by-symbol", "--symbols", "EURUSD,GBPUSD"]) in (0, 1)
    out = capsys.readouterr().out
    assert "MGAWANYO KWA SYMBOL" in out
    assert "hasi kwa EV net" in out and "hasi kwa GROSS" in out
    for symbol in ("EURUSD", "GBPUSD"):
        assert symbol in out


def test_by_symbol_gross_ni_ev_net_jumlisha_cost(tree, capsys):
    """Utambulisho `gross = EV net + cost_R` — si safu iliyohesabiwa kando.

    Ikivunjika, jedwali lingeonyesha symbol ikiwa "chanya kwa gross" wakati
    si kweli, na uamuzi wa kuiondoa ungejengwa juu ya hewa.
    """
    root = tree(step=ATR_PRICE / 100.0, symbols=("EURUSD",))
    assert main(["--config", CONFIG, "cost-audit", "--cell", "3.0/6.0",
                 "--by-symbol", "--symbols", "EURUSD"]) in (0, 1)
    out = capsys.readouterr().out
    line = next(l for l in out.splitlines() if l.strip().startswith("EURUSD"))
    parts = line.split()
    _, _, _, cost_r, gross, ev_net, _ = parts
    # Kila safu imezungushwa kwa 4dp KANDO — utambulisho unaweza kupishana kwa
    # nusu-unit ya safu mbili zilizozungushwa. 2e-4 inaruhusu hilo tu.
    assert float(gross) == pytest.approx(float(ev_net) + float(cost_r), abs=2e-4)


def test_by_symbol_inahitaji_cell(tree, capsys):
    """Bila `--cell` hakuna cell ya kugawa — jedwali halipaswi kutokea kimya."""
    tree(step=ATR_PRICE / 100.0)
    main(["--config", CONFIG, "cost-audit", "--by-symbol", "--symbols", "EURUSD"])
    assert "MGAWANYO KWA SYMBOL" not in capsys.readouterr().out


def test_by_symbol_hahitaji_scipy(tree, monkeypatch, capsys):
    """ρ lazima ihesabiwe bila scipy — haiko kwenye mazingira ya PD.

    `pandas.corr(method="spearman")` inaita scipy kimya kimya na inaanguka
    pale tu inapoendeshwa kwenye mashine halisi, baada ya jedwali lote
    kuchapishwa. Test hii inazuia kurudi kwake kwa kuficha scipy kabisa.
    """
    import builtins

    halisi = builtins.__import__

    def kataa(name, *rest):
        if name == "scipy" or name.startswith("scipy."):
            raise ImportError("scipy imefichwa na test")
        return halisi(name, *rest)

    monkeypatch.setattr(builtins, "__import__", kataa)
    tree(step=ATR_PRICE / 100.0, symbols=("EURUSD", "GBPUSD", "USDJPY"))
    assert main(["--config", CONFIG, "cost-audit", "--cell", "3.0/6.0",
                 "--by-symbol", "--symbols", "EURUSD,GBPUSD,USDJPY"]) in (0, 1)
    assert "ρ(spread/ATR, gross)" in capsys.readouterr().out
