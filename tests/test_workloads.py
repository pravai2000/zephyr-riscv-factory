import re

import pytest

pytestmark = [pytest.mark.app("apps/stress"), pytest.mark.stress]

CHECK = re.compile(r"CHECK (PASS|FAIL) name=(\w+) expected=(\d+) actual=(\d+)")
RESULT = re.compile(r"WORKLOAD RESULT name=(\w+) seed=(\d+) checks=(\d+) "
                    r"failed=(\d+) result=(PASS|FAIL)")

EXPECTED_CHECKS = {
    "mutex": {"counter", "mutex_free"},
    "sem": {"given", "taken", "sem_count", "timeouts"},
    "msgq": {"received_total", "value_sum", "producers_complete",
             "order_violations", "queue_empty", "timeouts"},
}


def run_workload(sh, name, seed=1, threads=4, iters=500, unsafe=0):
    cmd = (f"stress run workload={name} seed={seed} threads={threads} "
           f"iters={iters} unsafe={unsafe}")
    out = sh.run(cmd, timeout=90)
    m = RESULT.search(out)
    assert m, f"no WORKLOAD RESULT in output:\n{out}"
    checks = {n: (status, int(e), int(a)) for status, n, e, a in CHECK.findall(out)}
    return {"result": m[5], "nchecks": int(m[3]), "failed": int(m[4]), "checks": checks}


@pytest.mark.parametrize("name", ["mutex", "sem", "msgq"])
def test_workload_passes_all_checks(sh, name):
    r = run_workload(sh, name)
    assert r["result"] == "PASS" and r["failed"] == 0
    assert set(r["checks"]) == EXPECTED_CHECKS[name]      # no check silently dropped
    assert r["nchecks"] == len(r["checks"])
    assert all(status == "PASS" for status, _, _ in r["checks"].values())


def test_mutex_counter_matches_independent_expectation(sh):
    r = run_workload(sh, "mutex", threads=4, iters=300)
    assert r["checks"]["counter"] == ("PASS", 4 * 300, 4 * 300)


def test_unsafe_mutex_workload_is_caught(sh):
    r = run_workload(sh, "mutex", threads=4, iters=300, unsafe=1)
    status, expected, actual = r["checks"]["counter"]
    assert r["result"] == "FAIL" and status == "FAIL"
    assert actual < expected                               # updates were lost


@pytest.mark.parametrize("name", ["sem", "msgq"])
@pytest.mark.parametrize("threads", [2, 3, 8])
def test_producer_consumer_splits(sh, name, threads):
    iters = 200
    r = run_workload(sh, name, threads=threads, iters=iters)
    assert r["result"] == "PASS"
    producers = threads // 2                                # host-side expectation
    key = "given" if name == "sem" else "received_total"
    assert r["checks"][key][1] == producers * iters


@pytest.mark.parametrize("args, needle", [
    ("workload=bogus", "unknown workload"),
    ("seed=1", "workload=mutex|sem|msgq is required"),
    ("workload=sem threads=1", "needs threads >= 2"),
    ("workload=msgq unsafe=1", "unsafe only applies"),
])
def test_bad_arguments_rejected(sh, args, needle):
    assert needle in sh.run(f"stress run {args}")
