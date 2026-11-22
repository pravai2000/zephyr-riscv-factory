#include <errno.h>
#include <zephyr/kernel.h>
#include <zephyr/ztest.h>

ZTEST_SUITE(kernel_basic, NULL, NULL, NULL, NULL, NULL);

ZTEST(kernel_basic, test_semaphore_give_take)
{
	struct k_sem sem;

	k_sem_init(&sem, 0, 1);
	zassert_equal(k_sem_take(&sem, K_NO_WAIT), -EBUSY);
	k_sem_give(&sem);
	zassert_equal(k_sem_take(&sem, K_NO_WAIT), 0);
}

ZTEST(kernel_basic, test_mutex_lock_unlock)
{
	struct k_mutex m;

	k_mutex_init(&m);
	zassert_ok(k_mutex_lock(&m, K_NO_WAIT));
	zassert_ok(k_mutex_unlock(&m));
}

K_MSGQ_DEFINE(test_q, sizeof(int), 4, 4);

ZTEST(kernel_basic, test_msgq_fifo_order)
{
	int v, out;

	k_msgq_purge(&test_q);
	for (v = 1; v <= 3; v++) {
		zassert_ok(k_msgq_put(&test_q, &v, K_NO_WAIT));
	}
	for (v = 1; v <= 3; v++) {
		zassert_ok(k_msgq_get(&test_q, &out, K_NO_WAIT));
		zassert_equal(out, v);
	}
}

ZTEST(kernel_basic, test_msgq_full_rejects)
{
	int v = 7;

	k_msgq_purge(&test_q);
	for (int i = 0; i < 4; i++) {
		zassert_ok(k_msgq_put(&test_q, &v, K_NO_WAIT));
	}
	zassert_equal(k_msgq_put(&test_q, &v, K_NO_WAIT), -ENOMSG);
	k_msgq_purge(&test_q);
}

ZTEST(kernel_basic, test_sleep_duration)
{
	int64_t start = k_uptime_get();

	k_msleep(50);
	zassert_true(k_uptime_get() - start >= 50, "slept less than 50 ms");
}

static atomic_t ticks;

static void tick_fn(struct k_timer *t)
{
	atomic_inc(&ticks);
}
K_TIMER_DEFINE(tick_timer, tick_fn, NULL);

ZTEST(kernel_basic, test_timer_fires_periodically)
{
	atomic_set(&ticks, 0);
	k_timer_start(&tick_timer, K_MSEC(10), K_MSEC(10));
	k_msleep(100);
	k_timer_stop(&tick_timer);
	zassert_true(atomic_get(&ticks) >= 3, "timer fired %ld times",
		     (long)atomic_get(&ticks));
}

K_THREAD_STACK_DEFINE(worker_stack, 2048);
static struct k_thread worker;
static volatile int worker_ran;

static void worker_fn(void *a, void *b, void *c)
{
	worker_ran = 1;
}

ZTEST(kernel_basic, test_thread_runs_to_completion)
{
	worker_ran = 0;
	k_thread_create(&worker, worker_stack, K_THREAD_STACK_SIZEOF(worker_stack),
			worker_fn, NULL, NULL, NULL, K_PRIO_PREEMPT(5), 0, K_NO_WAIT);
	zassert_ok(k_thread_join(&worker, K_SECONDS(1)));
	zassert_equal(worker_ran, 1);
}

ZTEST(kernel_basic, test_skipped_example)
{
	ztest_test_skip();
}
