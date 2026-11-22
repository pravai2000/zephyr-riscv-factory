#include <zephyr/kernel.h>
#include <zephyr/shell/shell.h>
#include <zephyr/sys/__assert.h>

static int cmd_oops(const struct shell *sh, size_t argc, char **argv)
{
	k_oops();
	return 0;
}

static int cmd_panic(const struct shell *sh, size_t argc, char **argv)
{
	k_panic();
	return 0;
}

static int cmd_illegal(const struct shell *sh, size_t argc, char **argv)
{
	__asm__ volatile(".word 0x00000000");   /* all-zero word is an illegal RISC-V instruction */
	return 0;
}

static int cmd_assert(const struct shell *sh, size_t argc, char **argv)
{
	__ASSERT(0, "deliberate assertion failure");
	return 0;
}

static int cmd_hang(const struct shell *sh, size_t argc, char **argv)
{
	for (;;) {
	}
	return 0;
}

static int cmd_slow(const struct shell *sh, size_t argc, char **argv)
{
	k_msleep(1500);
	shell_print(sh, "done");
	return 0;
}

SHELL_STATIC_SUBCMD_SET_CREATE(crash_cmds,
	SHELL_CMD_ARG(oops, NULL, "k_oops()", cmd_oops, 1, 0),
	SHELL_CMD_ARG(panic, NULL, "k_panic()", cmd_panic, 1, 0),
	SHELL_CMD_ARG(illegal, NULL, "illegal instruction", cmd_illegal, 1, 0),
	SHELL_CMD_ARG(assert, NULL, "failed __ASSERT", cmd_assert, 1, 0),
	SHELL_CMD_ARG(hang, NULL, "spin forever", cmd_hang, 1, 0),
	SHELL_CMD_ARG(slow, NULL, "slow but healthy (1.5 s)", cmd_slow, 1, 0),
	SHELL_SUBCMD_SET_END);

SHELL_CMD_REGISTER(crash, &crash_cmds, "deliberate failures", NULL);
