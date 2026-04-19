"""Queue Handler for Gateway.

Provides message queue consumer (Redis/RabbitMQ).
"""
import json
import uuid
from datetime import datetime
from threading import Thread
from typing import Any, Callable, Dict, List, Optional

from utils.debug_log import debug_logger


class QueueHandler:
    """Queue consumer for Gateway.
    
    Supports Redis and RabbitMQ for message queuing.
    Receives payloads and forwards to analysis.
    
    Attributes:
        queue_type: Type of queue (redis/rabbitmq)
        queue_url: Queue connection URL
        central_agent: CentralAgent instance
    """
    
    def __init__(
        self,
        queue_type: str = "redis",
        queue_url: str = "redis://localhost:6379",
        queue_name: str = "suraksha:payloads",
        central_agent: Optional[Any] = None
    ):
        self.queue_type = queue_type
        self.queue_url = queue_url
        self.queue_name = queue_name
        self.central_agent = central_agent
        self._running = False
        self._thread = None
        self._client = None
        
        debug_logger.info("QueueHandler initialized", {
            "type": queue_type,
            "queue": queue_name
        })
    
    def connect(self) -> bool:
        """Connect to queue.
        
        Returns:
            True if connected
        """
        try:
            if self.queue_type == "redis":
                return self._connect_redis()
            elif self.queue_type == "rabbitmq":
                return self._connect_rabbitmq()
            else:
                debug_logger.error("Unknown queue type", {"type": self.queue_type})
                return False
        except ImportError:
            debug_logger.warning(
                f"Queue client not installed: {self.queue_type}",
                {"suggestion": f"pip install {self.queue_type}"}
            )
            return False
    
    def _connect_redis(self) -> bool:
        """Connect to Redis."""
        try:
            import redis
            self._client = redis.from_url(self.queue_url)
            self._client.ping()
            debug_logger.info("Connected to Redis")
            return True
        except Exception as e:
            debug_logger.error("Redis connection failed", {"error": str(e)})
            return False
    
    def _connect_rabbitmq(self) -> bool:
        """Connect to RabbitMQ."""
        try:
            import pika
            params = pika.URLParameters(self.queue_url)
            self._client = pika.BlockingConnection(params)
            self._channel = self._client.channel()
            self._channel.queue_declare(queue=self.queue_name, durable=True)
            debug_logger.info("Connected to RabbitMQ")
            return True
        except Exception as e:
            debug_logger.error("RabbitMQ connection failed", {"error": str(e)})
            return False
    
    def start_consuming(self) -> None:
        """Start consuming messages."""
        self._running = True
        
        if self.connect():
            self._thread = Thread(target=self._consume_loop, daemon=True)
            self._thread.start()
            
            debug_logger.info("Message consuming started")
        else:
            debug_logger.warning("Queue not connected - running in mock mode")
            self._running = False
    
    def stop_consuming(self) -> None:
        """Stop consuming messages."""
        self._running = False
        
        if self._client and self.queue_type == "rabbitmq":
            try:
                self._client.close()
            except Exception:
                pass
        
        debug_logger.info("Message consuming stopped")
    
    def _consume_loop(self) -> None:
        """Consume messages from queue."""
        if self.queue_type == "redis":
            self._consume_redis()
        elif self.queue_type == "rabbitmq":
            self._consume_rabbitmq()
    
    def _consume_redis(self) -> None:
        """Consume from Redis."""
        while self._running:
            try:
                message = self._client.blpop(self.queue_name, timeout=1)
                
                if message:
                    _, data = message
                    self._process_message(data)
            except Exception as e:
                debug_logger.error("Redis consume error", {"error": str(e)})
                break
    
    def _consume_rabbitmq(self) -> None:
        """Consume from RabbitMQ."""
        def callback(ch, method, properties, body):
            self._process_message(body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        
        self._channel.basic_qos(prefetch_count=1)
        self._channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=callback
        )
        self._channel.start_consuming()
    
    def _process_message(self, data: bytes) -> None:
        """Process queue message."""
        try:
            message = json.loads(data)
            
            session_id = message.get("session_id", str(uuid.uuid4()))
            payload = message.get("payload", message)
            trigger = message.get("trigger", "queue")
            
            debug_logger.info("Processing message", {
                "session_id": session_id,
                "trigger": trigger
            })
            
            if self.central_agent:
                result = self.central_agent.analyze(
                    payload=payload,
                    session_id=session_id,
                    trigger=trigger
                )
                
                debug_logger.info("Analysis complete", {
                    "session_id": session_id,
                    "risk_level": result.risk_level
                })
            else:
                debug_logger.warning("No central agent configured")
        
        except json.JSONDecodeError as e:
            debug_logger.error("Invalid message JSON", {"error": str(e)})
        except Exception as e:
            debug_logger.error("Message processing error", {"error": str(e)})
    
    def publish(
        self,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
        trigger: str = "schedule"
    ) -> bool:
        """Publish message to queue.
        
        Args:
            payload: Payload to publish
            session_id: Optional session ID
            trigger: What triggered this publish
            
        Returns:
            True if published
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        message = {
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "trigger": trigger,
            "payload": payload
        }
        
        try:
            if self.queue_type == "redis":
                self._client.rpush(self.queue_name, json.dumps(message))
            elif self.queue_type == "rabbitmq":
                self._channel.basic_publish(
                    "",
                    routing_key=self.queue_name,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=2
                    )
                )
            
            debug_logger.info("Message published", {"session_id": session_id})
            return True
        
        except Exception as e:
            debug_logger.error("Publish failed", {"error": str(e)})
            return False


def create_queue_handler(
    queue_type: str = "redis",
    queue_url: str = "redis://localhost:6379",
    queue_name: str = "suraksha:payloads",
    central_agent: Optional[Any] = None
) -> QueueHandler:
    """Create queue handler.
    
    Returns:
        Configured QueueHandler instance
    """
    return QueueHandler(
        queue_type=queue_type,
        queue_url=queue_url,
        queue_name=queue_name,
        central_agent=central_agent
    )