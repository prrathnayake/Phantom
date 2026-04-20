"""Log Analysis Skill.

Analyzes system and application logs for security events, errors, and anomalies.
"""
from typing import Any, Dict, List
import os
import platform
from pathlib import Path

from central_agent.skills.base import (
    BaseSkill,
    SkillCategory,
    SkillMetadata,
    SkillResult,
    SkillStatus,
)


class LogAnalysisSkill(BaseSkill):
    """Skill for analyzing system and application logs."""
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="log_analysis",
            category=SkillCategory.LOG,
            description="Analyzes system and application logs for security events, errors, and anomalies",
            version="1.0.0",
            tags=["log", "security", "analysis"],
            is_parallel=False,
            timeout_seconds=60,
        )
    
    def execute(self, context: Dict[str, Any]) -> SkillResult:
        log_paths = context.get("log_paths", [])
        
        if not log_paths:
            log_paths = self._get_default_log_paths()
        
        findings: List[Dict[str, Any]] = []
        
        for log_path in log_paths:
            result = self._analyze_log(log_path)
            if result:
                findings.extend(result)
        
        return SkillResult(
            skill_name=self.name,
            status=SkillStatus.COMPLETED,
            output={
                "logs_analyzed": len(log_paths),
                "findings": findings,
            },
        )
    
    def _get_default_log_paths(self) -> List[str]:
        system = platform.system()
        paths = []
        
        if system == "Windows":
            paths = [
                os.path.expandvars("%SystemRoot%\\System32\\LogFiles\\"),
                os.path.expandvars("%ProgramData%\\Microsoft\\Windows\\WER\\"),
            ]
        else:
            paths = [
                "/var/log",
                "/var/log/syslog",
                "/var/log/messages",
            ]
        
        return [p for p in paths if os.path.exists(p)]
    
    def _analyze_log(self, log_path: str) -> List[Dict[str, Any]]:
        findings = []
        keywords = ["error", "warning", "critical", "failed", "denied", "unauthorized"]
        
        try:
            path = Path(log_path)
            if path.is_file():
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()[-100:]
                    
                    for line in lines:
                        line_lower = line.lower()
                        for kw in keywords:
                            if kw in line_lower:
                                findings.append({
                                    "log": str(path),
                                    "keyword": kw,
                                    "line": line.strip()[:200],
                                })
                                break
                except PermissionError:
                    findings.append({
                        "log": str(path),
                        "error": "Permission denied",
                    })
            elif path.is_dir():
                for file in path.glob("*.log"):
                    if file.stat().st_size < 1024 * 1024:
                        findings.extend(self._analyze_log(str(file)))
        except Exception as e:
            findings.append({
                "log": log_path,
                "error": str(e),
            })
        
        return findings
    
    def validate(self, context: Dict[str, Any]) -> tuple[bool, str | None]:
        return True, None