"""Security Analysis Skill.

Analyzes system for security vulnerabilities, weak configurations, and suspicious activity.
"""
from typing import Any, Dict, List
import platform

from central_agent.skills.base import (
    BaseSkill,
    SkillCategory,
    SkillMetadata,
    SkillResult,
    SkillStatus,
)


class SecurityAnalysisSkill(BaseSkill):
    """Skill for comprehensive security analysis."""
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="security_analysis",
            category=SkillCategory.SECURITY,
            description="Analyzes system for security vulnerabilities, weak configurations, and suspicious activity",
            version="1.0.0",
            tags=["security", "vulnerability", "audit"],
            is_parallel=False,
            timeout_seconds=120,
        )
    
    def execute(self, context: Dict[str, Any]) -> SkillResult:
        findings: List[Dict[str, Any]] = []
        
        findings.extend(self._check_open_ports())
        findings.extend(self._check_unusual_processes())
        findings.extend(self._check_recent_auth())
        
        risk_level = self._calculate_risk_level(findings)
        
        return SkillResult(
            skill_name=self.name,
            status=SkillStatus.COMPLETED,
            output={
                "risk_level": risk_level,
                "findings": findings,
                "checks_performed": 3,
            },
        )
    
    def _check_open_ports(self) -> List[Dict[str, Any]]:
        findings = []
        
        try:
            from diagnostics.port_sensor import collect as port_collect
            
            result = port_collect({})
            ports = result.get("listening", [])
            
            high_risk_ports = [21, 23, 445, 3389, 5900]
            
            for port_info in ports:
                addr = port_info.get("address", "")
                if ":" in addr:
                    port = int(addr.rsplit(":", 1)[1])
                    
                    if port in high_risk_ports:
                        findings.append({
                            "type": "open_port",
                            "severity": "medium" if port not in [3389, 5900] else "high",
                            "description": f"High-risk port {port} is open: {addr}",
                            "port": port,
                            "address": addr,
                        })
        except Exception as e:
            findings.append({
                "type": "check_failed",
                "severity": "low",
                "description": f"Port check failed: {str(e)}",
            })
        
        return findings
    
    def _check_unusual_processes(self) -> List[Dict[str, Any]]:
        findings = []
        
        try:
            from diagnostics.process_sensor import collect as process_collect
            
            result = process_collect({})
            processes = result.get("top_processes", [])
            
            suspicious = ["nc.exe", "netcat", "psexec", "mimikatz", "pwdump"]
            
            for proc in processes:
                name = proc.get("name", "").lower()
                for sus in suspicious:
                    if sus.lower() in name:
                        findings.append({
                            "type": "suspicious_process",
                            "severity": "high",
                            "description": f"Suspicious process detected: {proc.get('name')}",
                            "process": proc,
                        })
        except Exception as e:
            findings.append({
                "type": "check_failed",
                "severity": "low",
                "description": f"Process check failed: {str(e)}",
            })
        
        return findings
    
    def _check_recent_auth(self) -> List[Dict[str, Any]]:
        findings = []
        
        system = platform.system()
        
        if system == "Windows":
            try:
                import subprocess
                result = subprocess.run(
                    ["powershell", "-Command", "Get-WinEvent -LogName Security -MaxEvents 10 | Select-Object TimeCreated, Id, Message"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    findings.append({
                        "type": "auth_events",
                        "severity": "info",
                        "description": "Retrieved recent security events",
                        "count": len(result.stdout.splitlines()),
                    })
            except Exception as e:
                pass
        
        return findings
    
    def _calculate_risk_level(self, findings: List[Dict[str, Any]]) -> str:
        if not findings:
            return "LOW"
        
        high_count = sum(1 for f in findings if f.get("severity") == "high")
        medium_count = sum(1 for f in findings if f.get("severity") == "medium")
        
        if high_count > 0:
            return "HIGH"
        elif medium_count > 2:
            return "MEDIUM"
        elif medium_count > 0:
            return "LOW"
        
        return "LOW"
    
    def validate(self, context: Dict[str, Any]) -> tuple[bool, str | None]:
        return True, None