import re

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
SUITE = re.compile(r"Running TESTSUITE (\S+)")
CASE = re.compile(r"^\s*(PASS|FAIL|SKIP) - (\S+) in [\d.]+ seconds")
VERDICT = re.compile(r"PROJECT EXECUTION (SUCCESSFUL|FAILED)")


def parse_ztest(text):
    """Return {'suite.test': 'PASS'|'FAIL'|'SKIP'} from ztest console text."""
    results, suite = {}, None
    for line in ANSI.sub("", text).replace("\r", "").split("\n"):
        m = SUITE.search(line)
        if m:
            suite = m.group(1)
            continue
        m = CASE.match(line)
        if m and suite:
            results[f"{suite}.{m.group(2)}"] = m.group(1)
    return results


def verdict(text):
    m = VERDICT.search(text)
    return m.group(1) if m else None
