"""§9 ya DATA_FEATURE_STANDARD — muundo wa research repo.

Rejista: kazi ya 4 ya T0 (muundo wa research repo).
"""

from __future__ import annotations

from src.data.research_layout import (
    LAYOUT_DIRS,
    init_research_tree,
    verify_research_tree,
)


def test_muundo_wote_wa_spec_9_unatengenezwa(tmp_path):
    root = tmp_path / "research"
    result = init_research_tree(root)
    assert set(result.created) == set(LAYOUT_DIRS)
    assert verify_research_tree(root) == []


def test_folda_za_tabaka_l0_hadi_l5_zipo(tmp_path):
    """L0→L5 + reports nne za spec §9."""
    root = tmp_path / "research"
    init_research_tree(root)
    for layer in ("L0_raw", "L1_clean", "L2_bars", "L3_features", "L4_labels", "L5_datasets"):
        assert (root / "data" / layer).is_dir()
    for report in ("quality", "screening", "ablation", "calibration"):
        assert (root / "reports" / report).is_dir()
    assert (root / "src").is_dir()


def test_ni_idempotent_na_haigusi_kilichopo(tmp_path):
    root = tmp_path / "research"
    init_research_tree(root)
    marker = root / "data" / "L0_raw" / "partition.parquet"
    marker.write_bytes(b"data ya L0")

    second = init_research_tree(root)
    assert second.created == []
    assert set(second.existing) == set(LAYOUT_DIRS)
    assert marker.read_bytes() == b"data ya L0"


def test_readme_inaeleza_sheria_za_l0_na_holdout(tmp_path):
    root = tmp_path / "research"
    init_research_tree(root)
    text = (root / "README.md").read_text(encoding="utf-8")
    assert "L0 haibadilishwi" in text
    assert "provenance=broker" in text
    assert "dataset_id" in text
    assert "R8" in text


def test_folda_iliyofutwa_inagunduliwa(tmp_path):
    root = tmp_path / "research"
    init_research_tree(root)
    (root / "reports" / "ablation").rmdir()
    assert verify_research_tree(root) == ["reports/ablation"]
