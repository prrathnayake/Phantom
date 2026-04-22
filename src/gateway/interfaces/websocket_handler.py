"""WebSocket Handler for Gateway.

Provides WebSocket for real-time updates.
"""
import json
import uuid
import asyncio
from datetime import datetime, timezone
from threading import Thread
from typing import Any, Callable, Dict, FrozenSet, Optional, Set

from src.utils.debug_log import debug_logger


class WebSocketHandler:
    """WebSocket handler for real-time Gateway updates.
    
    Provides WebSocket connections for real-time
    analysis updates and notifications.
    
    Attributes:
        host: Host to bind to
        port: Port to listen on
        agent: Agent instance
    """
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8001,
        agent: Optional[Any] = None
    ):
        self.host = host
        self.port = port
        self.agent = agent
        self._connections: Set[Any] = set()
        self._running = False
        self._server = None
        
        debug_logger.info("WebSocketHandler initialized", {
            "host": host,
            "port": port
        })
    
    def start(self) -> None:
        """Start WebSocket server."""
        try:
            import websockets
            self._running = True
            
            self._thread = Thread(
                target=self._run_server,
                args=(websockets,),
                daemon=True
            )
            self._thread.start()
            
            debug_logger.info("WebSocket started", {
                "host": self.host,
                "port": self.port
            })
        
        except ImportError:
            debug_logger.warning(
                "websockets library not installed",
                {"suggestion": "pip install websockets"}
            )
            self._running = False
    
    def stop(self) -> None:
        """Stop WebSocket server."""
        self._running = False
        
        if self._server:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._server.close())
                loop.close()
            except Exception as e:
                debug_logger.warning("WebSocket stop error", {"error": str(e)})
        
        debug_logger.info("WebSocket stopped")
    
    async def _run_server(self, websockets: Any) -> None:
        """Run WebSocket server."""
        async def handler(ws, path):
            await self._handle_connection(ws, path)
        
        self._server = await websockets.serve(
            handler,
            self.host,
            self.port
        )
        
        await self._server.ws_server.wait_closed()
    
    async def _handle_connection(self, ws: Any, path: str) -> None:
        """Handle WebSocket connection."""
        conn_id = str(uuid.uuid4())
        self._connections.add(ws)
        
        debug_logger.info("WebSocket connected", {"id": conn_id})
        
        try:
            async for message in ws:
                await self._process_message(message, ws)
        except Exception as e:
            debug_logger.error("Connection error", {"error": str(e)})
        finally:
            self._connections.discard(ws)
            debug_logger.info("WebSocket disconnected", {"id": conn_id})
    
    async def _process_message(self, message: str, ws: Any) -> None:
        """Process WebSocket message."""
        try:
            data = json.loads(message)
            
            session_id = data.get("session_id", str(uuid.uuid4()))
            action = data.get("action", "analyze")
            payload = data.get("payload", data)
            
            debug_logger.info("WS action", {
                "action": action,
                "session_id": session_id
            })
            
            if action == "analyze" and self.agent:
                result = self.agent.analyze(
                    payload=payload,
                    session_id=session_id,
                    trigger="websocket"
                )
                
                response = {
                    "type": "analysis_complete",
                    "session_id": session_id,
                    "risk_level": result.risk_level,
                    "timestamp": result.timestamp
                }
                
                await ws.send(json.dumps(response))
            
            elif action == "status":
                response = {
                    "type": "status",
                    "connections": len(self._connections),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await ws.send(json.dumps(response))
        
        except json.JSONDecodeError as e:
            error_response = {
                "type": "error",
                "error": "Invalid JSON",
                "details": str(e)
            }
            await ws.send(json.dumps(error_response))
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connections."""
        if not self._connections:
            return
        
        data = json.dumps(message)
        
        for ws in list(self._connections):
            try:
                await ws.send(data)
            except Exception:
                self._connections.discard(ws)
    
    async def send_to(
        self,
        session_id: str,
        message: Dict[str, Any]
    ) -> None:
        """Send message to specific session."""
        message["session_id"] = session_id
        await self.broadcast(message)
    
    def connection_count(self) -> int:
        """Get active connection count."""
        return len(self._connections)


def create_websocket_handler(
    host: str = "127.0.0.1",
    port: int = 8001,
    agent: Optional[Any] = None
) -> WebSocketHandler:
    """Create WebSocket handler.
    
    Returns:
        Configured WebSocketHandler instance
    """
    return WebSocketHandler(
        host=host,
        port=port,
        agent=agent
    )
