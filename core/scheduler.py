"""A very simple cooperative scheduler for recurring tasks.

The scheduler stores tasks with associated intervals and runs them in
a loop.  It is intentionally minimal; it does not support concurrent
execution or cron expressions.  Tasks are executed sequentially.

Example usage:

```python
from core.scheduler import Scheduler

def my_task(context):
    print("running my task")

scheduler = Scheduler()
scheduler.add_task("my_task", interval=60, func=my_task)
scheduler.run_forever()
```

Each task receives a single argument: `context`, which is a mutable
dictionary shared among all tasks.  This can be used to store state.
"""
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, Any


class Scheduler:
    def __init__(self):
        # Tasks are stored as a mapping from name to a dict containing
        # the function, interval in seconds, and next run time.
        self._tasks: Dict[str, Dict[str, Any]] = {}
        # Shared context passed to all tasks.  It can be used to share
        # common state or configuration across tasks.
        self.context: Dict[str, Any] = {}
        self._running = False

    def add_task(self, name: str, interval: int, func: Callable[[Dict[str, Any]], None]):
        """Register a task to be executed at a fixed interval.

        :param name: Unique name for the task.
        :param interval: Interval in seconds between runs.
        :param func: Function to call when the task runs.  It will be
            passed the shared context dictionary.
        """
        if name in self._tasks:
            raise ValueError(f"Task '{name}' is already registered")
        self._tasks[name] = {
            "func": func,
            "interval": interval,
            "next_run": datetime.utcnow(),
        }

    def run_forever(self):
        """Run tasks indefinitely.  This call blocks until interrupted.

        The scheduler computes the next task to run based on the earliest
        `next_run` timestamp.  If no task is due, it sleeps briefly.
        """
        self._running = True
        while self._running:
            now = datetime.utcnow()
            # Find the next task to run
            due_tasks = [
                (name, t)
                for name, t in self._tasks.items()
                if t["next_run"] <= now
            ]
            if due_tasks:
                for name, task_info in due_tasks:
                    try:
                        task_info["func"](self.context)
                    except Exception as exc:
                        # We log exceptions to the context; a real system might
                        # use the storage layer or a logging framework.
                        errors = self.context.setdefault("task_errors", [])
                        errors.append((name, str(exc), datetime.utcnow().isoformat()))
                    finally:
                        # Schedule the next run time for this task
                        task_info["next_run"] = now + timedelta(seconds=task_info["interval"])
            else:
                # Sleep briefly to avoid busy waiting
                time.sleep(0.5)

    def stop(self):
        """Stop the scheduler loop."""
        self._running = False
