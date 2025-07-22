import sys
import json
import logging
import time
import html
import libgmsec_python3 as lp
from gmsec_service.common.connection import GmsecConnection
from gmsec_service.common.job import JobState
from gmsec_service.handlers.directive_handler import GmsecRequestHandler
from gmsec_service.services.publisher import GmsecLog


class GmsecListener:
    def __init__(self, env: str = "PROD"):
        if env == "PROD":
            self.config = "config/config-prod.xml"
        elif env == "DEV":
            self.config = "config/config-dev.xml"
        else:
            raise ValueError(f"Unknown environment: {env}")

        self.subscription_name = "CMSS-REQUESTS-SUBSCRIPTION"

        self.gmsec = None
        self.subscription_pattern = None
        
        self.initialize_connection()

    def initialize_connection(self):
        if self.gmsec:
            try:
                self.gmsec.teardown()
            except Exception as e:
                lp.log_warning(f"Error during teardown: {e}")

        self.gmsec = GmsecConnection(self.config)
        self.subscription_pattern = self.gmsec.get_subscription_pattern(self.subscription_name)
        self.gmsec.conn.subscribe(self.subscription_pattern)
        lp.log_info("GMSEC connection initialized and subscription set.")

    def handle_request(self, request_msg: lp.Message):
        try:
            # Received a message!
            lp.log_info("Received Message:\n" + request_msg.to_xml())

            # Ensure required fields
            for field in ("DIRECTIVE-KEYWORD", "DIRECTIVE-STRING"):
                if not request_msg.has_field(field):
                    raise ValueError(f"Missing required field {field}")

            directive_keyword = request_msg.get_string_value("DIRECTIVE-KEYWORD")
            raw_directive_string = request_msg.get_string_value("DIRECTIVE-STRING")
            directive_string = html.unescape(raw_directive_string)

            request_handler = GmsecRequestHandler(directive_keyword, directive_string)

            if directive_keyword == "JOB-STATUS":
                try:
                    job_id = request_handler.get_job_id()
                    job_status = request_handler.get_job_status(job_id)
                except Exception as e:
                    logging.exception(e)

            elif directive_keyword == "SUBMIT-JOB":
                try:
                    job_status = request_handler.trigger_ingest()
                except Exception as e:
                    logging.exception(e)

            else:
                raise ValueError(f"Unsupported DIRECTIVE-KEYWORD: {directive_keyword}")
            
            # Ensure job is not a transient job failure before sending response
            if job_status.status_label == "FAILED":
                lp.log_info(f"Job {job_status.job_id} has FAILED status. Ensuring failure isn't transient before replying...")
                time.sleep(2)
                job_status = request_handler.get_job_status(job_status.job_id)

            lp.log_info(f"Constructing Reply: job_id {job_status.job_id} job_status {job_status.status_label}")

            # Construct a response
            response_msg = self.build_response(job_status, request_msg.get_field("REQUEST-ID"))
            if request_msg.has_field("COMPONENT"):
                response_msg.add_field(lp.StringField("DESTINATION-COMPONENT", request_msg.get_string_value("COMPONENT"),True))

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
        return response_msg

    def run(self):
        log_msg = "GMSEC listener initialized. Waiting to receive directive requests."
        log_publisher = GmsecLog("INFO", log_msg, self.gmsec)
        log_publisher.publish_log()

        timeout = 5000  # 5 seconds

        while True:
            try:
                request_msg = self.gmsec.conn.receive(timeout)

                if request_msg is not None:
                    self.handle_request(request_msg)

                time.sleep(0.5)

            except lp.GmsecError as e:
                lp.log_error(f"GMSEC error: {e}")
                log_publisher = GmsecLog("ERROR", f"GMSEC connection error: {e}", self.gmsec)
                log_publisher.publish_log()

                # Attempt to reconnect
                success = False
                retries = 0
                max_retries = 10
                
                while not success and retries < max_retries:
                    try:
                        lp.log_info("Attempting GMSEC reconnection...")
                        self.initialize_connection()
                        success = True
                        lp.log_info("GMSEC reconnection successful.")
                    except Exception as retry_error:
                        retries += 1
                        lp.log_error(f"Reconnect failed: {retry_error}")
                        time.sleep(5)
                        
                if not success:
                    lp.log_error("Max reconnect attempts reached. Exiting container.")
                    sys.exit(1)  # Let Docker Compose restart us

            except KeyboardInterrupt:
                print("\nCtrl+C was pressed. Exiting...")
                break

        self.gmsec.teardown()


if __name__ == "__main__":
    listener = GmsecListener()
    listener.run()
