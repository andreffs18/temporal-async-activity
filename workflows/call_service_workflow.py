import logging
from datetime import timedelta

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

with workflow.unsafe.imports_passed_through():
    from activities.async_activity import AsyncActivityInput
    from activities.async_activity import AsyncActivityName
    from activities.async_activity import AsyncActivityOutput


class CallServiceWorkflowInput(BaseModel):
    sleep_until_200: int
    sleep_until_callback: int
    action: str


class CallServiceWorkflowOutput(BaseModel):
    pass


@workflow.defn
class CallServiceWorkflow:
    @workflow.run
    async def run(self, workflow_input: CallServiceWorkflowInput) -> CallServiceWorkflowOutput:
        logger.info(f"Executing Workflow with {workflow_input=}")

        activity_output: AsyncActivityOutput = await workflow.execute_activity_method(
            # STEP
            activity=AsyncActivityName,
            # INPUT
            arg=AsyncActivityInput(
                sleep_until_200=workflow_input.sleep_until_200,
                sleep_until_callback=workflow_input.sleep_until_callback,
                action=workflow_input.action,
            ),
            # TASK QUEUE
            task_queue="task-queue",
            # TIMEOUT
            # Schedule-To-Close Timeout: is the maximum amount of time allowed for the overall Activity Execution.
            start_to_close_timeout=timedelta(seconds=60),
            # RETRY POLICY
            retry_policy=RetryPolicy(
                backoff_coefficient=2.0,
                maximum_attempts=10,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=16),
            ),
            # HEARTBEAT
            # heartbeat_timeout=timedelta(seconds=10),
        )
        logger.info(f"Done! {activity_output=}")
        return CallServiceWorkflowOutput()
