"""Port Analysis Skill.

Collects and analyzes open TCP and UDP ports, listening sockets.
Wraps port_sensor for skill-based execution.
"""
from typing import Any, Dict

from src.central_agent.skills.base import (
    BaseSkill,
    SkillCategory,
    SkillMetadata,
    SkillResult,
    SkillStatus,
)


class PortAnalysisSkill(BaseSkill):
    """Skill for port and socket analysis."""
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="port_analysis",
            category=SkillCategory.NETWORK,
            description="Collects and analyzes open TCP and UDP ports, listening sockets",
            version="1.0.0",
            tags=["port", "socket", "network", "diagnostic"],
            is_parallel=True,
            timeout_seconds=30,
        )
    
    def execute(self, context: Dict[str, Any]) -> SkillResult:
        try:
            from src.diagnostics.port_sensor import collect as port_collect
            
            result = port_collect(context)
            
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
