"""Kiungo kizima: `build-features` → `meta-label`, kwenye data bandia.

Tests za `test_experiment.py` zinapima purged CV, za `test_metalabel.py`
zinapima malango, za `test_features.py` zinapima features. Hakuna kati yao
inayopima **wiring** — kwamba parquet inaandikwa mahali amri inayofuata
inapoisoma, kwamba join inapata rows, kwamba breakeven inatoka `cost_audit.json`
na si kubuniwa.

Ndipo kosa la gharama kubwa zaidi lilipo: linaonekana baada ya kupakia data ya
kweli, si kabla. Hapa `research/` bandia nzima inajengwa ndani ya `tmp_path` —
bars za L2, points na barriers za L4, na `cost_audit.json` — kisha amri
zinaendeshwa kama zinavyoendeshwa kwenye mashine ya PD.
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
SYMBOLS = ("EURUSD", "GBPUSD")

# Kichwa halisi cha ledger — `budget.load` inasoma `SR\*` na `miaka` kutoka
# hapa, na matumizi kutoka safu za jedwali. Kichwa cha kubuni kingetoa
# `total = 0`, na `guard()` isingezuia chochote kimya kimya.
_LEDGER_HEAD = (
    "# BAJETI YA MAJARIBIO\n\n"
    "**SR\\* : 0.7**  ·  **miaka : 8.25**  ·  **bajeti : 7.5 configs**\n\n"
    "| # | lini | config | aina | uzito | zimebaki | sababu |\n"
    "|---|---|---|---|---|---|---|\n"
)


@pytest.fixture
def budget_ipo(monkeypatch, tmp_path):
    """Bajeti ya majaribio yenye nafasi — `meta-label` ina `budget.guard()`."""
    from src.governance import budget as bud

    ledger = tmp_path / "TRIAL_BUDGET.md"
    ledger.write_text(_LEDGER_HEAD, encoding="utf-8", newline="\n")
    monkeypatch.setattr(bud, "LEDGER", ledger, raising=False)
    return ledger


def _bars(symbol: str, n: int, seed: int) -> pd.DataFrame:
    """Bars za H1 zenye mwelekeo unaoendelea — feature zina kitu cha kushika."""
    rng = np.random.RandomState(seed)
    drift = np.cumsum(rng.normal(0, 1, n)) * 0.0002
    close = 1.10 * np.exp(drift)
    wick = np.abs(rng.normal(0, 0.0004, n)) * close
    frame = pd.DataFrame(
        {
            "open": close,
            "high": close + wick,
            "low": close - wick,
            "close": close,
            "spread_p50": 0.8 + rng.uniform(0, 0.4, n),
            "is_valid": True,
        },
        index=pd.date_range("2016-01-04", periods=n, freq="1h", tz="UTC"),
    )
    frame.index.name = "timestamp"
    return frame


def _research_tree(root: Path, n: int = 40_000, signal: float = 1.0) -> None:
    """L2 bars + L4 points/barriers + `cost_audit.json`.

    `y` inategemea return ya saa 24 zilizopita — signal halisi ndani ya
    features, si kelele. Ikiwa kiungo ni sahihi, `logistic` inaipata; ikiwa
    join au standardization imevunjika, hakuna kinachopita.
    """
    rng = np.random.RandomState(11)
    for i, symbol in enumerate(SYMBOLS):
        bars = _bars(symbol, n, seed=i)
        target = root / "data" / "L2_bars" / f"symbol={symbol}" / "tf=H1" / "bars.parquet"
        target.parent.mkdir(parents=True, exist_ok=True)
        bars.reset_index().to_parquet(target, index=False)

        # Decision points kila bar ya 8 — setups zote (control hazitumiki hapa).
        picked = bars.index[200::8]
        edge = np.log(bars["close"] / bars["close"].shift(24)).reindex(picked).fillna(0.0)
        prob = 1.0 / (1.0 + np.exp(-(signal * edge.to_numpy() / 0.004 - 0.1)))
        draw = rng.uniform(size=len(picked))
        outcome = np.where(draw < prob * 0.55, TP_FIRST,
                           np.where(draw < 0.93, SL_FIRST, TIMEOUT))

        points = pd.DataFrame(
            {
                "symbol": symbol,
                "decision_time": picked + pd.Timedelta(hours=1),
                "is_setup": True,
                "is_control": False,
                "atr_pips": 30.0,
                "direction": 1,
                "terminal_atr": rng.normal(0, 1, len(picked)),
            }
        )
        barriers = pd.DataFrame(
            {
                "symbol": symbol,
                "decision_time": picked + pd.Timedelta(hours=1),
                "sl_atr": 2.0,
                "tp_atr": 3.0,
                "sl_pips": 60.0,
                "tp_pips": 90.0,
                "outcome": outcome,
                "touch_past_pips": np.where(outcome == SL_FIRST, rng.uniform(0, 2, len(picked)), 0.0),
                "timeout_return_r": rng.normal(0, 0.2, len(picked)),
            }
        )
        folder = root / "data" / "L4_labels" / "labels" / f"symbol={symbol}"
        folder.mkdir(parents=True, exist_ok=True)
        points.to_parquet(folder / "points-2016.parquet", index=False)
        barriers.to_parquet(folder / "barriers-2016.parquet", index=False)

    cost = root / "reports" / "r1" / "cost_audit.json"
    cost.parent.mkdir(parents=True, exist_ok=True)
    cost.write_text(
        json.dumps(
            {
                "cells": [],
                "identities": {
                    "cell": [2.0, 3.0],
                    "dev_dp": 2.5,
                    "gap_to_breakeven": 0.0065,
                    "delta_mer": 0.0235,
                    "n_required": 500.0,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
        newline="\n",
    )


@pytest.fixture
def tree(monkeypatch, tmp_path):
    root = tmp_path / "research"
    monkeypatch.setenv("ELITEFX_RESEARCH_ROOT", str(root))
    monkeypatch.setenv("ELITEFX_HOLDOUT_ROOT", str(root / "_holdout"))
    _research_tree(root)
    return root


# ===========================================================================
# build-features
# ===========================================================================


def test_build_features_inaandika_l3_kwa_kila_symbol(tree, capsys):
    assert main(["--config", CONFIG, "build-features", "--symbols", ",".join(SYMBOLS)]) == 0
    for symbol in SYMBOLS:
        path = tree / "data" / "L3_features" / f"symbol={symbol}" / "features.parquet"
        assert path.exists()
        frame = pd.read_parquet(path)
        assert "decision_time" in frame.columns and len(frame) > 1000
    assert (tree / "reports" / "r3" / "features.json").exists()
    assert "coverage ndogo" in capsys.readouterr().out


def test_build_features_haigusi_holdout(tree):
    """G2 — bar ya kwanza ya holdout haiandikwi kabisa, si kuandikwa kisha kuchujwa."""
    from src.data.config import load_config
    from src.data.splits import SplitPlan

    main(["--config", CONFIG, "build-features", "--symbols", SYMBOLS[0]])
    cfg = load_config(Path(CONFIG))
    holdout = pd.Timestamp(SplitPlan.from_config(cfg).holdout_start, tz="UTC")
    frame = pd.read_parquet(tree / "data" / "L3_features" / f"symbol={SYMBOLS[0]}" / "features.parquet")
    assert (frame["decision_time"] <= holdout).all()


def test_setup_flag_inatoka_kwenye_points_si_kuhesabiwa_upya(tree):
    main(["--config", CONFIG, "build-features", "--symbols", SYMBOLS[0]])
    frame = pd.read_parquet(tree / "data" / "L3_features" / f"symbol={SYMBOLS[0]}" / "features.parquet")
    points = pd.read_parquet(
        tree / "data" / "L4_labels" / "labels" / f"symbol={SYMBOLS[0]}" / "points-2016.parquet"
    )
    assert frame["setup_v1_flag"].sum() == pytest.approx(float(len(points)), rel=0.02)


# ===========================================================================
# meta-label
# ===========================================================================


def test_meta_label_inadai_features_kwanza(tree, budget_ipo, capsys):
    """Amri inayoshindwa kwa sababu nzuri lazima iseme sababu hiyo."""
    assert main(["--config", CONFIG, "meta-label", "--symbols", ",".join(SYMBOLS)]) == 2
    assert "build-features" in capsys.readouterr().err


def test_meta_label_inakataa_cell_isiyofanana_na_cost_audit(tree, budget_ipo, capsys):
    """Kubadilisha cell baada ya kuona matokeo ni uteuzi juu ya label."""
    main(["--config", CONFIG, "build-features", "--symbols", ",".join(SYMBOLS)])
    rc = main(["--config", CONFIG, "meta-label", "--cell", "1.0/2.0",
               "--symbols", ",".join(SYMBOLS)])
    assert rc == 2
    assert "UTEUZI JUU YA LABEL" in capsys.readouterr().err


def test_meta_label_inakataa_model_isiyopatikana(tree, budget_ipo, capsys):
    main(["--config", CONFIG, "build-features", "--symbols", ",".join(SYMBOLS)])
    assert main(["--config", CONFIG, "meta-label", "--model", "haipo",
                 "--symbols", ",".join(SYMBOLS)]) == 2
    assert "haipatikani" in capsys.readouterr().err


def test_meta_label_inaendesha_mzunguko_mzima(tree, budget_ipo, capsys):
    """Kiungo kizima: features → join → uniqueness → purged CV → malango."""
    main(["--config", CONFIG, "build-features", "--symbols", ",".join(SYMBOLS)])
    rc = main(["--config", CONFIG, "meta-label", "--symbols", ",".join(SYMBOLS),
               "--bootstrap", "0"])
    assert rc == 0

    out = capsys.readouterr().out
    assert "META-LABELLING" in out and "HUKUMU" in out
    payload = json.loads(
        (tree / "reports" / "r3" / "meta_label_logistic.json").read_text(encoding="utf-8")
    )
    assert payload["cell"] == [2.0, 3.0]
    assert payload["model"] == "logistic" and payload["weighted"] is True
    assert payload["n_scored"] > 500
    assert len(payload["features"]) == 25
    # Breakeven = p_tp ya msingi + gap kutoka cost_audit.json, si namba ya hapa.
    assert payload["breakeven"] == pytest.approx(payload["p_tp_base"] + 0.0065, abs=1e-9)
    assert payload["delta_mer"] == pytest.approx(0.0235)


def test_ripoti_ina_r_halisi_kwa_kila_decile(tree, budget_ipo):
    """`R` halisi ni ushahidi wa kiuchumi; probability pekee inaficha timeout."""
    main(["--config", CONFIG, "build-features", "--symbols", ",".join(SYMBOLS)])
    main(["--config", CONFIG, "meta-label", "--symbols", ",".join(SYMBOLS), "--bootstrap", "0"])
    payload = json.loads(
        (tree / "reports" / "r3" / "meta_label_logistic.json").read_text(encoding="utf-8")
    )
    if payload["verdict"] == "INCONCLUSIVE":
        pytest.skip("sampuli bandia haitoshi — deciles hazikuhesabiwa")
    assert len(payload["deciles"]) == 10
    assert all("r_net_mean" in row for row in payload["deciles"])
    assert sum(row["n"] for row in payload["deciles"]) == payload["n_scored"]


def test_n_eff_inahesabiwa_upya_kwa_rows_zilizopata_score(tree, budget_ipo):
    """`effective_n.json` ni ya setups zote; baada ya NaN na folds ni ndogo.

    Kutumia namba kubwa kungefanya kifungu cha nguvu kisifanye kazi kabisa —
    ndicho kitu pekee kinachozuia sampuli ndogo kutoa jibu la kusadikisha.
    """
    main(["--config", CONFIG, "build-features", "--symbols", ",".join(SYMBOLS)])
    main(["--config", CONFIG, "meta-label", "--symbols", ",".join(SYMBOLS), "--bootstrap", "0"])
    payload = json.loads(
        (tree / "reports" / "r3" / "meta_label_logistic.json").read_text(encoding="utf-8")
    )
    neff = payload["effective_n_scored"]
    assert neff["n_raw"] == payload["n_scored"]
    assert payload["n_eff"] == pytest.approx(neff["n_eff"])
    assert neff["n_eff"] <= neff["n_raw"]


def test_bajeti_iliyokwisha_inazuia_jaribio(tree, monkeypatch, tmp_path, capsys):
    """Lango la bajeti liko KABLA ya kazi, si baada — la sivyo si lango."""
    from src.governance import budget as bud

    ledger = tmp_path / "spent.md"
    ledger.write_text(
        _LEDGER_HEAD + "| 1 | 2026-08-14 | `zote` | EVALUATION | 7.500 | 0.000 | imekwisha |\n",
        encoding="utf-8",
        newline="\n",
    )
    monkeypatch.setattr(bud, "LEDGER", ledger, raising=False)
    main(["--config", CONFIG, "build-features", "--symbols", ",".join(SYMBOLS)])
    with pytest.raises(RuntimeError, match="bajeti"):
        main(["--config", CONFIG, "meta-label", "--symbols", ",".join(SYMBOLS)])
