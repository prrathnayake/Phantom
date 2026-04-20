"""Base classes for Skills system.

Provides abstract base class for all skills with standardized
interface for execution, validation, and metadata.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class SkillCategory(Enum):
    """Categories for organizing skills."""
    NETWORK = "network"
    LOG = "log"
    VULNERABILITY = "vulnerability"
    SYSTEM = "system"
    REPORT = "report"
    SECURITY = "security"
    DIAGNOSTIC = "diagnostic"
    GENERAL = "general"


class SkillStatus(Enum):
    """Skill execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SkillResult:
    """Container for skill execution result."""
    skill_name: str
    status: SkillStatus
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SkillMetadata:
    """Lightweight metadata for skill discovery."""
    name: str
    category: SkillCategory
    description: str
    version: str = "1.0.0"
    requires: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    is_parallel: bool = True
    timeout_seconds: int = 30


class BaseSkill(ABC):
    """Abstract base class for all skills.
    
    All skills must inherit from this class and implement the execute method.
    Skills are loaded lazily - heavy imports happen only when skill is invoked.
    """
    
    def __init__(self):
        self._metadata: Optional[SkillMetadata] = None
        self._initialized: bool = False
    
    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        """Return skill metadata for discovery."""
        pass
    
    @property
    def name(self) -> str:
        """Return skill name."""
        return self.metadata.name
    
    @property
    def category(self) -> SkillCategory:
        """Return skill category."""
        return self.metadata.category
    
    @abstractmethod
    def execute(self, context: dict[str, Any]) -> SkillResult:
        """Execute the skill with given context.
        
        Args:
            context: Execution context with parameters
            
        Returns:
            SkillResult with execution output
        """
        pass
    
    def validate(self, context: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate context before execution.
        
        Args:
            context: Execution context to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return True, None
    
    def prepare(self, context: dict[str, Any]) -> dict[str, Any]:
        """Prepare context before execution.
        
        Can be overridden to transform/augment context.
        
        Args:
            context: Raw context
            
        Returns:
            Prepared context
        """
        return context
    
    def cleanup(self) -> None:
        """Cleanup after execution.
        
        Can be overridden for resource cleanup.
        """
        pass
    
    def get_dependencies(self) -> list[str]:
        """Return list of skill names this skill depends on."""
        return self.metadata.requires