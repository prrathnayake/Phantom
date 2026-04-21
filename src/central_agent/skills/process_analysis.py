"""Process Analysis Skill.

Collects and analyzes running processes, resource usage, and process tree.
Wraps process_sensor for skill-based execution.
"""
from typing import Any, Dict

from central_agent.skills.base import (
    BaseSkill,
    SkillCategory,
    SkillMetadata,
    SkillResult,
    SkillStatus,
)


class ProcessAnalysisSkill(BaseSkill):
    """Skill for process analysis and diagnostics."""
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="process_analysis",
            category=SkillCategory.SYSTEM,
            description="Collects and analyzes running processes, resource usage, and top consumers",
            version="1.0.0",
            tags=["process", "cpu", "memory", "diagnostic"],
            is_parallel=True,
            timeout_seconds=30,
        )
    
    def execute(self, context: Dict[str, Any]) -> SkillResult:
        try:
            from src.diagnostics.process_sensor import collect as process_collect
            
            result = process_collect(context)
            
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
