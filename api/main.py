from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
import logging
from typing import Dict, Any

app = FastAPI()
PUBLISHER_URL = "http://iss.publisher:9000"
REQUEST_TIMEOUT = 30.0  # seconds

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/health", tags=["Health"])
async def health_check():
    return JSONResponse(status_code=200, content={"status": "ok"})


async def proxy_request(endpoint: str, data: Dict[Any, Any]) -> JSONResponse:
    """Generic proxy function to handle requests to publisher service."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PUBLISHER_URL}/{endpoint}", json=data, timeout=REQUEST_TIMEOUT
            )

        # Return the same status code and response from the publisher
        return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.TimeoutException:
        logger.error(f"Timeout when proxying to {endpoint}")
        raise HTTPException(status_code=504, detail="Gateway timeout")
    except httpx.RequestError as e:
        logger.error(f"Error proxying request to {endpoint}: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/product")
async def proxy_product(request: Request):
    """Proxy /product POST requests to the iss.publisher service."""
    try:
        data = await request.json()
    except Exception as e:
        logger.warning(f"Failed to parse JSON body: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    logger.info(f"Received product request: {data}")
    return await proxy_request("product", data)


@app.post("/log")
async def proxy_log(request: Request):
    """Proxy /log POST requests to the iss.publisher service."""
    try:
        data = await request.json()
    except Exception as e:
        logger.warning(f"Failed to parse JSON body: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    logger.info(f"Received log request: {data}")
    return await proxy_request("log", data)
