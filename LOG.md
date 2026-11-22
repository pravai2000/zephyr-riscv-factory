# Build log

Environment: macOS (Apple silicon), Python 3.14, Zephyr <tag from west.yml>, Zephyr SDK <version>, QEMU <version>.

| Day | What | Result |
|---|---|---|
| 1 | Workspace, pinned west.yml, hello app on qemu_riscv32 | BOOT OK |
| 2 | pytest boot fixture (build + QEMU via pexpect), smoke tests | 2 passed |
| 3 | shell_demo app, Shell helper, 11 command/response tests | 13 passed |
| 4 | ztest kernel_basic suite parsed into per-test results | 24 passed, 1 skipped |
| 5 | crash_demo, FAULT/HANG/EXIT detection, markers | 32 passed, 1 skipped |
| 6 | Makefile, doctor script, README, pinned requirements | fresh clone passes |

## Lessons
- Day 5: Zephyr's QEMU runs with icount and idle skipping, so a guest `k_msleep(1500)` finishes in well under a second of wall time. A test that used it to provoke a timeout was invalid; `crash hang` (a busy loop) is the reliable way.
- Day 5: pytest only collects `test_*.py`; a misnamed test file is silently skipped. Check the test count after adding files.
