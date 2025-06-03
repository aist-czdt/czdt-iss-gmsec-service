from datetime import datetime
import logging
import time
import requests
import libgmsec_python3 as lp
from gmsec_service.common.connection import GmsecConnection


class ServiceStatus:
    def __init__(self, url):
        self.url = url
        self.status = None

    def check_status(self):
        try:
            response = requests.get(self.url, timeout=15)
            response.raise_for_status()
            self.status = True
        except requests.exceptions.RequestException:
            self.status = False
        return self.status


class GmsecHeartbeat:
    """
    Class for emitting ISS heartbeat
    """

    def __init__(self, env: str = "PROD"):
        if env == "PROD":
            config = "config/config-prod.xml"
        elif env == "DEV":
            config = "config/config-dev.xml"

        self.gmsec = GmsecConnection(config)

        self.publish_rate = int(self.gmsec.config.get_value("heartbeat-pub-rate"))

    def run(self):
        try:
            hbgen = lp.HeartbeatGenerator(
                self.gmsec.config,
                self.publish_rate,
                self.gmsec.get_standard_fields(),
            )

            hbgen.start()

            msg: lp.Message = self.gmsec.msg_factory.create_message("HB")
            counter = 1

            while True:
                try:
                    # Get status of SDAP
                    # sdap_status_check = ServiceStatus(self.config.get_value("sdap-hb-url"))
                    # sdap_status = sdap_status_check.check_status()
                    sdap_status = True

                    # Get status of HySDS
                    # hysds_status_check = ServiceStatus(self.config.get_value("hysds-hb-url"))
                    # hysds_status = hysds_status_check.check_status()
                    hysds_status = True

                    # Get status of titiler
                    # titiler_status_check = ServiceStatus(self.config.get_value("titiler-hb-url"))
                    # titiler_status = titiler_status_check.check_status()
                    titiler_status = True

                    # Get overall INFO status
                    iass_status = all([sdap_status, hysds_status, titiler_status])
                    dt_string = datetime.now().isoformat(timespec="seconds")
                    if iass_status:
                        status_msg = f"ISS - System running at {dt_string}"
                        status = True
                    else:
                        status_msg = f"ISS - System unavailable at {dt_string}"
                        status = False

                    if status:
                        msg.add_field(lp.I16Field("COMPONENT-STATUS", 1))
                    else:
                        msg.add_field(lp.I16Field("COMPONENT-STATUS", 2))

                    msg.add_field(lp.U16Field("COUNTER", counter))
                    msg.add_field(lp.U16Field("PUB-RATE", self.publish_rate))

                    # Publish the message
                    self.gmsec.conn.publish(msg)

                    # Output in XML what we have published
                    lp.log_info("Publishing Message:\n" + msg.to_xml())

                    time.sleep(self.publish_rate)
                    counter += 1

                except KeyboardInterrupt:
                    print("\nCtrl+C was pressed. Exiting...")
                    break

        except lp.GmsecError as e:
            lp.log_error("Exception: " + str(e))

        # Tear down GMSEC
        self.gmsec.teardown()


if __name__ == "__main__":
    hb_gen = GmsecHeartbeat()
    hb_gen.run()
