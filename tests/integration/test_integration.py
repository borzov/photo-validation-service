import pytest
import time
import requests
from PIL import Image
from io import BytesIO

class TestSystemIntegration:
    """Integration tests for the entire system."""
    
    @pytest.fixture(scope="class")
    def api_url(self):
        """URL for API testing."""
        return "http://localhost:8000"
    
    @pytest.fixture
    def test_image(self):
        """Create test image."""
        img = Image.new('RGB', (800, 600), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes.getvalue()
    
    def test_health_check(self, api_url):
        """Test system health check."""
        try:
            response = requests.get(f"{api_url}/health", timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["healthy", "unhealthy"]
        except requests.exceptions.RequestException:
            pytest.skip("API server not available for integration tests")
    
    def test_metrics_endpoints(self, api_url):
        """Test metrics endpoints."""
        try:
            # Basic metrics
            response = requests.get(f"{api_url}/metrics", timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert "uptime_seconds" in data
            
            # Detailed metrics
            response = requests.get(f"{api_url}/metrics/detailed", timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "metrics" in data
        except requests.exceptions.RequestException:
            pytest.skip("API server not available for integration tests")
    
    def test_full_validation_workflow(self, api_url, test_image):
        """Test complete validation workflow."""
        try:
            # Step 1: Submit image for validation
            files = {"file": ("test.jpg", test_image, "image/jpeg")}
            response = requests.post(f"{api_url}/api/v1/validate", files=files, timeout=30)
            assert response.status_code == 202
            
            request_data = response.json()
            assert "requestId" in request_data
            request_id = request_data["requestId"]
            
            # Step 2: Wait for processing completion
            max_attempts = 30
            for attempt in range(max_attempts):
                response = requests.get(f"{api_url}/api/v1/results/{request_id}", timeout=10)
                assert response.status_code == 200
                
                result_data = response.json()
                status = result_data["status"]
                
                if status in ["COMPLETED", "FAILED"]:
                    # Check response structure
                    assert "overallStatus" in result_data
                    assert "checks" in result_data
                    assert "issues" in result_data
                    
                    if status == "COMPLETED":
                        assert result_data["overallStatus"] in ["PASSED", "FAILED", "NEEDS_REVIEW", "REJECTED"]
                        assert isinstance(result_data["checks"], list)
                        assert isinstance(result_data["issues"], list)
                    
                    break
                elif status == "PROCESSING":
                    time.sleep(2)
                    continue
                else:
                    pytest.fail(f"Unexpected status: {status}")
            else:
                pytest.fail("Processing took too long")
                
        except requests.exceptions.RequestException:
            pytest.skip("API server not available for integration tests")
    
    def test_invalid_file_rejection(self, api_url):
        """Test invalid file rejection."""
        try:
            # Test with text file
            fake_content = b"This is not an image"
            files = {"file": ("test.txt", fake_content, "text/plain")}
            response = requests.post(f"{api_url}/api/v1/validate", files=files, timeout=10)
            assert response.status_code == 400
            
        except requests.exceptions.RequestException:
            pytest.skip("API server not available for integration tests")
    
    def test_nonexistent_result(self, api_url):
        """Test request for non-existent result."""
        try:
            response = requests.get(f"{api_url}/api/v1/results/nonexistent-id", timeout=10)
            assert response.status_code == 404
            
        except requests.exceptions.RequestException:
            pytest.skip("API server not available for integration tests")

class TestWorkerIntegration:
    """Tests for worker integration."""
    
    def test_worker_task_processing(self):
        """Test worker task processing."""
        # This test requires running worker
        # In real environment there would be worker task processing check
        pytest.skip("Worker integration tests require running worker process")
    
    def test_concurrent_processing(self):
        """Test concurrent processing of multiple tasks."""
        # This test requires full environment
        pytest.skip("Concurrent processing tests require full environment") 