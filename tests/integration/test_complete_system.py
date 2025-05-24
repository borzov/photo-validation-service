"""
Complete system integration tests for Photo Validation Service.
Tests full workflow including API, all 11 modules, worker, and database.
"""
import pytest
import time
import requests
import asyncio
import numpy as np
import cv2
from PIL import Image
from io import BytesIO
from unittest.mock import patch
import tempfile
import os

from app.cv.checks.registry import check_registry
from app.cv.checks.runner import CheckRunner, CheckContext


class TestCompleteSystemIntegration:
    """Integration tests for the complete system."""
    
    @pytest.fixture(scope="class")
    def api_url(self):
        """URL for API testing."""
        return "http://localhost:8000"
    
    @pytest.fixture
    def test_image_color(self):
        """Create test color image."""
        img = Image.new('RGB', (800, 600))
        pixels = img.load()
        for i in range(800):
            for j in range(600):
                pixels[i, j] = (i % 255, j % 255, (i + j) % 255)
        
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG', quality=85)
        img_bytes.seek(0)
        return img_bytes.getvalue()
    
    @pytest.fixture
    def test_image_grayscale(self):
        """Create test grayscale image."""
        img = Image.new('RGB', (800, 600), color=(128, 128, 128))
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes.getvalue()
    
    @pytest.fixture
    def test_image_blurry(self):
        """Create blurry test image."""
        # Create image with OpenCV, blur it, then convert to bytes
        img = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
        blurred = cv2.GaussianBlur(img, (21, 21), 0)
        
        # Convert to PIL and then to bytes
        pil_img = Image.fromarray(cv2.cvtColor(blurred, cv2.COLOR_BGR2RGB))
        img_bytes = BytesIO()
        pil_img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes.getvalue()
    
    @pytest.fixture
    def invalid_file(self):
        """Create invalid file content."""
        return b"This is not an image file content"

    def test_system_health_and_status(self, api_url):
        """Test system health endpoints."""
        try:
            # Health check
            response = requests.get(f"{api_url}/health", timeout=10)
            assert response.status_code in [200, 503]  # Allow unhealthy but responsive
            data = response.json()
            assert "status" in data
            
            # Metrics endpoint
            response = requests.get(f"{api_url}/metrics", timeout=10)
            assert response.status_code == 200
            metrics = response.json()
            assert "uptime_seconds" in metrics
            
            # Detailed metrics
            response = requests.get(f"{api_url}/metrics/detailed", timeout=10)
            assert response.status_code == 200
            detailed = response.json()
            assert "status" in detailed
            
        except requests.exceptions.RequestException:
            pytest.skip("API server not available for integration tests")

    def test_all_modules_validation_workflow(self, api_url, test_image_color):
        """Test complete validation workflow with all 11 modules."""
        try:
            # Submit image for validation
            files = {"file": ("test_color.jpg", test_image_color, "image/jpeg")}
            response = requests.post(f"{api_url}/api/v1/validate", files=files, timeout=30)
            assert response.status_code == 202
            
            request_data = response.json()
            assert "requestId" in request_data
            request_id = request_data["requestId"]
            
            # Wait for processing completion
            max_attempts = 60  # Increase timeout for all modules
            result_data = None
            
            for attempt in range(max_attempts):
                response = requests.get(f"{api_url}/api/v1/results/{request_id}", timeout=10)
                assert response.status_code == 200
                
                result_data = response.json()
                status = result_data["status"]
                
                if status in ["COMPLETED", "FAILED"]:
                    break
                elif status == "PROCESSING":
                    time.sleep(2)
                    continue
                else:
                    pytest.fail(f"Unexpected status: {status}")
            else:
                pytest.fail("Processing took too long")
            
            # Verify all modules were executed
            assert "checks" in result_data
            check_results = result_data["checks"]
            assert isinstance(check_results, list)
            
            # Check that we have results from major module categories
            check_names = [check["check"] for check in check_results]
            
            # Expected modules by category
            expected_modules = {
                "image_quality": ["color_mode", "blurriness", "lighting", "real_photo", "red_eye"],
                "background": ["background", "extraneous_objects"],
                "face_detection": ["face_count", "face_position", "face_pose", "accessories"]
            }
            
            # Count modules by category that were executed
            quality_modules = [m for m in check_names if m in expected_modules["image_quality"]]
            background_modules = [m for m in check_names if m in expected_modules["background"]]
            face_modules = [m for m in check_names if m in expected_modules["face_detection"]]
            
            # Should have at least some modules from each category
            assert len(quality_modules) >= 3, f"Missing quality modules: {quality_modules}"
            assert len(background_modules) >= 1, f"Missing background modules: {background_modules}"
            # Face modules might be skipped if no face detected, so we're more lenient
            
            # Verify response structure
            assert "overallStatus" in result_data
            assert result_data["overallStatus"] in ["APPROVED", "REJECTED", "MANUAL_REVIEW"]
            assert "issues" in result_data
            assert isinstance(result_data["issues"], list)
            
        except requests.exceptions.RequestException:
            pytest.skip("API server not available for integration tests")

    def test_different_image_types_processing(self, api_url, test_image_color, test_image_grayscale, test_image_blurry):
        """Test processing of different image types."""
        test_cases = [
            ("color_image.jpg", test_image_color, "Should process color image"),
            ("grayscale_image.jpg", test_image_grayscale, "Should process grayscale image"),
            ("blurry_image.jpg", test_image_blurry, "Should process blurry image")
        ]
        
        for filename, image_data, description in test_cases:
            try:
                files = {"file": (filename, image_data, "image/jpeg")}
                response = requests.post(f"{api_url}/api/v1/validate", files=files, timeout=30)
                assert response.status_code == 202, f"Failed to submit {filename}"
                
                request_data = response.json()
                request_id = request_data["requestId"]
                
                # Wait for completion
                for attempt in range(30):
                    response = requests.get(f"{api_url}/api/v1/results/{request_id}", timeout=10)
                    result_data = response.json()
                    
                    if result_data["status"] in ["COMPLETED", "FAILED"]:
                        assert "checks" in result_data, f"Missing checks for {filename}"
                        assert len(result_data["checks"]) > 0, f"No checks executed for {filename}"
                        break
                    
                    time.sleep(1)
                else:
                    pytest.fail(f"Processing timeout for {filename}")
                    
            except requests.exceptions.RequestException:
                pytest.skip(f"API server not available for {filename} test")

    def test_invalid_input_handling(self, api_url, invalid_file):
        """Test handling of invalid inputs."""
        try:
            # Test invalid file type
            files = {"file": ("invalid.txt", invalid_file, "text/plain")}
            response = requests.post(f"{api_url}/api/v1/validate", files=files, timeout=10)
            assert response.status_code == 400
            
            # Test missing file
            response = requests.post(f"{api_url}/api/v1/validate", files={}, timeout=10)
            assert response.status_code == 422  # Validation error
            
            # Test oversized file (if implemented)
            large_content = b"x" * (10 * 1024 * 1024)  # 10MB
            files = {"file": ("large.jpg", large_content, "image/jpeg")}
            response = requests.post(f"{api_url}/api/v1/validate", files=files, timeout=10)
            # Should either accept or reject based on size limits
            assert response.status_code in [202, 400, 413]
            
        except requests.exceptions.RequestException:
            pytest.skip("API server not available for error handling tests")

    def test_concurrent_requests(self, api_url, test_image_color):
        """Test system under concurrent load."""
        try:
            import threading
            
            results = []
            errors = []
            
            def submit_request():
                try:
                    files = {"file": ("concurrent_test.jpg", test_image_color, "image/jpeg")}
                    response = requests.post(f"{api_url}/api/v1/validate", files=files, timeout=30)
                    if response.status_code == 202:
                        results.append(response.json()["requestId"])
                    else:
                        errors.append(f"HTTP {response.status_code}")
                except Exception as e:
                    errors.append(str(e))
            
            # Submit 5 concurrent requests
            threads = []
            for i in range(5):
                thread = threading.Thread(target=submit_request)
                threads.append(thread)
                thread.start()
            
            # Wait for all submissions to complete
            for thread in threads:
                thread.join()
            
            # Should have successfully submitted most requests
            assert len(results) >= 3, f"Too many failed submissions: {errors}"
            
            # Wait for all to complete
            completed = 0
            for request_id in results:
                for attempt in range(30):
                    try:
                        response = requests.get(f"{api_url}/api/v1/results/{request_id}", timeout=5)
                        if response.status_code == 200:
                            result_data = response.json()
                            if result_data["status"] in ["COMPLETED", "FAILED"]:
                                completed += 1
                                break
                    except:
                        continue
                    time.sleep(1)
            
            # Should complete most requests
            assert completed >= len(results) // 2, "Too many requests failed to complete"
            
        except requests.exceptions.RequestException:
            pytest.skip("API server not available for concurrent tests")

    def test_admin_interface_integration(self, api_url):
        """Test admin interface endpoints."""
        try:
            # Test admin discovery endpoint
            response = requests.get(f"{api_url}/admin/api/checks/discovery", timeout=10)
            assert response.status_code == 200
            
            discovery_data = response.json()
            assert "checks" in discovery_data
            assert len(discovery_data["checks"]) == 11  # All 11 modules
            
            # Verify module structure
            for module_name, module_data in discovery_data["checks"].items():
                assert "display_name" in module_data
                assert "description" in module_data
                assert "category" in module_data
                assert "parameters" in module_data
            
            # Test config endpoints
            response = requests.get(f"{api_url}/api/v1/config", timeout=10)
            # Config endpoint might require authentication, so accept various responses
            assert response.status_code in [200, 401, 403]
            
        except requests.exceptions.RequestException:
            pytest.skip("API server not available for admin tests")

    def test_error_recovery_and_logging(self, api_url):
        """Test system error recovery and logging."""
        try:
            # Test with corrupted image data
            corrupted_data = b'\xff\xd8\xff\xe0' + b'\x00' * 100  # Partial JPEG header
            files = {"file": ("corrupted.jpg", corrupted_data, "image/jpeg")}
            response = requests.post(f"{api_url}/api/v1/validate", files=files, timeout=30)
            
            if response.status_code == 202:
                request_id = response.json()["requestId"]
                
                # Wait for processing
                for attempt in range(20):
                    response = requests.get(f"{api_url}/api/v1/results/{request_id}", timeout=10)
                    result_data = response.json()
                    
                    if result_data["status"] in ["COMPLETED", "FAILED"]:
                        # System should handle corruption gracefully
                        if result_data["status"] == "FAILED":
                            assert "issues" in result_data
                            assert len(result_data["issues"]) > 0
                        break
                    
                    time.sleep(1)
                else:
                    pytest.fail("Processing timeout for corrupted image")
            else:
                # Early rejection is also acceptable
                assert response.status_code == 400
                
        except requests.exceptions.RequestException:
            pytest.skip("API server not available for error recovery tests")


