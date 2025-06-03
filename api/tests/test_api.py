"""
Unit tests for the API proxy service.
This test suite covers all endpoints and error handling paths.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from api.main import app
import sys
import httpx

# Mock libgmsec_python3 before importing anything that uses it
sys.modules["libgmsec_python3"] = MagicMock()

# Only import after mocking
from gmsec_service.common.connection import GmsecConnection  # noqa: E402


@pytest.fixture(scope="module")
def client():
    """Create a TestClient instance for testing the FastAPI app."""
    return TestClient(app)


# Mock GMSEC connection
@pytest.fixture(autouse=True)
def mock_gmsec_connection():
    """
    Mock the GmsecConnection to prevent real GMSEC messaging.
    This fixture is applied to all tests automatically.
    """
    mock_connection = MagicMock(spec=GmsecConnection)

    mock_conn = MagicMock()
    mock_connection.conn = mock_conn
    mock_conn.publish = MagicMock(return_value=None)

    # Patch the GmsecConnection to return the mock when it's used in the tests
    with patch(
        "gmsec_service.common.connection.GmsecConnection", return_value=mock_connection
    ):
        yield mock_connection


# Mock the HTTPX AsyncClient to prevent actual external HTTP calls
@pytest.fixture
def mock_httpx_async_client():
    """
    Create a mock httpx.AsyncClient that returns a controlled response.
    This prevents actual HTTP requests to external services.
    """
    # Create mock response for the httpx post method
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}

    # Create mock client with post method returning our mock response
    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post.return_value = mock_response

    # Patch httpx.AsyncClient to return our mock client
    with patch("httpx.AsyncClient", return_value=mock_client):
        yield mock_client.__aenter__.return_value


# Test the /health endpoint
def test_health_check(client):
    """Test the /health endpoint returns a successful response."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# Test for /product endpoint with success response
def test_publish_product_success(
    client, mock_gmsec_connection, mock_httpx_async_client
):
    """Test successful product publish request."""

    product_data = {
        "collection": "example_collection",
        "ogc": "example_ogc",
        "uris": ["s3://example-bucket/file1.p", "s3://example-bucket/file2.p"],
    }

    mock_response = mock_httpx_async_client.post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "published"}

    response = client.post("/product", json=product_data)

    assert response.status_code == 200

    response_json = response.json()
    assert "status" in response_json
    assert response_json["status"] == "published"

    # Verify that the mock client post method was called with the right URL and data
    mock_httpx_async_client.post.assert_called_once()
    call_args = mock_httpx_async_client.post.call_args
    assert call_args[0][0] == "http://iss.publisher:9000/product"
    assert call_args[1]["json"] == product_data


# Test for /log endpoint with success response
def test_proxy_log_success(client, mock_gmsec_connection, mock_httpx_async_client):
    """Test successful log forwarding."""

    log_data = {
        "level": "INFO",
        "message": "Sample log message",
        "timestamp": "2025-05-09T10:15:30Z",
        "source": "test_application",
    }

    mock_response = mock_httpx_async_client.post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "logged"}

    response = client.post("/log", json=log_data)

    assert response.status_code == 200

    response_json = response.json()
    assert "status" in response_json
    assert response_json["status"] == "logged"

    mock_httpx_async_client.post.assert_called_once()
    call_args = mock_httpx_async_client.post.call_args
    assert call_args[0][0] == "http://iss.publisher:9000/log"
    assert call_args[1]["json"] == log_data


# Test publisher service returning an error
def test_publisher_service_error(
    client, mock_gmsec_connection, mock_httpx_async_client
):
    """Test handling of errors from the publisher service."""

    product_data = {
        "collection": "invalid_collection",
        "ogc": "example_ogc",
        "uris": ["s3://example-bucket/file.p"],
    }

    mock_response = mock_httpx_async_client.post.return_value
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "error": "Bad Request",
        "detail": "Invalid data format",
    }

    response = client.post("/product", json=product_data)

    assert response.status_code == 400
    assert response.json() == {"error": "Bad Request", "detail": "Invalid data format"}

    mock_httpx_async_client.post.assert_called_once()


# Test timeout exception handling
def test_publisher_service_timeout(client, mock_gmsec_connection):
    """Test handling of timeout exceptions when communicating with the publisher service."""

    log_data = {
        "level": "ERROR",
        "message": "System failure",
        "timestamp": "2025-05-09T10:20:30Z",
    }

    # Configure mock to raise a TimeoutException
    # Important: The exception must be a proper httpx.TimeoutException for the correct handler to trigger
    mock_client = MagicMock()
    timeout_exception = httpx.TimeoutException("Connection timed out")
    # Ensure it's recognized as a TimeoutException and not caught by the generic RequestError handler
    timeout_exception.__class__ = httpx.TimeoutException
    mock_client.__aenter__.return_value.post.side_effect = timeout_exception

    # Patch httpx.AsyncClient to return our mocked client that raises an exception
    with patch("httpx.AsyncClient", return_value=mock_client):
        response = client.post("/log", json=log_data)

        assert response.status_code == 504
        assert "Gateway timeout" in response.json()["detail"]


# Test connection error handling
def test_publisher_service_connection_error(client, mock_gmsec_connection):
    """Test handling of connection errors when communicating with the publisher service."""

    product_data = {
        "collection": "example_collection",
        "ogc": "example_ogc",
        "uris": ["s3://example-bucket/file.p"],
    }

    # Configure mock to raise a RequestError
    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post.side_effect = httpx.RequestError(
        "Connection refused", request=None
    )

    # Patch httpx.AsyncClient to return our mocked client that raises an exception
    with patch("httpx.AsyncClient", return_value=mock_client):
        response = client.post("/product", json=product_data)

        assert response.status_code == 503
        assert "Service unavailable" in response.json()["detail"]


# Test unexpected exception handling
def test_unexpected_exception(client, mock_gmsec_connection):
    """Test handling of unexpected exceptions in the proxy request flow."""

    product_data = {
        "collection": "example_collection",
        "ogc": "example_ogc",
        "uris": ["s3://example-bucket/file.p"],
    }

    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post.side_effect = ValueError(
        "Unexpected error"
    )

    # Patch httpx.AsyncClient to return our mocked client that raises an exception
    with patch("httpx.AsyncClient", return_value=mock_client):
        response = client.post("/product", json=product_data)

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]
