from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from agents.sandbox.sandboxes import UnixLocalSandboxClient
from temporalio.client import Client
from temporalio.contrib.openai_agents import (
    ModelActivityParameters,
    OpenAIAgentsPlugin,
    SandboxClientProvider,
)
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from agents_lab.activities import export_result, prepare_workspace
from agents_lab.config import load_settings
from agents_lab.model import configure_openrouter
from agents_lab.workflows.zip_inspect import ZipInspectWorkflow

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    settings = load_settings()
    _, model_provider = configure_openrouter(settings)
    settings.workspaces_dir.mkdir(parents=True, exist_ok=True)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)

    plugin = OpenAIAgentsPlugin(
        model_params=ModelActivityParameters(
            start_to_close_timeout=timedelta(minutes=3),
        ),
        model_provider=model_provider,
        sandbox_clients=[SandboxClientProvider("local", UnixLocalSandboxClient())],
        add_temporal_spans=False,
    )

    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        plugins=[plugin],
    )

    worker = Worker(
        client,
        task_queue=settings.task_queue,
        workflows=[ZipInspectWorkflow],
        activities=[prepare_workspace, export_result],
        workflow_runner=SandboxedWorkflowRunner(
            restrictions=SandboxRestrictions.default.with_passthrough_modules(
                "annotated_types",
                "pydantic_core",
            )
        ),
    )

    logger.info(
        "agents worker listening address=%s namespace=%s queue=%s model=%s",
        settings.temporal_address,
        settings.temporal_namespace,
        settings.task_queue,
        settings.openrouter_model,
    )
    await worker.run()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
