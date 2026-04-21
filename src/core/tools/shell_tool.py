"""Shell Tool for executing shell commands.

Provides safe shell command execution with validation and security checks.
"""
import subprocess
from typing import Any, List

from src.core.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDescriptor,
    ToolResult,
    ToolStatus,
)


class ShellTool(BaseTool):
    """Tool for executing shell commands safely."""
    
    BLOCKED_COMMANDS = [
        "rm -rf",
        "del /f /s /q",
        "format",
        "diskpart",
        "fdisk",
        "shutdown",
        "reboot",
        "> /dev/null",
        "> nul",
    ]
    
    @property
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            name="shell",
            category=ToolCategory.SHELL,
            description="Execute shell commands on the system",
            version="1.0.0",
            parameters={
                "command": {"type": "string", "required": True},
                "timeout": {"type": "integer", "default": 30},
                "cwd": {"type": "string", "required": False},
            },
            tags=["shell", "command", "execute"],
            timeout_seconds=30,
            requires_confirmation=True,
            safe_mode=True,
        )
    
    def execute(self, params: dict[str, Any]) -> ToolResult:
        command = params.get("command", "")
        timeout = params.get("timeout", 30)
        cwd = params.get("cwd")
        
        if not command:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="No command provided",
            )
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                output={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                },
                metadata={
                    "command": command,
                    "timeout": timeout,
                },
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.TIMEOUT,
                error=f"Command timed out after {timeout}s",
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )
    
    def check_safety(self, params: dict[str, Any]) -> tuple[bool, str | None]:
        command = params.get("command", "").lower()
        
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command:
                return False, f"Command contains blocked pattern: {blocked}"
        
        if command.strip().startswith("shutdown"):
            return False, "shutdown commands are blocked"
        
        return True, None
    
    def validate(self, params: dict[str, Any]) -> tuple[bool, str | None]:
        if "command" not in params:
            return False, "command parameter is required"
        
        return True, None
