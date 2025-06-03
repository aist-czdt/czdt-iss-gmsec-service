from typing import List, Optional, Annotated
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager

from pydantic import BaseModel, StringConstraints, field_validator

from gmsec_service.services.publisher import GmsecProduct, GmsecLog
from gmsec_service.common.connection import GmsecConnection


gmsec_connection: Optional[GmsecConnection] = None

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class LogRequest(BaseModel):
    level: NonEmptyStr
    msg_body: NonEmptyStr

    @field_validator("level")
    def validate_level(cls, v: str) -> str:
        allowed_levels = GmsecLog.LEVEL_SEVERITY_MAP.keys()
        if v.upper() not in allowed_levels:
            raise ValueError(f"Invalid log level '{v}'. Must be one of: {', '.join(allowed_levels)}")
        return v.upper()


class ProductRequest(BaseModel):
    job_id: NonEmptyStr
    collection: NonEmptyStr
    provenance: NonEmptyStr
    ogc: NonEmptyStr
    uris: List[NonEmptyStr]

    @field_validator("uris")
    def validate_s3_uris(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("uris list must not be empty")
        for uri in v:
            if not uri.startswith("s3://"):
                raise ValueError(f"Invalid URI: '{uri}'. Must start with 's3://'")
        return v


@asynccontextmanager
async def lifespan(app: FastAPI):
    global gmsec_connection
    gmsec_connection = GmsecConnection("config/config-prod.xml")
    yield
    if gmsec_connection:
        gmsec_connection.conn.disconnect()


app = FastAPI(lifespan=lifespan)


def get_gmsec_connection() -> GmsecConnection:
    if not gmsec_connection:
        raise RuntimeError("GMSEC connection is not initialized")
    return gmsec_connection


@app.post("/product")
def publish_product(product: ProductRequest, gmsec: GmsecConnection = Depends(get_gmsec_connection)):
    gmsec_product = GmsecProduct(
        product.job_id, product.collection, product.provenance, product.ogc, product.uris, gmsec
    )
    publish_status = gmsec_product.publish_product()
    return {"status": publish_status}


@app.post("/log")
def log_message(log: LogRequest, gmsec: GmsecConnection = Depends(get_gmsec_connection)):
    gmsec_log = GmsecLog(log.level, log.msg_body, gmsec)
    publish_status = gmsec_log.publish_log()
    return {"status": publish_status}
