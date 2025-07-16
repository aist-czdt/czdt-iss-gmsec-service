import logging

from typing import List, Optional, Annotated, Union
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager

from pydantic import BaseModel, StringConstraints, model_validator, field_validator, Field

from gmsec_service.services.publisher import GmsecProduct, GmsecLog
from gmsec_service.common.connection import GmsecConnection

logger = logging.getLogger("publisher_api")

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
    provenance: NonEmptyStr = Field(default="default", description="Data provenance string")
    ogc: NonEmptyStr = Field(..., description="OGC path (string or list; normalized to single string)")
    uris: List[NonEmptyStr]

    @field_validator("uris")
    def validate_s3_uris(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("uris list must not be empty")
        for uri in v:
            if not uri.startswith("s3://"):
                raise ValueError(f"Invalid URI: '{uri}'. Must start with 's3://'")
        return v

    @model_validator(mode="before")
    @classmethod
    def normalize_ogc(cls, data):
        raw_ogc = data.get("ogc")

        if raw_ogc is None:
            raise ValueError("ogc field is required and cannot be null")

        if isinstance(raw_ogc, list):
            if not raw_ogc:
                raise ValueError("ogc list must not be empty")
            raw_ogc = raw_ogc[0]
        
        if not isinstance(raw_ogc, str) or not raw_ogc.strip():
            raise ValueError("ogc must be a non-empty string")

        data["ogc"] = raw_ogc.strip()
        return data

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
    logger.info(f"Received /product request: {product.json()}")
    gmsec_product = GmsecProduct(
        product.job_id, product.collection, product.provenance, product.ogc, product.uris, gmsec
    )
    publish_status = gmsec_product.publish_product()
    return {"status": publish_status}


@app.post("/log")
def log_message(log: LogRequest, gmsec: GmsecConnection = Depends(get_gmsec_connection)):
    logger.info(f"Received /log request: {log.json()}")
    gmsec_log = GmsecLog(log.level, log.msg_body, gmsec)
    publish_status = gmsec_log.publish_log()
    return {"status": publish_status}
