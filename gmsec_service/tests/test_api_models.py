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
        job_id="1234-abcd",
        concept_id="collection-abc",
        provenance="source:dummy,parameter:dummy",
        ogc="ogc-id",
        uris=["s3://bucket/file1.txt", "https://another-bucket/data/file2.csv"],
    )
    assert product.job_id == "1234-abcd"
    assert product.concept_id == "collection-abc"
    assert product.provenance == "source:dummy,parameter:dummy"
    assert len(product.uris) > 0

def test_product_request_invalid_uri_scheme():
    with pytest.raises(ValidationError) as exc_info:
        ProductRequest(
            job_id="1234-abcd", concept_id="collection-x", ogc="ogc-y", uris=[]
        )
    assert "list must not be empty" in str(exc_info.value)


def test_product_request_empty_uris():
    with pytest.raises(ValidationError) as exc_info:
        ProductRequest(job_id="1234-abcd", concept_id="abc", ogc="def", uris=[])
    assert "uris list must not be empty" in str(exc_info.value)


def test_product_request_blank_collection():
    with pytest.raises(ValidationError) as exc_info:
        ProductRequest(job_id="1234-abcd", concept_id="  ", ogc="ogc-123", uris=["s3://bucket/file"])
    assert "at least 1 character" in str(exc_info.value)

def test_empty_list_ogc():
    product = ProductRequest(
        job_id="1234-abcd",
        concept_id="collection-abc",
        provenance="source:dummy,parameter:dummy",
        ogc=[],
        uris=["s3://bucket/file1.txt", "https://another-bucket/data/file2.csv"],
    )
    assert product.job_id == "1234-abcd"
    assert product.concept_id == "collection-abc"
    assert product.provenance == "source:dummy,parameter:dummy"
    assert len(product.uris) > 0
    assert product.ogc is None