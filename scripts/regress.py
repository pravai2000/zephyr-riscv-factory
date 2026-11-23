#!/usr/bin/env python3
"""Run the pytest suite and write results/results.json."""
import argparse
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WS = ROOT.parent
sys.path.insert(0, str(ROOT / "tests"))
from classify import summarise  # noqa: E402


def sh(*cmd):
    try:
        return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                              timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def zephyr_version():
    f = WS / "zephyr" / "VERSION"
    if not f.exists():
        return ""
    kv = {}
    for line in f.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip()
    ver = ".".join(kv.get(k, "?") for k in ("VERSION_MAJOR", "VERSION_MINOR", "PATCHLEVEL"))
    return ver + (f"-{kv['EXTRAVERSION']}" if kv.get("EXTRAVERSION") else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-m", dest="marker", default="", help="pytest marker expression")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--out", default=str(ROOT / "results" / "results.json"))
    ap.add_argument("pytest_args", nargs="*", help="extra args passed to pytest")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = out.with_suffix(".raw.json")
    raw.unlink(missing_ok=True)

    cmd = [sys.executable, "-m", "pytest", "-q", f"--seeds={args.seeds}",
           f"--results-json={raw}"]
    if args.marker:
        cmd += ["-m", args.marker]
    cmd += args.pytest_args

    t0 = time.time()
    rc = subprocess.run(cmd, cwd=ROOT).returncode
    duration = round(time.time() - t0, 1)

    data = json.loads(raw.read_text()) if raw.exists() else {"tests": [], "coverage": {}}
    raw.unlink(missing_ok=True)
    tests = data["tests"]

    result = {
        "schema": 1,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": {"sha": sh("git", "rev-parse", "--short", "HEAD"),
                "dirty": bool(sh("git", "status", "--porcelain"))},
        "env": {"zephyr": zephyr_version(),
                "qemu": (sh("qemu-system-riscv32", "--version").splitlines() or [""])[0],
                "python": platform.python_version(),
                "host": platform.platform()},
        "command": cmd[2:],
        "duration_s": duration,
        "exit_code": rc,
        "summary": summarise(tests),
        "tests": tests,
        "coverage": data["coverage"],
    }
    out.write_text(json.dumps(result, indent=2))

    print(f"\nresults: {out}")
    print("summary:", ", ".join(f"{k}={v}" for k, v in result["summary"].items()))
    for t in tests:
        if t["outcome"] == "failed":
            print(f"  {t['category']:<6} {t['id']}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
