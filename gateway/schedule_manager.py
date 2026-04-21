"""Schedule Manager for Gateway.

Manages scheduled diagnostic script runs autonomously.
Collects results and sends payloads to Central Agent.
"""
import time
import importlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from threading import Lock, Thread
from typing import Any, Callable, Dict, List, Optional

import config
from utils.debug_log import debug_logger

SCHEDULE_NOTIFICATIONS: List[Callable[[Dict], None]] = []


def on_schedule_run(callback: Callable[[Dict], None]) -> None:
    """Register callback for schedule run notifications."""
    SCHEDULE_NOTIFICATIONS.append(callback)


def _notify_schedule_run(result: dict) -> None:
    """Notify all registered callbacks of schedule run."""
    for callback in SCHEDULE_NOTIFICATIONS:
        try:
            callback(result)
        except Exception:
            pass


@dataclass
class Schedule:
    """Container for scheduled diagnostic configuration."""
    name: str
    interval: int
    script_module: str
    func: Callable[[Dict[str, Any]], None]
    next_run: datetime = field(default_factory=datetime.utcnow)
    last_result: Optional[dict] = None
    last_run_time: Optional[str] = None
    enabled: bool = True
    
    def should_run(self) -> bool:
        """Check if schedule is due to run."""
        if not self.enabled:
            return False
        return datetime.utcnow() >= self.next_run
    
    def mark_run(self, result: dict) -> None:
        """Mark schedule as run with result."""
        self.last_result = result
        self.last_run_time = datetime.utcnow().isoformat()
        self.next_run = datetime.utcnow() + timedelta(seconds=self.interval)


