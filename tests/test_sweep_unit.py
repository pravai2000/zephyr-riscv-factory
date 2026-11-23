import pytest

from sweep import COVERAGE, missing_bins,  parse_cover, record_cover, seed_list

pytestmark = pytest.mark.unit


def test_seed_list_is_deterministic_and_unique():
    a = seed_list(50)
    assert a == seed_list(50)
    assert len(set(a)) == 50


def test_seed_list_prefix_is_stable_and_in_range():
    assert seed_list(3) == [1, 0, 4294967295]
    assert seed_list(10) == seed_list(50)[:10]
    assert all(0 <= s <= 0xFFFFFFFF for s in seed_list(50))


def test_parse_cover_lines():
    out = "noise\nCOVER:mutex_contended=12\nCOVER:mutex_yield_in_cs=0\nWORKLOAD RESULT x"
    assert parse_cover(out) == {"mutex_contended": 12, "mutex_yield_in_cs": 0}


def test_record_cover_accumulates():
    record_cover({"unit_test_bin": 2})
    record_cover({"unit_test_bin": 3})
    assert COVERAGE["unit_test_bin"] == 5
    del COVERAGE["unit_test_bin"]          # leave real session data untouched


def test_missing_bins_reports_zero_and_absent():
    totals = {"mutex_contended": 3, "mutex_yield_in_cs": 0}
    assert missing_bins(totals, "mutex") == ["mutex_yield_in_cs"]
    assert missing_bins({}, "mutex") == ["mutex_contended", "mutex_yield_in_cs"]


def test_missing_bins_empty_when_all_hit():
    totals = {"msgq_put_blocked": 1, "msgq_get_blocked": 2, "msgq_yield": 5}
    assert missing_bins(totals, "msgq") == []
