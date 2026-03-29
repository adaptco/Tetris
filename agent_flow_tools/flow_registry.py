from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_BUNDLE_DIR = Path(__file__).resolve().parent.parent / "runtime" / "orchestration"


@dataclass(frozen=True)
class FlowRegistry:
    bundle_dir: Path = DEFAULT_BUNDLE_DIR

    def __post_init__(self) -> None:
        object.__setattr__(self, "bundle_dir", Path(self.bundle_dir))

    @property
    def plan_path(self) -> Path:
        return self.bundle_dir / "plan.json"

    @property
    def index_path(self) -> Path:
        return self.bundle_dir / "flow-index.json"

    def get_plan_summary(self) -> Dict[str, Any]:
        plan = self._read_json(self.plan_path)
        return {
            "generated_at": plan["generated_at"],
            "project_name": plan["project_name"],
            "objective": plan["objective"],
            "task_id": plan["task_id"],
            "mcp_server_entrypoint": plan["mcp_server_entrypoint"],
            "python_tool_library": plan["python_tool_library"],
            "sub_agent_count": len(plan["sub_agents"]),
        }

    def list_agents(self) -> List[Dict[str, Any]]:
        index = self._read_json(self.index_path)
        return list(index["agents"])

    def get_flow(self, agent_id: str) -> Dict[str, Any]:
        entry = self._find_agent_index_entry(agent_id)
        flow_path = self.bundle_dir / entry["flow_path"]
        flow = self._read_json(flow_path)
        flow["runtime_entrypoint"] = entry["runtime_entrypoint"]
        flow["tool_module"] = entry["tool_module"]
        return flow

    def search_states(self, query: str) -> List[Dict[str, Any]]:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return []

        matches: List[Dict[str, Any]] = []
        for entry in self.list_agents():
            flow = self.get_flow(entry["agent_id"])
            for state in flow["states"]:
                if normalized_query in state.lower():
                    matches.append(
                        {
                            "agent_id": flow["agent_id"],
                            "state": state,
                            "title": flow["title"],
                        }
                    )
            for transition in flow["transitions"]:
                haystack = " ".join(
                    [
                        transition["from"],
                        transition["to"],
                        transition["trigger"],
                        transition["description"],
                    ]
                ).lower()
                if normalized_query in haystack:
                    matches.append(
                        {
                            "agent_id": flow["agent_id"],
                            "state": f'{transition["from"]} -> {transition["to"]}',
                            "title": flow["title"],
                            "trigger": transition["trigger"],
                        }
                    )
        return matches

    def list_release_artifacts(self) -> List[Dict[str, Any]]:
        plan = self._read_json(self.plan_path)
        return [
            artifact
            for artifact in plan["production_artifacts"]
            if artifact["kind"] in {"workflow", "script", "mcp_server", "artifact"}
        ]

    def _find_agent_index_entry(self, agent_id: str) -> Dict[str, Any]:
        for entry in self.list_agents():
            if entry["agent_id"] == agent_id:
                return entry
        raise KeyError(f"Unknown agent_id: {agent_id}")

    def _read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Missing orchestration artifact: {path}")
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
