#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/shell/shell.h>

#include "workloads.h"

#define WL_MAX_THREADS 8
#define WL_STACK_SIZE  2048
#define WL_MAX_ITERS   100000
#define WL_WAIT        K_SECONDS(5)     /* bound every blocking wait: no silent deadlocks */

struct wl_ctx {
	uint32_t id;
	uint32_t seed;
	uint32_t iters;         /* mutex: increments; producer: items to send */
	uint32_t quota;         /* consumer: items to take */
	bool unsafe;
	uint32_t sent_sum;      /* producer */
	uint32_t recv_sum;      /* consumer */
	uint32_t recv_from[WL_MAX_THREADS];
};

K_THREAD_STACK_ARRAY_DEFINE(wl_stacks, WL_MAX_THREADS, WL_STACK_SIZE);
static struct k_thread wl_threads[WL_MAX_THREADS];
static struct wl_ctx wl_ctx[WL_MAX_THREADS];

struct report {
	const struct shell *sh;
	uint32_t checks;
	uint32_t failed;
};

static uint32_t wl_rand(uint32_t *s)
{
	uint32_t x = *s;

	x ^= x << 13;
	x ^= x >> 17;
	x ^= x << 5;
	*s = x;
	return x;
}

static uint32_t seed_state(uint32_t seed, uint32_t id)
{
	uint32_t s = (seed ^ 0x9E3779B9u) + id * 0x85EBCA6Bu;

	return s ? s : 1;
}

static void check(struct report *r, const char *name, uint32_t expected, uint32_t actual)
{
	bool ok = (expected == actual);

	r->checks++;
	if (!ok) {
		r->failed++;
	}
	shell_print(r->sh, "CHECK %s name=%s expected=%" PRIu32 " actual=%" PRIu32,
		    ok ? "PASS" : "FAIL", name, expected, actual);
}

/* Threads [0, first_consumer) run `prod`, the rest run `cons`. All start together. */
static void start_threads(uint32_t n, uint32_t first_consumer,
			  k_thread_entry_t prod, k_thread_entry_t cons)
{
	for (uint32_t i = 0; i < n; i++) {
		k_thread_entry_t fn = (i < first_consumer) ? prod : cons;

		k_thread_create(&wl_threads[i], wl_stacks[i], K_THREAD_STACK_SIZEOF(wl_stacks[i]),
				fn, &wl_ctx[i], NULL, NULL, K_PRIO_PREEMPT(5), 0, K_FOREVER);
	}
	for (uint32_t i = 0; i < n; i++) {
		k_thread_start(&wl_threads[i]);
	}
}

static void join_threads(uint32_t n)
{
	for (uint32_t i = 0; i < n; i++) {
		k_thread_join(&wl_threads[i], K_FOREVER);
	}
}

/* Fill contexts. Producers are threads [0, n/2); consumers share p*iters items. */
static uint32_t prepare(uint32_t n, uint32_t seed, uint32_t iters, bool unsafe)
{
	uint32_t p = n / 2, c = n - p, total = p * iters;

	memset(wl_ctx, 0, sizeof(wl_ctx));
	for (uint32_t i = 0; i < n; i++) {
		wl_ctx[i].id = i;
		wl_ctx[i].seed = seed;
		wl_ctx[i].iters = iters;
		wl_ctx[i].unsafe = unsafe;
		if (i >= p && c > 0) {
			uint32_t j = i - p;

			wl_ctx[i].quota = total / c + (j < total % c ? 1 : 0);
		}
	}
	return p;
}

/* ---------------------------- mutex ---------------------------- */

static struct k_mutex wl_mutex;
static volatile uint32_t wl_counter;

static void mutex_worker(void *p1, void *p2, void *p3)
{
	struct wl_ctx *c = p1;
	uint32_t st = seed_state(c->seed, c->id);

	for (uint32_t i = 0; i < c->iters; i++) {
		uint32_t r = wl_rand(&st);
		uint32_t v;

		if (!c->unsafe) {
			k_mutex_lock(&wl_mutex, K_FOREVER);
		}
		v = wl_counter;
		if (c->unsafe || (r & 0x7u) == 0) {
			k_yield();       /* switch threads in the middle of read-modify-write */
		}
		wl_counter = v + 1;
		if (!c->unsafe) {
			k_mutex_unlock(&wl_mutex);
		}
	}
}

