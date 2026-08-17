"""CLI ya T0 — ndiyo uso wa milango ya CI (DF-01 hash check, DF-04 alert).

Exit codes ndizo mkataba: 0 = sawa/skipped · 1 = ONYO au ukiukaji · 2 = hitilafu.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.data.cli import main
from tests.conftest import REPO_ROOT, variant_a_frame

CONFIG = str(REPO_ROOT / "config" / "data.yaml")


@pytest.fixture
def storage_env(monkeypatch, research_root):
    monkeypatch.setenv("ELITEFX_RESEARCH_ROOT", str(research_root))
    monkeypatch.setenv("ELITEFX_HOLDOUT_ROOT", str(research_root / "_holdout"))
    return research_root


def test_init_research_inasimamisha_muundo_wa_spec_9(storage_env, capsys):
    assert main(["--config", CONFIG, "init-research"]) == 0
    assert (storage_env / "data" / "L5_datasets").is_dir()
    assert "muundo wa research" in capsys.readouterr().out


def test_hash_l0_kisha_verify_l0_zinapita(storage_env, capsys):
    main(["--config", CONFIG, "init-research"])
    partition = storage_env / "data" / "L0_raw" / "symbol=EURUSD" / "2026-08-03.parquet"
    partition.parent.mkdir(parents=True, exist_ok=True)
    variant_a_frame().to_parquet(partition, index=False)

    assert main(["--config", CONFIG, "hash-l0"]) == 0
    out = capsys.readouterr().out
    assert "scanned=1" in out and "added=1" in out

    assert main(["--config", CONFIG, "verify-l0", "--require-storage"]) == 0
    assert "verify-l0: PASS" in capsys.readouterr().out


def test_verify_l0_inafelisha_build_partition_ikibadilika(storage_env, capsys):
    main(["--config", CONFIG, "init-research"])
    partition = storage_env / "data" / "L0_raw" / "symbol=EURUSD" / "2026-08-03.parquet"
    partition.parent.mkdir(parents=True, exist_ok=True)
    variant_a_frame().to_parquet(partition, index=False)
    main(["--config", CONFIG, "hash-l0"])
    capsys.readouterr()

    variant_a_frame().assign(bid=9.9).to_parquet(partition, index=False)
    assert main(["--config", CONFIG, "verify-l0"]) == 1
    captured = capsys.readouterr()
    assert "verify-l0: FAIL" in captured.out
    assert "IMEBADILIKA (DF-01)" in captured.err


def test_verify_l0_inaruka_pale_storage_haipo(monkeypatch, capsys):
    monkeypatch.delenv("ELITEFX_RESEARCH_ROOT", raising=False)
    assert main(["--config", CONFIG, "verify-l0"]) == 0
    assert "SKIPPED" in capsys.readouterr().out


def test_check_freshness_inaruka_bila_storage(monkeypatch, capsys):
    monkeypatch.delenv("ELITEFX_RESEARCH_ROOT", raising=False)
    assert main(["--config", CONFIG, "check-freshness"]) == 0
    assert "SKIPPED" in capsys.readouterr().out


def test_check_freshness_inatoa_json_na_exit_code(storage_env, tmp_path, capsys):
    main(["--config", CONFIG, "init-research"])
    out_file = tmp_path / "freshness.json"
    code = main(["--config", CONFIG, "check-freshness", "--json", "--out", str(out_file)])
    payload = json.loads(out_file.read_text())
    assert payload["status"] in {"SKIPPED", "NOT_STARTED"}
    assert code == (0 if payload["status"] == "SKIPPED" else 1)
    capsys.readouterr()


def test_inspect_inaonyesha_schema_moja(storage_env, capsys):
    partition = storage_env / "data" / "L0_raw" / "symbol=EURUSD" / "2026-08-03.parquet"
    partition.parent.mkdir(parents=True, exist_ok=True)
    variant_a_frame().to_parquet(partition, index=False)
    assert main(["--config", CONFIG, "inspect", str(partition)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_variant"] == "A"
    assert payload["rows"] == 6


def test_config_hash_inatoka_kwenye_faili_la_config(capsys):
    assert main(["--config", CONFIG, "config-hash"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["config_hash"].startswith("sha256:")


def test_hash_ya_sehemu_haiathiriwi_na_sehemu_nyingine(capsys):
    """Kigezo cha `labels` kikibadilika, hash ya `setups` ISIBADILIKE.

    Hii ndiyo kasoro iliyofelisha sahihi #11 (DF-20) tarehe 2026-08-13:
    `m1_check_frac` iliongezwa chini ya `labels`, `config_hash` ya faili
    nzima ikabadilika, na sahihi kuhusu SHERIA YA SETUPS ikaonekana
    imevunjika ingawa sheria haikuguswa hata herufi moja.
    """
    from src.data.config import load_config

    cfg = load_config(Path(CONFIG), env={"ELITEFX_RESEARCH_ROOT": "/tmp/x", "ELITEFX_HOLDOUT_ROOT": "/tmp/y"})
    kabla = cfg.section_hash("setups")

    badiliko = {**cfg.raw, "labels": {**cfg.raw["labels"], "m1_check_frac": 0.99}}
    mpya = replace(cfg, raw=badiliko)

    assert mpya.section_hash("labels") != cfg.section_hash("labels"), "iliyobadilika ionekane"
    assert mpya.section_hash("setups") == kabla, "isiyobadilika isiguswe"


def test_hash_ya_sehemu_haijali_maoni_wala_mpangilio(capsys):
    """Maoni na mpangilio wa mistari si maana — hash isiyaone.

    Sahihi ingevunjika kwa kuhariri maoni ya YAML, ambayo si uamuzi.
    """
    from src.data.config import load_config

    cfg = load_config(Path(CONFIG), env={"ELITEFX_RESEARCH_ROOT": "/tmp/x", "ELITEFX_HOLDOUT_ROOT": "/tmp/y"})
    upya = replace(cfg, raw={**cfg.raw, "setups": dict(reversed(list(cfg.raw["setups"].items())))})
    assert upya.section_hash("setups") == cfg.section_hash("setups")


def test_hitilafu_ya_config_inarudisha_exit_2(capsys):
    assert main(["--config", "/haipo/data.yaml", "config-hash"]) == 2
    assert "HITILAFU" in capsys.readouterr().err


# ===========================================================================
# T4 — orodha ya broker
# ===========================================================================


def test_underlyings_zinatolewa_kwenye_jozi_na_si_kwenye_index():
    """Jozi ya herufi 6 ina sarafu mbili; kitu kingine ni underlying MOJA.

    Kukisia zaidi ya hapo kunaleta makosa kimya kwenye majina yasiyo ya
    kawaida — na jina lililogawanywa vibaya linahesabiwa kama sarafu mpya
    ambayo haipo, likipotosha upangaji mzima.
    """
    from src.data.cli import _underlyings

    assert _underlyings("EURUSD") == ("EUR", "USD")
    assert _underlyings("XAUUSD") == ("XAU", "USD")
    assert _underlyings("US500") == ("US500",)
    assert _underlyings("GER40.cash") == ("GER40CASH",)
    # Kiambishi cha broker kinaondolewa kabla, kwa hiyo herufi 6 zinabaki 6.
    assert _underlyings("eurusd") == ("EUR", "USD")


def test_sarafu_mpya_ndiyo_inayopanga_orodha():
    """Blocs ndio kizuizi, si rows — na jozi za sarafu zilezile hazileti blocs."""
    from src.data.cli import _underlyings

    tuna = {"EUR", "USD", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD", "XAU"}

    def new_count(name: str) -> int:
        return len([p for p in _underlyings(name) if p not in tuna])

    assert new_count("EURSEK") == 1        # SEK ni mpya
    assert new_count("SEKNOK") == 2        # zote mbili mpya
    assert new_count("EURGBP") == 0        # jozi mpya, sarafu zilezile
    assert new_count("GBPCHF") == 0
    # Upangaji: nyingi za mpya kwanza.
    wagombea = ["EURGBP", "EURSEK", "SEKNOK", "GBPCHF"]
    wagombea.sort(key=lambda n: (-new_count(n), n))
    assert wagombea[:2] == ["SEKNOK", "EURSEK"]
    assert new_count(wagombea[-1]) == 0


def test_mwongozo_wa_amri_hautumii_mabano_ya_pembe():
    """`<...>` kwenye maandishi ya amri ni mtego kwenye cmd ya Windows.

    `set X=<thamani>` na `--symbol <JINA>` zote zinasoma `<` kama redirect ya
    faili, na PD anapata "The system cannot find the file specified" badala ya
    kile alichokusudia. Mifano lazima iwe ya kunakiliwa moja kwa moja.
    """
    import re

    source = (REPO_ROOT / "src" / "data" / "cli.py").read_text(encoding="utf-8")
    # Tafuta mabano ndani ya mistari inayoonyeshwa kwa mtumiaji pekee.
    makosa = [
        line.strip()
        for line in source.splitlines()
        if re.search(r'(set [A-Z_]+=|--symbol |--from )', line)
        and re.search(r'<[a-zA-Z ]+>', line)
    ]
    assert not makosa, f"mifano yenye mabano: {makosa}"


def test_majina_yasiyo_ya_fx_hayagawanywi_kuwa_sarafu_bandia():
    """`AUS.IDX` si `AUS`/`IDX`, na `BUND.TR` si `BUN`/`DTR`.

    Kugawanya kwa UREFU badala ya kwa ORODHA kulizalisha sarafu nne mpya
    zisizokuwepo, na kupandisha vitu visivyo FX juu ya orodha ya wagombea.
    """
    from src.data.cli import _is_fx, _underlyings

    for name in ("AUS.IDX", "BUND.TR", "CHE.IDX", "EUS.IDX", "US500", "GER40.cash"):
        parts = _underlyings(name)
        assert not _is_fx(parts), f"`{name}` imegawanywa kimakosa: {parts}"
    for name in ("EURUSD", "XAUUSD", "USDMXN", "AEDCNH"):
        assert _is_fx(_underlyings(name)), name


def test_jozi_bila_usd_au_eur_zinatambuliwa_kama_synthetic():
    """`AEDCNH` inaleta sarafu mbili mpya — na ndiyo sababu sheria ya 4 pekee ilishindwa.

    Broker anaijenga kutoka `AEDUSD × USDCNH`; spread ni jumla ya mbili, na
    utambulisho wa gharama unaifanya isiwezekane kwa `n` yoyote.
    """
    from src.data.cli import _has_anchor, _underlyings

    assert not _has_anchor(_underlyings("AEDCNH"))
    assert not _has_anchor(_underlyings("CNHZAR"))
    assert _has_anchor(_underlyings("USDMXN"))
    assert _has_anchor(_underlyings("EURSEK"))


def test_backfill_ina_ukaguzi_wa_kabla_wa_d1():
    """Ombi la ticks zisizokuwepo linazuia MT5 ~sekunde 100, bila timeout.

    Circuit breaker inasimamisha baada ya kufeli 5 — dakika 27 za kusubiri
    jibu tulilokwisha lijua. Bar ya D1 ni mpaka wa juu wa kina cha ticks, na
    kuiuliza ni ombi moja jepesi.
    """
    source = (REPO_ROOT / "src" / "data" / "cli.py").read_text(encoding="utf-8")
    assert "fetch_daily_close" in source
    assert "--skip-preflight" in source
    # Ukaguzi lazima uwe KABLA ya backfill_missing, la sivyo hauokoi chochote.
    assert source.index("UKAGUZI WA KABLA") < source.index("outcome = backfill_missing(")


def test_ukamilifu_unakamata_pande_zote_mbili():
    """Mashimo NA bars za ziada — zote mbili ni hatari, kwa sababu tofauti.

    `EURTRY` ilipita chujio cha tarehe ya kuanza ikiwa na bars 1,729 kati ya
    siku 2,150 za kazi (inakosa 421). `EURNOK` ilipita ikiwa na 2,415 — bars
    265 ZA ZIADA juu ya siku za kazi, yaani bars za wikendi.

    Mashimo yanavunja path ya ticks; bars za wikendi zinamaanisha barrier
    "iliyoguswa" wakati soko halisi limefungwa.
    """
    from datetime import date, timedelta

    a, b = date(2016, 1, 4), date(2024, 4, 1)
    siku_kazi = sum(
        1 for i in range((b - a).days) if (a + timedelta(days=i)).weekday() < 5
    )
    assert siku_kazi == 2150

    def hukumu(bars: int, lo: float = 0.90, hi: float = 1.02) -> str:
        sehemu = bars / siku_kazi
        if sehemu < lo:
            return "mashimo"
        if sehemu > hi:
            return "wikendi"
        return "sawa"

    assert hukumu(2146) == "sawa"      # EURUSD — rejeleo halisi
    assert hukumu(2175) == "sawa"      # EURZAR
    assert hukumu(2047) == "sawa"      # EURCZK
    assert hukumu(1729) == "mashimo"   # EURTRY
    assert hukumu(1627) == "mashimo"   # USDMXN
    assert hukumu(2415) == "wikendi"   # EURNOK
    assert hukumu(2433) == "wikendi"   # USDCZK


def test_symbols_zetu_hazipimwi_kwa_d1_ya_broker():
    """D1 za symbols zetu zinapakuliwa nusu — hazifai kuwa rejeleo wala mashtaka.

    `USDJPY` inaonyesha bars 1,677 kwenye D1 ya terminal, ilhali tuna bars
    50,276 za H1 kwenye L2 zilizotoka kwa broker huyu huyu. Kupima symbols
    zetu kwa D1 kungezitoa kwenye pool zenyewe.
    """
    source = (REPO_ROOT / "src" / "data" / "cli.py").read_text(encoding="utf-8")
    i = source.index("LANGO LA UKAMILIFU")
    j = source.index("hai = [s for s in wagombea if s in series]", i)
    assert "if symbol in tunazo:" in source[i:j], "zetu hazijaachwa nje ya lango"
