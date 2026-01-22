import pika
import json
import logging
import os
from typing import Dict, Any
from pika.exceptions import AMQPConnectionError, AMQPError

logger = logging.getLogger(__name__)

class QueueService:
    def __init__(self):
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.rabbitmq_port = int(os.getenv("RABBITMQ_PORT", 5672))
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
        self.rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "guest")
        self.queue_name = "sentiment_analysis_queue"
        self.exchange_name = "sentiment_exchange"
        self.routing_key = "sentiment.job"
        
    def _create_connection(self):
        """Create RabbitMQ connection with retry logic"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                credentials = pika.PlainCredentials(self.rabbitmq_user, self.rabbitmq_password)
                parameters = pika.ConnectionParameters(
                    host=self.rabbitmq_host,
                    port=self.rabbitmq_port,
                    credentials=credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300,
                    connection_attempts=3,
                    retry_delay=5
                )
                connection = pika.BlockingConnection(parameters)
                logger.info(f"RabbitMQ connection established (attempt {attempt + 1})")
                return connection
                
            except AMQPConnectionError as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to connect to RabbitMQ after {max_retries} attempts: {str(e)}")
                    raise
                logger.warning(f"RabbitMQ connection failed (attempt {attempt + 1}): {str(e)}")
                import time
                time.sleep(retry_delay)
    
    def publish_message(self, message: Dict[str, Any]):
        """Publish message to RabbitMQ queue with durability"""
        connection = None
        try:
            connection = self._create_connection()
            channel = connection.channel()
            
            # Declare exchange
            channel.exchange_declare(
                exchange=self.exchange_name,
                exchange_type='direct',
                durable=True
            )
            
            # Declare queue with durability and DLQ support
            channel.queue_declare(
                queue=self.queue_name,
                durable=True,
                arguments={
                    'x-dead-letter-exchange': '',
                    'x-dead-letter-routing-key': f"{self.queue_name}_dlq",
                    'x-max-priority': 10
                }
            )
            
            # Bind queue to exchange
            channel.queue_bind(
                exchange=self.exchange_name,
                queue=self.queue_name,
                routing_key=self.routing_key
            )
            
            # Declare DLQ
            channel.queue_declare(
                queue=f"{self.queue_name}_dlq",
                durable=True
            )
            
            # Publish message with persistent delivery
            channel.basic_publish(
                exchange=self.exchange_name,
                routing_key=self.routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json',
                    priority=5
                )
            )
            
            logger.info(f"Message published to queue: {message.get('job_id', 'unknown')}")
            
        except AMQPError as e:
            logger.error(f"RabbitMQ error: {str(e)}")
            raise Exception(f"Failed to publish message to queue: {str(e)}")
        finally:
            if connection and not connection.is_closed:
                connection.close()
    
    def check_connection(self):
        """Check if RabbitMQ is reachable"""
        try:
            connection = self._create_connection()
            if connection and not connection.is_closed:
                connection.close()
                return True
            return False
        except Exception as e:
            logger.error(f"RabbitMQ connection check failed: {str(e)}")
            return False
