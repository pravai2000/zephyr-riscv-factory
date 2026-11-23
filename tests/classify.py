"""Turn a pytest outcome plus failure text into one of a few stable categories."""

TAGS = ("FAULT", "HANG", "EXIT")


def classify(outcome, text):
    if outcome == "passed":
        return "PASS"
    if outcome == "skipped":
        return "SKIP"
    for tag in TAGS:
        if f"[{tag}]" in text:
            return tag
    return "ASSERT"


def summarise(tests):
    counts = {"total": len(tests)}
    for t in tests:
        counts[t["category"]] = counts.get(t["category"], 0) + 1
    return counts
