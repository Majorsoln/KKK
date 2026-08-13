"""Bajeti ya majaribio — lango linalozuia, si linaloonya.

Darasa la tatu la uvujaji (uteuzi) halina detector. Bajeti hii ndiyo dawa yake
ya kiufundi, kwa hiyo kila test hapa inauliza swali moja: **je inazuia kweli?**
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.governance import budget as bud


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "TRIAL_BUDGET.md"
    path.write_text(bud.render_header(sr_target=0.7, years=8.25), encoding="utf-8")
    return path


def test_bajeti_inatokana_na_sr_unayoiahidi(ledger):
    loaded = bud.load(ledger)
    assert loaded.sr_target == 0.7
    assert loaded.total == pytest.approx(7.5, rel=0.03)
    assert loaded.remaining == pytest.approx(7.5, rel=0.03)


def test_matumizi_yanapunguza_na_yanahifadhiwa(ledger):
    bud.spend("meta-label-v1", 1.0, "meta-labelling baseline kwenye L4 iliyopo", path=ledger)
    bud.spend("meta-label-v2", 1.0, "horizon 12H badala ya 24H", path=ledger)
    loaded = bud.load(ledger)
    assert loaded.spent == 2.0
    assert loaded.remaining == pytest.approx(5.5, rel=0.05)
    assert [e.config_id for e in loaded.entries] == ["meta-label-v1", "meta-label-v2"]


def test_bajeti_ikiisha_inakataa_si_kuonya(ledger):
    """Onyo lisingezuia chochote. Mtekelezaji aliyechoka angeliruka."""
    bud.spend("a", 7.0, "matumizi makubwa ya kwanza", path=ledger)
    with pytest.raises(ValueError, match="bajeti imekwisha"):
        bud.spend("b", 1.0, "jaribio jingine", path=ledger)


def test_guard_inainua_pale_bajeti_imekwisha(ledger):
    bud.guard(ledger)                       # bado ipo — kimya
    bud.spend("a", 7.0, "configs saba", path=ledger)
    # Imebaki 0.55 — chini ya config MOJA, kwa hiyo ni sifuri kwa vitendo.
    assert bud.load(ledger).remaining < 1.0
    with pytest.raises(RuntimeError, match="imekwisha"):
        bud.guard(ledger)


def test_replication_haipunguzi_lakini_inarekodiwa(ledger):
    """Msamaha mmoja, uliosainiwa — na bado unaonekana kwenye rekodi."""
    bud.spend(
        "menkhoff-monthly",
        1.0,
        "replication ya currency momentum; matokeo HAYARUHUSIWI kwenye uteuzi",
        kind="REPLICATION",
        path=ledger,
    )
    loaded = bud.load(ledger)
    assert loaded.spent == 0.0
    assert loaded.remaining == pytest.approx(7.5, rel=0.03)
    assert loaded.entries[0].kind == "REPLICATION"


def test_sababu_ni_ya_lazima(ledger):
    """Bila sababu, ledger ni orodha tupu — somo lile lile la sahihi #4."""
    with pytest.raises(ValueError, match="sababu"):
        bud.spend("a", 1.0, "...", path=ledger)


def test_bila_kichwa_matumizi_yanakataliwa(tmp_path):
    """Bajeti isiyotangazwa si bajeti. SR* lazima isainiwe KABLA."""
    path = tmp_path / "tupu.md"
    path.write_text("# tupu\n", encoding="utf-8")
    with pytest.raises(ValueError, match="haijatangazwa"):
        bud.spend("a", 1.0, "jaribio bila bajeti iliyotangazwa", path=path)


def test_cluster_weight_inahesabu_makundi_si_idadi():
    """Cells 25 zilizoangaliwa ni narrow/mid/wide — trials 3, si 25."""
    cells = [f"{sl}/{tp}" for sl in (0.5, 0.75, 1.0, 1.5, 2.0) for tp in (0.5, 1.0, 1.5, 2.0, 3.0)]
    clusters = {
        c: ("narrow" if float(c.split("/")[0]) <= 0.75 else
            "wide" if float(c.split("/")[0]) >= 1.5 else "mid")
        for c in cells
    }
    assert len(cells) == 25
    assert bud.cluster_weight(cells, clusters) == 3.0


def test_faili_ni_la_kuongezwa_tu(ledger):
    """Matumizi ya awali hayafutwi wala kuhaririwa."""
    bud.spend("a", 1.0, "ya kwanza", path=ledger)
    kabla = ledger.read_text(encoding="utf-8")
    bud.spend("b", 1.0, "ya pili", path=ledger)
    baada = ledger.read_text(encoding="utf-8")
    assert baada.startswith(kabla), "mstari wa zamani lazima ubaki kama ulivyo"
