"""
Integration tests for the connection to MAAP.
"""

import os
import html
from maap.maap import MAAP, DPSJob
from dotenv import load_dotenv
import pytest

from gmsec_service.common.job import JobState
from gmsec_service.handlers.directive_handler import GmsecRequestHandler


@pytest.fixture(scope="session")
def maap_client():
    load_dotenv("auth/.env")
    assert os.getenv("MAAP_PGT") is not None, "MAAP_PGT must be set in the .env file"
    maap = MAAP()
    assert maap.profile.account_info() is not None, "Failed to authenticate MAAP client"
    return maap

def test_maap_ingest_args(maap_client: MAAP):
    directive_keyword = "SUBMIT-JOB"
    directive_string = html.unescape("{&quot;concept_id&quot;: &quot;daily_flood_prediction&quot;, &quot;products&quot;: [&quot;s3://czdt-nfss/output_data/SURFACEMODEL/202509/LIS_HIST_202509150300.d01.nc&quot;], &quot;format&quot;: &quot;netcdf&quot;, &quot;essential_variables&quot;: [&quot;SoilMoist_tavg&quot;, &quot;TotalPrecip_tavg&quot;]}")
    request_handler = GmsecRequestHandler(directive_keyword, directive_string)
    
    concept_id = request_handler.get_ingest_concept_id()
    product_path = request_handler.get_ingest_product_path()
    product_type = request_handler.get_ingest_product_type()
    ingest_variables = request_handler.get_ingest_variables()
    
    assert concept_id == "daily_flood_prediction"
    assert product_path == "s3://czdt-nfss/output_data/SURFACEMODEL/202509/LIS_HIST_202509150300.d01.nc"
    
    ingest_args = request_handler.set_ingest_args(concept_id, product_path, ingest_variables)
    assert ingest_args["variables"] == "SoilMoist_tavg_0,TotalPrecip_tavg"

    for k,v in ingest_args.items():
        assert v not in [None, "none"]
        
def test_maap_ingest_LIS_ROUTING(maap_client: MAAP):
    directive_keyword = "SUBMIT-JOB"
    directive_string = html.unescape("{&quot;concept_id&quot;: &quot;daily_flood_prediction&quot;, &quot;products&quot;: [&quot;s3://czdt-nfss/output_data/ROUTING/202509/LIS_HIST_202509161900.d01.nc&quot;], &quot;format&quot;: &quot;netcdf&quot;, &quot;essential_variables&quot;: [&quot;SurfElev_tavg&quot;, &quot;FloodedFrac_tavg&quot;]}")
    request_handler = GmsecRequestHandler(directive_keyword, directive_string)
        
    concept_id = request_handler.get_ingest_concept_id()
    product_path = request_handler.get_ingest_product_path()
    product_type = request_handler.get_ingest_product_type()
    ingest_variables = request_handler.get_ingest_variables()
    
    ingest_args = request_handler.set_ingest_args(concept_id, product_path, ingest_variables)

    assert concept_id == "daily_flood_prediction"
    assert product_path == "s3://czdt-nfss/output_data/ROUTING/202509/LIS_HIST_202509161900.d01.nc"
    assert ingest_args["variables"] == "SurfElev_tavg,FloodedFrac_tavg"
    
    # try:
    #     job: DPSJob = maap_client.submitJob(**ingest_args)
    # except Exception as e:
    #     print(e)
        # 
    # print(job.id, job.status)
    
def test_maap_job_status(maap_client: MAAP):
    job_id = "a2eab7a9-f155-4b6d-8cd1-574350ed34f0"
    job_status = maap_client.getJobStatus(job_id)
    print(job_status)