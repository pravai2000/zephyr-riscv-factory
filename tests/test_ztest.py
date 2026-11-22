import pytest

from ztest_parse import parse_ztest, verdict

APP = "apps/ztest_kernel"

# The contract: these tests must exist in the firmware. A missing or renamed
# test fails test_no_missing_or_unexpected instead of vanishing quietly.
EXPECTED = [
    "kernel_basic.test_semaphore_give_take",
    "kernel_basic.test_mutex_lock_unlock",
    "kernel_basic.test_msgq_fifo_order",
    "kernel_basic.test_msgq_full_rejects",
    "kernel_basic.test_sleep_duration",
    "kernel_basic.test_timer_fires_periodically",
    "kernel_basic.test_thread_runs_to_completion",
    "kernel_basic.test_skipped_example",
]


@pytest.fixture(scope="module")
def ztest_output(run_to_marker):
    return run_to_marker(APP, r"PROJECT EXECUTION (SUCCESSFUL|FAILED)")


@pytest.fixture(scope="module")
def ztest_results(ztest_output):
    return parse_ztest(ztest_output)


@pytest.mark.parametrize("name", EXPECTED)
def test_ztest_case(name, ztest_results):
    status = ztest_results.get(name)
    if status == "SKIP":
        pytest.skip("skipped by ztest")
    assert status == "PASS", f"{name}: {status or 'did not run'}"


def test_no_missing_or_unexpected(ztest_results):
    assert set(ztest_results) == set(EXPECTED)


def test_project_verdict(ztest_output):
    assert verdict(ztest_output) == "SUCCESSFUL"
