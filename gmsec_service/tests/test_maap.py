"""
Integration tests for the connection to MAAP.
"""

import os
from maap.maap import MAAP, DPSJob
from dotenv import load_dotenv
import pytest

from gmsec_service.common.job import JobState


@pytest.fixture(scope="session")
def maap_client():
    load_dotenv("auth/.env")
    assert os.getenv("MAAP_PGT") is not None, "MAAP_PGT must be set in the .env file"
    maap = MAAP()
    assert maap.profile.account_info() is not None, "Failed to authenticate MAAP client"
    return maap


def test_job_submission(maap_client: MAAP):
    job: DPSJob = maap_client.submitJob(
        identifier="merra2-test",
        algo_id="czdt-iss-ingest",
        version="main",
        queue="maap-dps-czdt-worker-8gb",
        granule_id="M2T1NXFLX.5.12.4:MERRA2_400.tavg1_2d_flx_Nx.20250401.nc4",
        collection_id="C1276812838-GES_DISC",
        s3_bucket="czdt-hysds-dataset",
        s3_prefix="ingest",
        role_arn="arn:aws:iam::011528287727:role/czdt-hysds-verdi-role",
    )

    assert job.id is not None
    assert job.status.lower() in JobState.status_map.keys()


def test_job_status(maap_client: MAAP):
    job_id = "684a2f26-46da-4635-af59-3b36aa69e494"
    job_status = maap_client.getJobStatus(job_id)
    assert job_status.lower() in JobState.status_map.keys()
