"""
MCP server for querying generated orchestration flow bundles.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from agent_flow_tools import DEFAULT_BUNDLE_DIR, FlowRegistry


mcp = FastMCP(
    name="Orchestration Flow Index",
    instructions=(
        "Inspect generated sub-agent plans, working-state flow diagrams, and "
        "release artifacts for the orchestration runtime bundle."
    ),
)


def get_registry(bundle_dir: Optional[str] = None) -> FlowRegistry:
    path = Path(bundle_dir) if bundle_dir else DEFAULT_BUNDLE_DIR
    return FlowRegistry(path)


@mcp.tool(
    name="get_orchestration_summary",
    description="Summarize the generated orchestration bundle and its MCP tool library.",
    structured_output=True,
)
def get_orchestration_summary(bundle_dir: Optional[str] = None) -> Dict[str, Any]:
    return get_registry(bundle_dir).get_plan_summary()


@mcp.tool(
    name="list_sub_agents",
    description="List indexed sub-agents from the generated orchestration flow bundle.",
    structured_output=True,
)
def list_sub_agents(bundle_dir: Optional[str] = None) -> Dict[str, Any]:
    agents = get_registry(bundle_dir).list_agents()
    return {"agents": agents, "count": len(agents)}


@mcp.tool(
    name="get_sub_agent_flow",
    description="Fetch the full working-state flow diagram for a specific sub-agent.",
    structured_output=True,
)
def get_sub_agent_flow(agent_id: str, bundle_dir: Optional[str] = None) -> Dict[str, Any]:
    return get_registry(bundle_dir).get_flow(agent_id)


@mcp.tool(
    name="search_sub_agent_states",
    description="Search sub-agent states and transitions by keyword.",
    structured_output=True,
)
def search_sub_agent_states(query: str, bundle_dir: Optional[str] = None) -> Dict[str, Any]:
    matches = get_registry(bundle_dir).search_states(query)
    return {"matches": matches, "count": len(matches)}


@mcp.tool(
    name="list_release_artifacts",
    description="List GitHub workflows, shell scripts, and runtime artifacts that the release path manages.",
    structured_output=True,
)
def list_release_artifacts(bundle_dir: Optional[str] = None) -> Dict[str, Any]:
    artifacts = get_registry(bundle_dir).list_release_artifacts()
    return {"artifacts": artifacts, "count": len(artifacts)}


if __name__ == "__main__":
    mcp.run("stdio")
