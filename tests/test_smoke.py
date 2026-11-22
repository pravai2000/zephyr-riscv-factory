import re

import pexpect

BOOT_OK = re.escape("BOOT OK: zephyr-riscv-factory hello")
FATAL = re.escape("ZEPHYR FATAL ERROR")
REASONS = {1: "fatal error during boot", 2: "timed out waiting for banner",
           3: "QEMU exited before the banner"}


def test_boots_to_banner(qemu):
    idx = qemu.expect([BOOT_OK, FATAL, pexpect.TIMEOUT, pexpect.EOF])
    assert idx == 0, f"{REASONS.get(idx)}. Console so far:\n{qemu.before[-800:]}"


def test_no_fault_after_boot(qemu):
    qemu.expect(BOOT_OK)
    # Watch for 3 s: the only acceptable outcome is that nothing bad appears.
    idx = qemu.expect([FATAL, pexpect.TIMEOUT, pexpect.EOF], timeout=3)
    assert idx == 1, "fault or QEMU exit after the banner"
