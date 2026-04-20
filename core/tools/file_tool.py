"""File Tool for file system operations.

Provides safe file operations: read, write, list, and search.
"""
import os
from pathlib import Path
from typing import Any, List

from core.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDescriptor,
    ToolResult,
    ToolStatus,
)


class FileTool(BaseTool):
    """Tool for file system operations."""
    
    BLOCKED_EXTENSIONS = [".exe", ".dll", ".sys", ".bat", ".cmd", ".ps1"]
    BLOCKED_PATHS = ["/etc/passwd", "/etc/shadow", "C:\\Windows\\System32\\config\\"]
    
    @property
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            name="file",
            category=ToolCategory.FILE,
            description="Perform file system operations (read, write, list, search)",
            version="1.0.0",
            parameters={
                "operation": {"type": "string", "required": True, "enum": ["read", "write", "list", "search", "exists"]},
                "path": {"type": "string", "required": True},
                "content": {"type": "string", "required": False},
                "pattern": {"type": "string", "required": False},
            },
            tags=["file", " filesystem", "read", "write"],
            timeout_seconds=30,
            requires_confirmation=False,
            safe_mode=True,
        )
    
    def execute(self, params: dict[str, Any]) -> ToolResult:
        operation = params.get("operation", "list")
        path = params.get("path", "")
        
        if not path:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="No path provided",
            )
        
        try:
            if operation == "read":
                return self._read_file(path, params)
            elif operation == "write":
                return self._write_file(path, params)
            elif operation == "list":
                return self._list_directory(path, params)
            elif operation == "search":
                return self._search_files(path, params)
            elif operation == "exists":
                return self._check_exists(path)
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
    
    def _read_file(self, path: str, params: dict[str, Any]) -> ToolResult:
        try:
            file_path = Path(path).expanduser().resolve()
            
            if not file_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error="File does not exist",
                )
            
            if file_path.is_dir():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error="Path is a directory",
                )
            
            size = file_path.stat().st_size
            if size > 1024 * 1024:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"File too large: {size} bytes (max 1MB)",
                )
            
            encoding = params.get("encoding", "utf-8")
            content = file_path.read_text(encoding=encoding)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                output=content[:10000],
                metadata={"path": str(file_path), "size": size},
            )
        except UnicodeDecodeError:
            content = file_path.read_bytes()[:1000].hex()
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                output=f"[Binary data - hex]: {content}",
                metadata={"path": str(file_path), "encoding": "hex"},
            )
    
    def _write_file(self, path: str, params: dict[str, Any]) -> ToolResult:
        content = params.get("content", "")
        
        if not content:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="No content provided",
            )
        
        try:
            file_path = Path(path).expanduser().resolve()
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                output={"written": len(content), "path": str(file_path)},
                metadata={"path": str(file_path)},
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )
    
    def _list_directory(self, path: str, params: dict[str, Any]) -> ToolResult:
        try:
            dir_path = Path(path).expanduser().resolve()
            
            if not dir_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error="Directory does not exist",
                )
            
            if not dir_path.is_dir():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error="Path is not a directory",
                )
            
            max_items = params.get("max_items", 100)
            entries = []
            
            for item in dir_path.iterdir():
                try:
                    stat = item.stat()
                    entries.append({
                        "name": item.name,
                        "type": "dir" if item.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                    })
                except PermissionError:
                    continue
            
            entries.sort(key=lambda x: x["name"])
            entries = entries[:max_items]
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                output={"entries": entries, "count": len(entries)},
                metadata={"path": str(dir_path)},
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )
    
    def _search_files(self, path: str, params: dict[str, Any]) -> ToolResult:
        pattern = params.get("pattern", "*")
        
        try:
            dir_path = Path(path).expanduser().resolve()
            
            if not dir_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error="Directory does not exist",
                )
            
            max_results = params.get("max_results", 50)
            results = list(dir_path.rglob(pattern))[:max_results]
            
            files = []
            for item in results:
                try:
                    stat = item.stat()
                    files.append({
                        "path": str(item),
                        "type": "dir" if item.is_dir() else "file",
                        "size": stat.st_size,
                    })
                except PermissionError:
                    continue
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                output={"files": files, "count": len(files)},
                metadata={"path": str(dir_path), "pattern": pattern},
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )
    
    def _check_exists(self, path: str) -> ToolResult:
        file_path = Path(path).expanduser().resolve()
        
        return ToolResult(
            tool_name=self.name,
            status=ToolStatus.COMPLETED,
            output={"exists": file_path.exists(), "path": str(file_path)},
            metadata={"path": str(file_path)},
        )
    
    def check_safety(self, params: dict[str, Any]) -> tuple[bool, str | None]:
        path = params.get("path", "")
        
        for blocked in self.BLOCKED_PATHS:
            if blocked.lower() in path.lower():
                return False, f"Path is blocked: {blocked}"
        
        operation = params.get("operation", "list")
        if operation == "write":
            ext = os.path.splitext(path)[1].lower()
            if ext in self.BLOCKED_EXTENSIONS:
                return False, f"Extension {ext} is blocked for write"
        
        return True, None
    
    def validate(self, params: dict[str, Any]) -> tuple[bool, str | None]:
        if "path" not in params:
            return False, "path parameter is required"
        
        if "operation" not in params:
            return False, "operation parameter is required"
        
        valid_ops = ["read", "write", "list", "search", "exists"]
        if params.get("operation") not in valid_ops:
            return False, f"operation must be one of: {valid_ops}"
        
        return True, None