"""Kiungo cha T3 — purged CV, uzito wa uniqueness, utabiri wa out-of-fold.

Hii ndiyo sehemu ngumu, na haitegemei model. Model ni **kipande
kinachobadilishwa**; kinachoamua kama matokeo ni ya kweli ni kila kitu
kinachokizunguka:

* **Purged K-fold** — folds zinatoka `SplitPlan` iliyosainiwa (DF-14), tayari
  zikiwa zimepurgwa kwa embargo ya bars 36. Bila purge, label inayoanzia
  ndani ya train na kuishia ndani ya validation inavuja jibu.
* **Standardization ndani ya fold** — `mean`/`std` zinatoka **train pekee**,
  kisha zinapakwa kwenye validation. Kuzihesabu kwa data yote ni uvujaji wa
  kawaida kabisa (sheria 2 ya §6.1) na hauonekani kwenye matokeo.
* **Uzito wa uniqueness** — labels zinazopishana si observations kamili.
  Uzito unatoka `effective_n.average_uniqueness`, si idadi ghafi.
* **NaN ni NaN** — row yenye feature isiyokamilika **inatoka**, haijazwi.
  Idadi inaripotiwa; kuificha ni kuficha ukubwa halisi wa sampuli.

**Model ya msingi ni logistic yenye L2**, si gradient boosting. Sababu mbili:
wataalamu wote wawili waliidai kama baseline ya lazima kabla ya chochote
kigumu zaidi; na haina dependency, kwa hiyo inapimwa hapa hapa. Booster
inapatikana ikiwa `xgboost` imefungwa — lakini haitakiwi ili jaribio lianze,
na haitaingia bila kupita malango yale yale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd

EXPERIMENT_VERSION = 1

ModelFn = Callable[[np.ndarray, np.ndarray, np.ndarray, np.ndarray], np.ndarray]


@dataclass
class FoldReport:
    index: int
    n_train: int
    n_val: int
    val_start: str
    val_end: str


@dataclass
class OofResult:
    score: np.ndarray = field(default_factory=lambda: np.empty(0))
    mask: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=bool))
    folds: list[FoldReport] = field(default_factory=list)
    dropped_nan: int = 0
    notes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Model ya msingi — logistic yenye L2, Newton–Raphson
# --------------------------------------------------------------------------


def logistic_l2(
    x_train: np.ndarray,
    y_train: np.ndarray,
    w_train: np.ndarray,
    x_val: np.ndarray,
    lam: float = 1.0,
    iters: int = 50,
) -> np.ndarray:
    """Logistic yenye adhabu ya L2 — inarudisha **logit**, si probability.

    Logit ndiyo score ya kupanga; calibration inakuja baadaye kwenye
    `metalabel`, ikifit kwenye utabiri wa out-of-fold. Kuchanganya hizo mbili
    hapa kungeficha kama tatizo ni ranking au ni calibration.

    Intercept haiadhibiwi: kuiadhibu kungehamisha base rate kwa nguvu,
    ambayo si kitu tunachotaka kudhibiti.
    """
    n, p = x_train.shape
    design = np.hstack([x_train, np.ones((n, 1))])
    beta = np.zeros(p + 1)
    penalty = np.eye(p + 1) * lam
    penalty[-1, -1] = 0.0

    for _ in range(iters):
        z = np.clip(design @ beta, -30, 30)
        prob = 1.0 / (1.0 + np.exp(-z))
        weights = w_train * prob * (1.0 - prob)
        grad = design.T @ (w_train * (y_train - prob)) - penalty @ beta
        hess = (design * weights[:, None]).T @ design + penalty
        try:
            step = np.linalg.solve(hess + np.eye(p + 1) * 1e-9, grad)
        except np.linalg.LinAlgError:
            break
        beta += step
        if np.max(np.abs(step)) < 1e-8:
            break

    return np.hstack([x_val, np.ones((len(x_val), 1))]) @ beta


def xgboost_model(
    x_train: np.ndarray, y_train: np.ndarray, w_train: np.ndarray, x_val: np.ndarray
) -> np.ndarray:
    """Booster — **ikiwa imefungwa**. Hyperparameters zimefungwa hapa, si tuned.

    Kutuna hyperparameters kwa kuangalia matokeo ni config nyingine kila mara,
    na bajeti ya majaribio ni 7. Zimeandikwa hapa ili zionekane kwenye diff.
    """
    import xgboost as xgb  # noqa: PLC0415 — ya hiari kwa makusudi

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        min_child_weight=20,
        eval_metric="logloss",
        tree_method="hist",
        random_state=20260814,
    )
    model.fit(x_train, y_train, sample_weight=w_train)
    return model.predict_proba(x_val)[:, 1]


def available_models() -> dict[str, ModelFn]:
    models: dict[str, ModelFn] = {"logistic": logistic_l2}
    try:
        import xgboost  # noqa: F401,PLC0415
    except ImportError:
        pass
    else:
        models["xgboost"] = xgboost_model
    return models


# --------------------------------------------------------------------------
# Out-of-fold kwa folds zilizopurgwa
# --------------------------------------------------------------------------


def oof_predict(
    frame: pd.DataFrame,
    feature_names: Sequence[str],
    target: str,
    folds: list,
    model: ModelFn,
    weight_col: str | None = None,
) -> OofResult:
    """Utabiri wa out-of-fold kwa folds zilizopurgwa.

    `folds` zinatoka `SplitPlan.folds()` — `train_ranges` tayari zimepurgwa.
    Hakuna row inayotabiriwa na model iliyoiona.
    """
    out = OofResult()
    names = [n for n in feature_names if n in frame.columns]
    missing = [n for n in feature_names if n not in frame.columns]
    if missing:
        out.notes.append(f"features hazipo: {', '.join(missing)}")

    matrix = frame[names].to_numpy(dtype=float)
    good = np.isfinite(matrix).all(axis=1) & frame[target].notna().to_numpy()
    out.dropped_nan = int((~good).sum())

    days = pd.to_datetime(frame["decision_time"], utc=True).dt.date.to_numpy()
    y = frame[target].to_numpy(dtype=float)
    w = (
        frame[weight_col].to_numpy(dtype=float)
        if weight_col and weight_col in frame.columns
        else np.ones(len(frame))
    )

    score = np.full(len(frame), np.nan)
    covered = np.zeros(len(frame), dtype=bool)

    for fold in folds:
        val = good & (days >= fold.val_start) & (days <= fold.val_end)
        train = good & np.zeros(len(frame), dtype=bool)
        for start, end in fold.train_ranges:
            train |= good & (days >= start) & (days <= end)
        if train.sum() < 200 or val.sum() < 50:
            out.notes.append(f"fold {fold.index}: train {train.sum()} / val {val.sum()} — imerukwa")
            continue

        # Standardization kutoka TRAIN pekee — kuihesabu kwa data yote ni
        # uvujaji usioonekana kwenye matokeo.
        mu = matrix[train].mean(axis=0)
        sd = matrix[train].std(axis=0)
        sd[sd == 0] = 1.0
        x_train = (matrix[train] - mu) / sd
        x_val = (matrix[val] - mu) / sd

        score[val] = model(x_train, y[train], w[train], x_val)
        covered[val] = True
        out.folds.append(
            FoldReport(
                index=fold.index,
                n_train=int(train.sum()),
                n_val=int(val.sum()),
                val_start=str(fold.val_start),
                val_end=str(fold.val_end),
            )
        )

    out.score = score
    out.mask = covered
    return out


def add_uniqueness(frame: pd.DataFrame, horizon_bars: int) -> pd.DataFrame:
    """Ongeza safu ya `uniqueness` — uzito, si idadi ghafi.

    Labels zinazopishana zinashiriki mustakabali ule ule. Kuzipa uzito sawa ni
    kudai observations ambazo hazipo, na `z` inayotokana nayo ni ya uongo
    (mapitio ya nje: *"z-statistic yenu itupwe kabisa kama ushahidi"*).
    """
    from .effective_n import average_uniqueness

    _, weights = average_uniqueness(frame, horizon_bars)
    out = frame.copy()
    out["uniqueness"] = weights.reindex(frame.index).fillna(1.0)
    return out
