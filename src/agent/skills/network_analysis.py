"""Network Analysis Skill.

Collects and analyzes network connections, interfaces, and traffic.
Wraps network_sensor for skill-based execution.
"""
from typing import Any, Dict

from src.agent.skills.base import (
    BaseSkill,
    SkillCategory,
    SkillMetadata,
    SkillResult,
    SkillStatus,
)


class NetworkAnalysisSkill(BaseSkill):
    """Skill for network analysis and diagnostics."""
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="network_analysis",
            category=SkillCategory.NETWORK,
            description="Collects and analyzes network connections, interfaces, and traffic patterns",
            version="1.0.0",
            tags=["network", "connections", "diagnostic"],
            is_parallel=True,
            timeout_seconds=30,
        )
    
    def execute(self, context: Dict[str, Any]) -> SkillResult:
        try:
            from src.diagnostics.network_sensor import collect as network_collect
            
            result = network_collect(context)
            
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
