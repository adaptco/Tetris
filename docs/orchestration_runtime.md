# Orchestration Runtime

This runtime adds a production-oriented agent orchestration path on top of the existing Tetris repository:

- A C++ `orchestration_agent_cli` generates sub-agent manifests and working-state flow diagrams.
- A Python library, `agent_flow_tools`, indexes those diagrams as reusable tool definitions.
- An MCP server, `orchestration_mcp_server.py`, exposes the indexed plan to coding agents.
- Shell scripts and GitHub Actions package the runtime as uploadable production artifacts.

## Generated Bundle

The C++ orchestrator writes a bundle into `runtime/orchestration`:

- `plan.json`: top-level objective, production artifacts, and sub-agent definitions
- `flow-index.json`: lookup index for each agent's flow diagram
- `flows/*.json`: per-agent state machines for architecture, implementation, QA, and release

The flow bundle is designed so Python tools can answer questions like:

- Which sub-agent owns release packaging?
- What state transitions happen before GitHub artifacts are published?
- Which script or workflow is the entrypoint for a given agent?

## Runtime Commands

Build the C++ runtime:

```bash
./scripts/build_orchestration_agent.sh
```

Generate the bundle:

```bash
./scripts/generate_orchestration_bundle.sh
```

Package the production artifacts:

```bash
./scripts/release_orchestration_bundle.sh
```

Run the MCP server after the bundle exists:

```bash
python orchestration_mcp_server.py
```

## GitHub Artifact Path

`.github/workflows/orchestration-agent-release.yml` builds the C++ runtime, runs Python and C++ tests, packages the bundle, and uploads `dist/orchestration-bundle` as a GitHub Actions artifact. That makes the generated plan, indexed flows, and MCP tooling available as production-managed release outputs.
