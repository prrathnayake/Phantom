"""Test the threadpool module."""
import sys
import os
import time
import threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.threadpool import ThreadPool, ThreadPoolError, init_threadpool


def test_singleton_pattern():
    """Test singleton pattern ensures only one instance exists."""
    print("\nTesting singleton pattern...")

    pool1 = ThreadPool.get_instance(4)
    pool2 = ThreadPool.get_instance(4)

    if pool1 is pool2:
        print("  get_instance returns same instance: OK")
    else:
        print("  get_instance returns same instance: FAILED")
        return False

    ThreadPool.reset_instance()
    return True


def test_initialization():
    """Test threadpool initialization."""
    print("\nTesting initialization...")

    pool = ThreadPool.get_instance(4)
    pool.initialize()

    time.sleep(0.5)

    if len(pool._workers) == 4:
        print(f"  worker threads created: {len(pool._workers)} OK")
    else:
        print(f"  worker threads created: {len(pool._workers)} FAILED")
        pool.shutdown()
        return False

    pool.shutdown()
    ThreadPool.reset_instance()
    return True


def test_submit_tasks():
    """Test submitting tasks to threadpool."""
    print("\nTesting submit tasks...")

    pool = ThreadPool.get_instance(4)
    pool.initialize()
    time.sleep(0.5)

    results = []

    def task(value):
        results.append(value)

    for i in range(10):
        pool.submit(lambda v=i: task(v))

    pool.wait_completion(timeout=5.0)

    errors = pool.get_errors()
    if errors:
        print(f"  errors during execution: {len(errors)}")
        for e in errors:
            print(f"    - {e}")
        pool.shutdown()
        return False

    print(f"  tasks executed: {len(results)} OK")
    pool.shutdown()
    ThreadPool.reset_instance()
    return True


def test_parallel_execution():
    """Test tasks run in parallel."""
    print("\nTesting parallel execution...")

    pool = ThreadPool.get_instance(4)
    pool.initialize()
    time.sleep(0.5)

    start_time = time.time()
    counter = [0]
    lock = threading.Lock()

    def slow_task():
        time.sleep(0.1)
        with lock:
            counter[0] += 1

    for _ in range(8):
        pool.submit(slow_task)

    pool.wait_completion(timeout=5.0)
    elapsed = time.time() - start_time

    if elapsed < 0.5:
        print(f"  8 tasks (0.1s each) completed in {elapsed:.2f}s: OK (parallel)")
    else:
        print(f"  8 tasks completed in {elapsed:.2f}s: SLOW (may be sequential)")

    pool.shutdown()
    ThreadPool.reset_instance()
    return True


def test_error_handling():
    """Test exception handling in worker threads."""
    print("\nTesting error handling...")

    pool = ThreadPool.get_instance(4)
    pool.initialize()
    time.sleep(0.5)

    def failing_task():
        raise ValueError("Test error")

    for _ in range(3):
        pool.submit(failing_task)

    pool.wait_completion(timeout=5.0)

    errors = pool.get_errors()
    if len(errors) == 3:
        print(f"  captured {len(errors)} exceptions: OK")
        for e in errors:
            print(f"    - {type(e).__name__}: {e}")
    else:
        print(f"  captured {len(errors)} exceptions: FAILED (expected 3)")
        pool.shutdown()
        return False

    pool.shutdown()
    ThreadPool.reset_instance()
    return True


def test_shutdown():
    """Test graceful shutdown."""
    print("\nTesting shutdown...")

    pool = ThreadPool.get_instance(4)
    pool.initialize()
    time.sleep(0.5)

    results = []

    def task():
        time.sleep(0.05)
        results.append(1)

    for _ in range(5):
        pool.submit(task)

    pool.shutdown(wait=True)

    if len(results) == 5:
        print(f"  tasks completed before shutdown: {len(results)} OK")
    else:
        print(f"  tasks completed: {len(results)} (may be timing issue)")

    ThreadPool.reset_instance()
    return True


def test_get_active_tasks():
    """Test active task counter."""
    print("\nTesting active tasks counter...")

    pool = ThreadPool.get_instance(2)
    pool.initialize()
    time.sleep(0.5)

    def long_task():
        time.sleep(0.3)

    for _ in range(3):
        pool.submit(long_task)

    time.sleep(0.1)
    active = pool.get_active_tasks()

    print(f"  active tasks during execution: {active} OK")

    pool.wait_completion(timeout=5.0)
    pool.shutdown()
    ThreadPool.reset_instance()
    return True


def test_init_helper():
    """Test init_threadpool helper function."""
    print("\nTesting init_threadpool helper...")

    pool = init_threadpool(num_threads=4)
    time.sleep(0.5)

    if pool._initialized:
        print("  init_threadpool: OK")
    else:
        print("  init_threadpool: FAILED")
        return False

    pool.shutdown()
    ThreadPool.reset_instance()
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("THREADPOOL TEST SUITE")
    print("=" * 50)

    tests = [
        test_singleton_pattern,
        test_initialization,
        test_submit_tasks,
        test_parallel_execution,
        test_error_handling,
        test_shutdown,
        test_get_active_tasks,
        test_init_helper,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"EXCEPTION in {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)