class ScheduleManager:
    """Manages scheduled diagnostic script runs.
    
    Runs diagnostics autonomously at configured intervals,
    collects results, and sends payloads to Central Agent.
    
    Attributes:
        central_agent_endpoint: URL for central agent endpoint
        autonomous_mode: Whether to run autonomously
    """
    
    def __init__(
        self,
        central_agent_endpoint: Optional[str] = None,
        autonomous_mode: bool = True
    ):
        self.endpoint = central_agent_endpoint
        self.autonomous_mode = autonomous_mode
        self._schedules: Dict[str, Schedule] = {}
        self._running = False
        self._lock = Lock()
        
        debug_logger.info("ScheduleManager initialized", {
            "autonomous": autonomous_mode,
            "endpoint": central_agent_endpoint
        })
    
    def add_schedule(
        self,
        name: str,
        interval: int,
        script_module: str,
        func: Optional[Callable] = None
    ) -> None:
        """Add scheduled diagnostic.
        
        Args:
            name: Schedule name
            interval: Run interval in seconds
            script_module: Module name in diagnostics package
            func: Optional custom function (loaded from module if not provided)
        """
        if func is None:
            try:
                module = importlib.import_module(f"diagnostics.{script_module}")
                func = getattr(module, "collect", None)
                if func is None:
                    debug_logger.warning(
                        f"No collect function in {script_module}",
                        {"module": script_module}
                    )
                    return
            except ImportError as e:
                debug_logger.error(
                    f"Failed to import {script_module}",
                    {"error": str(e)}
                )
                return
        
        with self._lock:
            schedule = Schedule(
                name=name,
                interval=interval,
                script_module=script_module,
                func=func,
                next_run=datetime.utcnow()
            )
            self._schedules[name] = schedule
        
        debug_logger.info("Schedule added", {
            "name": name,
            "interval": interval,
            "module": script_module
        })
    
    def remove_schedule(self, name: str) -> bool:
        """Remove scheduled diagnostic.
        
        Args:
            name: Schedule name to remove
            
        Returns:
            True if removed
        """
        with self._lock:
            if name in self._schedules:
                del self._schedules[name]
                debug_logger.info("Schedule removed", {"name": name})
                return True
        
        return False
    
    def enable_schedule(self, name: str) -> bool:
        """Enable scheduled diagnostic.
        
        Args:
            name: Schedule name
            
        Returns:
            True if enabled
        """
        with self._lock:
            schedule = self._schedules.get(name)
            if schedule:
                schedule.enabled = True
                debug_logger.info("Schedule enabled", {"name": name})
                return True
        
        return False
    
    def disable_schedule(self, name: str) -> bool:
        """Disable scheduled diagnostic.
        
        Args:
            name: Schedule name
            
        Returns:
            True if disabled
        """
        with self._lock:
            schedule = self._schedules.get(name)
            if schedule:
                schedule.enabled = False
                debug_logger.info("Schedule disabled", {"name": name})
                return True
        
        return False
    
    def run_schedule(self, name: str) -> Optional[dict]:
        """Run specific schedule manually.
        
        Args:
            name: Schedule name
            
        Returns:
            Result dict or None
        """
        schedule = self._schedules.get(name)
        
        if schedule is None:
            debug_logger.warning("Schedule not found", {"name": name})
            return None
        
        debug_logger.info("Running schedule", {"name": name})
        
        try:
            context: Dict[str, Any] = {}
            schedule.func(context)
            result = {
                "name": name,
                "timestamp": datetime.utcnow().isoformat(),
                "source": name,
                "data": context
            }
            schedule.mark_run(result)
            
            debug_logger.info("Schedule complete", {
                "name": name,
                "has_data": bool(context)
            })
            
            _notify_schedule_run(result)
            
            return result
        
        except Exception as e:
            debug_logger.error("Schedule failed", {
                "name": name,
                "error": str(e)
            })
            return None
    
    def run_all_due(self) -> List[dict]:
        """Run all due schedules.
        
        Returns:
            List of result dicts
        """
        results = []
        
        with self._lock:
            due_schedules = [
                (name, sched)
                for name, sched in self._schedules.items()
                if sched.should_run()
            ]
        
        for name, schedule in due_schedules:
            result = self.run_schedule(name)
            if result:
                results.append(result)
        
        return results
    
    def collect_results(self) -> dict:
        """Collect all diagnostic results.
        
        Returns:
            Dict with all schedule results
        """
        results = {}
        
        with self._lock:
            for name, schedule in self._schedules.items():
                if schedule.last_result:
                    results[name] = schedule.last_result
        
        debug_logger.info("Results collected", {
            "count": len(results),
            "schedules": list(self._schedules.keys())
        })
        
        return results
    
    def get_schedule_info(self, name: str) -> Optional[dict]:
        """Get schedule information.
        
        Args:
            name: Schedule name
            
        Returns:
            Info dict or None
        """
        schedule = self._schedules.get(name)
        
        if schedule is None:
            return None
        
        return {
            "name": schedule.name,
            "interval": schedule.interval,
            "module": schedule.script_module,
            "enabled": schedule.enabled,
            "next_run": schedule.next_run.isoformat(),
            "last_run": schedule.last_run_time,
            "has_result": schedule.last_result is not None
        }
    
    def get_all_schedules(self) -> dict:
        """Get info for all schedules.
        
        Returns:
            Dict of schedule name -> info
        """
        return {
            name: self.get_schedule_info(name)
            for name in self._schedules.keys()
        }
    
    def run_autonomous(self) -> None:
        """Run all scheduled diagnostics autonomously.
        
        Runs in a loop checking for due schedules.
        """
        self._running = True
        
        debug_logger.info("Autonomous mode started")
        
        while self._running:
            try:
                results = self.run_all_due()
                
                if results:
                    debug_logger.info("Autonomous run complete", {
                        "schedules_run": len(results)
                    })
            except Exception as e:
                debug_logger.error("Autonomous loop error", {
                    "error": str(e)
                })
            
            time.sleep(1)
    
    def start_autonomous(self) -> Thread:
        """Start autonomous mode in background thread.
        
        Returns:
            Background thread
        """
        thread = Thread(target=self.run_autonomous, daemon=True)
        thread.start()
        
        debug_logger.info("Autonomous thread started")
        
        return thread
    
    def stop(self) -> None:
        """Stop autonomous mode."""
        self._running = False
        
        debug_logger.info("ScheduleManager stopped")


def create_schedule_manager() -> ScheduleManager:
    """Create ScheduleManager with default settings.
    
    Sets up default diagnostic schedules from config.
    
    Returns:
        Configured ScheduleManager instance
    """
    manager = ScheduleManager(
        central_agent_endpoint=None,
        autonomous_mode=True
    )
    
    for name, interval in config.POLL_INTERVALS.items():
        module_name = name.replace("_sensor", "")
        manager.add_schedule(
            name=name,
            interval=interval,
            script_module=module_name
        )
    
    debug_logger.info("Default schedules configured", {
        "count": len(config.POLL_INTERVALS)
    })
    
    return manager