import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import Body
from fastapi import FastAPI
from fastapi import Query
from temporalio.client import Client
from temporalio.worker import Worker

from activities.async_activity import AsyncActivity
from gateways.http_api_gateway import HttpApiClient
from gateways.http_api_gateway import HttpApiSettings
from settings import TemporalClusterSettings
from settings import TemporalWorkerSettings
from workflows.call_service_workflow import CallServiceWorkflow

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

interrupt_event = asyncio.Event()


async def main():
    """Commandline tool to start a Temporal Worker that executes Workflows and Activities"""
    logger.info("Initializing Client...")
    settings = TemporalClusterSettings()
    client = await Client.connect(target_host=settings.host, namespace=settings.namespace)
    logger.info(f'Client initialized! (connected to "{settings.host}")')

    logger.info("Initializing Worker...")
    http_api_client = HttpApiClient(settings=HttpApiSettings())
    worker_settings = TemporalWorkerSettings()
    activity = AsyncActivity(temporal_client=client, api_client=http_api_client, worker_settings=worker_settings)

    async with Worker(
        client=client,
        task_queue="task-queue",
        workflows=[CallServiceWorkflow],
        activities=[activity.run],
    ):
        # Wait until interrupted
        logger.info(f"Worker {activity.worker_settings.identity} initialized! Press ctrl+c to exit.")
        await create_webserver(activity=activity, logger=logger)
        # Commenting usual interrupt since we achieve the same with the webserver
        # await asyncio.gather(*[interrupt_event.wait()])
        logger.info("Shutting down")
    logger.info("Bye!")


async def create_webserver(activity: Any, logger: logging.Logger):
    logger.info("Initializing Webserver...")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Setup context manager for HTTP server to have Activity callback method in its context"""
        app.state.logger = logger
        app.state.callback = activity.callback
        yield

    app = FastAPI(lifespan=lifespan)

    @app.post("/callback")
    async def handle_callback(token: str = Query(""), payload: dict = Body(...)):
        """This callback simply picks up the token (TBD and payload) and passes it to the activity callback method"""
        app.state.logger.info(f"Callback received: {token}")
        await app.state.callback(task_token=token, data=payload)
        return {"message": "Callback received. Thank you."}

    host = activity.worker_settings.http_host
    port = activity.worker_settings.http_port
    config = uvicorn.Config(app, host, port)
    server = uvicorn.Server(config)
    logger.info(f'Webserver "{activity.worker_settings.identity}" initialized! Press ctrl+c to exit.')
    await server.serve()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
