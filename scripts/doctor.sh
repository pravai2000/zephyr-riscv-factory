#!/usr/bin/env bash
# Check that the tools and workspace the tests need are present.
here="$(cd "$(dirname "$0")/.." && pwd)"
ws="$(dirname "$here")"
fail=0

check() {   # check "<what>" "<command that must succeed>"
  if eval "$2" >/dev/null 2>&1; then printf "ok    %s\n" "$1"
  else printf "FAIL  %s\n" "$1"; fail=1; fi
}

check "virtualenv active"            "python -c 'import sys; sys.exit(sys.prefix == sys.base_prefix)'"
check "python >= 3.10"               "python -c 'import sys; sys.exit(sys.version_info < (3,10))'"
check "west on PATH"                 "command -v west"
check "pytest on PATH"               "command -v pytest"
check "pexpect importable"           "python -c 'import pexpect'"
check "qemu-system-riscv32"          "command -v qemu-system-riscv32"
check "west workspace ($ws/.west)"   "test -d '$ws/.west'"
check "zephyr checked out"           "test -f '$ws/zephyr/VERSION'"
check "Zephyr SDK registered"        "test -d \"\$HOME/.cmake/packages/Zephyr-sdk\""

if [ "$fail" -ne 0 ]; then
  echo; echo "Fix the FAIL lines above (see README, 'Fresh machine setup')."; exit 1
fi
echo; echo "All checks passed."
