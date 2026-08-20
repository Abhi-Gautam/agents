from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.contrib.openai_agents.workflow import temporal_sandbox_client

with workflow.unsafe.imports_passed_through():
    from agents import ModelSettings, Runner
    from agents.run import RunConfig
    from agents.sandbox import Manifest, SandboxAgent, SandboxPathGrant, SandboxRunConfig
    from agents.sandbox.capabilities import Shell
    from agents.sandbox.entries import LocalDir
    from agents.sandbox.sandboxes import UnixLocalSandboxClientOptions

    from agents_lab.activities import (
        ExportResult,
        ExportResultInput,
        PreparedWorkspace,
        PrepareWorkspaceInput,
        export_result,
        prepare_workspace,
    )


@dataclass
class ZipInspectInput:
    workspace_id: str
    zip_path: str
    question: str
    model: str
    workspaces_root: str
    exports_root: str


@dataclass
class ZipInspectResult:
    workspace_id: str
    answer: str
    workspace_root: str
    export_path: str
    file_count: int


@workflow.defn(name="ZipInspectWorkflow")
class ZipInspectWorkflow:
    """Durable zip inspect using SandboxAgent (harness-native shell).

    Ownership:
    - Agents SDK: agent loop + shell tools
    - Temporal: prepare/export activities, crash recovery, workflow identity
    - Disk: workspace tree under data/workspaces/{id}
    - No conversation DB in v1 (workflow-only + export file)
    """

    @workflow.run
    async def run(self, input: ZipInspectInput) -> ZipInspectResult:
        prepared: PreparedWorkspace = await workflow.execute_activity(
            prepare_workspace,
            PrepareWorkspaceInput(
                zip_path=input.zip_path,
                workspace_id=input.workspace_id,
                workspaces_root=input.workspaces_root,
            ),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        # input/ is copied into the sandbox workspace from the durable extract.
        # output_dir is a writable host path grant so artifacts survive sandbox teardown.
        agent = SandboxAgent(
            name="ZipInspectAgent",
            model=input.model,
            instructions=(
                "You investigate an incident bundle. "
                "Uploaded files are under the workspace path input/. "
                f"Write any artifacts you create under the durable directory "
                f"`{prepared.output_dir}` (for example "
                f"`{prepared.output_dir}/summary.md`). "
                "Use the shell tool to list and read files before answering. "
                "Prefer small commands: ls, find, cat, head, wc, rg or grep. "
                "Do not invent facts that are not in the files. "
                "Cite file paths that support each conclusion. "
                "End with a short markdown answer that a human can paste into a ticket."
            ),
            default_manifest=Manifest(
                entries={
                    "input": LocalDir(src=prepared.input_dir),
                },
                extra_path_grants=(
                    SandboxPathGrant(
                        path=prepared.output_dir,
                        description="durable host output directory for artifacts",
                    ),
                ),
            ),
            capabilities=[Shell()],
            model_settings=ModelSettings(tool_choice="auto"),
        )

        run_result = await Runner.run(
            agent,
            input.question,
            run_config=RunConfig(
                sandbox=SandboxRunConfig(
                    client=temporal_sandbox_client("local"),
                    options=UnixLocalSandboxClientOptions(),
                ),
                workflow_name="ZipInspectWorkflow",
                tracing_disabled=True,
            ),
        )

        answer = str(run_result.final_output or "").strip()
        if not answer:
            answer = "(empty final_output)"

        exported: ExportResult = await workflow.execute_activity(
            export_result,
            ExportResultInput(
                workspace_id=input.workspace_id,
                output_dir=prepared.output_dir,
                exports_root=input.exports_root,
                answer=answer,
                question=input.question,
            ),
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        return ZipInspectResult(
            workspace_id=input.workspace_id,
            answer=answer,
            workspace_root=prepared.root,
            export_path=exported.export_path,
            file_count=prepared.file_count,
        )
