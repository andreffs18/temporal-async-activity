import base64
import logging
from typing import Optional

from pydantic import AnyUrl
from pydantic import BaseModel
from temporalio import activity
from temporalio.client import Client

from gateways.http_api_gateway import HttpApiClient
from settings import TemporalWorkerSettings

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


AsyncActivityName: str = "async-activity"


class AsyncActivityInput(BaseModel):
    sleep_until_200: int
    sleep_until_callback: int
    action: Optional[str]
    callback_url: Optional[AnyUrl] = None


class AsyncActivityOutput(BaseModel):
    this_is_a_type: str
    and_a_boolean: bool


class AsyncActivity:
    # information to be able to use on `callback` method
    request_info: str = None

    def __init__(self, temporal_client: Client, api_client: HttpApiClient, worker_settings: TemporalWorkerSettings):
        self.temporal_client = temporal_client
        self.api_client = api_client
        self.worker_settings = worker_settings

    @activity.defn(name=AsyncActivityName)
    async def run(self, step_input: AsyncActivityInput) -> AsyncActivityOutput:
        # We need to send a token with that request so we can continue this execution later on.
        activity_token = activity.info().task_token
        # Needs to be encoded so it can be used as query parameter
        token = base64.b64encode(activity_token).decode("utf-8")
        step_input.callback_url = f"{self.worker_settings.http_callback}?token={token}"

        # Make HTTP request to Async Service
        response = await self.api_client.post_request(payload=step_input.dict())
        self.request_info = response.json()

        # Raise the complete-async error which will complete this execution but does not consider the activity
        # complete from the workflow perspective
        activity.raise_complete_async()

    async def callback(self, task_token: str, data: dict) -> None:
        logger.info(f"Inside callback function with {task_token=}")
        # Decode token back to its binary format
        task_token = base64.b64decode(task_token.encode("utf-8"))
        handle = self.temporal_client.get_async_activity_handle(task_token=task_token)

        # Do some business logic to handle this callback
        # _something something_
        logger.info(f"Peek at what we have:\n{self.request_info=}\n{data=}")

        # Complete activity
        if data.get("action") == "complete":
            logger.info('Doing a "complete" action to this activity.')
            await handle.complete(AsyncActivityOutput(this_is_a_type="type", and_a_boolean=True))

        elif data.get("action") == "heartbeat":
            logger.info('Doing a "heartbeat" action to this activity.')
            await handle.heartbeat('Doing a "heartbeat" action to this activity.')

        elif data.get("action") == "fail":
            logger.info('Doing a "fail" action to this activity.')
            await handle.fail(ValueError('Doing a "fail" action to this activity.'))

        elif data.get("action") == "report_cancellation":
            logger.info('Doing a "cancel" action to this activity.')
            await handle.report_cancellation('Doing a "cancel" action to this activity.')

        else:
            # what if we dont do nothing?
            logger.info("Doing nothing to this activity")
            pass
