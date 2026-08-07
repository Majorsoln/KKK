"""Sahihi ya PD — §0 ya IMPLEMENTATION_PLAN (lango G14).

`VERIFIED` ilikuwa neno lisilo na maana ya kiufundi: hakuna mahali sahihi
ilikaa, na hakuna kilichozuia kipengele kupanda bila mtu kukiangalia. Tests hizi
zinalinda maana yake.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.governance import signatures as sig

REPO = Path(__file__).resolve().parents[1]


PD = "PD <pd@elitefx.test>"


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    """Ledger yenye PD aliyetangazwa — ndivyo ilivyo kwenye repo halisi."""
    path = tmp_path / "SIGNATURES.md"
    path.write_text(f"# SAHIHI\n\n**PD:** `{PD}`\n\n", encoding="utf-8")
    return path


@pytest.fixture
def evidence(tmp_path: Path) -> Path:
    path = tmp_path / "quality_report.json"
    path.write_text(json.dumps({"totals": {"partitions": 400, "failed": 10}}), encoding="utf-8")
    return path


def _sign(ledger: Path, evidence: Path | None = None, **kwargs):
    payload = {
        "item": "DF-05",
        "decision": "VERIFIED",
        "reason": "nimekagua sababu zote za kufeli",
        "config_hash": "abc123def456",
        "code_rev": "deadbee",
        "signer": PD,
        "ledger": ledger,
        "plan": REPO / "docs" / "IMPLEMENTATION_PLAN.md",
        "root": ledger.parent,
    }
    payload.update(kwargs)
    return sig.append(evidence=evidence, **payload)


# ===========================================================================
# Rejista ndiyo mipaka ya sahihi
# ===========================================================================


def test_rejista_inasomeka_kamili_kutoka_kwenye_mpango():
    """Familia zote nne. `K1-07` ina namba kwenye prefix — isirukwe kimya."""
    ids = sig.register_ids(REPO / "docs" / "IMPLEMENTATION_PLAN.md")
    for expected in ("DF-05", "K1-07", "RCE-13", "RS-01", "DF-20", "RS-17"):
        assert expected in ids, f"{expected} haikusomeka kwenye rejista"


def test_sahihi_haiwezi_kutaja_kipengele_kisichokuwepo(ledger, evidence):
    with pytest.raises(sig.SignatureError, match="haipo kwenye rejista"):
        _sign(ledger, evidence, item="ZZ-99")


def test_uamuzi_usiojulikana_unakataliwa(ledger, evidence):
    with pytest.raises(sig.SignatureError, match="haujulikani"):
        _sign(ledger, evidence, decision="SAWA")


# ===========================================================================
# Sheria ya 3 ya §0: hakuna VERIFIED bila ushahidi
# ===========================================================================


def test_verified_bila_ushahidi_inakataliwa(ledger):
    with pytest.raises(sig.SignatureError, match="inahitaji faili la ushahidi"):
        _sign(ledger, None)


def test_lesson_haihitaji_faili_la_ushahidi(ledger):
    """`LESSON` ni jibu halali linaloweza kutokana na hoja, si ripoti."""
    signature = _sign(ledger, None, decision="LESSON", reason="familia haikupimika")
    assert signature.decision == "LESSON"


def test_sahihi_bila_sababu_inakataliwa(ledger, evidence):
    with pytest.raises(sig.SignatureError, match="alama tupu"):
        _sign(ledger, evidence, reason="   ")


# ===========================================================================
# Kinga kuu: ushahidi hauwezi kubadilika baada ya kusainiwa
# ===========================================================================


def test_ushahidi_ukibadilika_baada_ya_sahihi_uthibitisho_unafeli(ledger, evidence):
    """Hila ya kawaida zaidi: kusaini ripoti, kisha kuiandika upya."""
    _sign(ledger, evidence)
    assert sig.verify(ledger=ledger, plan=REPO / "docs" / "IMPLEMENTATION_PLAN.md",
                      root=ledger.parent).ok

    evidence.write_text(json.dumps({"totals": {"partitions": 400, "failed": 0}}), encoding="utf-8")
    report = sig.verify(
        ledger=ledger, plan=REPO / "docs" / "IMPLEMENTATION_PLAN.md", root=ledger.parent
    )
    assert not report.ok
    assert any("umebadilika baada ya kusainiwa" in p for p in report.problems)


def test_ushahidi_ukifutwa_uthibitisho_unafeli(ledger, evidence):
    _sign(ledger, evidence)
    evidence.unlink()
    report = sig.verify(
        ledger=ledger, plan=REPO / "docs" / "IMPLEMENTATION_PLAN.md", root=ledger.parent
    )
    assert not report.ok and any("haupo tena" in p for p in report.problems)


def test_config_hash_inahifadhiwa_pamoja_na_sahihi(ledger, evidence):
    """Kusaini ripoti kisha kubadilisha vizingiti kunaonekana — config_hash imo."""
    signature = _sign(ledger, evidence, config_hash="0123456789abcdef0123456789abcdef")
    assert signature.config_hash == "0123456789abcdef0123456789abcdef"
    # Jedwali linahifadhi herufi 16 za kwanza — inasomeka, na inatosha kugundua
    # vizingiti vilivyobadilika baada ya kusainiwa.
    stored = sig.load(ledger)[0].config_hash
    assert stored == "0123456789abcdef" and len(stored) == sig.HASH_PREFIX


# ===========================================================================
# Ledger ni ya kuongezwa tu
# ===========================================================================


def test_uamuzi_ukibadilika_unawekwa_mstari_mpya(ledger, evidence):
    _sign(ledger, evidence, decision="REJECTED", reason="ushahidi hautoshi")
    _sign(ledger, evidence, decision="VERIFIED", reason="ripoti mpya inatosha")
    rows = sig.load(ledger)
    assert [r.number for r in rows] == [1, 2]
    assert [r.decision for r in rows] == ["REJECTED", "VERIFIED"]

    report = sig.verify(
        ledger=ledger, plan=REPO / "docs" / "IMPLEMENTATION_PLAN.md", root=ledger.parent
    )
    assert report.verified_items == {"DF-05"}, "uamuzi wa mwisho ndio unaotawala"


def test_rejected_baada_ya_verified_inaondoa_hadhi(ledger, evidence):
    _sign(ledger, evidence, decision="VERIFIED", reason="ilionekana sawa")
    _sign(ledger, evidence, decision="REJECTED", reason="nimegundua kasoro")
    report = sig.verify(
        ledger=ledger, plan=REPO / "docs" / "IMPLEMENTATION_PLAN.md", root=ledger.parent
    )
    assert report.verified_items == set()


def test_mwenye_sahihi_lazima_awe_na_utambulisho_wa_git(ledger, evidence):
    _sign(ledger, evidence, signer="mtu fulani")
    report = sig.verify(
        ledger=ledger, plan=REPO / "docs" / "IMPLEMENTATION_PLAN.md", root=ledger.parent
    )
    assert not report.ok and any("utambulisho wa git" in p for p in report.problems)


def test_pending_inaonyesha_visivyosainiwa(ledger, evidence):
    _sign(ledger, evidence)
    ids = sig.register_ids(REPO / "docs" / "IMPLEMENTATION_PLAN.md")
    waiting = sig.pending(ids, ledger=ledger)
    assert "DF-05" not in waiting and "DF-06" in waiting


# ===========================================================================
# Ledger halisi ya repo
# ===========================================================================


def test_ledger_ya_repo_inapita_lango_g14():
    """Sahihi zilizowekwa kweli ni halali (ushahidi wa research hauko CI)."""
    report = sig.verify(
        ledger=REPO / sig.LEDGER,
        plan=REPO / "docs" / "IMPLEMENTATION_PLAN.md",
        root=REPO,
        check_evidence=False,
    )
    assert report.ok, report.problems


def test_mtekelezaji_hawezi_kujisainia_verified(ledger, evidence):
    """`VERIFIED` ni mamlaka ya PD PEKEE (§1.1) — si ya anayeandika code.

    Hii ndiyo kinga inayozuia mtekelezaji — au model — kujipandisha hadhi.
    """
    plan = REPO / "docs" / "IMPLEMENTATION_PLAN.md"
    assert sig.declared_pd(ledger) == PD
    _sign(ledger, evidence)
    assert sig.verify(ledger=ledger, plan=plan, root=ledger.parent).ok

    _sign(ledger, evidence, item="DF-06", signer="Mtekelezaji <dev@elitefx.test>")
    report = sig.verify(ledger=ledger, plan=plan, root=ledger.parent)
    assert not report.ok
    assert any("si PD" in p for p in report.problems)
    assert "DF-06" not in report.verified_items, "hadhi haipandi kwa sahihi isiyo halali"
