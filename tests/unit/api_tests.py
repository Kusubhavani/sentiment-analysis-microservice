import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from api.main import app

client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "timestamp" in data

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data
    assert "endpoints" in data

def test_sync_sentiment_analysis():
    """Test synchronous sentiment analysis endpoint"""
    test_data = {"text": "I love this product! It's amazing."}
    
    with patch('api.endpoints.load_sync_model') as mock_model:
        mock_service = Mock()
        mock_service.predict.return_value = ("positive", 0.92)
        mock_model.return_value = mock_service
        
        response = client.post("/api/sentiment/sync", json=test_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == test_data["text"][:100] + "..."
        assert data["sentiment"] == "positive"
        assert data["score"] == 0.92
        assert "processing_time" in data

def test_sync_sentiment_empty_text():
    """Test sync endpoint with empty text"""
    test_data = {"text": ""}
    response = client.post("/api/sentiment/sync", json=test_data)
    assert response.status_code == 422  # Validation error

def test_sync_sentiment_long_text():
    """Test sync endpoint with very long text"""
    test_data = {"text": "a" * 1001}  # Exceeds max length
    response = client.post("/api/sentiment/sync", json=test_data)
    assert response.status_code == 422  # Validation error

def test_async_sentiment_analysis():
    """Test asynchronous sentiment analysis endpoint"""
    test_data = {"text": "This is a test message for async processing"}
    
    with patch('api.endpoints.QueueService') as mock_queue:
        mock_instance = Mock()
        mock_queue.return_value = mock_instance
        
        response = client.post("/api/sentiment/async", json=test_data)
        
        assert response.status_code == 202  # Accepted
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "processing"
        assert "message" in data
        assert "timestamp" in data

def test_get_result_not_found():
    """Test getting non-existent result"""
    with patch('api.endpoints.DatabaseService') as mock_db:
        mock_instance = Mock()
        mock_instance.get_result.return_value = None
        mock_db.return_value = mock_instance
        
        response = client.get("/api/sentiment/results/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

def test_get_result_found():
    """Test getting existing result"""
    test_result = {
        "job_id": "test-id-123",
        "text": "Test text",
        "sentiment": "positive",
        "score": 0.85,
        "timestamp": "2024-01-21T10:30:00",
        "processed_at": "2024-01-21T10:30:02",
        "status": "completed"
    }
    
    with patch('api.endpoints.DatabaseService') as mock_db:
        mock_instance = Mock()
        mock_instance.get_result.return_value = test_result
        mock_db.return_value = mock_instance
        
        response = client.get("/api/sentiment/results/test-id-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "test-id-123"
        assert data["sentiment"] == "positive"
        assert "processing_time" in data

def test_api_docs_available():
    """Test that API documentation is available"""
    response = client.get("/docs")
    assert response.status_code == 200
    
    response = client.get("/openapi.json")
    assert response.status_code == 200
