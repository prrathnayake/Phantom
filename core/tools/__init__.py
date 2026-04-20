"""Tools package initialization.

Registers all available tools.
"""
from core.tools.base import BaseTool, ToolCategory, ToolDescriptor, ToolResult, ToolStatus
from core.tools.registry import ToolRegistry, get_tool_registry
from core.tools.executor import ToolExecutor, get_tool_executor

__all__ = [
    "BaseTool",
    "ToolCategory",
    "ToolDescriptor", 
    "ToolResult",
    "ToolStatus",
    "ToolRegistry",
    "ToolExecutor",
    "get_tool_registry",
    "get_tool_executor",
]

registry = get_tool_registry()

from core.tools.shell_tool import ShellTool
from core.tools.file_tool import FileTool
from core.tools.process_tool import ProcessTool
from core.tools.diagnostic_tool import DiagnosticTool, NetworkDiagTool, SystemDiagTool

registry.register(ShellTool())
registry.register(FileTool())
registry.register(ProcessTool())
registry.register(DiagnosticTool())
registry.register(NetworkDiagTool())
registry.register(SystemDiagTool())