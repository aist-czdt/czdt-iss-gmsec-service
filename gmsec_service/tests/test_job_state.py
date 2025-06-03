from gmsec_service.common.job import JobState


def test_job_state():
    maap_status = "Success"
    job_id = "684a2f26-46da-4635-af59-3b36aa69e494"
    job_state = JobState.from_maap_status(maap_status, job_id)

    assert job_state.job_id == job_id
    assert job_state.status_label == "COMPLETED"
    assert job_state.status_code == 3
