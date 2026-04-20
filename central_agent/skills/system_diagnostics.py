"""System Diagnostics Skill.

Collects comprehensive system information including hardware, OS, and services.
"""
from typing import Any, Dict
import platform

from central_agent.skills.base import (
    BaseSkill,
    SkillCategory,
    SkillMetadata,
    SkillResult,
    SkillStatus,
)


class SystemDiagnosticsSkill(BaseSkill):
    """Skill for comprehensive system diagnostics."""
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="system_diagnostics",
            category=SkillCategory.SYSTEM,
            description="Collects comprehensive system information including hardware, OS, services, and disk",
            version="1.0.0",
            tags=["system", "hardware", "diagnostic", "os"],
            is_parallel=True,
            timeout_seconds=30,
        )
    
    def execute(self, context: Dict[str, Any]) -> SkillResult:
        try:
            system_info = self._collect_system_info()
            service_info = self._collect_service_info()
            disk_info = self._collect_disk_info()
            
            return SkillResult(
                skill_name=self.name,
                status=SkillStatus.COMPLETED,
                output={
                    "system": system_info,
                    "services": service_info,
                    "disk": disk_info,
                },
            )
        except Exception as e:
            return SkillResult(
                skill_name=self.name,
                status=SkillStatus.FAILED,
                error=str(e),
            )
    
    def _collect_system_info(self) -> Dict[str, Any]:
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "processor": platform.processor(),
        }
    
    def _collect_service_info(self) -> Dict[str, Any]:
        system = platform.system()
        
        if system == "Windows":
            try:
                import subprocess
                result = subprocess.run(
                    ["sc", "query", "state=", "all"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                services = []
                current_service = {}
                for line in result.stdout.splitlines():
                    if "SERVICE_NAME" in line:
                        if current_service:
                            services.append(current_service)
                        current_service = {"name": line.split(":", 1)[1].strip()}
                    elif "STATE" in line:
                        state = line.split(":", 1)[1].strip()
                        current_service["state"] = state
                
                if current_service:
                    services.append(current_service)
                
                running = sum(1 for s in services if s.get("state") == "RUNNING")
                
                return {
                    "total": len(services),
                    "running": running,
                    "sample": services[:10],
                }
            except Exception as e:
                return {"error": str(e)}
        else:
            try:
                import subprocess
                result = subprocess.run(
                    ["systemctl", "list-units", "--type=service", "--no-pager"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                return {
                    "platform": "linux",
                    "note": "systemd detected",
                    "output": result.stdout[:500],
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _collect_disk_info(self) -> Dict[str, Any]:
        try:
            import psutil
            
            disks = []
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks.append({
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "percent": usage.percent,
                    })
                except PermissionError:
                    continue
            
            return {"disks": disks}
        except ImportError:
            return {"error": "psutil not available"}
    
    def validate(self, context: Dict[str, Any]) -> tuple[bool, str | None]:
        return True, None