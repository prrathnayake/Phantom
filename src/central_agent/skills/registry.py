"""Skill Registry for loading and managing skills.

Provides lazy loading - skills are only imported when invoked.
Manages skill lifecycle, caching, and discovery.
"""
import importlib
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .base import BaseSkill, SkillCategory, SkillResult, SkillStatus
from .metadata import SkillDescriptor, SkillMetadataStore, get_skill_metadata_store

logger = logging.getLogger(__name__)


@dataclass
class LoadedSkill:
    """Container for loaded skill instance."""
    skill: BaseSkill
    loaded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    use_count: int = 0
    last_used: Optional[str] = None


class SkillRegistry:
    """Registry for managing skill loading and execution.
    
    Supports lazy loading, caching, and lifecycle management.
    
    Attributes:
        cache_instances: Whether to cache skill instances
        max_cache_age: Maximum age in seconds before refresh
    """
    
    def __init__(
        self,
        cache_instances: bool = True,
        max_cache_age: int = 3600
    ):
        self._store = get_skill_metadata_store()
        self._loaded: dict[str, LoadedSkill] = {}
        self._lock = threading.RLock()
        self._cache_instances = cache_instances
        self._max_cache_age = max_cache_age
        self._loaders: dict[str, Callable[[], BaseSkill]] = {}
        
        logger.info("SkillRegistry initialized", {
            "cache": cache_instances,
            "max_age": max_cache_age
        })
    
    def register_loader(
        self,
        name: str,
        loader: Callable[[], BaseSkill]
    ) -> None:
        """Register a skill loader function.
        
        Args:
            name: Skill name
            loader: Function that returns skill instance
        """
        with self._lock:
            self._loaders[name] = loader
            
            desc = loader().metadata
            descriptor = SkillDescriptor(
                name=desc.name,
                category=desc.category,
                description=desc.description,
                version=desc.version,
                requires=desc.requires,
                tags=desc.tags,
                is_parallel=desc.is_parallel,
                timeout_seconds=desc.timeout_seconds,
            )
            self._store.register(descriptor)
        
        logger.info("Skill loader registered", {"name": name})
    
    def register_skill(
        self,
        name: str,
        category: SkillCategory,
        description: str,
        module_path: str,
        class_name: str,
        version: str = "1.0.0",
        requires: list[str] = None,
        tags: list[str] = None,
        is_parallel: bool = True,
        timeout_seconds: int = 30
    ) -> None:
        """Register a skill by module path.
        
        Args:
            name: Skill name
            category: Skill category
            description: Skill description
            module_path: Python module path
            class_name: Skill class name
            version: Skill version
            requires: Required skill names
            tags: Skill tags
            is_parallel: Whether skill can run in parallel
            timeout_seconds: Execution timeout
        """
        descriptor = SkillDescriptor(
            name=name,
            category=category,
            description=description,
            version=version,
            requires=requires or [],
            tags=tags or [],
            is_parallel=is_parallel,
            timeout_seconds=timeout_seconds,
            module_path=module_path,
            class_name=class_name,
        )
        self._store.register(descriptor)
        
        def _loader() -> BaseSkill:
            module = importlib.import_module(module_path)
            skill_class = getattr(module, class_name)
            return skill_class()
        
        self._loaders[name] = _loader
        
        logger.info("Skill registered", {
            "name": name,
            "module": module_path,
            "class": class_name
        })
    
    def load(self, name: str) -> Optional[BaseSkill]:
        """Load a skill by name.
        
        Args:
            name: Skill name
            
        Returns:
            Loaded skill instance or None
        """
        with self._lock:
            loaded = self._loaded.get(name)
            
            if loaded and self._cache_instances:
                loaded_at = datetime.fromisoformat(loaded.loaded_at)
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(loaded_at)).total_seconds()
                
                if age < self._max_cache_age:
                    loaded.use_count += 1
                    loaded.last_used = datetime.now(timezone.utc).isoformat()
                    return loaded.skill
            
            if name not in self._loaders:
                logger.warning("Skill loader not found", {"name": name})
                return None
            
            try:
                skill = self._loaders[name]()
                self._loaded[name] = LoadedSkill(skill=skill)
                
                logger.info("Skill loaded", {"name": name})
                return skill
                
            except Exception as e:
                logger.error("Skill load failed", {
                    "name": name,
                    "error": str(e)
                })
                return None
    
    def unload(self, name: str) -> bool:
        """Unload a skill from cache.
        
        Args:
            name: Skill name
            
        Returns:
            True if unloaded
        """
        with self._lock:
            loaded = self._loaded.get(name)
            
            if loaded:
                try:
                    loaded.skill.cleanup()
                except Exception as e:
                    logger.warning("Skill cleanup failed", {
                        "name": name,
                        "error": str(e)
                    })
                
                del self._loaded[name]
                logger.info("Skill unloaded", {"name": name})
                return True
            
            return False
    
    def get(self, name: str) -> Optional[BaseSkill]:
        """Get a skill, loading if necessary.
        
        Args:
            name: Skill name
            
        Returns:
            Skill instance or None
        """
        return self.load(name)
    
    def execute(
        self,
        name: str,
        context: dict[str, Any],
        timeout: Optional[int] = None
    ) -> SkillResult:
        """Execute a skill by name.
        
        Args:
            name: Skill name
            context: Execution context
            timeout: Optional timeout override
            
        Returns:
            SkillResult from execution
        """
        descriptor = self._store.get(name)
        
        if descriptor is None:
            return SkillResult(
                skill_name=name,
                status=SkillStatus.FAILED,
                error="Skill not registered"
            )
        
        if timeout is None:
            timeout = descriptor.timeout_seconds
        
        skill = self.load(name)
        
        if skill is None:
            return SkillResult(
                skill_name=name,
                status=SkillStatus.FAILED,
                error="Failed to load skill"
            )
        
        start_time = time.time()
        
        try:
            is_valid, error = skill.validate(context)
            
            if not is_valid:
                return SkillResult(
                    skill_name=name,
                    status=SkillStatus.FAILED,
                    error=error or "Validation failed",
                    duration_ms=(time.time() - start_time) * 1000
                )
            
            prepared_context = skill.prepare(context)
            result = skill.execute(prepared_context)
            
            result.duration_ms = (time.time() - start_time) * 1000
            return result
            
        except Exception as e:
            logger.error("Skill execution failed", {
                "name": name,
                "error": str(e)
            })
            return SkillResult(
                skill_name=name,
                status=SkillStatus.FAILED,
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000
            )
    
    def execute_parallel(
        self,
        names: list[str],
        contexts: list[dict[str, Any]]
    ) -> list[SkillResult]:
        """Execute multiple skills in parallel.
        
        Args:
            names: List of skill names
            contexts: List of execution contexts
            
        Returns:
            List of SkillResults
        """
        if len(names) != len(contexts):
            raise ValueError("Names and contexts must have same length")
        
        results: list[SkillResult] = []
        
        for name, context in zip(names, contexts):
            result = self.execute(name, context)
            results.append(result)
        
        return results
    
    def get_metadata(self, name: str) -> Optional[SkillDescriptor]:
        """Get skill metadata without loading.
        
        Args:
            name: Skill name
            
        Returns:
            SkillDescriptor or None
        """
        return self._store.get(name)
    
    def list_skills(self) -> list[SkillDescriptor]:
        """List all registered skills.
        
        Returns:
            List of SkillDescriptors
        """
        return self._store.list_all()
    
    def list_by_category(self, category: SkillCategory) -> list[SkillDescriptor]:
        """List skills by category.
        
        Args:
            category: SkillCategory
            
        Returns:
            List of SkillDescriptors
        """
        return self._store.get_by_category(category)
    
    def search_skills(self, query: str) -> list[SkillDescriptor]:
        """Search skills by query.
        
        Args:
            query: Search query
            
        Returns:
            List of matching SkillDescriptors
        """
        return self._store.search(query)
    
    def is_registered(self, name: str) -> bool:
        """Check if skill is registered.
        
        Args:
            name: Skill name
            
        Returns:
            True if registered
        """
        return self._store.get(name) is not None
    
    def is_loaded(self, name: str) -> bool:
        """Check if skill is loaded.
        
        Args:
            name: Skill name
            
        Returns:
            True if loaded
        """
        return name in self._loaded
    
    def get_loaded_skills(self) -> list[str]:
        """Get list of loaded skill names.
        
        Returns:
            List of loaded skill names
        """
        return list(self._loaded.keys())
    
    def clear_cache(self) -> None:
        """Clear all cached skill instances."""
        with self._lock:
            for name in list(self._loaded.keys()):
                self.unload(name)
            
            logger.info("Skill cache cleared")
    
    def reload(self, name: str) -> bool:
        """Reload a skill.
        
        Args:
            name: Skill name
            
        Returns:
            True if reloaded
        """
        if self.is_registered(name):
            self.unload(name)
            return self.load(name) is not None
        
        return False


_global_registry: Optional[SkillRegistry] = None
_registry_lock = threading.Lock()


def get_skill_registry() -> SkillRegistry:
    """Get global skill registry.
    
    Returns:
        Global SkillRegistry instance
    """
    global _global_registry
    
    if _global_registry is None:
        with _registry_lock:
            if _global_registry is None:
                _global_registry = SkillRegistry()
    
    return _global_registry


def reset_skill_registry() -> None:
    """Reset global skill registry."""
    global _global_registry
    
    with _registry_lock:
        if _global_registry is not None:
            _global_registry.clear_cache()
        _global_registry = None
