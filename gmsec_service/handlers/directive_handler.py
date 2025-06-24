import json
import os
import libgmsec_python3 as lp

from maap.maap import MAAP, DPSJob

from gmsec_service.common.job import JobState


class GmsecRequestHandler:
    """
    Parent class for containing GMSEC directive fields
    """

    def __init__(self, directive_keyword: str, directive_string: str):
        self.directive_keyword = directive_keyword
        self.directive_string = directive_string
        try:
            self.directive_string_data: dict = json.loads(directive_string)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(
                "Unable to decode DIRECTIVE-STRING: not valid JSON."
            ) from e

        # MAAP API uses token stored in MAAP_PGT env var
        if not os.getenv("MAAP_PGT"):
            raise EnvironmentError(
                "Required environment variable 'MAAP_PGT' is not set."
            )

        self.maap = MAAP()

        if not self.maap.profile or not self.maap.profile.account_info():
            raise RuntimeError("Unable to connect to MAAP with provided token.")


class GmsecJobStatus(GmsecRequestHandler):
    def __init__(self, directive_keyword, directive_string):
        super().__init__(directive_keyword, directive_string)

    def get_job_id(self) -> str:
        """ """
        job_id = self.directive_string_data.get("job-id")
        if not job_id:
            raise ValueError("Unable to extract 'job-id' from DIRECTIVE-STRING.")
        return job_id

    def get_job_status(self, job_id: str) -> JobState:
        """
        Hit MAAP API to get status of job
        """
        try:
            maap_job_status = self.maap.getJobStatus(job_id)
            lp.log_info(f"Obtained job status {maap_job_status} for job {job_id}")
            return JobState.from_maap_status(maap_job_status, job_id)
        except Exception as e:
            lp.log_error(f"Unable to obtain job status: {e}")
            raise


class GmsecSubmitJob(GmsecRequestHandler):
    def __init__(self, directive_keyword, directive_string):
        super().__init__(directive_keyword, directive_string)

    def get_ingest_params(self) -> dict:
        ingest_params = {}
        return ingest_params

    def get_ingest_product_path(self) -> str:
        product_path = self.directive_string_data.get("products")
        if not product_path:
            raise ValueError("Unable to extract 'products' from DIRECTIVE-STRING.")
        if len(product_path) > 1:
            raise ValueError(f"Expected 1 product path exctracted from DIRECTIVE-STRING, found {len(product_path)}")
        return product_path[0]
    
    def get_ingest_product_type(self) ->str:
        # TODO: directive string will contain a "format" field which will dictate
        # which ingest workflow to use
        product_format = self.directive_string_data.get("format")
        if not product_format:
            raise ValueError("Unable to extract 'format' from DIRECTIVE-STRING.")
        return product_format

    def trigger_ingest(self) -> JobState:
        """
        Hit MAAP API to submit ingest job
        Returns a JobState instance containing job id and status
        """
        product_path = self.get_ingest_product_path()
        product_type = self.get_ingest_product_type()
        
        try:
            job: DPSJob = self.maap.submitJob(
                identifier="gmsec-directive-ingest",
                algo_id="czdt-iss-ingest",
                version="main",
                queue="maap-dps-czdt-worker-8gb",
                file_uri=product_path,
                s3_bucket="czdt-hysds-dataset",
                s3_prefix="ingest",
                role_arn="arn:aws:iam::011528287727:role/czdt-hysds-verdi-role",
            )

            return JobState.from_maap_status(job.status, job.id)
        except Exception as e:
            lp.log_error(f"Unable to submit job {e}")
            raise
