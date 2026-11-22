#include <stdlib.h>
#include <zephyr/kernel.h>
#include <zephyr/shell/shell.h>

static int cmd_add(const struct shell *sh, size_t argc, char **argv)
{
    long a = strtol(argv[1], NULL, 0);
    long b = strtol(argv[2], NULL, 0);

    shell_print(sh, "sum=%ld", a + b);
    return 0;
}

static int cmd_echo(const struct shell *sh, size_t argc, char **argv)
{
    shell_print(sh, "%s", argv[1]);
    return 0;
}

static int cmd_info(const struct shell *sh, size_t argc, char **argv)
{
    shell_print(sh, "board=%s", CONFIG_BOARD);
    return 0;
}

SHELL_STATIC_SUBCMD_SET_CREATE(factory_cmds,
    SHELL_CMD_ARG(add, NULL, "Add two integers", cmd_add, 3, 0),
    SHELL_CMD_ARG(echo, NULL, "Echo one word", cmd_echo, 2, 0),
    SHELL_CMD_ARG(info, NULL, "Show board name", cmd_info, 1, 0),
    SHELL_SUBCMD_SET_END);

SHELL_CMD_REGISTER(factory, &factory_cmds, "zephyr-riscv-factory commands", NULL);
