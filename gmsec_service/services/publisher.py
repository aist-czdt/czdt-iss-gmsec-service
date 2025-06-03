from typing import Iterable
from gmsec_service.common.connection import GmsecConnection
import libgmsec_python3 as lp


class GmsecProduct:
    """
    Class for publishing LOG or PRODUCT messages
    """

    PRODUCT_TOPIC = "ESDT.CZDT.ISS.MSG.PROD.PRODUCT-INGEST"

    def __init__(
        self, job_id: str, collection: str, provenance: str, ogc: str, uris: Iterable[str], gmsec: GmsecConnection
    ):
        self.gmsec = gmsec
        self.collection = collection
        self.ogc = ogc
        self.URIs = uris
        self.job_id = job_id
        self.provenance = provenance

    def _construct_product_message(self) -> lp.Message:
        gmsec_msg: lp.Message = self.gmsec.msg_factory.create_message("MSG.PROD")
        gmsec_msg.set_subject(self.PRODUCT_TOPIC)

        gmsec_msg.add_field(lp.F32Field("CONTENT-VERSION", 2024))
        gmsec_msg.add_field(lp.StringField("PROD-NAME", self.collection))
        gmsec_msg.add_field(lp.StringField("PROD-DESCRIPTION", self.ogc))
        gmsec_msg.add_field(lp.StringField("JOB-ID", self.job_id))
        gmsec_msg.add_field(lp.StringField("PROVENANCE", self.provenance))
        gmsec_msg.add_field(lp.U16Field("NUM-OF-FILES", len(self.URIs)))

        for i, uri in enumerate(self.URIs, 1):
            gmsec_msg.add_field(lp.StringField(f"FILE.{i}.URI", uri))
        return gmsec_msg

    def publish_product(self) -> str:
        gmsec_msg = self._construct_product_message()
        lp.log_info("Sending PRODUCT Message:\n" + gmsec_msg.to_xml())
        try:
            self.gmsec.conn.publish(gmsec_msg)
            publish_status = "Successfully published PRODUCT message"
        except Exception as e:
            publish_status = f"Error publishing PRODUCT message: {e}"
        return publish_status


class GmsecLog:
    LEVEL_SEVERITY_MAP = {
        "DEBUG": 0,
        "INFO": 1,
        "WARNING": 2,
        "ERROR": 3,
        "CRITICAL": 4,
    }

    LOG_TOPIC = "ESDT.CZDT.ISS.MSG.LOG.PRODUCT-INGEST"

    def __init__(self, level: str, msg_body: str, gmsec: GmsecConnection):
        self.gmsec = gmsec
        self.level = self._convert_level_severity(level)
        self.msg_body = msg_body

    def _convert_level_severity(self, level: str) -> int:
        """Converts log level to int value ranging 0-4"""
        if level not in self.LEVEL_SEVERITY_MAP.keys():
            raise ValueError(f"Invalid log level. Must be one of {', '.join(self.LEVEL_SEVERITY_MAP.keys())}")
        return self.LEVEL_SEVERITY_MAP[level]

    def _construct_log_message(self) -> lp.Message:
        gmsec_msg: lp.Message = self.gmsec.msg_factory.create_message("LOG")
        gmsec_msg.set_subject(self.LOG_TOPIC)

        gmsec_msg.add_field(lp.F32Field("CONTENT-VERSION", 2024))
        gmsec_msg.add_field(lp.U16Field("SEVERITY", self.level))
        gmsec_msg.add_field(lp.StringField("MSG-TEXT", self.msg_body))
        return gmsec_msg

    def publish_log(self) -> str:
        log_msg = self._construct_log_message()
        lp.log_info("Sending LOG Message:\n" + log_msg.to_xml())
        try:
            self.gmsec.conn.publish(log_msg)
            publish_status = "Successfully published LOG message"
        except Exception as e:
            publish_status = f"Error publishing LOG message: {e}"
        return publish_status
