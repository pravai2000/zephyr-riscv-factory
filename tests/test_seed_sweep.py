import pytest

from sweep import (EXPECTED_CHECKS, hint, model_checksum, parse_start,
                   parse_workload, run_cmd)

pytestmark = [pytest.mark.app("apps/stress"), pytest.mark.stress]

THREADS, ITERS = 4, 300


@pytest.mark.parametrize("name", ["mutex", "sem", "msgq"])
def test_workload_sweep(shared, request, name, seed):
    cmd = f"stress run workload={name} seed={seed} threads={THREADS} iters={ITERS}"
    where = f"{hint(cmd)}\nor: pytest '{request.node.nodeid}'"
    r = parse_workload(run_cmd(shared, cmd))
    bad = {k: v for k, v in r["checks"].items() if v[0] != "PASS"}
    assert not bad, f"failed checks (status, expected, actual): {bad}{where}"
    assert r["result"] == "PASS" and r["failed"] == 0, where
    assert set(r["checks"]) == EXPECTED_CHECKS[name], where


def test_start_matches_model(shared, request, seed):
    cmd = f"stress start seed={seed} threads={THREADS} iters={ITERS}"
    r = parse_start(run_cmd(shared, cmd))
    expected = [model_checksum(seed, t, ITERS) for t in range(THREADS)]
    assert r["checksums"] == expected, (
        f"firmware {r['checksums']} != model {expected}{hint(cmd)}")


def test_unsafe_mutex_is_always_caught(shared, request, seed):
    cmd = f"stress run workload=mutex seed={seed} iters=100 unsafe=1"
    r = parse_workload(run_cmd(shared, cmd))
    assert r["checks"]["counter"][0] == "FAIL", f"lost updates not detected{hint(cmd)}"
