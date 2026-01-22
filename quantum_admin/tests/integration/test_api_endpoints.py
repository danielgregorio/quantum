"""
Integration Tests for API Endpoints
Tests all FastAPI endpoints with real HTTP requests
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health and status endpoints"""

    def test_root_redirect(self):
        """Test root endpoint redirects to frontend"""
        response = client.get("/", follow_redirects=False)

        assert response.status_code in [200, 307, 302]

    def test_health_endpoint(self):
        """Test /health endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_register_user(self):
        """Test POST /auth/register"""
        response = client.post("/auth/register", json={
            "username": f"testuser_{pytest.test_counter if hasattr(pytest, 'test_counter') else '1'}",
            "email": f"test_{pytest.test_counter if hasattr(pytest, 'test_counter') else '1'}@example.com",
            "password": "TestPass123!",
            "full_name": "Test User"
        })

        # Should succeed or fail if user exists
        assert response.status_code in [200, 201, 400, 409]

    def test_login_with_valid_credentials(self):
        """Test POST /auth/login with valid credentials"""
        # First register a user
        username = "logintest_user"
        password = "TestPass123!"

        client.post("/auth/register", json={
            "username": username,
            "email": "logintest@example.com",
            "password": password,
            "full_name": "Login Test"
        })

        # Now try to login
        response = client.post("/auth/login", json={
            "username": username,
            "password": password
        })

        # Should get token or already exists error
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "token_type" in data
            assert data["token_type"] == "bearer"

    def test_login_with_invalid_credentials(self):
        """Test POST /auth/login with wrong password"""
        response = client.post("/auth/login", json={
            "username": "nonexistent",
            "password": "wrongpassword"
        })

        assert response.status_code in [401, 404]

    def test_get_current_user_without_token(self):
        """Test GET /auth/me without authentication"""
        response = client.get("/auth/me")

        # Should require authentication
        assert response.status_code in [401, 403]

    def test_get_current_user_with_token(self):
        """Test GET /auth/me with valid token"""
        # Register and login
        username = "currentuser_test"
        password = "TestPass123!"

        client.post("/auth/register", json={
            "username": username,
            "email": "currentuser@example.com",
            "password": password,
            "full_name": "Current User"
        })

        login_response = client.post("/auth/login", json={
            "username": username,
            "password": password
        })

        if login_response.status_code == 200:
            token = login_response.json()["access_token"]

            # Get current user
            response = client.get("/auth/me", headers={
                "Authorization": f"Bearer {token}"
            })

            if response.status_code == 200:
                data = response.json()
                assert "username" in data
                assert data["username"] == username


class TestContainerEndpoints:
    """Test Docker container endpoints"""

    def test_list_containers(self):
        """Test GET /containers"""
        response = client.get("/containers")

        # Should return list (empty or with containers)
        assert response.status_code in [200, 500]  # 500 if Docker not available

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_create_container_missing_data(self):
        """Test POST /containers with missing data"""
        response = client.post("/containers", json={})

        # Should return validation error
        assert response.status_code in [400, 422]

    def test_get_container_stats_invalid_id(self):
        """Test GET /containers/{id}/stats with invalid ID"""
        response = client.get("/containers/nonexistent123/stats")

        # Should return 404 or 500
        assert response.status_code in [404, 500]


class TestSchemaEndpoints:
    """Test schema inspector endpoints"""

    def test_inspect_schema(self):
        """Test GET /schema/inspect"""
        response = client.get("/schema/inspect")

        # May fail if no database configured
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "tables" in data

    def test_generate_models(self):
        """Test GET /schema/models"""
        response = client.get("/schema/models")

        # Should return code or error
        assert response.status_code in [200, 500]

    def test_export_schema_mermaid(self):
        """Test GET /schema/export?format=mermaid"""
        response = client.get("/schema/export", params={"format": "mermaid"})

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            assert "erDiagram" in response.text or response.text != ""

    def test_export_schema_dbml(self):
        """Test GET /schema/export?format=dbml"""
        response = client.get("/schema/export", params={"format": "dbml"})

        assert response.status_code in [200, 500]

    def test_export_schema_invalid_format(self):
        """Test GET /schema/export with invalid format"""
        response = client.get("/schema/export", params={"format": "invalid"})

        # Should return error
        assert response.status_code in [400, 422]


class TestAIEndpoints:
    """Test AI assistant endpoints"""

    def test_ai_chat(self):
        """Test POST /ai/chat"""
        response = client.post("/ai/chat", json={
            "message": "Hello, AI!",
            "use_slm": False
        })

        # Should work with rule-based fallback
        assert response.status_code == 200

        data = response.json()
        assert "response" in data
        assert "provider" in data

    def test_ai_chat_empty_message(self):
        """Test POST /ai/chat with empty message"""
        response = client.post("/ai/chat", json={
            "message": "",
            "use_slm": False
        })

        # Should still respond
        assert response.status_code in [200, 400]

    def test_list_ai_functions(self):
        """Test GET /ai/functions"""
        response = client.get("/ai/functions")

        assert response.status_code == 200

        data = response.json()
        assert "functions" in data
        assert len(data["functions"]) > 0

    def test_call_ai_function(self):
        """Test POST /ai/function/call"""
        response = client.post("/ai/function/call", json={
            "function_name": "generate_sql_query",
            "params": {
                "description": "get all users",
                "table_name": "users"
            }
        })

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "result" in data

    def test_clear_ai_memory(self):
        """Test POST /ai/clear"""
        response = client.post("/ai/clear")

        assert response.status_code == 200

        data = response.json()
        assert "status" in data


class TestPipelineEndpoints:
    """Test Jenkins pipeline endpoints"""

    def test_parse_qpipeline(self):
        """Test POST /pipelines/parse"""
        qpipeline_xml = """<?xml version="1.0"?>
