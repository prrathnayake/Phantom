"""Centralized singleton threadpool with mutex-based error handling.

This module provides a thread-safe singleton ThreadPool implementation for parallel task execution.

Features:
- Singleton pattern: ensures single shared instance across the application
- Mutex-protected shared state for thread-safe operations
- Worker thread pool for parallel task execution
- Exception catching and storage for later retrieval
- Graceful shutdown with task completion waiting

Usage:
    from utils.threadpool import init_threadpool, ThreadPool

    # Initialize (typically once at application startup)
    pool = init_threadpool(num_threads=4)

    # Submit work to be executed in parallel
    pool.submit(lambda: print("Task running in thread"))

    # Wait for all submitted tasks to complete
    pool.wait_completion(timeout=30.0)

    # Retrieve any exceptions that occurred during execution
    errors = pool.get_errors()
    for error in errors:
        print(f"Error: {error}")

    # Graceful shutdown when application exits
    pool.shutdown(wait=True)

Example:
    import time
    from utils.threadpool import init_threadpool

    pool = init_threadpool(num_threads=4)

    results = []

    def process_item(item):
        time.sleep(0.1)  # Simulate work
        return item * 2

    # Submit multiple tasks
    for i in range(10):
        pool.submit(lambda i=i: results.append(process_item(i)))

    # Wait for completion
    pool.wait_completion(timeout=30.0)

    print(f"Processed {len(results)} items")
    pool.shutdown()
"""

import threading
import queue
from typing import Callable, Any, Optional
from dataclasses import dataclass


