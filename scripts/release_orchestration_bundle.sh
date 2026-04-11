#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${1:-$ROOT_DIR/dist/orchestration-bundle}"
OBJECTIVE="${2:-End-to-end production software design and release for the agent runtime.}"
BUILD_DIR="${BUILD_DIR:-$ROOT_DIR/build/orchestration}"
RUNTIME_DIR="$ROOT_DIR/runtime/orchestration"

"$ROOT_DIR/scripts/generate_orchestration_bundle.sh" "$RUNTIME_DIR" "$OBJECTIVE"

ctest --test-dir "$BUILD_DIR" --output-on-failure -C Release
python -m pytest "$ROOT_DIR/tests/test_tetris_controls.py" "$ROOT_DIR/tests/test_orchestration_flow_registry.py"

mkdir -p "$DIST_DIR"
cp "$ROOT_DIR/runtime/orchestration/plan.json" "$DIST_DIR/plan.json"
cp "$ROOT_DIR/runtime/orchestration/flow-index.json" "$DIST_DIR/flow-index.json"
mkdir -p "$DIST_DIR/flows"
cp "$ROOT_DIR/runtime/orchestration/flows/"*.json "$DIST_DIR/flows/"
cp "$ROOT_DIR/orchestration_mcp_server.py" "$DIST_DIR/orchestration_mcp_server.py"
cp -R "$ROOT_DIR/agent_flow_tools" "$DIST_DIR/agent_flow_tools"
