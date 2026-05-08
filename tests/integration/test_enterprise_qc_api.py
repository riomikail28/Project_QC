"""
Integration Tests - Enterprise QC API
====================================

Comprehensive integration tests for the QC Central Kitchen enterprise API.
Testing strategy includes:
- End-to-end API workflow testing
- Authentication and authorization testing
- Database integration testing
- Error handling and edge cases
- Performance and load testing
- Security vulnerability testing

These tests ensure the enterprise refactoring maintains quality,
reliability, and security standards for production deployment.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from http import HTTPStatus
import requests

from backend.layers.application.api.enterprise_qc_api import create_enterprise_qc_app
from backend.layers.domain.di.service_config import create_service_config
from backend.layers.domain.entities.qc_entities import ValidationLevel, QCEntityStatus

@pytest.fixture
def app():
    """Create test Flask application"""
    app = create_enterprise_qc_app()
    app.config['TESTING'] = True
    app.config['ENVIRONMENT'] = 'testing'
    return app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
async def test_data():
    """Setup test data for integration tests"""
    config = create_service_config()
    
    # Initialize test database
    db_manager = config.get_container().get('DatabaseManager')
    await db_manager.initialize()
    
    # Create test facility
    facility = {
        'id': 'test-facility-1',
        'name': 'Test Central Kitchen',
        'code': 'TCK001',
        'address': '123 Test Street',
        'city': 'Test City',
        'province': 'Test Province',
        'postal_code': '12345',
        'phone': '+1234567890',
        'manager_name': 'Test Manager'
    }
    
    # Create test batch
    batch = {
        'batch_number': 'BATCH-001',
        'product_id': 'PRODUCT-001',
        'quantity_produced': 1000,
        'production_date': datetime.utcnow().isoformat(),
        'expiry_date': (datetime.utcnow() + timedelta(days=30)).isoformat(),
        'facility_id': 'test-facility-1'
    }
    
    yield {
        'facility': facility,
        'batch': batch,
        'db_manager': db_manager
    }
    
    # Cleanup
    await db_manager.close()

class TestAuthentication:
    """Test authentication and authorization endpoints"""
    
    def test_login_success(self, client):
        """Test successful login"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'admin',
            'password': 'password'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
        assert 'expires_at' in data['data']
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'invalid',
            'password': 'invalid'
        })
        
        assert response.status_code == 401
        data = json.loads(response.data)
        
        assert data['status'] == 'error'
        assert 'AUTHENTICATION_ERROR' in data['errors'][0]['code']
    
    def test_login_missing_fields(self, client):
        """Test login with missing required fields"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'admin'
            # Missing password
        })
        
        assert response.status_code == 422
        data = json.loads(response.data)
        
        assert data['status'] == 'error'
        assert 'VALIDATION_ERROR' in data['errors'][0]['code']
    
    def test_token_refresh(self, client):
        """Test token refresh endpoint"""
        # First login
        login_response = client.post('/api/v1/auth/login', json={
            'username': 'admin',
            'password': 'password'
        })
        
        login_data = json.loads(login_response.data)
        refresh_token = login_data['data']['refresh_token']
        
        # Refresh token
        refresh_response = client.post('/api/v1/auth/refresh', json={
            'refresh_token': refresh_token
        })
        
        assert refresh_response.status_code == 200
        data = json.loads(refresh_response.data)
        
        assert data['status'] == 'success'
        assert 'access_token' in data['data']
        assert new_access_token != login_data['data']['access_token']

class TestQCRecords:
    """Test QC record endpoints"""
    
    @pytest.fixture
    def auth_headers(self, client):
        """Get authentication headers for protected endpoints"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'admin',
            'password': 'password'
        })
        
        token = json.loads(response.data)['data']['access_token']
        return {'Authorization': f'Bearer {token}'}
    
    def test_create_qc_record_success(self, client, test_data, auth_headers):
        """Test successful QC record creation"""
        response = client.post('/api/v1/qc/records', 
            headers=auth_headers,
            json={
                'batch_id': test_data['batch']['batch_number'],
                'facility_id': test_data['facility']['id'],
                'check_type': 'production',
                'performed_by': 'test-user',
                'temperature_readings': [
                    {
                        'unit_type': 'chiller',
                        'temperature_celsius': 4.0,
                        'target_min': 0.0,
                        'target_max': 8.0,
                        'monitored_by': 'test-monitor'
                    }
                ],
                'visual_inspection': {
                    'result': 'PASS',
                    'notes': 'Visual inspection passed'
                }
            })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert 'data' in data
        assert data['data']['batch_id'] == test_data['batch']['batch_number']
    
    def test_create_qc_record_validation_error(self, client, auth_headers):
        """Test QC record creation with validation error"""
        response = client.post('/api/v1/qc/records',
            headers=auth_headers,
            json={
                # Missing required fields
                'check_type': 'production'
            })
        
        assert response.status_code == 422
        data = json.loads(response.data)
        
        assert data['status'] == 'error'
        assert 'VALIDATION_ERROR' in data['errors'][0]['code']
    
    def test_get_facility_qc_records(self, client, test_data, auth_headers):
        """Test getting QC records for facility"""
        # First create a record
        client.post('/api/v1/qc/records',
            headers=auth_headers,
            json={
                'batch_id': test_data['batch']['batch_number'],
                'facility_id': test_data['facility']['id'],
                'check_type': 'production',
                'performed_by': 'test-user'
            })
        
        # Get records
        response = client.get(
            f"/api/v1/qc/records/facility/{test_data['facility']['id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert 'data' in data
        assert isinstance(data['data'], list)

class TestTemperatureMonitoring:
    """Test temperature monitoring endpoints"""
    
    @pytest.fixture
    def auth_headers(self, client):
        """Get authentication headers"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'admin',
            'password': 'password'
        })
        
        token = json.loads(response.data)['data']['access_token']
        return {'Authorization': f'Bearer {token}'}
    
    def test_create_temperature_reading(self, client, test_data, auth_headers):
        """Test creating temperature reading"""
        response = client.post('/api/v1/temperature/readings',
            headers=auth_headers,
            json={
                'batch_id': test_data['batch']['batch_number'],
                'facility_id': test_data['facility']['id'],
                'unit_type': 'chiller',
                'temperature_celsius': 4.5,
                'target_min': 0.0,
                'target_max': 8.0,
                'monitored_by': 'test-monitor'
            })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert 'data' in data
        assert data['data']['temperature_celsius'] == 4.5
    
    def test_get_temperature_readings(self, client, test_data, auth_headers):
        """Test getting temperature readings"""
        # Create a reading first
        client.post('/api/v1/temperature/readings',
            headers=auth_headers,
            json={
                'batch_id': test_data['batch']['batch_number'],
                'unit_type': 'chiller',
                'temperature_celsius': 4.5,
                'monitored_by': 'test-monitor'
            })
        
        # Get readings
        response = client.get(
            f"/api/v1/temperature/readings?batch_id={test_data['batch']['batch_number']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert 'data' in data
        assert isinstance(data['data'], list)
    
    def test_get_anomaly_readings(self, client, test_data, auth_headers):
        """Test getting anomalous temperature readings"""
        response = client.get(
            f"/api/v1/temperature/readings?facility_id={test_data['facility']['id']}&hours_back=24",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert 'data' in data

class TestBatches:
    """Test batch management endpoints"""
    
    @pytest.fixture
    def auth_headers(self, client):
        """Get authentication headers"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'admin',
            'password': 'password'
        })
        
        token = json.loads(response.data)['data']['access_token']
        return {'Authorization': f'Bearer {token}'}
    
    def test_get_batches(self, client, test_data, auth_headers):
        """Test getting batches"""
        response = client.get(
            f"/api/v1/batches?facility_id={test_data['facility']['id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert 'data' in data
        assert isinstance(data['data'], list)
    
    def test_get_batch_by_id(self, client, test_data, auth_headers):
        """Test getting specific batch"""
        response = client.get(
            f"/api/v1/batches/{test_data['batch']['batch_number']}",
            headers=auth_headers
        )
        
        assert response.status_code == 404  # Batch doesn't exist yet
        data = json.loads(response.data)
        
        assert data['status'] == 'error'
        assert 'BATCH_NOT_FOUND' in data['errors'][0]['code']

class TestDashboard:
    """Test dashboard endpoints"""
    
    @pytest.fixture
    def auth_headers(self, client):
        """Get authentication headers"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'admin',
            'password': 'password'
        })
        
        token = json.loads(response.data)['data']['access_token']
        return {'Authorization': f'Bearer {token}'}
    
    def test_get_qc_dashboard(self, client, test_data, auth_headers):
        """Test getting QC dashboard data"""
        response = client.get(
            f"/api/v1/dashboard/qc-summary?facility_id={test_data['facility']['id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert 'data' in data
        
        # Check dashboard structure
        dashboard_data = data['data']
        expected_keys = [
            'compliance_summary',
            'recent_records', 
            'temperature_anomalies',
            'pending_tasks',
            'trends'
        ]
        
        for key in expected_keys:
            assert key in dashboard_data
    
    def test_dashboard_validation_error(self, client, auth_headers):
        """Test dashboard with missing facility_id"""
        response = client.get(
            '/api/v1/dashboard/qc-summary',
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        
        assert data['status'] == 'error'
        assert 'facility_id' in data['errors'][0]['field']

class TestSecurity:
    """Test security features"""
    
    def test_unauthorized_access(self, client):
        """Test accessing protected endpoints without authentication"""
        protected_endpoints = [
            '/api/v1/qc/records',
            '/api/v1/temperature/readings',
            '/api/v1/batches',
            '/api/v1/dashboard/qc-summary'
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401
    
    def test_csrf_protection(self, client):
        """Test CSRF protection on state-changing endpoints"""
        # This test would check CSRF tokens are enforced
        # Implementation depends on CSRF middleware configuration
        pass
    
    def test_rate_limiting(self, client):
        """Test rate limiting is enforced"""
        # Make multiple requests to test rate limiting
        responses = []
        for _ in range(200):  # Over the rate limit
            response = client.post('/api/v1/auth/login', json={
                'username': 'invalid',
                'password': 'invalid'
            })
            responses.append(response)
        
        # Should eventually get rate limited
        rate_limited = any(r.status_code == 429 for r in responses)
        assert rate_limited, "Rate limiting should be enforced"

class TestPerformance:
    """Performance and load testing"""
    
    def test_api_response_time(self, client, test_data):
        """Test API response times are within acceptable limits"""
        import time
        
        # Login first
        login_response = client.post('/api/v1/auth/login', json={
            'username': 'admin',
            'password': 'password'
        })
        
        token = json.loads(login_response.data)['data']['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Test endpoint response times
        endpoints = [
            ('GET', f"/api/v1/qc/records/facility/{test_data['facility']['id']}"),
            ('GET', f"/api/v1/temperature/readings?batch_id={test_data['batch']['batch_number']}"),
            ('GET', f"/api/v1/dashboard/qc-summary?facility_id={test_data['facility']['id']}")
        ]
        
        for method, endpoint in endpoints:
            start_time = time.time()
            
            if method == 'GET':
                response = client.get(endpoint, headers=headers)
            else:
                response = client.post(endpoint, headers=headers)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # API should respond within 2 seconds
            assert response_time < 2.0, f"Endpoint {endpoint} took too long: {response_time}s"
    
    def test_concurrent_requests(self, client, test_data):
        """Test API can handle concurrent requests"""
        import threading
        import queue
        import time
        
        def make_request(result_queue, endpoint):
            """Make request and put result in queue"""
            try:
                start_time = time.time()
                response = client.get('/health')
                end_time = time.time()
                result_queue.put((response.status_code, end_time - start_time))
            except Exception as e:
                result_queue.put(('error', str(e)))
        
        # Make 10 concurrent requests
        threads = []
        result_queue = queue.Queue()
        
        for i in range(10):
            thread = threading.Thread(
                target=make_request, 
                args=(result_queue, '/health')
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check all requests succeeded
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())
        
        assert len(results) == 10
        assert all(status == 200 and time < 1.0 for status, time in results)

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_malformed_requests(self, client):
        """Test handling of malformed requests"""
        # Invalid JSON
        response = client.post('/api/v1/auth/login', 
            data='invalid json',
            content_type='application/json')
        
        assert response.status_code == 400
    
    def test_invalid_parameters(self, client):
        """Test handling of invalid parameters"""
        response = client.get('/api/v1/qc/records/facility/invalid-id')
        
        assert response.status_code == 401  # First, unauthorized
        
        # With authentication
        login_response = client.post('/api/v1/auth/login', json={
            'username': 'admin',
            'password': 'password'
        })
        
        token = json.loads(login_response.data)['data']['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        response = client.get('/api/v1/qc/records/facility/invalid-id', headers=headers)
        
        # Should handle gracefully (not crash)
        assert response.status_code in [200, 404]  # Either works or facility not found
    
    def test_database_connection_error(self, client):
        """Test handling of database connection errors"""
        # This would require mocking database connections
        # to test error handling when database is unavailable
        pass

@pytest.mark.integration
class TestWorkflowIntegration:
    """End-to-end workflow integration tests"""
    
    def test_complete_qc_workflow(self, client, test_data):
        """Test complete QC workflow from login to dashboard"""
        
        # 1. Login
        login_response = client.post('/api/v1/auth/login', json={
            'username': 'admin',
            'password': 'password'
        })
        
        assert login_response.status_code == 200
        token = json.loads(login_response.data)['data']['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # 2. Create QC record
        qc_response = client.post('/api/v1/qc/records',
            headers=headers,
            json={
                'batch_id': test_data['batch']['batch_number'],
                'facility_id': test_data['facility']['id'],
                'check_type': 'production',
                'performed_by': 'test-user',
                'temperature_readings': [
                    {
                        'unit_type': 'chiller',
                        'temperature_celsius': 4.0,
                        'target_min': 0.0,
                        'target_max': 8.0,
                        'monitored_by': 'test-monitor'
                    }
                ]
            })
        
        assert qc_response.status_code == 200
        qc_data = json.loads(qc_response.data)
        qc_record_id = qc_data['data']['id']
        
        # 3. Complete QC record
        complete_response = client.put(
            f'/api/v1/qc/records/{qc_record_id}',
            headers=headers,
            json={
                'completed_by': 'test-supervisor',
                'final_inspection': {
                    'result': 'PASS'
                }
            })
        
        assert complete_response.status_code == 200
        
        # 4. Check dashboard
        dashboard_response = client.get(
            f"/api/v1/dashboard/qc-summary?facility_id={test_data['facility']['id']}",
            headers=headers
        )
        
        assert dashboard_response.status_code == 200
        dashboard_data = json.loads(dashboard_response.data)
        
        # Should see our recent record in dashboard
        assert len(dashboard_data['data']['recent_records']) >= 1

if __name__ == '__main__':
    pytest.main(['-v', __file__, '--tb=short'])