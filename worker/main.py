import json
import logging
import os
import time
import uuid
from datetime import datetime
from worker.services.model_service import ModelService
from worker.services.database_service import DatabaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SentimentWorker:
    def __init__(self):
        self.worker_id = str(uuid.uuid4())[:8]
        self.model_service = ModelService()
        self.db_service = DatabaseService()
        self.queue_name = "sentiment_analysis_queue"
        self.dlq_name = f"{self.queue_name}_dlq"
        self.setup_rabbitmq()
        
        # Metrics
        self.metrics = {
            "total_processed": 0,
            "total_failed": 0,
            "total_duplicates": 0,
            "start_time": time.time()
        }
        
        logger.info(f"Worker {self.worker_id} initialized")
    
    def setup_rabbitmq(self):
        """Setup RabbitMQ connection and channel with retry logic"""
        import pika
        import pika.exceptions
        
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.rabbitmq_port = int(os.getenv("RABBITMQ_PORT", 5672))
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
        self.rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "guest")
        
        max_retries = 5
        retry_delay = 5
        
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
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                
                # Declare exchange
                self.channel.exchange_declare(
                    exchange='sentiment_exchange',
                    exchange_type='direct',
                    durable=True
                )
                
                # Declare main queue
                self.channel.queue_declare(
                    queue=self.queue_name,
                    durable=True,
                    arguments={
                        'x-dead-letter-exchange': '',
                        'x-dead-letter-routing-key': self.dlq_name,
                        'x-max-priority': 10
                    }
                )
                
                # Bind queue to exchange
                self.channel.queue_bind(
                    exchange='sentiment_exchange',
                    queue=self.queue_name,
                    routing_key='sentiment.job'
                )
                
                # Declare DLQ
                self.channel.queue_declare(
                    queue=self.dlq_name,
                    durable=True
                )
                
                # Set QoS to prevent overloading
                self.channel.basic_qos(prefetch_count=1)
                
                logger.info(f"Worker {self.worker_id} connected to RabbitMQ (attempt {attempt + 1})")
                return
                
            except pika.exceptions.AMQPConnectionError as e:
                logger.warning(f"Worker {self.worker_id} failed to connect to RabbitMQ (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Worker {self.worker_id} max retries reached. Exiting...")
                    raise
    
    def process_message(self, ch, method, properties, body):
        """Process incoming message from queue"""
        message = None
        job_id = "unknown"
        
        try:
            message = json.loads(body)
            job_id = message.get("job_id", "unknown")
            text = message.get("text", "")
            timestamp_str = message.get("timestamp", datetime.now().isoformat())
            
            logger.info(f"Worker {self.worker_id} processing job: {job_id}")
            
            # Check for duplicate processing (idempotency)
            existing_result = self.db_service.get_result(job_id)
            if existing_result:
                logger.warning(f"Worker {self.worker_id} skipping duplicate job: {job_id}")
                self.metrics["total_duplicates"] += 1
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Perform sentiment analysis
            start_time = time.time()
            sentiment, score = self.model_service.predict(text)
            processing_time = time.time() - start_time
            
            # Create result document
            result = {
                "job_id": job_id,
                "text": text,
                "sentiment": sentiment,
                "score": float(score),
                "timestamp": timestamp_str,
                "processed_at": datetime.now().isoformat(),
                "worker_id": self.worker_id,
                "processing_time": processing_time,
                "status": "completed"
            }
            
            # Store result in MongoDB
            self.db_service.save_result(result)
            
            self.metrics["total_processed"] += 1
            logger.info(f"Worker {self.worker_id} completed job: {job_id} - {sentiment} ({score:.4f}) in {processing_time:.3f}s")
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except json.JSONDecodeError as e:
            logger.error(f"Worker {self.worker_id} invalid JSON for job {job_id}: {str(e)}")
            # Reject without requeue (send to DLQ)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            self.metrics["total_failed"] += 1
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id} error processing job {job_id}: {str(e)}")
            # Reject with requeue (retry)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            self.metrics["total_failed"] += 1
    
    def get_metrics(self):
        """Get worker metrics"""
        uptime = time.time() - self.metrics["start_time"]
        return {
            **self.metrics,
            "worker_id": self.worker_id,
            "uptime": uptime,
            "processing_rate": self.metrics["total_processed"] / uptime if uptime > 0 else 0
        }
    
    def start(self):
        """Start consuming messages from queue"""
        try:
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self.process_message,
                auto_ack=False,
                consumer_tag=f"worker_{self.worker_id}"
            )
            
            logger.info(f"Worker {self.worker_id} started. Waiting for messages...")
            logger.info(f"Metrics: {self.get_metrics()}")
            
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info(f"Worker {self.worker_id} shutting down...")
            metrics = self.get_metrics()
            logger.info(f"Final metrics: {metrics}")
            if self.connection and not self.connection.is_closed:
                self.connection.close()
        except Exception as e:
            logger.error(f"Worker {self.worker_id} error: {str(e)}")
            if self.connection and not self.connection.is_closed:
                self.connection.close()

if __name__ == "__main__":
    worker = SentimentWorker()
    worker.start()
