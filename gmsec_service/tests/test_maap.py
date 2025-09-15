"""
Integration tests for the connection to MAAP.
"""

import os
from maap.maap import MAAP, DPSJob
from dotenv import load_dotenv
import pytest

from gmsec_service.common.job import JobState


@pytest.fixture(scope="session")
def test_maap_client():
    load_dotenv("auth/.env")
    assert os.getenv("MAAP_PGT") is not None, "MAAP_PGT must be set in the .env file"
    maap = MAAP()
    assert maap.profile.account_info() is not None, "Failed to authenticate MAAP client"
    return maap