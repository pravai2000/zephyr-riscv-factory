import pytest
import time

from detect import TargetFault, TargetHang

pytestmark = [pytest.mark.app("apps/crash_demo"), pytest.mark.fault]


def test_boots_healthy(sh):
    assert "crash" in sh.run("help")


@pytest.mark.parametrize("cmd, needle", [
    ("crash oops", "Kernel oops"),
    ("crash panic", "Kernel panic"),
    ("crash illegal", "CPU exception"),
])
def test_fault_is_detected(sh, cmd, needle):
    with pytest.raises(TargetFault) as exc:
        sh.run(cmd)
    text = str(exc.value)
    assert "ZEPHYR FATAL ERROR" in text
    assert needle in text


def test_assertion_is_detected(sh):
    with pytest.raises(TargetFault) as exc:
        sh.run("crash assert")
    assert "ASSERTION FAIL" in str(exc.value)


def test_hang_is_detected(sh):
    with pytest.raises(TargetHang):
        sh.run("crash hang", timeout=3)


def test_slow_command_is_not_a_hang(sh):
    assert sh.run("crash slow", timeout=8) == "done"

def test_timeout_is_honoured(sh):
	t0 = time.monotonic()
	with pytest.raises(TargetHang):
		sh.run("crash hang", timeout=0.5)
	assert time.monotonic() -t0 < 5 
