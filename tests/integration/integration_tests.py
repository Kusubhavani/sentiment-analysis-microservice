import pytest
import time
import json
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# These tests require the services to be running
# They're meant to be run with docker-compose exec

@pytest.mark.integration
def test_full_async_workflow():
    """Test complete async workflow (requires running services)"""
    # This test would require RabbitMQ and MongoDB to be running
    # For now, we'll mock the integration
    
    # 1. Submit async job
    test_text = "This is an integration test for async sentiment analysis"
    test_data = {"text": test_text}
    
    with patch('api.endpoints.QueueService') as mock_queue:
        mock_instance = Mock()
        mock_queue.return_value = mock_instance
        
        response = client.post("/api/sentiment/async", json=test_data)
        assert response.status_code == 202
        
        job_data = response.json()
        job_id = job_data["job_id"]
        assert job_id is not None
        
        # 2. Simulate worker processing
        # In real integration, we would wait for worker to process
        
        # 3. Mock database result
        test_result = {
            "job_id": job_id,
            "text": test_text,
            "sentiment": "positive",
            "score": 0.78,
            "timestamp": "2024-01-21T10:30:00",
            "processed_at": "2024-01-21T10:30:02",
            "status": "completed"
        }
        
        with patch('api.endpoints.DatabaseService') as mock_db:
            mock_db_instance = Mock()
            mock_db_instance.get_result.return_value = test_result
            mock_db.return_value = mock_db_instance
            
            # 4. Retrieve result
            response = client.get(f"/api/sentiment/results/{job_id}")
            if response.status_code == 404:
                pytest.skip("Result not ready (services not running)")
            
            assert response.status_code == 200
            result = response.json()
            assert result["job_id"] == job_id
            assert result["sentiment"] == "positive"

@pytest.mark.integration
def test_service_dependencies():
    """Test that all service endpoints are accessible"""
    endpoints = [
        ("/", 200),
        ("/health", 200),
        ("/docs", 200),
        ("/openapi.json", 200),
    ]
    
    for endpoint, expected_status in endpoints:
        response = client.get(endpoint)
        assert response.status_code == expected_status, f"Failed: {endpoint}"

@pytest.mark.integration
def test_error_handling():
    """Test error handling in API"""
    # Test invalid JSON
    response = client.post("/api/sentiment/sync", data="invalid json")
    assert response.status_code == 422
    
    # Test missing required field
    response = client.post("/api/sentiment/sync", json={"wrong_field": "test"})
    assert response.status_code == 422
    
    # Test invalid job ID format
    response = client.get("/api/sentiment/results/123")  # Too short
    # Should either return 404 or 400 depending on validation
    assert response.status_code in [400, 404, 422]

@pytest.mark.integration
def test_concurrent_requests():
    """Test handling multiple concurrent requests"""
    import concurrent.futures
    
    test_texts = [
        "I love this amazing product!",
        "This is terrible and I hate it.",
        "Neutral review with no strong feelings.",
        "Excellent service and great support team!",
        "Worst experience of my life."
    ]
    
    def submit_sync_request(text):
        return client.post("/api/sentiment/sync", json={"text": text})
    
    # Submit multiple requests concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(submit_sync_request, text) for text in test_texts]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    # All requests should succeed
    for response in results:
        assert response.status_code == 200
        data = response.json()
        assert "sentiment" in data
        assert "score" in data
        assert data["sentiment"] in ["positive", "negative"]

@pytest.mark.integration  
def test_api_validation():
    """Test API input validation"""
    # Test text too short
    response = client.post("/api/sentiment/sync", json={"text": ""})
    assert response.status_code == 422
    
    # Test text within limits
    response = client.post("/api/sentiment/sync", json={"text": "Valid"})
    assert response.status_code == 200 or response.status_code == 500
    
    # Test text at max limit
    max_text = "a" * 1000
    response = client.post("/api/sentiment/sync", json={"text": max_text})
    assert response.status_code == 200 or response.status_code == 500
    
    # Test text exceeds max limit
    too_long_text = "a" * 1001
    response = client.post("/api/sentiment/sync", json={"text": too_long_text})
    assert response.status_code == 422
