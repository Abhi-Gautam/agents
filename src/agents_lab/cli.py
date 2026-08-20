from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from datetime import timedelta
from pathlib import Path

from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin

from agents_lab.config import REPO_ROOT, load_settings
from agents_lab.model import configure_openrouter
from agents_lab.workflows.zip_inspect import ZipInspectInput, ZipInspectWorkflow

DEFAULT_QUESTION = (
    "What service version is running, what INCIDENT_ID and severity are recorded, "
    "and what is the most likely root cause based on the logs and runbook? "
    "Write a short markdown summary table to output/summary.md if you can, "
    "and also return the summary in your final answer."
)


async def _connect(settings) -> Client:
    _, model_provider = configure_openrouter(settings)
    plugin = OpenAIAgentsPlugin(
        model_params=ModelActivityParameters(start_to_close_timeout=timedelta(minutes=3)),
        model_provider=model_provider,
        add_temporal_spans=False,
        # Starter only starts workflows; activities run on the worker process.
        register_activities=False,
    )
    return await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        plugins=[plugin],
    )


async def cmd_run(args: argparse.Namespace) -> int:
    settings = load_settings()
    zip_path = Path(args.zip).expanduser()
    if not zip_path.is_absolute():
        zip_path = (Path.cwd() / zip_path).resolve()
    if not zip_path.is_file():
        candidate = REPO_ROOT / zip_path
        if candidate.is_file():
            zip_path = candidate
        else:
            raise SystemExit(f"zip not found: {args.zip}")

    workspace_id = args.workspace_id or f"zip-{uuid.uuid4().hex[:10]}"
    question = args.question or DEFAULT_QUESTION

    client = await _connect(settings)
    handle = await client.start_workflow(
        ZipInspectWorkflow.run,
        ZipInspectInput(
            workspace_id=workspace_id,
            zip_path=str(zip_path),
            question=question,
            model=args.model or settings.openrouter_model,
            workspaces_root=str(settings.workspaces_dir),
            exports_root=str(settings.exports_dir),
        ),
        id=f"zip-inspect/{workspace_id}",
        task_queue=settings.task_queue,
        id_conflict_policy=WorkflowIDConflictPolicy.FAIL,
    )
    print(f"started workflow_id={handle.id} run_id={handle.result_run_id}")
    print(f"task_queue={settings.task_queue} temporal={settings.temporal_address}")

    if args.detach:
        return 0

    result = await handle.result()
    print("---")
    print(f"workspace_id: {result.workspace_id}")
    print(f"files:        {result.file_count}")
    print(f"workspace:    {result.workspace_root}")
    print(f"export:       {result.export_path}")
    print("--- answer ---")
    print(result.answer)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agents-lab", description="Agents lab CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Start ZipInspectWorkflow")
    run_p.add_argument(
        "--zip",
        default=str(REPO_ROOT / "fixtures" / "incident.zip"),
        help="Path to zip bundle (default: fixtures/incident.zip)",
    )
    run_p.add_argument("--question", default=None, help="User question")
    run_p.add_argument("--workspace-id", default=None, help="Stable workspace id")
    run_p.add_argument("--model", default=None, help="Override OPENROUTER_MODEL")
    run_p.add_argument(
        "--detach",
        action="store_true",
        help="Start workflow and exit without waiting",
    )
    run_p.set_defaults(func=cmd_run)

    worker_p = sub.add_parser("worker", help="Run the Temporal worker")
    worker_p.set_defaults(func=None)

    return parser


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "worker":
        from agents_lab.worker import main as worker_main

        worker_main()
        return

    raise SystemExit(asyncio.run(args.func(args)))


if __name__ == "__main__":
    main()
