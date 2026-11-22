import re
import time

import pytest

pytestmark = pytest.mark.app("apps/shell_demo")


def uptime_ms(sh):
    m = re.search(r"Uptime:\s*(\d+)\s*ms", sh.run("kernel uptime"))
    assert m, "no uptime in output"
    return int(m.group(1))


def test_help_lists_factory(sh):
    assert "factory" in sh.run("help")


def test_kernel_version(sh):
    assert re.search(r"Zephyr version \d+\.\d+\.\d+", sh.run("kernel version"))


def test_uptime_advances(sh):
    t1 = uptime_ms(sh)
    time.sleep(0.3)
    assert uptime_ms(sh) > t1


@pytest.mark.parametrize("a,b", [(2, 3), (-4, 10), (0, 0), (100000, 23)])
def test_add(sh, a, b):
    assert sh.run(f"factory add {a} {b}") == f"sum={a + b}"


def test_echo(sh):
    assert sh.run("factory echo hello") == "hello"


def test_info_reports_board(sh, request):
    board = request.config.getoption("--board").split("/")[0]
    assert sh.run("factory info") == f"board={board}"


def test_wrong_argument_count(sh):
    assert "wrong parameter count" in sh.run("factory add 1")


def test_unknown_command(sh):
    assert "command not found" in sh.run("nosuchcmd")
