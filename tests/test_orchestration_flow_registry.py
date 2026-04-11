from __future__ import annotations

from agent_flow_tools import FlowRegistry
import orchestration_mcp_server


def test_flow_registry_reads_generated_bundle():
    registry = FlowRegistry()

    summary = registry.get_plan_summary()
    assert summary["project_name"] == "Tetris"
    assert summary["python_tool_library"] == "agent_flow_tools"
    assert summary["sub_agent_count"] == 4

    agents = registry.list_agents()
    assert len(agents) == 4
    assert {agent["agent_id"] for agent in agents} == {
        "architecture-agent",
        "implementation-agent",
        "qa-agent",
        "release-agent",
    }


def test_flow_registry_searches_states_and_transitions():
    registry = FlowRegistry()

    matches = registry.search_states("release")
    assert matches
    assert any(match["agent_id"] == "release-agent" for match in matches)

    flow = registry.get_flow("implementation-agent")
    assert flow["entry_state"] == "queued"
    assert flow["terminal_state"] == "completed"
    assert flow["runtime_entrypoint"] == "scripts/build_orchestration_agent.sh"


def test_mcp_server_tools_wrap_registry():
    listed = orchestration_mcp_server.list_sub_agents()
    assert listed["count"] == 4

    artifacts = orchestration_mcp_server.list_release_artifacts()
    assert artifacts["count"] >= 4

    flow = orchestration_mcp_server.get_sub_agent_flow("qa-agent")
    assert flow["title"] == "QA Agent Working State"
