import json
import os

import yaml
import libgmsec_python3 as lp
from time import sleep
from typing import Optional

from maap.maap import MAAP, DPSJob

from gmsec_service.common.job import JobState


def authenticate_maap(max_retries=5, base_delay=1.0, backoff_factor=2.0):
    # MAAP API uses token stored in MAAP_PGT env var
    if not os.getenv("MAAP_PGT"):
        raise EnvironmentError("Required environment variable 'MAAP_PGT' is not set.")

    for attempt in range(1, max_retries + 1):
        try:
            maap = MAAP()
            if maap.profile and maap.profile.account_info():
                return maap
            else:
                raise RuntimeError("Unable to connect to MAAP with provided token.")
        except Exception as e:
            if attempt == max_retries:
                raise RuntimeError(f"MAAP authentication failed after {max_retries} attempts.") from e

            delay = base_delay * (backoff_factor ** (attempt - 1))
            lp.log_info(f"[Retry {attempt}/{max_retries}] Authentication failed: {e}. Retrying in {delay:.1f}s...")
            sleep(delay)


maap = authenticate_maap()


class GmsecRequestHandler:
    """
    Class for handling GMSEC directive requests and responses
    """

    def __init__(self, directive_keyword: str, directive_string: str):
        self.directive_keyword = directive_keyword
        self.directive_string = directive_string
        try:
            self.directive_string_data: dict = json.loads(directive_string)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError("Unable to decode DIRECTIVE-STRING: not valid JSON.") from e

    def get_job_id(self) -> str:
        """ """
        job_id = self.directive_string_data.get("job-id", "N/A")
        if job_id == "N/A":
            lp.log_warning("Unable to extract job-id from directive string.")
        return job_id

    def get_job_status(self, job_id: str) -> JobState:
        """
        Query MAAP API to get the job status with retry logic if the job status is 'deleted'
        """
        max_retries = 3

        if job_id == "N/A":
            return JobState.from_maap_status("failed", "N/A")

        for attempt in range(max_retries + 1):
            try:
                maap_job_status = maap.getJobStatus(job_id)
            except Exception as e:
                lp.log_error(f"Attempt {attempt + 1}: Failed to get job status for {job_id}: {e}", exc_info=True)
                if attempt < max_retries:
                    sleep(2**attempt)
                    continue
                else:
                    return JobState.from_maap_status("failed", "N/A")

            if maap_job_status and maap_job_status.lower() != "deleted":
                break

            lp.log_warning(f"Attempt {attempt + 1}: Job {job_id} returned 'deleted'. Retrying after {2**attempt}s...")
            sleep(2**attempt)

        else:
            # Still 'deleted' after all retries
            lp.log_error(f"Job {job_id} remained in 'deleted' state after {max_retries + 1} attempts.")
            return JobState.from_maap_status("failed", "N/A")

        lp.log_info(f"Obtained job status '{maap_job_status}' for job {job_id}")
        return JobState.from_maap_status(maap_job_status, job_id)

    def get_ingest_concept_id(self) -> str:
        concept_id = self.directive_string_data.get("concept_id")
        if not concept_id:
            raise ValueError("Unable to extract 'concept_id' from DIRECTIVE-STRING.")
        return concept_id

    def get_ingest_product_path(self) -> str:
        product_path = self.directive_string_data.get("products")
        if not product_path:
            raise ValueError("Unable to extract 'products' from DIRECTIVE-STRING.")
        if len(product_path) > 1:
            raise ValueError(f"Expected 1 product path exctracted from DIRECTIVE-STRING, found {len(product_path)}")
        return product_path[0]

    def get_ingest_product_type(self) -> str:
        product_format = self.directive_string_data.get("format")
        if not product_format:
            raise ValueError("Unable to extract 'format' from DIRECTIVE-STRING.")
        return product_format

    def get_ingest_variables(self) -> Optional[str]:
        product_variables = self.directive_string_data.get("essential_variables")
        return product_variables
    
    def set_ingest_args(self, concept_id: str, product_path: str, ingest_variables: Optional[list[str]]) -> dict[str, str]:
        with open("gmsec_service/handlers/ingest_config.yaml") as f:
            config = yaml.safe_load(f)
            
        default_args = {**config["defaults"],
                        "input_s3": product_path,
                        "collection_id": concept_id}
        
        if "LIS" in product_path:
            if ingest_variables:
                ingest_variables = ["SoilMoist_tavg_0" if v == "SoilMoist_tavg" else v for v in ingest_variables]
            job_args = {**default_args, **config["variants"]["lis"]}
        elif "gpkg" in product_path:
            job_args = {**default_args, **config["variants"]["gpkg"]}
        else:
            job_args = {**default_args, **config["variants"]["base"]}
        
        if ingest_variables:
            job_args["variables"] = ",".join(ingest_variables)
        
        return job_args

    def trigger_ingest(self) -> JobState:
        """
        Hit MAAP API to submit ingest job
        Returns a JobState instance containing job id and status
        """
        concept_id = self.get_ingest_concept_id()
        product_path = self.get_ingest_product_path()
        product_type = self.get_ingest_product_type()
        ingest_variables = self.get_ingest_variables()

        if None in [concept_id, product_path, product_type]:
            raise ValueError("Missing required argument for ingest")

        job_args = self.set_ingest_args(concept_id, product_path, ingest_variables)

        try:
            job: DPSJob = maap.submitJob(**job_args)
        except Exception as e:
            lp.log_error(f"Unable to submit job {e}")
            return JobState.from_maap_status("failed", "N/A")

        if job.status == "success":
            return JobState.from_maap_status("accepted", job.id)
        return JobState.from_maap_status(job.status, job.id)
