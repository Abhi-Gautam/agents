from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from temporalio import activity


@dataclass
class PrepareWorkspaceInput:
    zip_path: str
    workspace_id: str
    workspaces_root: str


@dataclass
class PreparedWorkspace:
    workspace_id: str
    root: str
    input_dir: str
    output_dir: str
    file_count: int


@activity.defn(name="prepare_workspace")
async def prepare_workspace(input: PrepareWorkspaceInput) -> PreparedWorkspace:
    """Extract a zip into a durable-on-disk workspace the sandbox will mount.

    The zip bytes never enter Temporal History. Only paths and counts return.
    """
    zip_path = Path(input.zip_path).expanduser().resolve()
    if not zip_path.is_file():
        raise ValueError(f"zip not found: {zip_path}")

    root = Path(input.workspaces_root).expanduser().resolve() / input.workspace_id
    input_dir = root / "input"
    output_dir = root / "output"

    if root.exists():
        shutil.rmtree(root)
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(input_dir)

    file_count = sum(1 for p in input_dir.rglob("*") if p.is_file())
    activity.logger.info(
        "prepared workspace id=%s files=%s root=%s",
        input.workspace_id,
        file_count,
        root,
    )
    return PreparedWorkspace(
        workspace_id=input.workspace_id,
        root=str(root),
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        file_count=file_count,
    )


@dataclass
class ExportResultInput:
    workspace_id: str
    output_dir: str
    exports_root: str
    answer: str
    question: str


@dataclass
class ExportResult:
    export_path: str
    answer_preview: str


@activity.defn(name="export_result")
async def export_result(input: ExportResultInput) -> ExportResult:
    """Write a reviewable export of the answer + output tree (not a chat DB)."""
    exports_root = Path(input.exports_root).expanduser().resolve()
    exports_root.mkdir(parents=True, exist_ok=True)
    export_path = exports_root / f"{input.workspace_id}.md"

    output_dir = Path(input.output_dir)
    produced: list[str] = []
    if output_dir.is_dir():
        for path in sorted(output_dir.rglob("*")):
            if path.is_file():
                rel = path.relative_to(output_dir)
                try:
                    body = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    body = f"(binary or unreadable: {path.stat().st_size} bytes)"
                produced.append(f"### output/{rel}\n\n```\n{body.rstrip()}\n```\n")

    text = "\n".join(
        [
            f"# Zip inspect export — {input.workspace_id}",
            "",
            "## Question",
            "",
            input.question.strip(),
            "",
            "## Answer",
            "",
            input.answer.strip(),
            "",
            "## Produced files",
            "",
            *(produced if produced else ["(no files under output/)", ""]),
        ]
    )
    export_path.write_text(text, encoding="utf-8")
    preview = input.answer.strip().replace("\n", " ")
    if len(preview) > 200:
        preview = preview[:197] + "..."
    return ExportResult(export_path=str(export_path), answer_preview=preview)
