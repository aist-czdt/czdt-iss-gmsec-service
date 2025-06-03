"""
Unit tests for the API models.
"""

import sys
from unittest.mock import MagicMock
import pytest
from pydantic import ValidationError

# Mock libgmsec_python3 before importing anything that uses it
sys.modules["libgmsec_python3"] = MagicMock()

# Only import after mocking
from gmsec_service.api.publisher_api import LogRequest, ProductRequest


def test_log_request_valid():
    log = LogRequest(level="info", msg_body="Something happened")
    assert log.level == "INFO"
    assert log.msg_body == "Something happened"


def test_log_request_invalid_level():
    with pytest.raises(ValidationError) as exc_info:
        LogRequest(level="notalevel", msg_body="Test message")
    assert "Invalid log level" in str(exc_info.value)


def test_product_request_valid():
    product = ProductRequest(
        collection="collection-abc",
        ogc="ogc-id",
        uris=["s3://bucket/file1.txt", "s3://another-bucket/data/file2.csv"],
    )
    assert product.collection == "collection-abc"
    assert product.uris[0].startswith("s3://")


def test_product_request_invalid_uri_scheme():
    with pytest.raises(ValidationError) as exc_info:
        ProductRequest(
            collection="collection-x", ogc="ogc-y", uris=["http://example.com/file.txt"]
        )
    assert "Invalid URI" in str(exc_info.value)


def test_product_request_empty_uris():
    with pytest.raises(ValidationError) as exc_info:
        ProductRequest(collection="abc", ogc="def", uris=[])
    assert "uris list must not be empty" in str(exc_info.value)


def test_product_request_blank_collection():
    with pytest.raises(ValidationError) as exc_info:
        ProductRequest(collection="  ", ogc="ogc-123", uris=["s3://bucket/file"])
    assert "at least 1 character" in str(exc_info.value)
