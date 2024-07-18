import asyncio
import logging
import time
import uuid
from functools import wraps

import click
from temporalio import activity
from temporalio.client import Client

from settings import TemporalClusterSettings
from workflows.call_service_workflow import CallServiceWorkflow
from workflows.call_service_workflow import CallServiceWorkflowInput
from workflows.call_service_workflow import CallServiceWorkflowOutput

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
interrupt_event = asyncio.Event()


def coro(f):
    """Auxiliary decorator to make click commands async be default"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(f(*args, **kwargs))
        except KeyboardInterrupt:
            interrupt_event.set()
            loop.run_until_complete(loop.shutdown_asyncgens())

    return wrapper


@click.command(context_settings={"show_default": True})
@click.option(
    "-ttr",
    "--time-to-request",
    "time_to_request",
    type=int,
    default=1,
    help=("How much time (in seconds) the HTTP Service waits until it returns an HTTP 200 OK response to the activity"),
)
@click.option(
    "-ttc",
    "--time-to-callback",
    "time_to_callback",
    type=int,
    default=10,
    help=(
        "How much time (in seconds) the HTTP Service waits until it makes a callback request to the "
        "Worker HTTP /callback endpoint"
    ),
)
@click.option(
    "-a",
    "--activity-action",
    "activity_action",
    type=click.Choice(["heartbeat", "complete", "fail", "report_cancellation"]),
    default="complete",
    help=(
        "Which activity action do we want the activity to perform. (maps to the different handle options described on "
        "https://docs.temporal.io/develop/python/asynchronous-activity-completion)."
    ),
)
@coro
async def main(time_to_request, time_to_callback, activity_action):
    logger.info(f"{time_to_request=}, {time_to_callback=}, {activity_action=}")

    logger.info("Initializing client...")
    settings = TemporalClusterSettings()
    client = await Client.connect(target_host=settings.host, namespace=settings.namespace)
    logger.info(f'Client initialized! Connected to "{settings.host}"...')

    start_time = time.time()
    # This call is async, so we need to explicitly set an awaitable to get the results
    workflow_id = str(uuid.uuid4())
    logger.info(f"Starting workflow {workflow_id=}...")
    handle = await client.start_workflow(
        workflow=CallServiceWorkflow,
        arg=CallServiceWorkflowInput(
            sleep_until_200=time_to_request, sleep_until_callback=time_to_callback, action=activity_action
        ),
        id=workflow_id,
        task_queue="task-queue",
    )
    activity.logger.info(f"Started workflow. Workflow ID: {handle.id}")
    # Await for results
    result: CallServiceWorkflowOutput = await handle.result()
    logger.info(
        f"Concluded workflow. "
        f"Workflow ID: {handle.id}, RunID {handle.result_run_id}, "
        f"Time Taken {time.time() - start_time}, Result: {result.dict()}"
    )
    return handle, result


if __name__ == "__main__":
    main()
