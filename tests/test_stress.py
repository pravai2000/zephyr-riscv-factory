import re

import pytest

pytestmark = [pytest.mark.app("apps/stress"), pytest.mark.stress]

SUMMARY = re.compile(r"STRESS SUMMARY seed=(\d+) threads=(\d+) iters=(\d+) "
                     r"total=0x([0-9a-f]{8}) result=(\w+)")
THREAD = re.compile(r"STRESS THREAD id=(\d+) checksum=0x([0-9a-f]{8})")
M = 0xFFFFFFFF


def model_checksum(seed, tid, iters):
    """Host-side reference model of the firmware worker."""
    state = ((seed ^ 0x9E3779B9) + tid * 0x85EBCA6B) & M or 1
    s = 0
    for _ in range(iters):
        state ^= (state << 13) & M
        state ^= state >> 17
        state ^= (state << 5) & M
        s = ((s * 31) & M) ^ state
    return s


def run_stress(sh, args=""):
    out = sh.run(f"stress start {args}".strip(), timeout=60)
    m = SUMMARY.search(out)
    assert m, f"no summary in output:\n{out}"
    return {
        "seed": int(m[1]), "threads": int(m[2]), "iters": int(m[3]),
        "total": int(m[4], 16), "result": m[5],
        "checksums": [int(c, 16) for _, c in THREAD.findall(out)],
    }


def test_runs_and_summarises(sh):
    r = run_stress(sh, "seed=42 threads=4 iters=500")
    assert r["result"] == "DONE"
    assert (r["seed"], r["threads"], r["iters"]) == (42, 4, 500)
    assert len(r["checksums"]) == 4


def test_defaults(sh):
    r = run_stress(sh)
    assert (r["seed"], r["threads"], r["iters"]) == (1, 4, 1000)


@pytest.mark.parametrize("threads", [1, 2, 8])
def test_thread_counts(sh, threads):
    r = run_stress(sh, f"seed=7 threads={threads} iters=200")
    assert len(r["checksums"]) == threads


def test_same_seed_same_result(sh):
    a = run_stress(sh, "seed=99 iters=300")
    b = run_stress(sh, "seed=99 iters=300")
    assert a["checksums"] == b["checksums"] and a["total"] == b["total"]


def test_different_seed_different_total(sh):
    a = run_stress(sh, "seed=1 iters=300")
    b = run_stress(sh, "seed=2 iters=300")
    assert a["total"] != b["total"]


def test_threads_get_distinct_streams(sh):
    r = run_stress(sh, "seed=5 threads=8 iters=300")
    assert len(set(r["checksums"])) == 8


@pytest.mark.parametrize("seed", [0, 1, 42, 4294967295])
def test_matches_reference_model(sh, seed):
    iters = 400
    r = run_stress(sh, f"seed={seed} threads=4 iters={iters}")
    expected = [model_checksum(seed, t, iters) for t in range(4)]
    assert r["checksums"] == expected
    assert r["total"] == expected[0] ^ expected[1] ^ expected[2] ^ expected[3]


@pytest.mark.parametrize("args, needle", [
    ("seed=abc", "bad argument"),
    ("threads=9", "bad argument"),
    ("bogus=1", "bad argument"),
    ("threads=0", "must be"),
])
def test_bad_arguments_rejected(sh, args, needle):
    assert needle in sh.run(f"stress start {args}")