static void run_mutex(struct report *rep, uint32_t seed, uint32_t n, uint32_t iters, bool unsafe)
{
	bool free;

	k_mutex_init(&wl_mutex);
	wl_counter = 0;
	prepare(n, seed, iters, unsafe);
	start_threads(n, n, mutex_worker, mutex_worker);
	join_threads(n);

	check(rep, "counter", n * iters, wl_counter);
	free = (k_mutex_lock(&wl_mutex, K_NO_WAIT) == 0);
	if (free) {
		k_mutex_unlock(&wl_mutex);
	}
	check(rep, "mutex_free", 1, free);
}

/* -------------------------- semaphore -------------------------- */

static struct k_sem wl_sem;
static atomic_t wl_given, wl_taken, wl_sem_timeouts;

static void sem_producer(void *p1, void *p2, void *p3)
{
	struct wl_ctx *c = p1;
	uint32_t st = seed_state(c->seed, c->id);

	for (uint32_t i = 0; i < c->iters; i++) {
		uint32_t r = wl_rand(&st);

		k_sem_give(&wl_sem);
		atomic_inc(&wl_given);
		if ((r & 3u) == 0) {
			k_yield();
		}
	}
}

static void sem_consumer(void *p1, void *p2, void *p3)
{
	struct wl_ctx *c = p1;
	uint32_t st = seed_state(c->seed, c->id);

	for (uint32_t i = 0; i < c->quota; i++) {
		uint32_t r = wl_rand(&st);

		if (k_sem_take(&wl_sem, WL_WAIT) != 0) {
			atomic_inc(&wl_sem_timeouts);
			return;
		}
		atomic_inc(&wl_taken);
		if ((r & 3u) == 0) {
			k_yield();
		}
	}
}

static void run_sem(struct report *rep, uint32_t seed, uint32_t n, uint32_t iters)
{
	uint32_t p = prepare(n, seed, iters, false);

	k_sem_init(&wl_sem, 0, K_SEM_MAX_LIMIT);
	atomic_set(&wl_given, 0);
	atomic_set(&wl_taken, 0);
	atomic_set(&wl_sem_timeouts, 0);
	start_threads(n, p, sem_producer, sem_consumer);
	join_threads(n);

	check(rep, "given", p * iters, (uint32_t)atomic_get(&wl_given));
	check(rep, "taken", p * iters, (uint32_t)atomic_get(&wl_taken));
	check(rep, "sem_count", 0, k_sem_count_get(&wl_sem));
	check(rep, "timeouts", 0, (uint32_t)atomic_get(&wl_sem_timeouts));
}

/* ------------------------ message queue ------------------------ */

struct wl_msg {
	uint32_t producer;
	uint32_t seq;
	uint32_t value;
};

K_MSGQ_DEFINE(wl_q, sizeof(struct wl_msg), 4, 4);   /* small on purpose: forces backpressure */
static atomic_t wl_put_to, wl_get_to, wl_order_bad;

static void msgq_producer(void *p1, void *p2, void *p3)
{
	struct wl_ctx *c = p1;
	uint32_t st = seed_state(c->seed, c->id);

	for (uint32_t i = 0; i < c->iters; i++) {
		struct wl_msg m = { .producer = c->id, .seq = i, .value = wl_rand(&st) };

		if (k_msgq_put(&wl_q, &m, WL_WAIT) != 0) {
			atomic_inc(&wl_put_to);
			return;
		}
		c->sent_sum += m.value;
		if ((m.value & 3u) == 0) {
			k_yield();
		}
	}
}

static void msgq_consumer(void *p1, void *p2, void *p3)
{
	struct wl_ctx *c = p1;
	uint32_t last[WL_MAX_THREADS] = { 0 };   /* seq+1 of last message seen per producer */

	for (uint32_t i = 0; i < c->quota; i++) {
		struct wl_msg m;

		if (k_msgq_get(&wl_q, &m, WL_WAIT) != 0) {
			atomic_inc(&wl_get_to);
			return;
		}
		if (m.producer >= WL_MAX_THREADS) {
			atomic_inc(&wl_order_bad);
			continue;
		}
		if (m.seq + 1 <= last[m.producer]) {     /* FIFO per producer must hold */
			atomic_inc(&wl_order_bad);
		}
		last[m.producer] = m.seq + 1;
		c->recv_from[m.producer]++;
		c->recv_sum += m.value;
		if ((m.value & 3u) == 0) {
			k_yield();
		}
	}
}

