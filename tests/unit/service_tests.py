import pytest
import json
from unittest.mock import Mock, patch
from api.services.queue_service import QueueService
from api.services.database_service import DatabaseService
from worker.services.model_service import ModelService
from worker.services.database_service import DatabaseService as WorkerDatabaseService

def test_queue_service_initialization():
    """Test QueueService initialization"""
    with patch('pika.BlockingConnection') as mock_connection:
        queue_service = QueueService()
        assert queue_service.queue_name == "sentiment_analysis_queue"
        assert queue_service.rabbitmq_host == "rabbitmq"

def test_queue_service_publish_message():
    """Test publishing message to queue"""
    with patch('pika.BlockingConnection') as mock_connection:
        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel
        
        queue_service = QueueService()
        test_message = {"job_id": "test-123", "text": "Test message"}
        
        # Mock the private method
        with patch.object(queue_service, '_create_connection', return_value=mock_connection()):
            queue_service.publish_message(test_message)
            
        # Verify queue was declared
        mock_channel.queue_declare.assert_called()
        # Verify message was published
        mock_channel.basic_publish.assert_called()

def test_database_service_connection():
    """Test DatabaseService connection"""
    with patch('pymongo.MongoClient') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        mock_instance.admin.command.return_value = True
        
        db_service = DatabaseService()
        assert db_service.client is not None
        assert db_service.collection is not None

def test_database_service_get_result():
    """Test getting result from database"""
    with patch('pymongo.MongoClient') as mock_client:
        mock_instance = Mock()
        mock_collection = Mock()
        
        test_result = {
            "_id": "507f1f77bcf86cd799439011",
            "job_id": "test-123",
            "text": "Test text",
            "sentiment": "positive",
            "score": 0.85
        }
        
        mock_collection.find_one.return_value = test_result
        mock_instance.sentiment_db.sentiment_results = mock_collection
        mock_client.return_value = mock_instance
        
        db_service = DatabaseService()
        db_service.client = mock_instance
        db_service.collection = mock_collection
        
        result = db_service.get_result("test-123")
        assert result is not None
        assert result["job_id"] == "test-123"

def test_model_service_initialization():
    """Test ModelService initialization"""
    with patch('tensorflow.keras.models.load_model') as mock_load_model:
        with patch('os.path.exists', return_value=True):
            model_service = ModelService()
            assert model_service.model is not None
            assert model_service.tokenizer is not None

def test_model_service_predict():
    """Test sentiment prediction"""
    model_service = ModelService()
    
    # Test with positive text
    sentiment, score = model_service.predict("I love this amazing product!")
    assert sentiment in ["positive", "negative", "neutral"]
    assert 0 <= score <= 1
    
    # Test with negative text
    sentiment, score = model_service.predict("I hate this terrible product!")
    assert sentiment in ["positive", "negative", "neutral"]
    assert 0 <= score <= 1

def test_worker_database_service():
    """Test worker database service"""
    with patch('pymongo.MongoClient') as mock_client:
        mock_instance = Mock()
        mock_collection = Mock()
        
        mock_instance.sentiment_db.sentiment_results = mock_collection
        mock_client.return_value = mock_instance
        
        db_service = WorkerDatabaseService()
        db_service.client = mock_instance
        db_service.collection = mock_collection
        
        # Test save result
        test_result = {
            "job_id": "test-123",
            "text": "Test text",
            "sentiment": "positive",
            "score": 0.85
        }
        
        db_service.save_result(test_result)
        mock_collection.insert_one.assert_called_with(test_result)
        
        # Test get result
        mock_collection.find_one.return_value = test_result
        result = db_service.get_result("test-123")
        assert result["job_id"] == "test-123"

def test_queue_service_connection_check():
    """Test RabbitMQ connection check"""
    queue_service = QueueService()
    
    with patch.object(queue_service, '_create_connection') as mock_connection:
        mock_conn = Mock()
        mock_conn.is_closed = False
        mock_connection.return_value = mock_conn
        
        assert queue_service.check_connection() is True
        
        mock_connection.side_effect = Exception("Connection failed")
        assert queue_service.check_connection() is False

def test_database_service_connection_check():
    """Test MongoDB connection check"""
    db_service = DatabaseService()
    
    with patch.object(db_service.client.admin, 'command') as mock_command:
        mock_command.return_value = True
        assert db_service.check_connection() is True
        
        mock_command.side_effect = Exception("Connection failed")
        assert db_service.check_connection() is False
