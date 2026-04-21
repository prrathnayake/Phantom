"""Process Tool for process management operations.

Provides process listing, killing, and monitoring.
"""
import signal
from typing import Any

from src.core.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDescriptor,
    ToolResult,
    ToolStatus,
)


class ProcessTool(BaseTool):
    """Tool for process management operations."""
    
    PROTECTED_PROCESSES = ["explorer.exe", "csrss.exe", "smss.exe", "wininit.exe", "services.exe"]
    
    @property
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            name="process",
            category=ToolCategory.PROCESS,
            description="Process management (list, kill, info)",
            version="1.0.0",
            parameters={
                "operation": {"type": "string", "required": True, "enum": ["list", "kill", "info", "find"]},
                "pid": {"type": "integer", "required": False},
                "name": {"type": "string", "required": False},
                "signal": {"type": "string", "default": "SIGTERM"},
            },
            tags=["process", "kill", "list"],
            timeout_seconds=30,
            requires_confirmation=True,
            safe_mode=True,
        )
    
    def execute(self, params: dict[str, Any]) -> ToolResult:
        operation = params.get("operation", "list")
        
        try:
            if operation == "list":
                return self._list_processes(params)
            elif operation == "kill":
                return self._kill_process(params)
            elif operation == "info":
                return self._process_info(params)
            elif operation == "find":
                return self._find_process(params)
            else:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"Unknown operation: {operation}",
                )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )
    
    def _list_processes(self, params: dict[str, Any]) -> ToolResult:
        try:
            import psutil
            
            limit = params.get("limit", 50)
            processes = []
            
            for proc in psutil.process_iter(attrs=["pid", "name", "username", "cpu_percent", "memory_percent"]):
                try:
                    info = proc.info
                    processes.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            processes.sort(key=lambda p: p.get("cpu_percent", 0), reverse=True)
            processes = processes[:limit]
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                output={"processes": processes, "count": len(processes)},
            )
        except ImportError:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="psutil not available",
            )
    
    def _kill_process(self, params: dict[str, Any]) -> ToolResult:
        pid = params.get("pid")
        name = params.get("name")
        
        if not pid and not name:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="pid or name required",
            )
        
        if name:
            name_lower = name.lower()
            if name_lower in [p.lower() for p in self.PROTECTED_PROCESSES]:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.DENIED,
                    error=f"Cannot kill protected process: {name}",
                )
        
        try:
            import psutil
            
            if pid:
                proc = psutil.Process(pid)
                if proc.name().lower() in [p.lower() for p in self.PROTECTED_PROCESSES]:
                    return ToolResult(
                        tool_name=self.name,
                        status=ToolStatus.DENIED,
                        error="Cannot kill protected process",
                    )
                proc.kill()
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.COMPLETED,
                    output={"killed": pid},
                )
            
            killed = []
            for proc in psutil.process_iter():
                try:
                    if name and proc.name().lower() == name.lower():
                        proc.kill()
                        killed.append(proc.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                output={"killed": killed, "count": len(killed)},
            )
        except ImportError:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="psutil not available",
            )
        except psutil.NoSuchProcess:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="Process not found",
            )
    
    def _process_info(self, params: dict[str, Any]) -> ToolResult:
        pid = params.get("pid")
        
        if not pid:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="pid required",
            )
        
        try:
            import psutil
            
            proc = psutil.Process(pid)
            
            info = {
                "pid": proc.pid,
                "name": proc.name(),
                "status": proc.status(),
                "username": proc.username(),
                "create_time": proc.create_time(),
                "cpu_percent": proc.cpu_percent(),
                "memory_info": proc.memory_info()._asdict(),
                "connections": len(proc.connections()),
                "open_files": len(proc.open_files()),
            }
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                output=info,
            )
        except ImportError:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="psutil not available",
            )
        except psutil.NoSuchProcess:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="Process not found",
            )
    
    def _find_process(self, params: dict[str, Any]) -> ToolResult:
        name = params.get("name", "")
        
        if not name:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="name required",
            )
        
        try:
            import psutil
            
            matches = []
            for proc in psutil.process_iter():
                try:
                    if name.lower() in proc.name().lower():
                        matches.append({
                            "pid": proc.pid,
                            "name": proc.name(),
                            "status": proc.status(),
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                output={"processes": matches, "count": len(matches)},
            )
        except ImportError:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="psutil not available",
            )
    
    def check_safety(self, params: dict[str, Any]) -> tuple[bool, str | None]:
        operation = params.get("operation", "list")
        
        if operation == "kill":
            pid = params.get("pid")
            name = params.get("name", "")
            
            if name:
                if name.lower() in [p.lower() for p in self.PROTECTED_PROCESSES]:
                    return False, f"Cannot kill protected process: {name}"
            
            if pid and pid in [0, 1, 4]:
                return False, "Cannot kill system process"
        
        return True, None
    
    def validate(self, params: dict[str, Any]) -> tuple[bool, str | None]:
        if "operation" not in params:
            return False, "operation parameter is required"
        
        valid_ops = ["list", "kill", "info", "find"]
        if params.get("operation") not in valid_ops:
            return False, f"operation must be one of: {valid_ops}"
        
        return True, None
