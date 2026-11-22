import pexpect

# Console text that means the target has faulted.
FATAL_PATTERNS = ["ZEPHYR FATAL ERROR", "ASSERTION FAIL", "Halting system"]


class TargetProblem(AssertionError):
    """Base for target failures. Subclasses AssertionError so pytest reports FAILED."""
    category = "PROBLEM"


class TargetFault(TargetProblem):
    category = "FAULT"


class TargetHang(TargetProblem):
    category = "HANG"


class TargetExit(TargetProblem):
    category = "EXIT"


def _tail(text, n):
    return (text or "")[-n:]


def expect_ok(child, text, timeout=30):
    """Wait for literal `text`. Raise a categorised error on fault, hang or exit.
    Returns the console text seen before `text`."""
    n = len(FATAL_PATTERNS)
    idx = child.expect_exact([text] + FATAL_PATTERNS + [pexpect.TIMEOUT, pexpect.EOF],
                             timeout=timeout)
    if idx == 0:
        return child.before

    before = _tail(child.before, 500)
    if 1 <= idx <= n:
        hit = child.after
        # Let the rest of the fault report arrive, up to the halt message.
        child.expect_exact(["Halting system", pexpect.TIMEOUT, pexpect.EOF], timeout=2)
        raise TargetFault(f"[FAULT] while waiting for {text!r}. Console:\n"
                          f"{before}{hit}{_tail(child.before, 800)}")
    if idx == n + 1:
        raise TargetHang(f"[HANG] no {text!r} within {timeout}s. Console tail:\n{before}")
    raise TargetExit(f"[EXIT] QEMU exited while waiting for {text!r}. Console tail:\n{before}")
