#!/bin/bash
set -e

# Get the absolute path of the repository root (one level up from this script)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$REPO_ROOT/build/orchestration"

echo "Using Repository Root: $REPO_ROOT"
echo "Target Build Directory: $BUILD_DIR"

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure and Build
cmake "$REPO_ROOT"
make -j$(nproc)

echo "Orchestration bundle generated successfully in $BUILD_DIR"
