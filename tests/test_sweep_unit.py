import pytest

from sweep import seed_list

pytestmark = pytest.mark.unit


def test_seed_list_is_deterministic_and_unique():
    a = seed_list(50)
    assert a == seed_list(50)
    assert len(set(a)) == 50


def test_seed_list_prefix_is_stable_and_in_range():
    assert seed_list(3) == [1, 0, 4294967295]
    assert seed_list(10) == seed_list(50)[:10]
    assert all(0 <= s <= 0xFFFFFFFF for s in seed_list(50))