static void run_msgq(struct report *rep, uint32_t seed, uint32_t n, uint32_t iters)
{
	uint32_t p = prepare(n, seed, iters, false);
	uint32_t received = 0, sent_sum = 0, recv_sum = 0, complete = 0;

	k_msgq_purge(&wl_q);
	atomic_set(&wl_put_to, 0);
	atomic_set(&wl_get_to, 0);
	atomic_set(&wl_order_bad, 0);
	start_threads(n, p, msgq_producer, msgq_consumer);
	join_threads(n);

	for (uint32_t i = 0; i < p; i++) {
		sent_sum += wl_ctx[i].sent_sum;
	}
	for (uint32_t i = p; i < n; i++) {
		recv_sum += wl_ctx[i].recv_sum;
		for (uint32_t j = 0; j < p; j++) {
			received += wl_ctx[i].recv_from[j];
		}
	}
	for (uint32_t j = 0; j < p; j++) {
		uint32_t got = 0;

		for (uint32_t i = p; i < n; i++) {
			got += wl_ctx[i].recv_from[j];
		}
		complete += (got == iters);
	}

	check(rep, "received_total", p * iters, received);
	check(rep, "value_sum", sent_sum, recv_sum);
	check(rep, "producers_complete", p, complete);
	check(rep, "order_violations", 0, (uint32_t)atomic_get(&wl_order_bad));
	check(rep, "queue_empty", 0, k_msgq_num_used_get(&wl_q));
	check(rep, "timeouts", 0, (uint32_t)(atomic_get(&wl_put_to) + atomic_get(&wl_get_to)));
}

/* --------------------------- command --------------------------- */

int cmd_run(const struct shell *sh, size_t argc, char **argv)
{
	uint32_t seed = 1, n = 4, iters = 500, unsafe = 0;
	const char *name = NULL;
	struct report rep = { .sh = sh };
	bool is_mutex, is_sem, is_msgq;

	for (size_t i = 1; i < argc; i++) {
		int rc;

		if (strncmp(argv[i], "workload=", 9) == 0) {
			name = argv[i] + 9;
			continue;
		}
		rc = parse_kv(argv[i], "seed", &seed, UINT32_MAX);
		if (rc == 1) {
			rc = parse_kv(argv[i], "threads", &n, WL_MAX_THREADS);
		}
		if (rc == 1) {
			rc = parse_kv(argv[i], "iters", &iters, WL_MAX_ITERS);
		}
		if (rc == 1) {
			rc = parse_kv(argv[i], "unsafe", &unsafe, 1);
		}
		if (rc != 0) {
			shell_error(sh, "bad argument: %s", argv[i]);
			return -EINVAL;
		}
	}
	if (name == NULL) {
		shell_error(sh, "workload=mutex|sem|msgq is required");
		return -EINVAL;
	}
	is_mutex = (strcmp(name, "mutex") == 0);
	is_sem = (strcmp(name, "sem") == 0);
	is_msgq = (strcmp(name, "msgq") == 0);
	if (!is_mutex && !is_sem && !is_msgq) {
		shell_error(sh, "unknown workload: %s", name);
		return -EINVAL;
	}
	if (n == 0 || iters == 0) {
		shell_error(sh, "threads and iters must be >= 1");
		return -EINVAL;
	}
	if (!is_mutex && n < 2) {
		shell_error(sh, "workload %s needs threads >= 2", name);
		return -EINVAL;
	}
	if (unsafe && !is_mutex) {
		shell_error(sh, "unsafe only applies to workload=mutex");
		return -EINVAL;
	}

	shell_print(sh, "WORKLOAD START name=%s seed=%" PRIu32 " threads=%" PRIu32
		    " iters=%" PRIu32 " unsafe=%" PRIu32, name, seed, n, iters, unsafe);
	if (is_mutex) {
		run_mutex(&rep, seed, n, iters, unsafe != 0);
	} else if (is_sem) {
		run_sem(&rep, seed, n, iters);
	} else {
		run_msgq(&rep, seed, n, iters);
	}
	shell_print(sh, "WORKLOAD RESULT name=%s seed=%" PRIu32 " checks=%" PRIu32
		    " failed=%" PRIu32 " result=%s", name, seed, rep.checks, rep.failed,
		    rep.failed ? "FAIL" : "PASS");
	return 0;
}
