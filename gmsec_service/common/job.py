from dataclasses import dataclass


@dataclass
class JobState:
    """
    Class for containing MAAP job ID and its mapped GMSEC status and code.
    """

    job_id: str
    status_label: str
    status_code: int

    status_map = {
        "accepted": "SUBMITTED",
        "running": "IN_PROGRESS",
        "succeeded": "COMPLETED",
        "failed": "FAILED",
        "job-revoked": "FAILED",
    }

    status_code_map = {
        "SUBMITTED": 1,
        "IN_PROGRESS": 2,
        "COMPLETED": 3,
        "FAILED": 4,
        "INVALID": 5,
    }

    @classmethod
    def from_maap_status(cls, maap_status: str, job_id: str) -> "JobState":
        label = cls.status_map.get(maap_status.lower(), "INVALID")
        code = cls.status_code_map.get(label, 5)
        return cls(job_id=job_id, status_label=label, status_code=code)
