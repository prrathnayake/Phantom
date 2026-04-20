"""Skill metadata storage for lightweight discovery.

Provides metadata storage that can be loaded without importing
skill implementations - enabling lazy loading.
"""
from dataclasses import dataclass, field
from typing import Any, Optional
from .base import SkillCategory


@dataclass
class SkillDescriptor:
    """Lightweight descriptor for skill discovery.
    
    Contains only metadata - actual skill class loaded on demand.
    """
    name: str
    category: SkillCategory
    description: str
    version: str = "1.0.0"
    requires: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    is_parallel: bool = True
    timeout_seconds: int = 30
    module_path: str = ""
    class_name: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "version": self.version,
            "requires": self.requires,
            "tags": self.tags,
            "is_parallel": self.is_parallel,
            "timeout_seconds": self.timeout_seconds,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillDescriptor":
        """Create from dictionary."""
        category = data.get("category", "general")
        if isinstance(category, str):
            category = SkillCategory(category.lower())
        
        return cls(
            name=data.get("name", ""),
            category=category,
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            requires=data.get("requires", []),
            tags=data.get("tags", []),
            is_parallel=data.get("is_parallel", True),
            timeout_seconds=data.get("timeout_seconds", 30),
            module_path=data.get("module_path", ""),
            class_name=data.get("class_name", ""),
        )


class SkillMetadataStore:
    """In-memory store for skill metadata.
    
    Provides fast lookup without loading skill implementations.
    """
    
    def __init__(self):
        self._descriptors: dict[str, SkillDescriptor] = {}
        self._by_category: dict[SkillCategory, list[str]] = {}
        self._by_tag: dict[str, list[str]] = {}
    
    def register(self, descriptor: SkillDescriptor) -> None:
        """Register a skill descriptor.
        
        Args:
            descriptor: SkillDescriptor to register
        """
        self._descriptors[descriptor.name] = descriptor
        
        cat = descriptor.category
        if cat not in self._by_category:
            self._by_category[cat] = []
        if descriptor.name not in self._by_category[cat]:
            self._by_category[cat].append(descriptor.name)
        
        for tag in descriptor.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = []
            if descriptor.name not in self._by_tag[tag]:
                self._by_tag[tag].append(descriptor.name)
    
    def get(self, name: str) -> Optional[SkillDescriptor]:
        """Get descriptor by name.
        
        Args:
            name: Skill name
            
        Returns:
            SkillDescriptor or None
        """
        return self._descriptors.get(name)
    
    def get_by_category(self, category: SkillCategory) -> list[SkillDescriptor]:
        """Get all descriptors in category.
        
        Args:
            category: SkillCategory
            
        Returns:
            List of SkillDescriptors
        """
        names = self._by_category.get(category, [])
        return [self._descriptors[n] for n in names if n in self._descriptors]
    
    def get_by_tag(self, tag: str) -> list[SkillDescriptor]:
        """Get all descriptors with tag.
        
        Args:
            tag: Tag to search
            
        Returns:
            List of SkillDescriptors
        """
        names = self._by_tag.get(tag, [])
        return [self._descriptors[n] for n in names if n in self._descriptors]
    
    def list_all(self) -> list[SkillDescriptor]:
        """List all registered descriptors.
        
        Returns:
            List of all SkillDescriptors
        """
        return list(self._descriptors.values())
    
    def search(self, query: str) -> list[SkillDescriptor]:
        """Search descriptors by name or description.
        
        Args:
            query: Search query
            
        Returns:
            List of matching SkillDescriptors
        """
        query_lower = query.lower()
        results = []
        
        for desc in self._descriptors.values():
            if query_lower in desc.name.lower() or query_lower in desc.description.lower():
                results.append(desc)
        
        return results
    
    def unregister(self, name: str) -> bool:
        """Unregister a skill.
        
        Args:
            name: Skill name
            
        Returns:
            True if unregistered
        """
        if name not in self._descriptors:
            return False
        
        desc = self._descriptors[name]
        
        if desc.category in self._by_category:
            self._by_category[desc.category] = [
                n for n in self._by_category[desc.category] if n != name
            ]
        
        for tag in desc.tags:
            if tag in self._by_tag:
                self._by_tag[tag] = [
                    n for n in self._by_tag[tag] if n != name
                ]
        
        del self._descriptors[name]
        return True


_global_store: Optional[SkillMetadataStore] = None


def get_skill_metadata_store() -> SkillMetadataStore:
    """Get global skill metadata store.
    
    Returns:
        Global SkillMetadataStore instance
    """
    global _global_store
    if _global_store is None:
        _global_store = SkillMetadataStore()
    return _global_store


def reset_skill_metadata_store() -> None:
    """Reset global skill metadata store."""
    global _global_store
    _global_store = None