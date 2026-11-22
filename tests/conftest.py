import os
import signal
import subprocess
from pathlib import Path

import pexpect
import pytest

REPO = Path(__file__).resolve().parents[1]
WS = REPO.parent                      # the west workspace
BUILD_TIMEOUT = 900                   # first build is slow
BOOT_TIMEOUT = 30


def pytest_addoption(parser):
    parser.addoption("--board", default="qemu_riscv32")
    parser.addoption("--app", default="apps/hello")
    parser.addoption("--rebuild", action="store_true",
                     help="pristine rebuild before testing")


@pytest.fixture(scope="session")
def firmware(request):
    """Build the app once per test session; return its build directory."""
    board = request.config.getoption("--board")
    app = REPO / request.config.getoption("--app")
    pristine = "always" if request.config.getoption("--rebuild") else "auto"
    bdir = WS / "build" / "pytest" / app.name / board.replace("/", "_")

    cmd = ["west", "build", "-p", pristine, "-b", board, str(app), "-d", str(bdir)]
    res = subprocess.run(cmd, cwd=WS, capture_output=True, text=True,
                         timeout=BUILD_TIMEOUT)
    if res.returncode != 0:
        tail = "\n".join((res.stdout + res.stderr).splitlines()[-40:])
        pytest.fail(f"west build failed:\n{tail}", pytrace=False)
    return bdir


def _stop(child):
    if child.isalive():
        child.sendcontrol("a")        # QEMU: Ctrl-A X quits
        child.send("x")
        try:
            child.expect(pexpect.EOF, timeout=5)
        except pexpect.TIMEOUT:
            pass
    if child.isalive():               # still there: kill the whole process group
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    child.close(force=True)


@pytest.fixture
def qemu(firmware, request):
    """Boot the built image in QEMU; yield the pexpect child."""
    logdir = REPO / "logs"
    logdir.mkdir(exist_ok=True)
    logfile = open(logdir / f"{request.node.name}.log", "w")

    child = pexpect.spawn("west", ["build", "-d", str(firmware), "-t", "run"],
                          cwd=str(WS), encoding="utf-8", timeout=BOOT_TIMEOUT)
    child.logfile_read = logfile
    try:
        yield child
    finally:
        _stop(child)
        logfile.close()
