"""Tool Executor with safety checks and error handling.

Provides safe execution of tools with validation, retry logic,
circuit breaker pattern, and comprehensive error handling.
"""
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from .base import BaseTool, ToolResult, ToolStatus
from .registry import ToolRegistry, get_tool_registry

logger = logging.getLogger(__name__)


@dataclass
class ExecutionRecord:
    """Record of a tool execution."""
    tool_name: str
    status: ToolStatus
    duration_ms: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    error: Optional[str] = None


@dataclass
class CircuitState:
    """Circuit breaker state."""
    failures: int = 0
    last_failure: Optional[str] = None
    state: str = "closed"
    last_attempt: Optional[str] = None


class ToolExecutor:
    """Executor for running tools with safety and error handling.
    
    Features:
    - Validation before execution
    - Safety checks
    - Retry with exponential backoff
    - Circuit breaker pattern
    - Execution logging
    
    Attributes:
        registry: Tool registry to use
        max_retries: Maximum retry attempts
        base_delay: Base delay for retries (ms)
        circuit_threshold: Failures before circuit opens
        circuit_timeout: Seconds before circuit retries
    """
    
    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        max_retries: int = 3,
        base_delay: float = 100,
        circuit_threshold: int = 5,
        circuit_timeout: int = 60
    ):
        self._registry = registry or get_tool_registry()
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._circuit_threshold = circuit_threshold
        self._circuit_timeout = circuit_timeout
        
        self._circuit_breakers: dict[str, CircuitState] = {}
        self._execution_history: list[ExecutionRecord] = []
        self._history_lock = threading.Lock()
        self._circuit_lock = threading.RLock()
        
        logger.info("ToolExecutor initialized", {
            "max_retries": max_retries,
            "circuit_threshold": circuit_threshold,
            "circuit_timeout": circuit_timeout
        })
    
    def execute(
        self,
        tool_name: str,
        params: dict[str, Any] = None,
        timeout: Optional[int] = None,
        retries: Optional[int] = None
    ) -> ToolResult:
        """Execute a tool by name.
        
        Args:
            tool_name: Tool name
            params: Execution parameters
            timeout: Optional timeout override
            retries: Optional retry count override
            
        Returns:
            ToolResult from execution
        """
        if params is None:
            params = {}
        
        descriptor = self._registry.get_descriptor(tool_name)
        
        if descriptor is None:
            return ToolResult(
                tool_name=tool_name,
                status=ToolStatus.DENIED,
                error="Tool not registered"
            )
        
        if self._is_circuit_open(tool_name):
            return ToolResult(
                tool_name=tool_name,
                status=ToolStatus.DENIED,
                error="Circuit breaker is open"
            )
        
        tool = self._registry.load(tool_name)
        
        if tool is None:
            self._record_failure(tool_name, "Tool load failed")
            return ToolResult(
                tool_name=tool_name,
                status=ToolStatus.FAILED,
                error="Failed to load tool"
            )
        
        if not tool.is_enabled():
            return ToolResult(
                tool_name=tool_name,
                status=ToolStatus.DENIED,
                error="Tool is disabled"
            )
        
        if timeout is None:
            timeout = descriptor.timeout_seconds
        
        if retries is None:
            retries = self._max_retries
        
        last_error = None
        
        for attempt in range(retries + 1):
            result = self._execute_single(
                tool, descriptor, params, timeout, attempt
            )
            
            if result.status == ToolStatus.COMPLETED:
                self._record_success(tool_name)
                return result
            
            last_error = result.error
            
            if result.status == ToolStatus.DENIED:
                break
            
            if attempt < retries:
                delay = self._base_delay * (2 ** attempt)
                logger.info("Retrying tool", {
                    "tool": tool_name,
                    "attempt": attempt + 1,
                    "delay_ms": delay
                })
                time.sleep(delay / 1000)
        
        self._record_failure(tool_name, last_error or "Unknown error")
        
        return ToolResult(
            tool_name=tool_name,
            status=ToolStatus.FAILED,
            error=last_error or "Execution failed"
        )
    
    def _execute_single(
        self,
        tool: BaseTool,
        descriptor,
        params: dict[str, Any],
        timeout: int,
        attempt: int
    ) -> ToolResult:
        """Execute tool once with validation and safety checks."""
        start_time = time.time()
        
        try:
            is_valid, error = tool.validate(params)
            
            if not is_valid:
                logger.warning("Tool validation failed", {
                    "tool": tool.name,
                    "error": error
                })
                return ToolResult(
                    tool_name=tool.name,
                    status=ToolStatus.DENIED,
                    error=error or "Validation failed",
                    duration_ms=(time.time() - start_time) * 1000
                )
            
            if descriptor.safe_mode:
                is_safe, reason = tool.check_safety(params)
                
                if not is_safe:
                    logger.warning("Tool safety check failed", {
                        "tool": tool.name,
                        "reason": reason
                    })
                    return ToolResult(
                        tool_name=tool.name,
                        status=ToolStatus.DENIED,
                        error=reason or "Safety check failed",
                        duration_ms=(time.time() - start_time) * 1000
                    )
            
            result = tool.execute(params)
            
            result.duration_ms = (time.time() - start_time) * 1000
            
            if attempt > 0:
                result.metadata["retry_attempt"] = attempt
            
            return result
            
        except Exception as e:
            logger.error("Tool execution exception", {
                "tool": tool.name,
                "error": str(e)
            })
            return ToolResult(
                tool_name=tool.name,
                status=ToolStatus.FAILED,
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000
            )
    
    def _is_circuit_open(self, tool_name: str) -> bool:
        """Check if circuit breaker is open for tool."""
        with self._circuit_lock:
            state = self._circuit_breakers.get(tool_name)
            
            if state is None:
                return False
            
            if state.state == "open":
                if state.last_attempt:
                    last_attempt_time = datetime.fromisoformat(state.last_attempt)
                    if datetime.utcnow() - last_attempt_time > timedelta(seconds=self._circuit_timeout):
                        state.state = "half-open"
                        logger.info("Circuit half-open", {"tool": tool_name})
                        return False
                return True
            
            return False
    
    def _record_success(self, tool_name: str) -> None:
        """Record successful execution."""
        with self._circuit_lock:
            if tool_name in self._circuit_breakers:
                state = self._circuit_breakers[tool_name]
                state.failures = 0
                state.state = "closed"
        
        logger.debug("Tool execution success", {"tool": tool_name})
    
    def _record_failure(self, tool_name: str, error: str) -> None:
        """Record failed execution."""
        with self._circuit_lock:
            if tool_name not in self._circuit_breakers:
                self._circuit_breakers[tool_name] = CircuitState()
            
            state = self._circuit_breakers[tool_name]
            state.failures += 1
            state.last_failure = error
            state.last_attempt = datetime.utcnow().isoformat()
            
            if state.failures >= self._circuit_threshold:
                state.state = "open"
                logger.warning("Circuit breaker opened", {
                    "tool": tool_name,
                    "failures": state.failures
                })
        
        logger.warning("Tool execution failed", {
            "tool": tool_name,
            "error": error
        })
    
    def get_execution_history(
        self,
        tool_name: Optional[str] = None,
        limit: int = 100
    ) -> list[ExecutionRecord]:
        """Get execution history.
        
        Args:
            tool_name: Optional tool name to filter
            limit: Maximum records to return
            
        Returns:
            List of ExecutionRecords
        """
        with self._history_lock:
            history = self._execution_history
            
            if tool_name:
                history = [r for r in history if r.tool_name == tool_name]
            
            return history[-limit:]
    
    def get_circuit_state(self, tool_name: str) -> Optional[CircuitState]:
        """Get circuit breaker state for tool.
        
        Args:
            tool_name: Tool name
            
        Returns:
            CircuitState or None
        """
        return self._circuit_breakers.get(tool_name)
    
    def reset_circuit(self, tool_name: str) -> bool:
        """Reset circuit breaker for tool.
        
        Args:
            tool_name: Tool name
            
        Returns:
            True if reset
        """
        with self._circuit_lock:
            if tool_name in self._circuit_breakers:
                self._circuit_breakers[tool_name] = CircuitState()
                logger.info("Circuit breaker reset", {"tool": tool_name})
                return True
        
        return False
    
    def get_stats(self) -> dict[str, Any]:
        """Get executor statistics.
        
        Returns:
            Stats dictionary
        """
        with self._history_lock:
            total = len(self._execution_history)
            completed = sum(1 for r in self._execution_history if r.status == ToolStatus.COMPLETED)
            failed = sum(1 for r in self._execution_history if r.status == ToolStatus.FAILED)
        
        with self._circuit_lock:
            open_circuits = sum(
                1 for s in self._circuit_breakers.values()
                if s.state == "open"
            )
        
        return {
            "total_executions": total,
            "completed": completed,
            "failed": failed,
            "open_circuits": open_circuits,
            "registered_tools": len(self._registry.list_tools()),
        }


_global_executor: Optional[ToolExecutor] = None
_executor_lock = threading.Lock()


def get_tool_executor() -> ToolExecutor:
    """Get global tool executor.
    
    Returns:
        Global ToolExecutor instance
    """
    global _global_executor
    
    if _global_executor is None:
        with _executor_lock:
            if _global_executor is None:
                _global_executor = ToolExecutor()
    
    return _global_executor


def reset_tool_executor() -> None:
    """Reset global tool executor."""
    global _global_executor
    
    with _executor_lock:
        _global_executor = None
