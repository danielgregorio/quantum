"""
Integration Tests for Web Server

Tests the complete rendering pipeline.
"""

import pytest
from pathlib import Path


class TestWebServerIntegration:
    """Test complete web server integration"""

    @pytest.mark.integration
    @pytest.mark.phase1
    def test_simple_component_rendering(self, client, tmp_path):
        """Test rendering a simple component via HTTP"""
        # Test endpoint exists
        response = client.get('/test')
        assert response.status_code in [200, 400, 404]  # Any response means server working

    @pytest.mark.integration
    @pytest.mark.phase2
    def test_component_composition(self, client):
        """components/demo.q composes <Layout>, <Card> and <Button>.

        This asserted `status in [200, 400, 404]`, so it passed on a 404 and
        proved nothing about composition. It only ever caught the 500 — and
        it caught a real one: ComponentCallNode was missing from the
        render-only list in _execute_statement, so every page using component
        composition raised "No modular executor registered" the moment the
        legacy if-elif chain that used to swallow it was removed.
        """
        response = client.get('/demo')
        assert response.status_code == 200, response.get_data(as_text=True)[:400]

        html = response.get_data(as_text=True)
        # Content that can only come from the composed children.
        assert 'Component Composition Demo' in html
        assert 'Feature 1' in html
        assert 'ComponentCallNode' not in html

    @pytest.mark.integration
    def test_static_files(self, client):
        """Test static file serving"""
        # Test that static route exists
        response = client.get('/static/css/style.css')
        # OK if file exists or 404 if not
        assert response.status_code in [200, 404]

    @pytest.mark.integration
    def test_404_handling(self, client):
        """Test 404 error handling"""
        response = client.get('/nonexistent')
        assert response.status_code == 404
