import os
import re
import signal
import subprocess
from pathlib import Path
from detect import TargetProblem, expect_ok
from sweep import COVERAGE, seed_list

import pexpect
import pytest

REPO = Path(__file__).resolve().parents[1]
WS = REPO.parent                      # the west workspace
BUILD_TIMEOUT = 900
BOOT_TIMEOUT = 30
PROMPT = "factory> "
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_BUILT = {}                           # (app, board) -> build dir



def pytest_terminal_summary(terminalreporter):
    if not COVERAGE:
        return
    terminalreporter.section("firmware functional coverage")
    width = max(len(name) for name in COVERAGE)
    for name in sorted(COVERAGE):
        total = COVERAGE[name]
        note = "   <-- never hit" if total == 0 else ""
        terminalreporter.write_line(f"{name:<{width}}  {total:>10}{note}")

def pytest_addoption(parser):
    parser.addoption("--board", default="qemu_riscv32")
    parser.addoption("--app", default="apps/hello")
    parser.addoption("--rebuild", action="store_true",
                     help="pristine rebuild before testing")
    parser.addoption("--seeds", type=int, default=10,
                     help="number of seeds each seed-sweep test runs (default 10)")

def pytest_generate_tests(metafunc):
    if "seed" not in metafunc.fixturenames:
        return
    for mark in metafunc.definition.iter_markers("parametrize"):
        argnames = mark.args[0] if mark.args else mark.kwargs.get("argnames", "")
        names = ([a.strip() for a in argnames.split(",")]
                 if isinstance(argnames, str) else list(argnames))
        if "seed" in names:
            return                    # this test supplies its own seeds
    n = max(metafunc.config.getoption("--seeds"), 1)
    params = [
        pytest.param(s, id=f"seed={s}",
                     marks=[pytest.mark.slow] if i >= 10 else [])
        for i, s in enumerate(seed_list(n))
    ]
    metafunc.parametrize("seed", params)


def build_app(config, app_rel):
    """Build an app once per session; return its build directory."""
    board = config.getoption("--board")
    key = (app_rel, board)
    if key not in _BUILT:
        pristine = "always" if config.getoption("--rebuild") else "auto"
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


def spawn_qemu(bdir, logfile):
    child = pexpect.spawn("west", ["build", "-d", str(bdir), "-t", "run"],
                          cwd=str(WS), encoding="utf-8", timeout=BOOT_TIMEOUT)
    child.logfile_read = logfile
    return child


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


def _open_log(name):
    logdir = REPO / "logs"
    logdir.mkdir(exist_ok=True)
    return open(logdir / f"{name}.log", "w")


@pytest.fixture
def firmware(request):
    marker = request.node.get_closest_marker("app")
    app_rel = marker.args[0] if marker else request.config.getoption("--app")
    return build_app(request.config, app_rel)


@pytest.fixture
def qemu(firmware, request):
    """Boot the built image in QEMU; yield the pexpect child."""
    logfile = _open_log(request.node.name)
    child = spawn_qemu(firmware, logfile)
    try:
        yield child
    finally:
        _stop(child)
        logfile.close()


@pytest.fixture(scope="session")
def run_to_marker(pytestconfig):
    """f(app_rel, pattern, timeout) -> console text up to and including pattern."""
    def run(app_rel, pattern, timeout=120):
        bdir = build_app(pytestconfig, app_rel)
        logfile = _open_log(Path(app_rel).name)
        child = spawn_qemu(bdir, logfile)
        try:
            child.expect(pattern, timeout=timeout)
            return child.before + child.after
        except (pexpect.TIMEOUT, pexpect.EOF) as exc:
            pytest.fail(f"{app_rel}: {type(exc).__name__} waiting for {pattern!r}. "
                        f"Console tail:\n{(child.before or '')[-1500:]}", pytrace=False)
        finally:
            _stop(child)
            logfile.close()
    return run

class Shell:
    """Send a shell command, return its output as clean text.
    Raises TargetFault / TargetHang / TargetExit if the target misbehaves."""

    def __init__(self, child):
        self.child = child

    def wait_ready(self):
        expect_ok(self.child, PROMPT, BOOT_TIMEOUT)

    def run(self, cmd, timeout=10):
        self.child.sendline(cmd)
        before = expect_ok(self.child, PROMPT, timeout)
        text = ANSI.sub("", before).replace("\r", "")
        lines = text.split("\n")
        first = lines[0].strip() if lines else ""
        if first != cmd and first.startswith(cmd.split()[0]):
            raise AssertionError("shell echo mismatch (characters lost? line too long?)\n"
                                 f"  sent:   {cmd!r}\n  echoed: {first!r}")
        if lines and cmd in lines[0]:          # drop the echoed command line
            lines = lines[1:]
        return "\n".join(lines).strip()


@pytest.fixture
def sh(qemu):
    s = Shell(qemu)
    s.wait_ready()
    return s

class SharedShell:
    """One QEMU boot shared by many commands; reboots after a fault, hang or exit."""

    def __init__(self, config, app_rel, logname):
        self.config, self.app_rel, self.logname = config, app_rel, logname
        self.child = self.logfile = self.sh = None
        self.boots = 0

    def _boot(self):
        bdir = build_app(self.config, self.app_rel)
        self.logfile = _open_log(f"{self.logname}-boot{self.boots}")
        self.child = spawn_qemu(bdir, self.logfile)
        self.boots += 1
        self.sh = Shell(self.child)
        try:
            self.sh.wait_ready()
        except TargetProblem:
            self.close()
            raise

    def run(self, cmd, timeout=10):
        if self.sh is None:
            self._boot()
        try:
            return self.sh.run(cmd, timeout)
        except TargetProblem:
            self.close()              # dead target: the next command boots a fresh one
            raise

    def close(self):
        if self.child is not None:
            _stop(self.child)
            self.logfile.close()
        self.child = self.logfile = self.sh = None


@pytest.fixture(scope="module")
def shared(request):
    marker = request.node.get_closest_marker("app")
    app_rel = marker.args[0] if marker else request.config.getoption("--app")
    target = SharedShell(request.config, app_rel, request.module.__name__)
    yield target
    target.close()
