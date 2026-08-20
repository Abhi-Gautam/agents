# Agents

The orchestration engine already knows how to run an operation without inventing a second ledger for retries, cancellation, or progress. What it does not yet know is how to host the kind of work that looks like an agent: a long-lived thread that thinks, uses tools, waits on humans, and keeps a workspace without turning the agent framework into the orchestrator.

That is the seam this lab is for. Temporal stays the durable execution plane. An agent harness owns the loop and the tools models already understand. Workspaces and large artifacts stay on disk or object storage. Conversation product memory, when it arrives, is not allowed to become a second run store.

The first cut is deliberately small so the ownership can be proven. The direction is not a single zip workflow — it is agents as first-class operations the engine can start, attach to, cancel, and observe the same way it does everything else.

These are experiments.
