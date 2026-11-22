Day 1: workspace + west.yml pinned to <tag>, hello app runs on qemu_riscv32 (SDK <version>).
Day 2: pytest boot fixture (build + QEMU via pexpect), 2 smoke tests green, failure path verified.
Day 3: shell_demo app + Shell helper; 11 shell tests (builtin + custom commands, error paths) green.
Day 4: ztest kernel_basic suite on qemu_riscv32; console parsed into per-test pytest results; expected-test list guards against silent loss.
