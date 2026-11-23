#ifndef COV_H
#define COV_H

#include <zephyr/shell/shell.h>

enum cov_bin {
	COV_MUTEX_CONTENDED,
	COV_MUTEX_YIELD_IN_CS,
	COV_SEM_TAKE_BLOCKED,
	COV_SEM_BACKLOG,
	COV_SEM_YIELD,
	COV_MSGQ_PUT_BLOCKED,
	COV_MSGQ_GET_BLOCKED,
	COV_MSGQ_YIELD,
	COV_COUNT
};

void cov_reset(void);
void cov_hit(enum cov_bin bin);
void cov_dump(const struct shell *sh, const char *prefix);   /* bins whose name starts with prefix */

#endif
