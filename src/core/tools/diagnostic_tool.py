"""Diagnostic Tool for running diagnostic collectors.

Wraps diagnostic sensors for tool-based execution.
"""
from typing import Any

from src.core.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDescriptor,
    ToolResult,
    ToolStatus,
)


class DiagnosticTool(BaseTool):
    """Tool for running diagnostic collectors."""
    
    AVAILABLE_SENSORS = [
        "network",
        "process",
        "memory",
        "port",
        "disk_io",
        "file",
        "service",
        "hardware",
        "certificate",
        "driver",
        "dns",
        "registry",
        "auth",
    ]
    
    @property
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            name="diagnostic",
            category=ToolCategory.DIAGNOSTIC,
            description="Run diagnostic collectors for system information",
            version="1.0.0",
            parameters={
                "sensor": {"type": "string", "required": True},
                "context": {"type": "object", "required": False},
            },
            tags=["diagnostic", "sensor", "collect"],
            timeout_seconds=30,
            requires_confirmation=False,
            safe_mode=False,
        )
    
    def execute(self, params: dict[str, Any]) -> ToolResult:
        sensor = params.get("sensor", "")
        
        if not sensor:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="No sensor specified",
            )
        
        if sensor not in self.AVAILABLE_SENSORS:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Unknown sensor: {sensor}. Available: {self.AVAILABLE_SENSORS}",
            )
        
        try:
            module_name = f"diagnostics.{sensor}_sensor"
            module = __import__(module_name, fromlist=["collect"])
            collect_func = getattr(module, "collect")
            
            context = params.get("context", {})
            result = collect_func(context)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                output=result,
                metadata={"sensor": sensor},
            )
        except ImportError as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Module import failed: {str(e)}",
            )
        except AttributeError as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Sensor function not found: {str(e)}",
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )
    
    def validate(self, params: dict[str, Any]) -> tuple[bool, str | None]:
        if "sensor" not in params:
            return False, "sensor parameter is required"
        
        sensor = params.get("sensor")
        if sensor not in self.AVAILABLE_SENSORS:
            return False, f"Unknown sensor. Available: {self.AVAILABLE_SENSORS}"
        
        return True, None


class NetworkDiagTool(BaseTool):
    """Tool specifically for network diagnostics."""
    
    @property
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            name="network_diag",
            category=ToolCategory.DIAGNOSTIC,
            description="Run network diagnostic collection",
            version="1.0.0",
            parameters={
                "detail_level": {"type": "string", "default": "standard"},
            },
            tags=["network", "diagnostic"],
            timeout_seconds=30,
            requires_confirmation=False,
            safe_mode=False,
        )
    
    def execute(self, params: dict[str, Any]) -> ToolResult:
        try:
            from src.diagnostics.network_sensor import collect
            
            result = collect({})
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                output=result,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )


class SystemDiagTool(BaseTool):
    """Tool specifically for system diagnostics."""
    
    @property
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            name="system_diag",
            category=ToolCategory.DIAGNOSTIC,
            description="Run system diagnostic collection",
            version="1.0.0",
            parameters={},
            tags=["system", "diagnostic"],
            timeout_seconds=30,
            requires_confirmation=False,
            safe_mode=False,
        )
    
    def execute(self, params: dict[str, Any]) -> ToolResult:
        import platform
        
        try:
            import psutil
            
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            
            result = {
                "platform": platform.system(),
                "cpu_percent": cpu,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                },
                "disk": {
                    "total": disk.total,
                    "free": disk.free,
                    "percent": disk.percent,
                },
            }
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                output=result,
            )
        except ImportError:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                output={"platform": platform.system()},
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )
