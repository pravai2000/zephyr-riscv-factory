import pytest

from sweep import EXPECTED_BINS, missing_bins, parse_workload, run_cmd, seed_list

pytestmark = [pytest.mark.stress, pytest.mark.app("apps/stress")]

SHAPES = [(2, 200), (4, 500), (8, 300)]      # (threads, iters)


@pytest.mark.parametrize("workload", sorted(EXPECTED_BINS))
def test_every_bin_is_hit(shared, request, workload):
    n = request.config.getoption("--seeds")
    totals = {}
    last = ""
    runs = 0

    for seed in seed_list(n):
        for threads, iters in SHAPES:
            last = f"stress run workload={workload} seed={seed} threads={threads} iters={iters}"
            r = parse_workload(run_cmd(shared, last))
            runs += 1
            assert r["failed"] == 0, f"workload itself failed, fix that first: {last}"
            for name, count in r["cover"].items():
                totals[name] = totals.get(name, 0) + count
            if not missing_bins(totals, workload):
                return                          # closed: every bin hit at least once

    missing = missing_bins(totals, workload)
    pytest.fail(
        f"{workload}: bins never hit after {runs} runs: {missing}\n"
        f"totals: {totals}\n"
        f"last command: {last}"
    )
