# Agents lab

Sibling lab to [`orchestration`](https://github.com/Abhi-Gautam/orchestration).  
**Temporal owns durable execution. OpenAI Agents SDK owns the agent harness (SandboxAgent + shell). Disk owns the workspace tree.**

## What this proves

1. User provides a **zip** + a **question**
2. Zip is extracted to `data/workspaces/{id}/input` (bytes never enter History)
3. A **SandboxAgent** inspects the tree with **harness-native shell tools** (`UnixLocalSandboxClient`)
4. Model calls go to **OpenRouter via Chat Completions** (not Responses API, not LiteLLM)
5. Temporal worker on task queue `agents` (alongside orchestration’s `orchestration` queue)
6. Result is exported to `data/exports/{id}.md` (workflow-only transcript strategy — no chat DB)

## Ownership

| Concern | Owner |
|---|---|
| Agent loop, shell tools | OpenAI Agents SDK `SandboxAgent` |
| Model HTTP + tool durability | Temporal OpenAI Agents plugin (activities) |
| Zip extract / export write | Temporal Activities |
| Thread / run identity | Temporal Workflow ID `zip-inspect/{workspace_id}` |
| Conversation DB | **Not in v1** (workflow-only + export file) |
| GPU scheduling | Separate lab (later) |

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- Running Temporal reachable at `localhost:7234` (the orchestration compose stack)
- `OPENROUTER_API_KEY`

```bash
# from orchestration repo, if Temporal is down:
docker compose up -d postgresql temporal temporal-ui
```

## Setup

```bash
cd agents
cp .env.example .env
# put OPENROUTER_API_KEY in .env
uv sync
```

## Run

Terminal 1 — worker:

```bash
uv run agents-lab worker
```

Terminal 2 — demo:

```bash
uv run agents-lab run --zip fixtures/incident.zip
```

Optional:

```bash
uv run agents-lab run \
  --zip fixtures/incident.zip \
  --workspace-id demo-001 \
  --question "What INCIDENT_ID and version do you see?"
```

## Fixture

`fixtures/incident.zip` is a tiny payments-api incident bundle (`VERSION`, logs, runbook, noise).  
Expected facts the agent should recover: version `2.4.1`, `INCIDENT_ID=inc-2026-0818-01`, SEV2, card-network upstream timeout — not the `legacy_retry` red herring.

## Layout

```text
src/agents_lab/
  config.py           # env
  model.py            # OpenRouter Chat Completions pin
  activities.py       # prepare_workspace, export_result
  workflows/zip_inspect.py
  worker.py
  cli.py
fixtures/incident.zip
```

## Non-goals (v1)

- SQLAlchemy / Mastra session tables
- LiteLLM / Any-LLM
- E2B / Docker sandbox (Unix local first; swap client later)
- Custom `read_file` / `list_files` tools that replace sandbox shell
- GPU / Volcano
