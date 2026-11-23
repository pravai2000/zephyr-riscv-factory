#include <string.h>
#include <zephyr/kernel.h>

#include "cov.h"

static const char *const names[COV_COUNT] = {
	[COV_MUTEX_CONTENDED]   = "mutex_contended",
	[COV_MUTEX_YIELD_IN_CS] = "mutex_yield_in_cs",
	[COV_SEM_TAKE_BLOCKED]  = "sem_take_blocked",
	[COV_SEM_BACKLOG]       = "sem_backlog",
	[COV_SEM_YIELD]         = "sem_yield",
	[COV_MSGQ_PUT_BLOCKED]  = "msgq_put_blocked",
	[COV_MSGQ_GET_BLOCKED]  = "msgq_get_blocked",
	[COV_MSGQ_YIELD]        = "msgq_yield",
};

static atomic_t counts[COV_COUNT];

void cov_reset(void)
{
	for (int i = 0; i < COV_COUNT; i++) {
		atomic_set(&counts[i], 0);
	}
}

void cov_hit(enum cov_bin bin)
{
	atomic_inc(&counts[bin]);
}

void cov_dump(const struct shell *sh, const char *prefix)
{
	size_t n = strlen(prefix);

	for (int i = 0; i < COV_COUNT; i++) {
		if (strncmp(names[i], prefix, n) == 0) {
			shell_print(sh, "COVER:%s=%ld", names[i], (long)atomic_get(&counts[i]));
		}
	}
}
