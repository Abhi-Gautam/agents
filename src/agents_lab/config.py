from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Repo root: .../agents
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str
    openrouter_base_url: str
    openrouter_model: str
    temporal_address: str
    temporal_namespace: str
    task_queue: str
    data_dir: Path

    @property
    def workspaces_dir(self) -> Path:
        return self.data_dir / "workspaces"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"


def load_settings(env_file: Path | None = None) -> Settings:
    """Load settings from the environment. Prefer repo .env when present."""
    load_dotenv(env_file or (REPO_ROOT / ".env"), override=False)

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "OPENROUTER_API_KEY is required. Copy .env.example to .env and set the key."
        )

    data_dir = Path(os.getenv("AGENTS_DATA_DIR", str(REPO_ROOT / "data"))).expanduser()
    if not data_dir.is_absolute():
        data_dir = (REPO_ROOT / data_dir).resolve()

    return Settings(
        openrouter_api_key=api_key,
        openrouter_base_url=os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ).strip(),
        openrouter_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip(),
        temporal_address=os.getenv("TEMPORAL_ADDRESS", "localhost:7234").strip(),
        temporal_namespace=os.getenv("TEMPORAL_NAMESPACE", "default").strip(),
        task_queue=os.getenv("TASK_QUEUE", "agents").strip(),
        data_dir=data_dir,
    )
