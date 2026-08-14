"""Kiungo cha T3 — purged CV na out-of-fold.

Tests hapa hazipimi model. Zinapima **kila kitu kinachozunguka model**, kwa
sababu ndipo uvujaji unapoishi: fold inayoona validation yake, standardization
inayotumia data yote, NaN iliyojazwa kimya.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.data.experiment import (
    add_uniqueness,
    available_models,
    logistic_l2,
    oof_predict,
)
from src.data.splits import Fold


def _folds() -> list[Fold]:
    """Folds mbili zilizopurgwa, zikiacha dirisha lisilotumiwa na yeyote.

    `Okt 1 – Des 31` haiko kwenye train wala val ya fold yoyote. Dirisha hilo
    ndilo linalofanya test ya standardization iwezekane: chini ya code sahihi
    rows hizo hazina athari yoyote, chini ya standardization ya global
    zinabadilisha kila utabiri.
    """
    return [
        Fold(
            index=1,
            val_start=date(2020, 2, 1),
            val_end=date(2020, 2, 29),
            train_ranges=((date(2020, 3, 5), date(2020, 9, 30)),),
        ),
        Fold(
            index=2,
            val_start=date(2020, 8, 1),
            val_end=date(2020, 8, 31),
            train_ranges=((date(2020, 1, 1), date(2020, 7, 25)),),
        ),
    ]


def _frame(n: int = 2920, seed: int = 0, signal: float = 1.0) -> pd.DataFrame:
    rng = np.random.RandomState(seed)
    stamps = pd.date_range("2020-01-01", periods=n, freq="3h", tz="UTC")
    f1 = rng.normal(0, 1, n)
    f2 = rng.normal(0, 1, n)
    prob = 1.0 / (1.0 + np.exp(-(signal * f1 - 0.2)))
    return pd.DataFrame(
        {
            "symbol": "EURUSD",
            "decision_time": stamps,
            "f1": f1,
            "f2": f2,
            "y": (rng.uniform(size=n) < prob).astype(float),
        }
    )


# ===========================================================================
# Model ya msingi
# ===========================================================================


def test_logistic_inapata_signal_na_kupuuza_kelele():
    frame = _frame(n=8000, signal=1.5)
    x = frame[["f1", "f2"]].to_numpy()
    y = frame["y"].to_numpy()
    w = np.ones(len(y))
    score = logistic_l2(x, y, w, x)
    assert np.corrcoef(score, frame["f1"])[0, 1] > 0.9
    assert abs(np.corrcoef(score, frame["f2"])[0, 1]) < 0.3


def test_logistic_inarudisha_logit_si_probability():
    """Score ya kupanga ni logit; calibration inakuja baadaye, si hapa.

    Kuvichanganya kungeficha kama tatizo ni ranking au ni calibration.
    """
    frame = _frame(n=4000, signal=2.0)
    x = frame[["f1", "f2"]].to_numpy()
    score = logistic_l2(x, frame["y"].to_numpy(), np.ones(len(frame)), x)
    assert score.min() < 0.0 and score.max() > 1.0, "probability ingekuwa ndani ya [0,1]"


def test_orodha_ya_models_daima_ina_baseline():
    models = available_models()
    assert "logistic" in models, "baseline lazima ipatikane bila dependency yoyote"


# ===========================================================================
# Purged CV — hapa ndipo uvujaji unapoishi
# ===========================================================================


def test_hakuna_row_inayotabiriwa_na_model_iliyoiona():
    """Kila utabiri ni out-of-fold. Ndiyo maana yote ya purged CV."""
    frame = _frame(n=2920)
    folds = _folds()
    result = oof_predict(frame, ["f1", "f2"], "y", folds, logistic_l2)

    days = pd.to_datetime(frame["decision_time"], utc=True).dt.date.to_numpy()
    for fold in result.folds:
        spec = next(f for f in folds if f.index == fold.index)
        val = (days >= spec.val_start) & (days <= spec.val_end)
        for start, end in spec.train_ranges:
            train = (days >= start) & (days <= end)
            assert not (val & train).any(), "fold inaona validation yake"


def test_rows_nje_ya_folds_hazipati_utabiri():
    """Pengo la purge/embargo halipaswi kupata score — likipata, purge ni bandia."""
    frame = _frame(n=2920)
    result = oof_predict(frame, ["f1", "f2"], "y", _folds(), logistic_l2)
    days = pd.to_datetime(frame["decision_time"], utc=True).dt.date.to_numpy()

    ndani = np.zeros(len(frame), dtype=bool)
    for fold in _folds():
        ndani |= (days >= fold.val_start) & (days <= fold.val_end)
    assert not result.mask[~ndani].any()
    assert np.isnan(result.score[~ndani]).all()


def test_standardization_haitumii_data_nje_ya_train():
    """`mean`/`std` za dataset nzima ni uvujaji usioonekana kwenye matokeo.

    Kupima: chafua rows za `Okt–Des`, ambazo HAZIKO kwenye train wala val ya
    fold yoyote. Chini ya code sahihi hazina athari — utabiri wote unabaki
    bit-kwa-bit ule ule. Chini ya `matrix.mean(axis=0)` ya global, `mu`/`sd`
    zinahama na KILA utabiri unabadilika.

    **Toleo la kwanza la test hii lilikuwa batili.** Lilichafua validation ya
    fold 1 na kudai fold 2 isibadilike — kumbe validation ya fold 1 ipo NDANI
    ya train ya fold 2, ndivyo purged K-fold inavyofanya kazi. Test iliyofeli
    ilikuwa ikipima kitu kisichowezekana, si bug.
    """
    frame = _frame(n=2920, seed=3)
    folds = _folds()
    kabla = oof_predict(frame, ["f1", "f2"], "y", folds, logistic_l2)

    days = pd.to_datetime(frame["decision_time"], utc=True).dt.date.to_numpy()
    nje = days >= date(2020, 10, 1)
    assert nje.sum() > 100, "dirisha lisilotumiwa halina rows za kutosha kupima"

    tainted = frame.copy()
    tainted.loc[nje, "f1"] = tainted.loc[nje, "f1"] * 50.0 + 1000.0
    baada = oof_predict(tainted, ["f1", "f2"], "y", folds, logistic_l2)

    assert (kabla.mask == baada.mask).all()
    a, b = kabla.score[kabla.mask], baada.score[baada.mask]
    assert len(a) > 100
    assert np.allclose(a, b, rtol=1e-10, atol=1e-12), (
        "utabiri umebadilika baada ya kuchafua rows zisizo kwenye fold yoyote — "
        "standardization inatumia data yote"
    )


def test_labels_za_validation_hazitumiki_kwenye_kufit():
    """`y` ya validation lazima ibaki bila kuguswa hadi tathmini.

    Kupima: geuza `y` ZOTE za validation ya fold 2. Utabiri wa fold 2 haupaswi
    kubadilika hata kidogo — model haiwezi kuwa imeziona. (Fold 1 ITABADILIKA,
    kwa sababu Agosti iko ndani ya train yake; ndiyo maana tunapima fold 2
    pekee.)
    """
    frame = _frame(n=2920, seed=4)
    folds = _folds()
    kabla = oof_predict(frame, ["f1", "f2"], "y", folds, logistic_l2)

    days = pd.to_datetime(frame["decision_time"], utc=True).dt.date.to_numpy()
    fold2_val = (days >= folds[1].val_start) & (days <= folds[1].val_end)
    tainted = frame.copy()
    tainted.loc[fold2_val, "y"] = 1.0 - tainted.loc[fold2_val, "y"]
    baada = oof_predict(tainted, ["f1", "f2"], "y", folds, logistic_l2)

    a = kabla.score[fold2_val & kabla.mask]
    b = baada.score[fold2_val & baada.mask]
    assert len(a) > 50
    assert np.allclose(a, b, rtol=1e-10, atol=1e-12), (
        "utabiri wa fold 2 umebadilika baada ya kugeuza labels zake — model imeziona"
    )


def test_nan_zinatolewa_na_kuhesabiwa_si_kujazwa():
    """Sheria 7 — hakuna imputation ya kubuni, na idadi inaripotiwa."""
    frame = _frame(n=2920)
    frame.loc[frame.index[:300], "f1"] = np.nan
    result = oof_predict(frame, ["f1", "f2"], "y", _folds(), logistic_l2)
    assert result.dropped_nan == 300
    assert not result.mask[:300].any()


def test_feature_isiyokuwepo_inaripotiwa_si_kunyamazwa():
    frame = _frame(n=1200)
    result = oof_predict(frame, ["f1", "haipo"], "y", _folds(), logistic_l2)
    assert any("haipo" in n for n in result.notes)


def test_fold_isiyo_na_data_ya_kutosha_inarukwa_kwa_kelele():
    frame = _frame(n=200)
    result = oof_predict(frame, ["f1", "f2"], "y", _folds(), logistic_l2)
    assert any("imerukwa" in n for n in result.notes)


# ===========================================================================
# Uzito wa uniqueness
# ===========================================================================


def test_uniqueness_inaongezwa_na_iko_ndani_ya_sifuri_na_moja():
    frame = add_uniqueness(_frame(n=1000), horizon_bars=24)
    assert "uniqueness" in frame.columns
    assert (frame["uniqueness"] > 0).all() and (frame["uniqueness"] <= 1.0 + 1e-9).all()


def test_labels_zinazopishana_zinapata_uzito_mdogo():
    """Bars 23/24 zikishirikiwa, observation si observation kamili."""
    mnene = _frame(n=600)
    mnene["decision_time"] = pd.date_range("2020-01-01", periods=600, freq="1h", tz="UTC")
    mwembamba = _frame(n=600)
    mwembamba["decision_time"] = pd.date_range("2020-01-01", periods=600, freq="48h", tz="UTC")

    assert add_uniqueness(mnene, 24)["uniqueness"].mean() < 0.3
    assert add_uniqueness(mwembamba, 24)["uniqueness"].mean() == pytest.approx(1.0)
