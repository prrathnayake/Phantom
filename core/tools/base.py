"""Base classes for Tools system.

Provides abstract base class for all tools with standardized
interface for execution, validation, and safety checks.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ToolCategory(Enum):
    """Categories for organizing tools."""
    SHELL = "shell"
    FILE = "file"
    PROCESS = "process"
    NETWORK = "network"
    SYSTEM = "system"
    DIAGNOSTIC = "diagnostic"
    SECURITY = "security"
    QUERY = "query"
    GENERAL = "general"


class ToolStatus(Enum):
    """Tool execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    DENIED = "denied"


@dataclass
class ToolResult:
    """Container for tool execution result."""
    tool_name: str
    status: ToolStatus
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ToolDescriptor:
    """Metadata descriptor for tool."""
    name: str
    category: ToolCategory
    description: str
    version: str = "1.0.0"
    parameters: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    timeout_seconds: int = 30
    requires_confirmation: bool = False
    safe_mode: bool = True


class BaseTool(ABC):
    """Abstract base class for all tools.
    
    All tools must inherit from this class and implement the execute method.
    Tools execute real actions on the system - must implement safety checks.
    """
    
    def __init__(self):
        self._descriptor: Optional[ToolDescriptor] = None
        self._enabled: bool = True
    
    @property
    @abstractmethod
    def descriptor(self) -> ToolDescriptor:
        """Return tool descriptor for discovery."""
        pass
    
    @property
    def name(self) -> str:
        """Return tool name."""
        return self.descriptor.name
    
    @property
    def category(self) -> ToolCategory:
        """Return tool category."""
        return self.descriptor.category
    
    @abstractmethod
    def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute the tool with given parameters.
        
        Args:
            params: Execution parameters
            
        Returns:
            ToolResult with execution output
        """
        pass
    
    def validate(self, params: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate parameters before execution.
        
        Args:
            params: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return True, None
    
    def check_safety(self, params: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Check if execution is safe.
        
        Override to implement safety checks.
        
        Args:
            params: Execution parameters
            
        Returns:
            Tuple of (is_safe, reason)
        """
        return True, None
    
    def enable(self) -> None:
        """Enable the tool."""
        self._enabled = True
    
    def disable(self) -> None:
        """Disable the tool."""
        self._enabled = False
    
    def is_enabled(self) -> bool:
        """Check if tool is enabled."""
        return self._enabled


class SafeToolMixin:
    """Mixin for safe tool execution patterns."""
    
    def __init__(self):
        self._blocked_patterns: list[str] = []
    
    def add_blocked_pattern(self, pattern: str) -> None:
        """Add a blocked command pattern."""
        self._blocked_patterns.append(pattern)
    
    def check_blocked(self, command: str) -> tuple[bool, Optional[str]]:
        """Check if command matches blocked pattern."""
        for pattern in self._blocked_patterns:
            if pattern in command:
                return False, f"Command matches blocked pattern: {pattern}"
        return True, None