class ThreadPoolError(Exception):
    """Custom exception for thread pool errors.
    
    Attributes:
        message: Human-readable error message
        code: Error code for programmatic handling
    """
    def __init__(self, message: str, code: str = "THREADPOOL_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class ThreadPool:
    """Singleton thread pool for parallel task execution.
    
    This class implements a thread-safe worker pool using a bounded queue
    for task distribution. All shared state is protected by a mutex for
    thread safety.
    
    Class Attributes:
        _instance: Singleton instance (class-level)
        _lock: Class-level lock for singleton creation
    
    Instance Attributes:
        _num_threads: Number of worker threads
        _work_queue: Queue of pending tasks
        _workers: List of worker thread objects
        _shutdown_flag: Event flag signaling shutdown
        _error_queue: Queue for capturing worker exceptions
        _mutex: Mutex for protecting shared state
        _active_tasks: Counter of currently executing tasks
        _initialized: Flag indicating pool is initialized
    """
    _instance: Optional['ThreadPool'] = None
    _lock = threading.Lock()

    def __init__(self, num_threads: int = 8):
        """Initialize thread pool (internal - use get_instance).
        
        Args:
            num_threads: Number of worker threads to create
            
        Raises:
            ThreadPoolError: If pool already initialized
        """
        if ThreadPool._instance is not None:
            raise ThreadPoolError(
                "ThreadPool already initialized. Use get_instance()",
                "ALREADY_INITIALIZED"
            )

        self._num_threads = num_threads
        self._work_queue: queue.Queue[Callable[[], Any]] = queue.Queue()
        self._workers: list[threading.Thread] = []
        self._shutdown_flag = threading.Event()
        self._error_queue: queue.Queue[Exception] = queue.Queue()
        self._mutex = threading.Lock()
        self._active_tasks = 0
        self._initialized = False

    @classmethod
    def get_instance(cls, num_threads: int = 8) -> 'ThreadPool':
        """Get or create the singleton ThreadPool instance.
        
        Uses double-checked locking pattern for efficient singleton access.
        
        Args:
            num_threads: Number of worker threads (only used on first call)
            
        Returns:
            The singleton ThreadPool instance
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(num_threads)
            return cls._instance

    def initialize(self) -> None:
        """Initialize and start worker threads.
        
        Creates worker threads and begins processing tasks from the queue.
        Thread-safe: uses mutex to protect initialization state.
        
        Raises:
            ThreadPoolError: If thread count is invalid
        """
        with self._mutex:
            if self._initialized:
                return

            if self._num_threads <= 0:
                raise ThreadPoolError("Invalid thread count", "INVALID_THREAD_COUNT")

            self._shutdown_flag.clear()
            self._error_queue.queue.clear()

            for i in range(self._num_threads):
                worker = threading.Thread(
                    target=self._worker_loop,
                    daemon=False,
                    name=f"ThreadPool-Worker-{i}"
                )
                self._workers.append(worker)
                worker.start()

            self._initialized = True

    def _worker_loop(self) -> None:
        """Main worker loop - processes tasks from queue.
        
        Internal method that runs in each worker thread.
        Catches all exceptions and stores them in error_queue.
        Thread-safe: uses mutex to protect active task counter.
        """
        while not self._shutdown_flag.is_set():
            try:
                task = self._work_queue.get(timeout=0.5)
                if task is None:
                    break

                with self._mutex:
                    self._active_tasks += 1

                try:
                    task()
                except Exception as e:
                    self._error_queue.put(e)
                finally:
                    self._work_queue.task_done()
                    with self._mutex:
                        self._active_tasks -= 1

            except queue.Empty:
                continue
            except Exception as e:
                with self._mutex:
                    if not self._shutdown_flag.is_set():
                        self._error_queue.put(e)

    def submit(self, func: Callable[[], Any]) -> None:
        """Submit a task for execution in worker threads.
        
        Thread-safe: uses mutex to check state before queuing.
        
        Args:
            func: Callable to execute in worker thread
            
        Raises:
            ThreadPoolError: If pool not initialized or shutting down
        """
        with self._mutex:
            if not self._initialized:
                raise ThreadPoolError(
                    "ThreadPool not initialized. Call initialize() first",
                    "NOT_INITIALIZED"
                )
            if self._shutdown_flag.is_set():
                raise ThreadPoolError("ThreadPool is shutting down", "SHUTTING_DOWN")

            self._work_queue.put(func)

    def wait_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for all submitted tasks to complete.
        
        Uses queue.join() to wait for all tasks to finish.
        Thread-safe: uses mutex to check initialization state.
        
        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)
            
        Returns:
            True if all tasks completed, False on timeout or error
        """
        with self._mutex:
            if not self._initialized:
                return True

        try:
            self._work_queue.join()
            return True
        except Exception:
            return False

    def get_errors(self) -> list[Exception]:
        """Get all exceptions that occurred during task execution.
        
        Returns:
            List of exceptions captured from worker threads
        """
        errors = []
        while not self._error_queue.empty():
            try:
                errors.append(self._error_queue.get_nowait())
            except queue.Empty:
                break
        return errors

    def get_active_tasks(self) -> int:
        """Get count of currently executing tasks.
        
        Thread-safe: uses mutex to read active counter.
        
        Returns:
            Number of tasks currently being executed
        """
        with self._mutex:
            return self._active_tasks

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the thread pool gracefully.
        
        Sets shutdown flag, waits for task completion if requested,
        then joins all worker threads.
        Thread-safe: uses mutex to protect state changes.
        
        Args:
            wait: If True, wait for all tasks to complete first
        """
        with self._mutex:
            if not self._initialized:
                return

            self._shutdown_flag.set()

        for _ in range(self._num_threads):
            self._work_queue.put(None)

        if wait:
            for worker in self._workers:
                if threading.current_thread() != worker:
                    worker.join(timeout=5.0)

        with self._mutex:
            self._workers.clear()
            self._initialized = False

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing or reinitialization).
        
        Shuts down the pool and clears the singleton instance.
        Use with caution - ensures all tasks complete first.
        """
        with cls._lock:
            if cls._instance is not None:
                cls._instance.shutdown(wait=False)
                cls._instance = None


def init_threadpool(num_threads: int = 8) -> ThreadPool:
    """Initialize and return a singleton ThreadPool.
    
    Convenience function that combines get_instance() and initialize().
    
    Args:
        num_threads: Number of worker threads
        
    Returns:
        Initialized ThreadPool instance
        
    Example:
        pool = init_threadpool(num_threads=8)
        pool.submit(my_task)
    """
    pool = ThreadPool.get_instance(num_threads)
    pool.initialize()
    return pool