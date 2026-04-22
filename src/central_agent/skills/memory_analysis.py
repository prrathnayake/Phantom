"""Memory Analysis Skill.

Collects and analyzes system RAM and swap usage, memory pressure indicators.
Wraps memory_sensor for skill-based execution.
"""
from typing import Any, Dict

from src.central_agent.skills.base import (
    BaseSkill,
    SkillCategory,
    SkillMetadata,
    SkillResult,
    SkillStatus,
)


class MemoryAnalysisSkill(BaseSkill):
    """Skill for memory analysis and diagnostics."""
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="memory_analysis",
            category=SkillCategory.SYSTEM,
            description="Collects and analyzes system RAM and swap usage, memory pressure indicators, top consumers",
            version="1.0.0",
            tags=["memory", "ram", "swap", "diagnostic"],
            is_parallel=True,
            timeout_seconds=30,
        )
    
    def execute(self, context: Dict[str, Any]) -> SkillResult:
        try:
            from src.diagnostics.memory_sensor import collect as memory_collect
            
            result = memory_collect(context)
            
            return SkillResult(
                skill_name=self.name,
                status=SkillStatus.COMPLETED,
                output=result,
            )
        except Exception as e:
            return SkillResult(
                skill_name=self.name,
                status=SkillStatus.FAILED,
                error=str(e),
            )
    
    def validate(self, context: Dict[str, Any]) -> tuple[bool, str | None]:
        return True, None
