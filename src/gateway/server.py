"""Gateway Server.

Main server that wires together all input interfaces,
schedule manager, and agent.
"""
from pathlib import Path
from threading import Thread
from typing import Any, Optional

from src.utils.debug_log import debug_logger

from src.gateway.schedule_manager import ScheduleManager, create_schedule_manager
from src.gateway.payload_sender import PayloadSender, create_payload_sender
from src.gateway.interfaces.http_handler import GatewayHTTPServer, create_http_server
from src.gateway.interfaces.cli_handler import CLIHandler, create_cli_handler
from src.gateway.interfaces.queue_handler import QueueHandler, create_queue_handler
from src.gateway.interfaces.file_trigger import FileTrigger, create_file_trigger
from src.gateway.interfaces.websocket_handler import WebSocketHandler, create_websocket_handler


class Gateway:
    """Gateway Server for Phantom.
    
    Manages all input interfaces and schedules,
    sends payloads to agent for analysis.
    
    Interfaces:
    - HTTP API (port 8000)
    - CLI commands
    - Message queue (Redis/RabbitMQ)
    - File triggers
    - WebSocket (port 8001)
    """
    
    def __init__(
        self,
        agent: Optional[Any] = None,
        http_port: int = 8000,
        ws_port: int = 8001,
        autonomous: bool = True
    ):
        self.agent = agent
        self.http_port = http_port
        self.ws_port = ws_port
        self.autonomous = autonomous
        
        self.schedule_manager = create_schedule_manager()
        self.payload_sender = create_payload_sender()
        
        self.http_server = create_http_server(
            port=http_port,
            schedule_manager=self.schedule_manager,
            agent=agent
        )
        
        self.cli_handler = create_cli_handler(
            schedule_manager=self.schedule_manager,
            agent=agent
        )
        
        self.queue_handler = create_queue_handler(central_agent=central_agent)
        self.file_trigger = create_file_trigger(central_agent=central_agent)
        self.ws_handler = create_websocket_handler(
            port=ws_port,
            agent=agent
        )
        
        self._running = False
        
        debug_logger.info("Gateway initialized", {
            "http_port": http_port,
            "ws_port": ws_port,
            "autonomous": autonomous
        })
    
    def start(self) -> None:
        """Start all gateway components."""
        if self._running:
            return
        
        self._running = True
        
        if self.autonomous:
            self.schedule_manager.start_autonomous()
            debug_logger.info("Autonomous mode started")
        
        self.http_server.start()
        debug_logger.info("HTTP server started")
        
        try:
            self.queue_handler.start_consuming()
        except ImportError as e:
            debug_logger.info("Queue handler not available", {"error": str(e)})
        except Exception as e:
            debug_logger.warning("Queue handler connection failed", {"error": str(e)})
        
        self.file_trigger.start()
        debug_logger.info("File trigger started")
        
        try:
            self.ws_handler.start()
        except Exception as e:
            debug_logger.warning("WebSocket handler not started", {"error": str(e)})
        
        debug_logger.info("Gateway started successfully")
    
    def stop(self) -> None:
        """Stop all gateway components."""
        self._running = False
        
        self.schedule_manager.stop()
        self.http_server.stop()
        self.queue_handler.stop_consuming()
        self.file_trigger.stop()
        self.ws_handler.stop()
        
        debug_logger.info("Gateway stopped")
    
    def run_cli(self, args: list[str]) -> int:
        """Run CLI command.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code
        """
        return self.cli_handler.run_command(args)
    
    def get_status(self) -> dict:
        """Get gateway status."""
        return {
            "running": self._running,
            "autonomous": self.autonomous,
            "schedules": self.schedule_manager.get_all_schedules(),
            "connections": self.ws_handler.connection_count()
        }


def create_gateway(
    central_agent: Optional[Any] = None,
    http_port: int = 8000,
    ws_port: int = 8001,
    autonomous: bool = True
) -> Gateway:
    """Create Gateway with default settings.
    
    Returns:
        Configured Gateway instance
    """
    return Gateway(
        central_agent=central_agent,
        http_port=http_port,
        ws_port=ws_port,
        autonomous=autonomous
    )