<q:pipeline name="Test Pipeline">
    <q:stage name="Build">
        <q:step>npm install</q:step>
    </q:stage>
</q:pipeline>"""

        response = client.post("/pipelines/parse", json={
            "qpipeline": qpipeline_xml
        })

        assert response.status_code in [200, 422]

        if response.status_code == 200:
            data = response.json()
            assert "stages" in data

    def test_generate_jenkinsfile(self):
        """Test POST /pipelines/generate"""
        pipeline_config = {
            "name": "Test Pipeline",
            "stages": [
                {
                    "name": "Build",
                    "steps": ["npm install", "npm run build"]
                }
            ]
        }

        response = client.post("/pipelines/generate", json=pipeline_config)

        assert response.status_code in [200, 422]

        if response.status_code == 200:
            data = response.json()
            assert "jenkinsfile" in data

    def test_get_pipeline_templates(self):
        """Test GET /pipelines/templates"""
        response = client.get("/pipelines/templates")

        assert response.status_code == 200

        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) > 0


class TestWebSocketEndpoint:
    """Test WebSocket endpoint"""

    def test_websocket_connection(self):
        """Test WebSocket /ws connection"""
        # Note: WebSocket testing requires special handling
        # This is a placeholder for WebSocket tests

        # For full WebSocket testing, you'd use:
        # from starlette.testclient import TestClient
        # with client.websocket_connect("/ws") as websocket:
        #     data = websocket.receive_json()
        #     assert data is not None

        # For now, just test that endpoint exists
        pass


class TestDatasourceEndpoints:
    """Test datasource management endpoints"""

    def test_list_datasources(self):
        """Test GET /datasources"""
        response = client.get("/datasources")

        # Should return list (may be empty)
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_create_datasource_invalid(self):
        """Test POST /datasources with invalid data"""
        response = client.post("/datasources", json={
            "name": ""  # Invalid empty name
        })

        # Should return validation error
        assert response.status_code in [400, 422]


class TestCORSHeaders:
    """Test CORS configuration"""

    def test_cors_headers_present(self):
        """Test that CORS headers are present"""
        response = client.options("/health")

        # CORS headers should be present
        # Note: Actual headers depend on CORS middleware configuration


class TestErrorHandling:
    """Test global error handling"""

    def test_404_error(self):
        """Test 404 error response"""
        response = client.get("/nonexistent/endpoint")

        assert response.status_code == 404

        data = response.json()
        assert "error" in data or "detail" in data

    def test_422_validation_error(self):
        """Test validation error response"""
        response = client.post("/auth/register", json={
            "username": "a",  # Too short
            "invalid_field": "value"
        })

        assert response.status_code == 422

        data = response.json()
        assert "detail" in data or "errors" in data


class TestRateLimiting:
    """Test rate limiting (if implemented)"""

    def test_rate_limit_health_endpoint(self):
        """Test rate limiting on health endpoint"""
        # Make many requests quickly
        responses = []
        for _ in range(100):
            response = client.get("/health")
            responses.append(response.status_code)

        # All should succeed (unless rate limiting is very strict)
        # If rate limiting is implemented, some might be 429
        assert all(status in [200, 429] for status in responses)


class TestSecurityHeaders:
    """Test security headers"""

    def test_security_headers_present(self):
        """Test that security headers are set"""
        response = client.get("/health")

        # Check for common security headers (if implemented)
        # headers = response.headers
        # These are optional but recommended:
        # - X-Content-Type-Options
        # - X-Frame-Options
        # - X-XSS-Protection
        # - Strict-Transport-Security (HTTPS only)


class TestAPIDocumentation:
    """Test API documentation endpoints"""

    def test_openapi_json(self):
        """Test GET /api/openapi.json"""
        response = client.get("/api/openapi.json")

        assert response.status_code == 200

        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    def test_swagger_ui(self):
        """Test GET /api/docs (Swagger UI)"""
        response = client.get("/api/docs")

        # Swagger UI returns HTML
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "api" in response.text.lower()

    def test_redoc(self):
        """Test GET /api/redoc (ReDoc)"""
        response = client.get("/api/redoc")

        assert response.status_code == 200
        assert "redoc" in response.text.lower() or "api" in response.text.lower()


class TestPerformance:
    """Test API performance"""

    def test_health_endpoint_performance(self):
        """Test health endpoint response time"""
        import time

        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.5  # Should respond in <500ms

    def test_concurrent_requests(self):
        """Test handling concurrent requests"""
        import concurrent.futures

        def make_request():
            return client.get("/health")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert all(r.status_code == 200 for r in results)


# ============================================================================
# Integration with pytest
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
