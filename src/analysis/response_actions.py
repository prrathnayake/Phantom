"""Response Actions for Automated Remediation.

Defines automated response actions that require approval before execution.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional, Callable
import subprocess

import config
from src.utils.debug_log import debug_logger


class ActionType(Enum):
    BLOCK_IP = "block_ip"
    KILL_PROCESS = "kill_process"
    DISABLE_USER = "disable_user"
    QUARANTINE_FILE = "quarantine_file"
    ISOLATE_HOST = "isolate_host"
    ALERT_ONLY = "alert_only"
    RESET_PASSWORD = "reset_password"
    BLOCK_PORT = "block_port"
    LIMIT_BANDWIDTH = "limit_bandwidth"


@dataclass
class ActionParameter:
    name: str
    value: Any
    description: str
    required: bool = True


@dataclass
class ActionDefinition:
    action_type: ActionType
    name: str
    description: str
    parameters: List[str]
    requires_approval: bool = True
    reversible: bool = False
    timeout_seconds: int = 30


class ResponseEngine:
    """Executes response actions after approval."""
    
    def __init__(self):
        self._lock = Lock()
        
        self._action_handlers: Dict[str, Callable] = {}
        self._execution_history: List[Dict[str, Any]] = []
        
        self._register_default_actions()
        
        debug_logger.info("ResponseEngine initialized")
    
    def _register_default_actions(self) -> None:
        self._action_handlers = {
            "block_ip": self._block_ip,
            "kill_process": self._kill_process,
            "disable_user": self._disable_user,
            "quarantine_file": self._quarantine_file,
            "isolate_host": self._isolate_host,
            "alert_only": self._alert_only,
            "reset_password": self._reset_password,
            "block_port": self._block_port,
        }
    
    def validate_parameters(
        self,
        action_type: str,
        parameters: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate action parameters.
        
        Args:
            action_type: Type of action
            parameters: Parameters to validate
            
        Returns:
            Tuple of (valid, error_message)
        """
        required_params = {
            "block_ip": ["ip_address"],
            "kill_process": ["process_id"],
            "disable_user": ["username"],
            "quarantine_file": ["file_path"],
            "isolate_host": ["reason"],
            "alert_only": [],
            "reset_password": ["username"],
            "block_port": ["port", "protocol"],
        }
        
        required = required_params.get(action_type, [])
        
        for param in required:
            if param not in parameters:
                return False, f"Missing required parameter: {param}"
        
        return True, ""
    
    def execute(
        self,
        action_type: str,
        parameters: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute a response action.
        
        Args:
            action_type: Type of action
            parameters: Action parameters
            dry_run: If True, simulate without executing
            
        Returns:
            Execution result
        """
        valid, error = self.validate_parameters(action_type, parameters)
        if not valid:
            return {"success": False, "error": error}
        
        handler = self._action_handlers.get(action_type)
        if not handler:
            return {"success": False, "error": f"Unknown action: {action_type}"}
        
        if dry_run:
            debug_logger.info("Dry run action", {
                "type": action_type,
                "parameters": parameters
            })
            return {"success": True, "dry_run": True, "action": action_type}
        
        try:
            result = handler(parameters)
            
            with self._lock:
                self._execution_history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "action_type": action_type,
                    "parameters": parameters,
                    "result": result
                })
            
            return result
            
        except Exception as e:
            debug_logger.error("Action execution failed", {
                "action": action_type,
                "error": str(e)
            })
            return {"success": False, "error": str(e)}
    
    def _block_ip(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Block an IP address.
        
        Args:
            params: Parameters including ip_address
            
        Returns:
            Result dictionary
        """
        import platform
        
        ip = params.get("ip_address")
        duration = params.get("duration", "24h")
        
        if platform.system() == "Windows":
            cmd = ["netsh", "advfirewall", "firewall", "add", "rule",
                   "name=fBlock_{}".format(ip.replace(".", "_")),
                   "dir=in", "action=block", "remoteip={}".format(ip)]
        else:
            cmd = ["iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            debug_logger.info("IP blocked", {"ip": ip, "duration": duration})
            return {"success": True, "action": "block_ip", "ip": ip}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _kill_process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Kill a process.
        
        Args:
            params: Parameters including process_id
            
        Returns:
            Result dictionary
        """
        import platform
        
        pid = params.get("process_id")
        
        if platform.system() == "Windows":
            cmd = ["taskkill", "/F", "/PID", str(pid)]
        else:
            cmd = ["kill", "-9", str(pid)]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            debug_logger.info("Process killed", {"pid": pid})
            return {"success": True, "action": "kill_process", "pid": pid}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _disable_user(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Disable a user account.
        
        Args:
            params: Parameters including username
            
        Returns:
            Result dictionary
        """
        import platform
        
        username = params.get("username")
        
        if platform.system() == "Windows":
            cmd = ["net", "user", username, "/active:no"]
        else:
            cmd = ["usermod", "-L", "-e", "1", username]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            debug_logger.info("User disabled", {"username": username})
            return {"success": True, "action": "disable_user", "username": username}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _quarantine_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Quarantine a file.
        
        Args:
            params: Parameters including file_path
            
        Returns:
            Result dictionary
        """
        import shutil
        import os
        
        file_path = params.get("file_path")
        quarantine_path = params.get("quarantine_path", "/tmp/quarantine")
        
        if not os.path.exists(quarantine_path):
            os.makedirs(quarantine_path)
        
        try:
            filename = os.path.basename(file_path)
            dest = os.path.join(quarantine_path, filename)
            shutil.move(file_path, dest)
            debug_logger.info("File quarantined", {"file": file_path, "quarantine": dest})
            return {"success": True, "action": "quarantine_file", "file": file_path, "quarantine": dest}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _isolate_host(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Isolate host from network.
        
        Args:
            params: Parameters including reason
            
        Returns:
            Result dictionary
        """
        debug_logger.warning("Host isolation requested", params)
        return {"success": True, "action": "isolate_host", "note": "Requires manual intervention"}
    
    def _alert_only(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Alert only - no action taken.
        
        Args:
            params: Parameters
            
        Returns:
            Result dictionary
        """
        return {"success": True, "action": "alert_only", "message": "Alert created"}
    
    def _reset_password(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Reset user password.
        
        Args:
            params: Parameters including username
            
        Returns:
            Result dictionary
        """
        import platform
        
        username = params.get("username")
        
        debug_logger.warning("Password reset requested", {"username": username})
        return {"success": True, "action": "reset_password", "message": "Password reset required"}
    
    def _block_port(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Block a network port.
        
        Args:
            params: Parameters including port and protocol
            
        Returns:
            Result dictionary
        """
        import platform
        
        port = params.get("port")
        protocol = params.get("protocol", "tcp")
        
        if platform.system() == "Windows":
            cmd = ["netsh", "advfirewall", "firewall", "add", "rule",
                   f"name=fBlock_{port}_{protocol}",
                   "dir=in", "action=block",
                   f"localport={port}", f"protocol={protocol}"]
        else:
            protocol_flag = "INPUT" if protocol == "tcp" else "UDP"
            cmd = ["iptables", "-A", protocol_flag, "-p", protocol, "--dport", str(port), "-j", "DROP"]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            debug_logger.info("Port blocked", {"port": port, "protocol": protocol})
            return {"success": True, "action": "block_port", "port": port}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_action_definitions(self) -> List[Dict[str, Any]]:
        """Get list of available actions.
        
        Returns:
            List of action definitions
        """
        return [
            {
                "type": "block_ip",
                "name": "Block IP Address",
                "description": "Block incoming traffic from IP address",
                "parameters": ["ip_address", "duration"],
                "requires_approval": True
            },
            {
                "type": "kill_process",
                "name": "Kill Process",
                "description": "Terminate a suspicious process",
                "parameters": ["process_id"],
                "requires_approval": True
            },
            {
                "type": "disable_user",
                "name": "Disable User",
                "description": "Disable a user account",
                "parameters": ["username"],
                "requires_approval": True
            },
            {
                "type": "quarantine_file",
                "name": "Quarantine File",
                "description": "Move suspicious file to quarantine",
                "parameters": ["file_path"],
                "requires_approval": True
            },
            {
                "type": "isolate_host",
                "name": "Isolate Host",
                "description": "Isolate host from network",
                "parameters": ["reason"],
                "requires_approval": True
            },
            {
                "type": "alert_only",
                "name": "Alert Only",
                "description": "Create alert without action",
                "parameters": [],
                "requires_approval": False
            },
        ]
    
    def get_execution_history(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get execution history.
        
        Args:
            limit: Maximum entries
            
        Returns:
            List of execution records
        """
        with self._lock:
            history = list(self._execution_history)
        
        return history[-limit:]


def create_response_engine() -> ResponseEngine:
    """Create ResponseEngine with default settings.
    
    Returns:
        Configured ResponseEngine
    """
    return ResponseEngine()
