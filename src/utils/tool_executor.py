"""Tool executor module for logging agent actions.

Tracks tool/agent actions with success/failure status
and provides execution history.
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Optional

import config


class ExecutionStatus(Enum):
    """Tool execution status."""
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"
    PENDING = "pending"


class ActionType(Enum):
    """Agent action types."""
    SCAN = "scan"
    CHECK = "check"
    ALERT = "alert"
    KILL_PROCESS = "kill_process"
    BLOCK_PORT = "block_port"
    ISOLATE = "isolate"
    NOTIFY = "notify"
    ANALYSIS = "analysis"


@dataclass
class ToolExecution:
    """Single tool execution record."""
    tool_name: str
    args: dict[str, Any]
    result: Any
    timestamp: float
    status: str
    error: Optional[str] = None
    duration: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "args": self.args,
            "result": str(self.result)[:100] if self.result else None,
            "timestamp": self.timestamp,
            "status": self.status,
            "error": self.error,
            "duration": self.duration,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolExecution":
        return cls(
            tool_name=data.get("tool_name", ""),
            args=data.get("args", {}),
            result=data.get("result"),
            timestamp=data.get("timestamp", time.time()),
            status=data.get("status", "pending"),
            error=data.get("error"),
            duration=data.get("duration", 0.0),
        )


class ToolLogger:
    """Tool execution logger.
    
    Logs tool executions and provides history.
    Supports file persistence across restarts.
    
    Attributes:
        max_executions: Maximum executions to keep
        persist_path: Optional path for file persistence
    """
    
    def __init__(
        self,
        max_executions: int = 50,
        persist_path: Optional[Path] = None
    ):
        self.max_executions = max_executions
        self.persist_path = persist_path
        self._executions: list[ToolExecution] = []
        self._lock = Lock()
        
        if persist_path:
            self._load()
    
    def log(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: Any,
        status: str = "success",
        error: Optional[str] = None,
        duration: float = 0.0
    ) -> None:
        """Log a tool execution.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            result: Execution result
            status: Execution status
            error: Error message if any
            duration: Execution time in seconds
        """
        execution = ToolExecution(
            tool_name=tool_name,
            args=args,
            result=result,
            timestamp=time.time(),
            status=status,
            error=error,
            duration=duration
        )
        
        with self._lock:
            self._executions.append(execution)
            
            if len(self._executions) > self.max_executions:
                self._executions = self._executions[-self.max_executions:]
        
        if self.persist_path:
            self._save()
    
    def get_logs(self, count: int = 10) -> list[ToolExecution]:
        """Get recent execution logs.
        
        Args:
            count: Number of logs to return
            
        Returns:
            List of executions (newest first)
        """
        with self._lock:
            return list(reversed(self._executions[-count:]))
    
    def get_success_count(self) -> int:
        """Get count of successful executions.
        
        Returns:
            Number of successful executions
        """
        with self._lock:
            return sum(1 for e in self._executions if e.status == "success")
    
    def get_failure_count(self) -> int:
        """Get count of failed executions.
        
        Returns:
            Number of failed executions
        """
        with self._lock:
            return sum(1 for e in self._executions if e.status == "failure")
    
    def get_last_execution(self) -> Optional[ToolExecution]:
        """Get last execution.
        
        Returns:
            Most recent execution or None
        """
        with self._lock:
            return self._executions[-1] if self._executions else None
    
    def get_last_action(self) -> Optional[str]:
        """Get description of last action.
        
        Returns:
            Formatted last action string
        """
        execution = self.get_last_execution()
        if not execution:
            return None
        
        ts = time.strftime("%H:%M:%S", time.localtime(execution.timestamp))
        status_symbol = "✓" if execution.status == "success" else "✗"
        
        return f"{ts} {status_symbol} {execution.tool_name}"
    
    def clear(self) -> None:
        """Clear execution logs."""
        with self._lock:
            self._executions.clear()
        
        if self.persist_path:
            self._save()
    
    def _save(self) -> None:
        """Save logs to file."""
        if not self.persist_path:
            return
        
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            with self.persist_path.open("w", encoding="utf-8") as f:
                data = [e.to_dict() for e in self._executions]
                json.dump(data, f)
        except OSError:
            pass
    
    def _load(self) -> None:
        """Load logs from file."""
        if not self.persist_path or not self.persist_path.exists():
            return
        
        try:
            with self.persist_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                self._executions = [ToolExecution.from_dict(e) for e in data]
        except (json.JSONDecodeError, OSError):
            pass


class AgentAction:
    """Agent action executor with logging.
    
    Provides execution framework for agent actions
    with automatic logging and error handling.
    """
    
    def __init__(self, logger: ToolLogger):
        self.logger = logger
        self._actions: dict[str, Callable] = {}
    
    def register(self, name: str, func: Callable) -> None:
        """Register an action.
        
        Args:
            name: Action name
            func: Action function
        """
        self._actions[name] = func
    
    def execute(
        self,
        name: str,
        args: Optional[dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Execute an action with logging.
        
        Args:
            name: Action name
            args: Action arguments
            **kwargs: Additional arguments
            
        Returns:
            Action result
        """
        args = args or {}
        start_time = time.time()
        
        self.logger.log(
            tool_name=name,
            args={**args, **kwargs},
            result=None,
            status="running"
        )
        
        try:
            func = self._actions.get(name)
            if not func:
                raise ValueError(f"Unknown action: {name}")
            
            result = func(**args, **kwargs)
            duration = time.time() - start_time
            
            self.logger.log(
                tool_name=name,
                args={**args, **kwargs},
                result=result,
                status="success",
                duration=duration
            )
            
            return result
        
        except Exception as e:
            duration = time.time() - start_time
            
            self.logger.log(
                tool_name=name,
                args={**args, **kwargs},
                result=None,
                status="failure",
                error=str(e),
                duration=duration
            )
            
            raise
    
    def list_actions(self) -> list[str]:
        """List registered actions.
        
        Returns:
            List of action names
        """
        return list(self._actions.keys())


def create_tool_logger() -> ToolLogger:
    """Create tool logger with config settings.
    
    Returns:
        ToolLogger instance
    """
    return ToolLogger(
        max_executions=config.MEMORY_MAX_ENTRIES,
        persist_path=config.LOG_DIR / "tool_executions.json"
    )


def create_agent_executor() -> AgentAction:
    """Create agent action executor.
    
    Returns:
        AgentAction instance
    """
    return AgentAction(create_tool_logger())
