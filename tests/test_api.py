"""Tests for the web scraping API."""

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check_success(self):
        """Test that health check endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert "static" in data["scrapers"]
        assert "dynamic" in data["scrapers"]

    def test_root_endpoint(self):
        """Test root endpoint returns info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestScrapeEndpoint:
    """Tests for the scrape endpoint."""

    def test_scrape_missing_url(self):
        """Test that scrape endpoint requires URL."""
        response = client.post("/scrape", json={})
        assert response.status_code == 422  # Validation error

    def test_scrape_invalid_url_scheme(self):
        """Test that scrape endpoint rejects non-HTTP schemes."""
        response = client.post(
            "/scrape",
            json={
                "url": "ftp://example.com",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert "not allowed" in data["detail"].lower() or "scheme" in data["detail"].lower()

    def test_scrape_invalid_mode(self):
        """Test that scrape endpoint validates mode."""
        response = client.post(
            "/scrape",
            json={
                "url": "https://example.com",
                "mode": "invalid",
            },
        )
        assert response.status_code == 400

    def test_scrape_request_model_validation(self):
        """Test that request validation works correctly."""
        # Valid minimal request
        response = client.post(
            "/scrape",
            json={
                "url": "https://example.com",
            },
        )
        # Should succeed or fail with actual scraping error, not validation error
        assert response.status_code != 422

    def test_scrape_with_extraction_config(self):
        """Test scrape request with extraction config."""
        response = client.post(
            "/scrape",
            json={
                "url": "https://example.com",
                "extract": {
                    "selector": ".content",
                    "attribute": None,
                    "multiple": False,
                },
            },
        )
        # Should not fail validation
        assert response.status_code != 422

    def test_scrape_with_actions(self):
        """Test scrape request with user actions."""
        response = client.post(
            "/scrape",
            json={
                "url": "https://example.com",
                "mode": "dynamic",
                "actions": [
                    {
                        "type": "click",
                        "selector": "#button",
                    },
                    {
                        "type": "type",
                        "selector": "input",
                        "value": "test",
                    },
                ],
            },
        )
        # Should not fail validation
        assert response.status_code != 422

    def test_scrape_response_structure(self):
        """Test that scrape response has correct structure when successful."""
        # We'll just check structure, not actual scraping
        response = client.post(
            "/scrape",
            json={
                "url": "https://example.com",
                "mode": "static",
            },
        )
        # Response should be JSON
        assert response.headers["content-type"] == "application/json"
        data = response.json()

        # Check response structure
        assert "success" in data
        assert "metadata" in data
        assert "error" in data or "data" in data

        # Check metadata structure
        metadata = data["metadata"]
        assert "scrape_mode" in metadata
        assert "duration_ms" in metadata
        assert "timestamp" in metadata

    def test_scrape_output_formats(self):
        """Test different output format options."""
        for output_format in ["json", "html", "text", "markdown"]:
            response = client.post(
                "/scrape",
                json={
                    "url": "https://example.com",
                    "output_format": output_format,
                },
            )
            # Should not fail validation
            assert response.status_code != 422

    def test_scrape_screenshot_option(self):
        """Test screenshot option."""
        response = client.post(
            "/scrape",
            json={
                "url": "https://example.com",
                "screenshot": True,
            },
        )
        # Should not fail validation
        assert response.status_code != 422

    def test_scrape_url_too_long(self):
        """Test that extremely long URLs are rejected."""
        from src.config import settings

        # Create URL longer than max allowed
        long_url = f"https://example.com/{'a' * (settings.MAX_URL_LENGTH + 100)}"
        response = client.post(
            "/scrape",
            json={
                "url": long_url,
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert "exceeds maximum length" in data["detail"]


class TestExtractionModel:
    """Tests for extraction configuration validation."""

    def test_extraction_required_selector(self):
        """Test that extraction requires selector."""
        response = client.post(
            "/scrape",
            json={
                "url": "https://example.com",
                "extract": {
                    "attribute": "href",
                },
            },
        )
        # Should fail validation - selector is required
        assert response.status_code == 422

    def test_extraction_with_attribute(self):
        """Test extraction with HTML attribute."""
        response = client.post(
            "/scrape",
            json={
                "url": "https://example.com",
                "extract": {
                    "selector": "a",
                    "attribute": "href",
                    "multiple": True,
                },
            },
        )
        # Should not fail validation
        assert response.status_code != 422


class TestActionModel:
    """Tests for action validation."""

    def test_action_types(self):
        """Test all action types are accepted."""
        action_types = ["click", "type", "wait", "scroll", "screenshot"]

        for action_type in action_types:
            action = {"type": action_type}
            if action_type == "type":
                action["value"] = "test"
            if action_type == "wait":
                action["condition"] = "timeout"

            response = client.post(
                "/scrape",
                json={
                    "url": "https://example.com",
                    "actions": [action],
                },
            )
            # Should not fail validation
            assert response.status_code != 422

    def test_action_click_with_selector(self):
        """Test click action with selector."""
        response = client.post(
            "/scrape",
            json={
                "url": "https://example.com",
                "actions": [
                    {
                        "type": "click",
                        "selector": "#button",
                        "wait_after": 1000,
                    }
                ],
            },
        )
        assert response.status_code != 422

    def test_action_wait_conditions(self):
        """Test wait action with different conditions."""
        conditions = ["selector", "timeout", "networkidle", "load"]

        for condition in conditions:
            action = {
                "type": "wait",
                "condition": condition,
            }
            if condition == "selector":
                action["value"] = ".selector"
            else:
                action["timeout"] = 5000

            response = client.post(
                "/scrape",
                json={
                    "url": "https://example.com",
                    "actions": [action],
                },
            )
            assert response.status_code != 422
