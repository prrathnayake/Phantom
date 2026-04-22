"""Tool Registry for loading and managing tools.

Provides centralized tool management with safety checks,
caching, and discovery.
"""
import importlib
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .base import BaseTool, ToolCategory, ToolDescriptor, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


@dataclass
class LoadedTool:
    """Container for loaded tool instance."""
    tool: BaseTool
    loaded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    use_count: int = 0
    last_used: Optional[str] = None


class ToolRegistry:
    """Registry for managing tool loading and execution.
    
    Supports lazy loading, safety checks, and lifecycle management.
    
    Attributes:
        safe_mode: Whether to enforce safety checks
        cache_instances: Whether to cache tool instances
    """
    
    def __init__(
        self,
        safe_mode: bool = True,
        cache_instances: bool = True
    ):
        self._tools: dict[str, BaseTool] = {}
        self._descriptors: dict[str, ToolDescriptor] = {}
        self._lock = threading.RLock()
        self._safe_mode = safe_mode
        self._cache_instances = cache_instances
        self._loaders: dict[str, Callable[[], BaseTool]] = {}
        self._blocked_tools: set[str] = set()
        
        logger.info("ToolRegistry initialized", {
            "safe_mode": safe_mode,
            "cache": cache_instances
        })
    
    def register_tool(
        self,
        name: str,
        category: ToolCategory,
        description: str,
        module_path: str,
        class_name: str,
        version: str = "1.0.0",
        parameters: dict[str, Any] = None,
        tags: list[str] = None,
        timeout_seconds: int = 30,
        requires_confirmation: bool = False,
        safe_mode: bool = True
    ) -> None:
        """Register a tool by module path.
        
        Args:
            name: Tool name
            category: Tool category
            description: Tool description
            module_path: Python module path
            class_name: Tool class name
            version: Tool version
            parameters: Parameter schema
            tags: Tool tags
            timeout_seconds: Execution timeout
            requires_confirmation: Whether tool requires confirmation
            safe_mode: Whether safety checks enabled
        """
        descriptor = ToolDescriptor(
            name=name,
            category=category,
            description=description,
            version=version,
            parameters=parameters or {},
            tags=tags or [],
            timeout_seconds=timeout_seconds,
            requires_confirmation=requires_confirmation,
            safe_mode=safe_mode,
        )
        self._descriptors[name] = descriptor
        
        def _loader() -> BaseTool:
            module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)
            return tool_class()
        
        self._loaders[name] = _loader
        
        logger.info("Tool registered", {
            "name": name,
            "module": module_path,
            "class": class_name
        })
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool instance.
        
        Args:
            tool: Tool instance to register
        """
        with self._lock:
            descriptor = tool.descriptor
            self._descriptors[descriptor.name] = descriptor
            self._tools[descriptor.name] = tool
            
            logger.info("Tool instance registered", {
                "name": descriptor.name,
                "category": descriptor.category.value
            })
    
    def register_loader(
        self,
        name: str,
        loader: Callable[[], BaseTool],
        descriptor: Optional[ToolDescriptor] = None
    ) -> None:
        """Register a tool loader function.
        
        Args:
            name: Tool name
            loader: Function that returns tool instance
            descriptor: Optional pre-built descriptor to avoid early instantiation
        """
        with self._lock:
            self._loaders[name] = loader
            
            if descriptor is not None:
                self._descriptors[name] = descriptor
            else:
                tool = loader()
                self._descriptors[name] = tool.descriptor
            
            logger.info("Tool loader registered", {"name": name})
    
    def load(self, name: str) -> Optional[BaseTool]:
        """Load a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Loaded tool instance or None
        """
        with self._lock:
            if name in self._blocked_tools:
                logger.warning("Tool is blocked", {"name": name})
                return None
            
            if name in self._tools:
                return self._tools[name]
            
            if name not in self._loaders:
                logger.warning("Tool loader not found", {"name": name})
                return None
            
            try:
                tool = self._loaders[name]()
                self._tools[name] = tool
                
                logger.info("Tool loaded", {"name": name})
                return tool
                
            except Exception as e:
                logger.error("Tool load failed", {
                    "name": name,
                    "error": str(e)
                })
                return None
    
    def unload(self, name: str) -> bool:
        """Unload a tool from cache.
        
        Args:
            name: Tool name
            
        Returns:
            True if unloaded
        """
        with self._lock:
            if name in self._tools:
                del self._tools[name]
                logger.info("Tool unloaded", {"name": name})
                return True
            
            return False
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool, loading if necessary.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None
        """
        return self.load(name)
    
    def get_descriptor(self, name: str) -> Optional[ToolDescriptor]:
        """Get tool descriptor without loading.
        
        Args:
            name: Tool name
            
        Returns:
            ToolDescriptor or None
        """
        return self._descriptors.get(name)
    
    def list_tools(self) -> list[ToolDescriptor]:
        """List all registered tools.
        
        Returns:
            List of ToolDescriptors
        """
        return list(self._descriptors.values())
    
    def list_by_category(self, category: ToolCategory) -> list[ToolDescriptor]:
        """List tools by category.
        
        Args:
            category: ToolCategory
            
        Returns:
            List of ToolDescriptors
        """
        return [
            d for d in self._descriptors.values()
            if d.category == category
        ]
    
    def search_tools(self, query: str) -> list[ToolDescriptor]:
        """Search tools by query.
        
        Args:
            query: Search query
            
        Returns:
            List of matching ToolDescriptors
        """
        query_lower = query.lower()
        results = []
        
        for desc in self._descriptors.values():
            if query_lower in desc.name.lower() or query_lower in desc.description.lower():
                results.append(desc)
        
        return results
    
    def is_registered(self, name: str) -> bool:
        """Check if tool is registered.
        
        Args:
            name: Tool name
            
        Returns:
            True if registered
        """
        return name in self._descriptors
    
    def is_loaded(self, name: str) -> bool:
        """Check if tool is loaded.
        
        Args:
            name: Tool name
            
        Returns:
            True if loaded
        """
        return name in self._tools
    
    def block_tool(self, name: str) -> None:
        """Block a tool from execution.
        
        Args:
            name: Tool name
        """
        with self._lock:
            self._blocked_tools.add(name)
            logger.info("Tool blocked", {"name": name})
    
    def unblock_tool(self, name: str) -> None:
        """Unblock a tool for execution.
        
        Args:
            name: Tool name
        """
        with self._lock:
            self._blocked_tools.discard(name)
            logger.info("Tool unblocked", {"name": name})
    
    def is_blocked(self, name: str) -> bool:
        """Check if tool is blocked.
        
        Args:
            name: Tool name
            
        Returns:
            True if blocked
        """
        return name in self._blocked_tools
    
    def clear_cache(self) -> None:
        """Clear all cached tool instances."""
        with self._lock:
            self._tools.clear()
            logger.info("Tool cache cleared")
    
    def set_safe_mode(self, enabled: bool) -> None:
        """Set safe mode.
        
        Args:
            enabled: Whether safe mode is enabled
        """
        self._safe_mode = enabled
        logger.info("Safe mode set", {"enabled": enabled})


_global_registry: Optional[ToolRegistry] = None
_registry_lock = threading.Lock()


def get_tool_registry() -> ToolRegistry:
    """Get global tool registry.
    
    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    
    if _global_registry is None:
        with _registry_lock:
            if _global_registry is None:
                _global_registry = ToolRegistry()
    
    return _global_registry


def reset_tool_registry() -> None:
    """Reset global tool registry."""
    global _global_registry
    
    with _registry_lock:
        if _global_registry is not None:
            _global_registry.clear_cache()
        _global_registry = None
