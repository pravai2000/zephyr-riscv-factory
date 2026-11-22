from ztest_parse import parse_ztest, verdict

SAMPLE = """\
*** Booting Zephyr OS build v4.0.0 ***
Running TESTSUITE alpha
START - test_one
 PASS - test_one in 0.001 seconds
START - test_two
 FAIL - test_two in 0.002 seconds
START - test_three
 SKIP - test_three in 0.000 seconds
TESTSUITE alpha failed.
------ TESTSUITE SUMMARY START ------
SUITE FAIL - 33.33% [alpha]: pass = 1, fail = 1, skip = 1, total = 3
 - PASS - [alpha.test_one] duration = 0.001 seconds
------ TESTSUITE SUMMARY END ------
PROJECT EXECUTION FAILED
"""


def test_parse_pass_fail_skip():
    assert parse_ztest(SAMPLE) == {
        "alpha.test_one": "PASS",
        "alpha.test_two": "FAIL",
        "alpha.test_three": "SKIP",
    }


def test_verdict():
    assert verdict(SAMPLE) == "FAILED"
    assert verdict("nothing here") is None
