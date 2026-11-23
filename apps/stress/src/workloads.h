#ifndef WORKLOADS_H
#define WORKLOADS_H

#include <stddef.h>
#include <stdint.h>
#include <zephyr/shell/shell.h>

/* 0 = parsed, 1 = arg is not for `key`, -1 = bad value */
int parse_kv(const char *arg, const char *key, uint32_t *out, unsigned long max);

int cmd_run(const struct shell *sh, size_t argc, char **argv);

#endif
