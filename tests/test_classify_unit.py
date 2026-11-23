import pytest

from classify import classify, summarise

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("outcome,text,expected", [
    ("passed", "", "PASS"),
    ("skipped", "", "SKIP"),
    ("failed", "TargetFault: [FAULT] ZEPHYR FATAL ERROR", "FAULT"),
    ("failed", "TargetHang: [HANG] no prompt", "HANG"),
    ("failed", "TargetExit: [EXIT] eof", "EXIT"),
    ("failed", "assert 1 == 2", "ASSERT"),
])
def test_classify(outcome, text, expected):
    assert classify(outcome, text) == expected


def test_summarise_counts():
    tests = [{"category": "PASS"}, {"category": "PASS"}, {"category": "HANG"}]
    assert summarise(tests) == {"total": 3, "PASS": 2, "HANG": 1}
