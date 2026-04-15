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

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.debug_log import debug_logger


class Scheduler:
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self.context: Dict[str, Any] = {}
        self._running = False

    def add_task(self, name: str, interval: int, func: Callable[[Dict[str, Any]], None]):
        if name in self._tasks:
            raise ValueError(f"Task '{name}' is already registered")
        self._tasks[name] = {
            "func": func,
            "interval": interval,
            "next_run": datetime.utcnow(),
        }
        debug_logger.task("scheduler", f"Task '{name}' registered", {"interval": interval})

    def run_forever(self):
        self._running = True
        debug_logger.task("scheduler", "Scheduler started")
        while self._running:
            now = datetime.utcnow()
            due_tasks = [
                (name, t)
                for name, t in self._tasks.items()
                if t["next_run"] <= now
            ]
            if due_tasks:
                for name, task_info in due_tasks:
                    try:
                        debug_logger.task(name, "Task execution started")
                        task_info["func"](self.context)
                        debug_logger.task(name, "Task execution completed")
                    except Exception as exc:
                        errors = self.context.setdefault("task_errors", [])
                        errors.append((name, str(exc), datetime.utcnow().isoformat()))
                        debug_logger.error(f"Task '{name}' failed", {"error": str(exc)})
                    finally:
                        task_info["next_run"] = now + timedelta(seconds=task_info["interval"])
            else:
                time.sleep(0.5)

    def stop(self):
        self._running = False
        debug_logger.task("scheduler", "Scheduler stopped")
