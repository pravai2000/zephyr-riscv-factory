import os
import re
import signal
import subprocess
from pathlib import Path

import pexpect
import pytest

REPO = Path(__file__).resolve().parents[1]
WS = REPO.parent                      # the west workspace
BUILD_TIMEOUT = 900
BOOT_TIMEOUT = 30
PROMPT = "factory> "
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_BUILT = {}                           # (app, board) -> build dir


def pytest_addoption(parser):
    parser.addoption("--board", default="qemu_riscv32")
    parser.addoption("--app", default="apps/hello")
    parser.addoption("--rebuild", action="store_true",
                     help="pristine rebuild before testing")


@pytest.fixture
def firmware(request):
    """Build the app named by @pytest.mark.app (or --app) once; return its build dir."""
    marker = request.node.get_closest_marker("app")
    app_rel = marker.args[0] if marker else request.config.getoption("--app")
    board = request.config.getoption("--board")
    key = (app_rel, board)
    if key not in _BUILT:
        pristine = "always" if request.config.getoption("--rebuild") else "auto"
        app = REPO / app_rel
        bdir = WS / "build" / "pytest" / app.name / board.replace("/", "_")
        cmd = ["west", "build", "-p", pristine, "-b", board, str(app), "-d", str(bdir)]
        res = subprocess.run(cmd, cwd=WS, capture_output=True, text=True,
                             timeout=BUILD_TIMEOUT)
        if res.returncode != 0:
            tail = "\n".join((res.stdout + res.stderr).splitlines()[-40:])
            pytest.fail(f"west build failed for {app_rel}:\n{tail}", pytrace=False)
        _BUILT[key] = bdir
    return _BUILT[key]


def _stop(child):
    if child.isalive():
        child.sendcontrol("a")        # QEMU: Ctrl-A X quits
        child.send("x")
        try:
            child.expect(pexpect.EOF, timeout=5)
        except pexpect.TIMEOUT:
            pass
    if child.isalive():
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


class Shell:
    """Send a shell command, return its output as clean text."""

    def __init__(self, child):
        self.child = child

    def wait_ready(self):
        self.child.expect_exact(PROMPT, timeout=BOOT_TIMEOUT)

    def run(self, cmd, timeout=10):
        self.child.sendline(cmd)
        self.child.expect_exact(PROMPT, timeout=timeout)
        text = ANSI.sub("", self.child.before).replace("\r", "")
        lines = text.split("\n")
        if lines and cmd in lines[0]:          # drop the echoed command line
            lines = lines[1:]
        return "\n".join(lines).strip()


@pytest.fixture
def sh(qemu):
    s = Shell(qemu)
    s.wait_ready()
    return s
