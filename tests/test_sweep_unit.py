import pytest

from sweep import COVERAGE, parse_cover, record_cover, seed_list

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
