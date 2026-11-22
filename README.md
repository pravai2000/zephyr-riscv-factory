# zephyr-riscv-factory

Automated tests for Zephyr RTOS running on an emulated RISC-V board
(QEMU `qemu_riscv32`), driven by pytest. Zephyr is the thing under test;
the emulator is only the platform it runs on.

## How it works

pytest builds a Zephyr app with `west`, boots it in QEMU, and watches the
serial console with `pexpect`. Faults, hangs and unexpected exits are
reported as distinct failure categories.

| Layer | What it checks | Files |
|---|---|---|
| Smoke | the image boots and prints its banner | `tests/test_smoke.py` |
| Shell | built-in and custom shell commands, error paths | `apps/shell_demo`, `tests/test_shell.py` |
| ztest | in-firmware kernel tests, one pytest result each | `apps/ztest_kernel`, `tests/test_ztest.py` |
| Fault | deliberate crashes/hangs are detected and classified | `apps/crash_demo`, `tests/test_crash.py` |
| Unit | the console parsers, with no QEMU | `tests/test_ztest_parser.py` |

Failure categories (`tests/detect.py`): **FAULT** (Zephyr fatal error or
assertion), **HANG** (no expected output within the timeout), **EXIT**
(QEMU quit early).

## Quickstart (workspace already set up)

```bash
source ~/myenvs/zephyr314/bin/activate     # your virtualenv
cd <workspace>/zephyr-riscv-factory
make doctor     # check tools
make test       # full suite
```

Other targets: `make quick` (no crash tests), `make unit` (no QEMU),
`make smoke|shell|ztest|fault`. Pass pytest options with
`make test PYTEST_ARGS='-k add -v'`. Console logs for each test are written to `logs/`.

## Fresh machine setup

This repository is a west *manifest repository*: Zephyr is cloned next to it,
never inside it.

```bash
brew install cmake ninja gperf ccache qemu dtc libmagic wget   # macOS
mkdir zephyr-ws && cd zephyr-ws
git clone <this repo's URL> zephyr-riscv-factory
python3 -m venv .venv && source .venv/bin/activate
pip install west
west init -l zephyr-riscv-factory
west update                         # large download
west zephyr-export
west packages pip --install         # Zephyr's Python requirements
west sdk install --toolchains riscv64-zephyr-elf
pip install -r zephyr-riscv-factory/requirements.txt
cd zephyr-riscv-factory && make test
```

Zephyr is pinned in `west.yml`. Tested with Python 3.14 (Zephyr recommends 3.12,
use it if a dependency fails to build).

## Things worth knowing

- QEMU runs with instruction counting and skips idle time, so guest sleeps
  finish quickly in real time. Test timeouts are wall-clock.
- Each test boots a fresh QEMU; the app for a test file is chosen with
  `@pytest.mark.app("apps/<name>")`.
- Adding a ztest case? Add its name to `EXPECTED` in `tests/test_ztest.py`;
  a missing or unexpected case fails the suite on purpose.
