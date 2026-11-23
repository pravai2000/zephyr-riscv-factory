#include <errno.h>
#include <inttypes.h>
#include <stdlib.h>
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/shell/shell.h>
#include "workloads.h"

#define MAX_THREADS     8
#define STACK_SIZE      2048
#define DEFAULT_THREADS 4
#define DEFAULT_ITERS   1000
#define MAX_ITERS       1000000

struct worker_ctx {
	uint32_t id;
	uint32_t seed;
	uint32_t iters;
	uint32_t checksum;
};

K_THREAD_STACK_ARRAY_DEFINE(stacks, MAX_THREADS, STACK_SIZE);
static struct k_thread threads[MAX_THREADS];
static struct worker_ctx ctx[MAX_THREADS];

static uint32_t xorshift32(uint32_t *s)
{
	uint32_t x = *s;

	x ^= x << 13;
	x ^= x >> 17;
	x ^= x << 5;
	*s = x;
	return x;
}

static void worker(void *p1, void *p2, void *p3)
{
	struct worker_ctx *c = p1;
	uint32_t state = (c->seed ^ 0x9E3779B9u) + c->id * 0x85EBCA6Bu;
	uint32_t sum = 0;

	if (state == 0) {
		state = 1;
	}
	for (uint32_t i = 0; i < c->iters; i++) {
		uint32_t r = xorshift32(&state);

		sum = (sum * 31u) ^ r;
		if ((r & 0x3fu) == 0) {
			k_yield();      /* vary the interleaving; checksum is unaffected */
		}
	}
	c->checksum = sum;
}

/* Returns 0 if parsed, 1 if `arg` is not for `key`, -1 on a bad value. */
int parse_kv(const char *arg, const char *key, uint32_t *out, unsigned long max)
{
	size_t n = strlen(key);
	char *end;
	unsigned long v;

	if (strncmp(arg, key, n) != 0 || arg[n] != '=') {
		return 1;
	}
	v = strtoul(arg + n + 1, &end, 0);
	if (end == arg + n + 1 || *end != '\0' || v > max) {
		return -1;
	}
	*out = (uint32_t)v;
	return 0;
}

static int cmd_start(const struct shell *sh, size_t argc, char **argv)
{
	uint32_t seed = 1, nthreads = DEFAULT_THREADS, iters = DEFAULT_ITERS;
	uint32_t total = 0;

	for (size_t i = 1; i < argc; i++) {
		int rc = parse_kv(argv[i], "seed", &seed, UINT32_MAX);

		if (rc == 1) {
			rc = parse_kv(argv[i], "threads", &nthreads, MAX_THREADS);
		}
		if (rc == 1) {
			rc = parse_kv(argv[i], "iters", &iters, MAX_ITERS);
		}
		if (rc != 0) {
			shell_error(sh, "bad argument: %s", argv[i]);
			return -EINVAL;
		}
	}
	if (nthreads == 0 || iters == 0) {
		shell_error(sh, "threads and iters must be >= 1");
		return -EINVAL;
	}

	shell_print(sh, "STRESS START seed=%" PRIu32 " threads=%" PRIu32 " iters=%" PRIu32,
		    seed, nthreads, iters);

	for (uint32_t i = 0; i < nthreads; i++) {
		ctx[i] = (struct worker_ctx){ .id = i, .seed = seed, .iters = iters };
		k_thread_create(&threads[i], stacks[i], K_THREAD_STACK_SIZEOF(stacks[i]),
				worker, &ctx[i], NULL, NULL, K_PRIO_PREEMPT(5), 0, K_NO_WAIT);
	}
	for (uint32_t i = 0; i < nthreads; i++) {
		k_thread_join(&threads[i], K_FOREVER);
		shell_print(sh, "STRESS THREAD id=%" PRIu32 " checksum=0x%08" PRIx32,
			    i, ctx[i].checksum);
		total ^= ctx[i].checksum;
	}

	shell_print(sh, "STRESS SUMMARY seed=%" PRIu32 " threads=%" PRIu32 " iters=%" PRIu32
		    " total=0x%08" PRIx32 " result=DONE", seed, nthreads, iters, total);
	return 0;
}

SHELL_STATIC_SUBCMD_SET_CREATE(stress_cmds,
	SHELL_CMD_ARG(start, NULL, "start [seed=N] [threads=1..8] [iters=N]", cmd_start, 1, 3),
        SHELL_CMD_ARG(run, NULL, "run workload=mutex|sem|msgq [seed=N] [threads=N] [iters=N] [unsafe=0|1]",
		      cmd_run, 2, 4), SHELL_SUBCMD_SET_END);

SHELL_CMD_REGISTER(stress, &stress_cmds, "seeded stress workload", NULL);
