import asyncio
import logging

import httpx
import uvicorn
from fastapi import BackgroundTasks
from fastapi import Body
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic import BaseSettings
from pydantic import Field

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


class Settings(BaseSettings):
    http_host: str
    http_port: int

    class Config:
        env_prefix = "service_"
        case_insensitive = True


class Payload(BaseModel):
    sleep_until_200: int = Field(..., description="Time it takes to /request endpoint to return HTTP 200 OK.")
    sleep_until_callback: int = Field(
        ...,
        description="Time it takes to make the callback request back to `callback_url`, "
        "after the /request endpoint has returned HTTP 200 OK.",
    )
    callback_url: str = Field(
        ..., description="URL provided by the client of /request. Used to send the callback request to."
    )
    action: str = Field(..., description="Action to be returned to client requester.")


def create_app():
    """Creates a simple FastAPI application that exposes a single POST /request endpoint.
    This only logs the request and adds to a BackgroundTask the callback request.
    You can control how much time the request to "POST /request" takes to return 200 (`sleep`), and how much time the
    BackgroundTask will wait until requesting the `callback_url`
    """
    app = FastAPI()

    @app.api_route("/request", methods=["POST"])
    async def request(background_tasks: BackgroundTasks, payload: Payload = Body(...)) -> JSONResponse:
        logger.info(f"POST /request with {payload=}")
        logger.info(f"Sleeping for {payload.sleep_until_200=} seconds...")
        await asyncio.sleep(payload.sleep_until_200)
        background_tasks.add_task(callback, *(payload.callback_url, payload.sleep_until_callback, payload.action))
        logger.info("Cya!")
        return JSONResponse({"message": "ok"}, status_code=200)

    return app


async def callback(callback_url: str, sleep_until_callback: int, action: str) -> None:
    logger.info(f"Sleeping {sleep_until_callback=} secs until we make a callback to {callback_url=}...")
    await asyncio.sleep(sleep_until_callback)

    try:
        logger.info(f"Making callback to {callback_url=} with {action=}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=callback_url,
                headers={"Content-Type": "application/json"},
                json={
                    "action": action,
                    "message": f"This is the callback response after {sleep_until_callback} seconds.",
                },
            )
        logger.info(f"Callback response: {response=}")
    except Exception as e:
        logger.info(f"Failed to send callback: {e}")


app = create_app()

if __name__ == "__main__":
    settings = Settings()
    uvicorn.run(app, host=settings.http_host, port=settings.http_port)
