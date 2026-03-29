#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${1:-$ROOT_DIR/runtime/orchestration}"
OBJECTIVE="${2:-End-to-end production software design and release for the agent runtime.}"
BUILD_DIR="${BUILD_DIR:-$ROOT_DIR/build/orchestration}"

"$ROOT_DIR/scripts/build_orchestration_agent.sh" "$BUILD_DIR"

EXECUTABLE="$BUILD_DIR/orchestration_agent_cli"
if [[ ! -x "$EXECUTABLE" && -x "$BUILD_DIR/Release/orchestration_agent_cli.exe" ]]; then
  EXECUTABLE="$BUILD_DIR/Release/orchestration_agent_cli.exe"
fi

"$EXECUTABLE" \
  --project-name "Tetris" \
  --task-id "task-tetris-runtime" \
  --objective "$OBJECTIVE" \
  --output-dir "$OUTPUT_DIR"
