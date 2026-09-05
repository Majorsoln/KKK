"""Mkataba wa dirisha la data — DOCTRINE §16.1, R9, R18.

Tests hizi hazipimi kwamba code inaendesha. Zinapima kwamba **haiwezi kufanya
kile ambacho doctrine imekataza**:

* hatua ya utafiti haiwezi kuishia ndani ya holdout — hata kwa siku moja
* function inayopokea `Stage` haiwezi kusoma nje ya dirisha lake
* holdout haifunguliwi mara mbili, wala bila sheria iliyoandikwa kabla

Kila moja ni njia ambayo matokeo yangeonekana mazuri bila kuwa mazuri.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pandas as pd
import pytest

from src.data import window as win


# ===========================================================================
# Mipaka inatoka config, si kwenye code
# ===========================================================================


def test_dirisha_la_utafiti_linaishia_kabla_ya_holdout(cfg):
    """Siku ya mwisho ya utafiti LAZIMA iwe kabla ya siku ya kwanza ya holdout."""
    research = win.research_window(cfg)
    assert research.end < win.holdout_start(cfg)
    assert research.kind == win.RESEARCH


def test_madirisha_mawili_hayapishani_wala_hayaachi_pengo(cfg):
    """Kila siku ya universe iko upande MMOJA — hakuna eneo lisilo na mwenyewe."""
    research, holdout = win.research_window(cfg), win.holdout_window(cfg)
    assert (holdout.start - research.end).days == 1, (
        "siku kati ya trainval_end na holdout_start ni eneo lisilokaguliwa"
    )


def test_mipaka_haijaandikwa_kwenye_code(cfg):
    """Tarehe zinatoka config. Zikibadilika config, code inafuata."""
    assert win.research_window(cfg).start == date.fromisoformat(
        str(cfg.get("splits.data_start"))
    )
    assert win.holdout_start(cfg) == date.fromisoformat(
        str(cfg.get("splits.holdout_start"))
    )


# ===========================================================================
# R18 — assertion, si nidhamu
# ===========================================================================


def test_dirisha_linaloingia_holdout_kwa_siku_MOJA_linakataliwa(cfg):
    """Siku moja ndani ya holdout ni uvujaji ule ule na miaka miwili."""
    boundary = win.holdout_start(cfg)
    with pytest.raises(win.WindowError, match="holdout"):
        win.guard(win.Window(date(2016, 1, 4), boundary), cfg=cfg)


def test_dirisha_linaloishia_siku_moja_kabla_linapita(cfg):
    boundary = win.holdout_start(cfg)
    ok = win.Window(date(2016, 1, 4), boundary - pd.Timedelta(days=1).to_pytimedelta())
    assert win.guard(ok, cfg=cfg) is ok


def test_declare_inakagua_wakati_wa_kutangaza_si_baadaye(cfg):
    """Hatua isiyo halali inashindwa PALE inapotangazwa, kabla data haijasomwa."""
    with pytest.raises(win.WindowError):
        win.declare(
            "cost_calibration",
            "Calibration A",
            win.Window(date(2016, 1, 4), date(2025, 12, 31)),
            cfg=cfg,
        )


def test_stage_ina_sehemu_tatu_za_ushahidi(cfg):
    """§16.1: kila hatua inatangaza {start, end, purpose}."""
    stage = win.declare(
        "cost_calibration", "Calibration A (§8.3)", win.research_window(cfg), cfg=cfg
    )
    payload = stage.to_json()
    assert payload["stage"] == "cost_calibration"
    assert payload["purpose"].startswith("Calibration A")
    assert payload["start"] == "2016-01-04" and payload["end"] == "2024-03-31"


def test_stage_haiwezi_kupanuliwa_baada_ya_kutangazwa(cfg):
    """`frozen`: kupanua kunahitaji kutangaza upya, na hilo linaonekana."""
    stage = win.declare("x", "y", win.research_window(cfg), cfg=cfg)
    with pytest.raises(Exception):
        stage.window = win.holdout_window(cfg)   # type: ignore[misc]


def test_dirisha_lililogeuzwa_linakataliwa():
    with pytest.raises(win.WindowError, match="limegeuzwa"):
        win.Window(date(2024, 1, 1), date(2023, 1, 1))


# ===========================================================================
# clip() — kizuizi kiko kwenye function, si kwenye mtumiaji
# ===========================================================================


def _ticks(start: str, days: int) -> pd.DataFrame:
    stamps = pd.date_range(start, periods=days, freq="1D", tz="UTC")
    return pd.DataFrame({"timestamp": stamps, "bid": 1.10, "ask": 1.1001})


def test_clip_hairudishi_row_ya_holdout_hata_ikiwa_ipo_kwenye_frame(cfg):
    """Ndilo jaribio la msingi: data ya holdout ikiwa mezani, clip haiiguse.

    Frame inayopewa ina 2024-03-30 hadi 2024-04-03. Hatua ya utafiti lazima
    irudishe siku mbili pekee, si tano.
    """
    stage = win.declare("q", "ukaguzi", win.research_window(cfg), cfg=cfg)
    frame = _ticks("2024-03-30", 5)
    out = win.clip(frame, stage)
    assert len(out) == 2
    assert out["timestamp"].max().date() == date(2024, 3, 31)


def test_clip_inajumuisha_siku_ya_mwisho_nzima(cfg):
    """Mpaka ni INCLUSIVE — tick ya 23:59 ya siku ya mwisho ni ya utafiti."""
    stage = win.declare("q", "ukaguzi", win.research_window(cfg), cfg=cfg)
    frame = pd.DataFrame(
        {"timestamp": [pd.Timestamp("2024-03-31 23:59:59.999999", tz="UTC")],
         "bid": [1.1], "ask": [1.1001]}
    )
    assert len(win.clip(frame, stage)) == 1


def test_clip_inadai_safu_ya_muda(cfg):
    stage = win.declare("q", "ukaguzi", win.research_window(cfg), cfg=cfg)
    with pytest.raises(win.WindowError, match="haipo"):
        win.clip(pd.DataFrame({"bid": [1.1]}), stage)


# ===========================================================================
# R9 — holdout inafunguliwa MARA MOJA
# ===========================================================================


def test_holdout_haifunguliwi_bila_sheria_iliyoandikwa_kabla(cfg, tmp_path):
    with pytest.raises(win.WindowError, match="sheria ya uteuzi haipo"):
        win.open_holdout(
            cfg, rule_path=tmp_path / "haipo.json", ledger=tmp_path / "ledger.json"
        )


def test_holdout_inafunguliwa_mara_moja_kisha_inakataa(cfg, tmp_path):
    """Ufunguzi wa pili unashindwa, na ujumbe unaeleza kwa nini si urasimu."""
    rule = tmp_path / "sheria.json"
    rule.write_text(json.dumps({"min_share": 0.6}), encoding="utf-8")
    ledger = tmp_path / "holdout_touch.json"

    stage = win.open_holdout(cfg, rule_path=rule, ledger=ledger)
    assert stage.window.kind == win.HOLDOUT
    assert stage.window.start == win.holdout_start(cfg)

    with pytest.raises(win.WindowError, match="MARA MOJA"):
        win.open_holdout(cfg, rule_path=rule, ledger=ledger)


def test_ufunguzi_unarekodi_sha256_ya_sheria(cfg, tmp_path):
    """Sheria ikibadilishwa baada ya ufunguzi, rekodi inaonyesha tofauti.

    Bila hash, sheria "iliyoandikwa kabla" ingeweza kuandikwa upya baada ya
    kuona jibu, na hakuna kitu kingeonyesha.
    """
    import hashlib

    rule = tmp_path / "sheria.json"
    payload = json.dumps({"min_share": 0.6}).encode()
    rule.write_bytes(payload)
    ledger = tmp_path / "holdout_touch.json"

    win.open_holdout(cfg, rule_path=rule, ledger=ledger)
    rekodi = json.loads(ledger.read_text(encoding="utf-8"))
    assert rekodi["rule_sha256"] == hashlib.sha256(payload).hexdigest()
    assert rekodi["kind"] == win.HOLDOUT
    datetime.fromisoformat(rekodi["opened_at"])   # ni ISO halali


def test_kupata_dirisha_la_holdout_SI_kuifungua(cfg, tmp_path):
    """`holdout_window()` haiandiki ledger — kutazama mpaka si kutumia data."""
    ledger = tmp_path / "holdout_touch.json"
    win.holdout_window(cfg)
    assert not ledger.exists()
