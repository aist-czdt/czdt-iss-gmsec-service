import json
import logging
import time
import libgmsec_python3 as lp
from gmsec_service.common.connection import GmsecConnection
from gmsec_service.common.job import JobState
from gmsec_service.handlers.directive_handler import GmsecJobStatus, GmsecSubmitJob
from gmsec_service.services.publisher import GmsecLog


class GmsecListener:
    def __init__(self, env: str = "PROD"):
        if env == "PROD":
            config = "config/config-prod.xml"
        elif env == "DEV":
            config = "config/config-dev.xml"

        self.subscription_name = "CMSS-REQUESTS-SUBSCRIPTION"

        self.gmsec = GmsecConnection(config)

        self.subscription_pattern = self.gmsec.get_subscription_pattern(self.subscription_name)

    def handle_request(self, request_msg: lp.Message):
        try:
            # Received a message!
            lp.log_info("Received Message:\n" + request_msg.to_xml())

            # Ensure required fields
            for field in ("DIRECTIVE-KEYWORD", "DIRECTIVE-STRING"):
                if not request_msg.has_field(field):
                    raise ValueError(f"Missing required field {field}")

            directive_keyword = request_msg.get_string_value("DIRECTIVE-KEYWORD")
            directive_string = request_msg.get_string_value("DIRECTIVE-STRING")

            if directive_keyword == "JOB-STATUS":
                request_handler = GmsecJobStatus(directive_keyword, directive_string)
                try:
                    job_id = request_handler.get_job_id()
                    job_status = request_handler.get_job_status(job_id)
                except Exception as e:
                    logging.exception(e)

            elif directive_keyword == "SUBMIT-JOB":
                request_handler = GmsecSubmitJob(directive_keyword, directive_string)
                try:
                    job_status = request_handler.trigger_ingest()
                except Exception as e:
                    logging.exception(e)

            else:
                raise ValueError(f"Unsupported DIRECTIVE-KEYWORD: {directive_keyword}")

            lp.log_info(f"Constructing Reply: job_id {job_status.job_id} job_status {job_status.status_label}")

            # Construct a response
            response_msg = self.build_response(job_status, request_msg.get_field("REQUEST-ID"))

            lp.log_info("Sending Response:\n" + response_msg.to_xml())

            self.gmsec.conn.reply(request_msg, response_msg)

            request_msg.acknowledge()

        finally:
            lp.Message.destroy(request_msg)

    def build_response(self, job_status: JobState, request_id_field: lp.Field) -> lp.Message:
        """
        Builds response message from JobState object along with request message's id Field object
        """
        response_data = {
            "job-id": job_status.job_id,
            "job-status": job_status.status_label,
        }

        response_msg: lp.Message = self.gmsec.msg_factory.create_message("RESP.DIR")
        response_msg.add_field(request_id_field)
        response_msg.add_field(lp.I16Field("RESPONSE-STATUS", job_status.status_code))
        response_msg.add_field(lp.StringField("DATA-STRING", json.dumps(response_data)))
        response_msg.add_field(lp.StringField("DESTINATION-COMPONENT", "PRODUCT-MONITOR", True))
        return response_msg

    def run(self):
        try:
            log_msg = "GMSEC listener initialized. Waiting to receive directive requests."
            log_publisher = GmsecLog("INFO", log_msg, self.gmsec)
            log_publisher.publish_log()

            timeout = lp.GMSEC_WAIT_FOREVER

            # Set up subscription
            self.gmsec.conn.subscribe(self.subscription_pattern)

            # Wait for message to come in
            while True:
                try:
                    request_msg: lp.Message = self.gmsec.conn.receive(timeout)

                    if request_msg is not None:
                        self.handle_request(request_msg)

                    time.sleep(1)
                except KeyboardInterrupt:
                    print("\nCtrl+C was pressed. Exiting...")
                    break

        except lp.GmsecError as e:
            lp.log_error("Exception: " + str(e))
            log_msg = "Error in GMSEC listener. Please check status."
            log_publisher = GmsecLog("ERROR", log_msg, self.gmsec)
            log_publisher.publish_log()
        finally:
            # Tear down GMSEC
            self.gmsec.teardown()


if __name__ == "__main__":
    listener = GmsecListener()
    listener.run()
