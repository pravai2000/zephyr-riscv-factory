import re

from detect import TargetProblem

EDGE_SEEDS = [1, 0, 4294967295]
M = 0xFFFFFFFF


def seed_list(n):
    """Deterministic seeds: edge values first, then a fixed pseudo-random sequence.
    The first k seeds never change when n grows, so --seeds only adds seeds."""
    seeds = list(EDGE_SEEDS)
    s = 42
    while len(seeds) < n:
        s = (s * 1664525 + 1013904223) & M
        if s not in seeds:
            seeds.append(s)
    return seeds[:n]


def hint(cmd):
    return f"\nreplay at the factory> prompt:\n  {cmd}"


def run_cmd(target, cmd, timeout=90):
    """Run a shell command; if the target faults or hangs, add a replay line."""
    try:
        return target.run(cmd, timeout)
    except TargetProblem as exc:
        raise type(exc)(f"{exc}\nreplay: {cmd}") from None


CHECK = re.compile(r"CHECK (PASS|FAIL) name=(\w+) expected=(\d+) actual=(\d+)")
RESULT = re.compile(r"WORKLOAD RESULT name=(\w+) seed=(\d+) checks=(\d+) "
                    r"failed=(\d+) result=(PASS|FAIL)")
SUMMARY = re.compile(r"STRESS SUMMARY seed=(\d+) threads=(\d+) iters=(\d+) "
                     r"total=0x([0-9a-f]{8}) result=(\w+)")
THREAD = re.compile(r"STRESS THREAD id=(\d+) checksum=0x([0-9a-f]{8})")

EXPECTED_CHECKS = {
    "mutex": {"counter", "mutex_free"},
    "sem": {"given", "taken", "sem_count", "timeouts"},
    "msgq": {"received_total", "value_sum", "producers_complete",
             "order_violations", "queue_empty", "timeouts"},
}


def parse_workload(out):
    m = RESULT.search(out)
    assert m, f"no WORKLOAD RESULT in output:\n{out}"
    return {
        "result": m[5], "failed": int(m[4]),
        "checks": {n: (st, int(e), int(a)) for st, n, e, a in CHECK.findall(out)},
    }


def parse_start(out):
    m = SUMMARY.search(out)
    assert m, f"no STRESS SUMMARY in output:\n{out}"
    return {"total": int(m[4], 16),
            "checksums": [int(c, 16) for _, c in THREAD.findall(out)]}


def model_checksum(seed, tid, iters):
    """Host-side model of the firmware worker (same as Day 8)."""
    state = ((seed ^ 0x9E3779B9) + tid * 0x85EBCA6B) & M or 1
    s = 0
    for _ in range(iters):
        state ^= (state << 13) & M
        state ^= state >> 17
        state ^= (state << 5) & M
        s = ((s * 31) & M) ^ state
    return s