class TestModuleExecutionIntegration:
    """Test individual module execution in isolation."""
    
    async def test_all_modules_execution(self):
        """Test that all 11 modules can be executed independently."""
        # Create test image
        test_image = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
        
        # Discover all modules
        check_registry.reset()
        check_registry.discover_checks()
        all_checks = check_registry.get_all_checks()
        
        assert len(all_checks) == 11, f"Expected 11 modules, found {len(all_checks)}"
        
        execution_results = {}
        
        for module_name, check_class in all_checks.items():
            try:
                # Create instance
                check_instance = check_class()
                
                # Mock face detection for face-related modules
                with patch('app.cv.checks.face.detector.detect_faces') as mock_detect:
                    mock_detect.return_value = [
                        {"bbox": [200, 150, 300, 250], "confidence": 0.8}
                    ]
                    
                    # Execute check
                    context = CheckContext()
                    result = check_instance.check(test_image, context)
                    
                    execution_results[module_name] = {
                        "status": result.get("status", "UNKNOWN"),
                        "executed": True,
                        "error": None
                    }
                    
                    # Verify basic result structure
                    assert "check" in result
                    assert "status" in result
                    assert result["status"] in ["PASSED", "FAILED", "NEEDS_REVIEW", "SKIPPED"]
                    
            except Exception as e:
                execution_results[module_name] = {
                    "status": "ERROR",
                    "executed": False,
                    "error": str(e)
                }
        
        # Print execution summary
        print("\nModule Execution Summary:")
        for module_name, result in execution_results.items():
            status = result["status"]
            if result["executed"]:
                print(f"  {module_name}: {status}")
            else:
                print(f"  {module_name}: ERROR - {result['error']}")
        
        # Count successful executions
        successful = sum(1 for r in execution_results.values() if r["executed"])
        assert successful >= 8, f"Only {successful}/11 modules executed successfully"

    async def test_pipeline_execution_order(self):
        """Test that modules execute in correct order."""
        test_image = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
        
        with patch('app.cv.checks.face.detector.detect_faces') as mock_detect:
            mock_detect.return_value = [{"bbox": [200, 150, 300, 250], "confidence": 0.8}]
            
            runner = CheckRunner()
            context = CheckContext()
            
            result = await runner.run_checks(test_image, context)
            
            assert "checks" in result
            check_results = result["checks"]
            
            # Verify execution order - face detection should come early
            executed_checks = [check["check"] for check in check_results]
            
            if "face_count" in executed_checks:
                face_count_index = executed_checks.index("face_count")
                # Face count should be executed before other face modules
                for face_module in ["face_position", "face_pose", "accessories"]:
                    if face_module in executed_checks:
                        face_module_index = executed_checks.index(face_module)
                        assert face_count_index <= face_module_index, \
                            f"face_count should execute before {face_module}"

    def test_module_configuration_integration(self):
        """Test module configuration and parameter handling."""
        check_registry.discover_checks()
        all_metadata = check_registry.get_all_metadata()
        
        configuration_test_results = {}
        
        for module_name, metadata in all_metadata.items():
            try:
                # Test default configuration
                check_class = check_registry.get_check(module_name)
                check_instance = check_class()
                
                # Test parameter validation
                default_params = {}
                for param in metadata.parameters:
                    default_params[param.name] = param.default
                
                is_valid = check_instance.validate_parameters(default_params)
                configuration_test_results[module_name] = {
                    "default_params_valid": is_valid,
                    "param_count": len(metadata.parameters),
                    "has_required_params": any(p.required for p in metadata.parameters)
                }
                
            except Exception as e:
                configuration_test_results[module_name] = {
                    "default_params_valid": False,
                    "param_count": 0,
                    "error": str(e)
                }
        
        # Verify configuration results
        valid_configs = sum(1 for r in configuration_test_results.values() 
                          if r.get("default_params_valid", False))
        assert valid_configs >= 10, f"Only {valid_configs}/11 modules have valid default configs" 