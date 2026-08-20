# Agents

We already know how to run durable work on Temporal. What we did not have was an agent that could open a real workspace, use a shell the way coding harnesses do, and still leave execution ownership in one place.

This lab is that cut. A zip lands on disk, a SandboxAgent works inside a jailed directory with native tools, model calls go out through OpenRouter, and Temporal keeps the run. Nothing about the loop is rebuilt as custom file tools, and nothing about the run lives in a second framework’s tables.

Task queue is `agents` against the same Temporal the orchestration lab uses. These are experiments.
