import pytest

from detect import TargetFault, TargetHang
from sweep import run_cmd

pytestmark = [pytest.mark.app("apps/crash_demo"), pytest.mark.fault]


def test_target_recovers_after_fault(shared):
    assert "crash" in run_cmd(shared, "help")
    boots = shared.boots
    with pytest.raises(TargetFault) as exc:
        run_cmd(shared, "crash oops")
    assert "replay: crash oops" in str(exc.value)      # the replay hint is attached
    assert "crash" in run_cmd(shared, "help")          # a fresh boot answers
    assert shared.boots == boots + 1


def test_target_recovers_after_hang(shared):
    assert "crash" in run_cmd(shared, "help")
    boots = shared.boots
    with pytest.raises(TargetHang):
        run_cmd(shared, "crash hang", timeout=3)
    assert "crash" in run_cmd(shared, "help")
    assert shared.boots == boots + 1
