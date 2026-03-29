"""
Actual MCP server for controlling the running Tetris web app over tools.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from game.tetris_engine import TetrisAction
from tetris_api_client import TetrisApiClient


client = TetrisApiClient()
mcp = FastMCP(
    name="Standalone Tetris Controls",
    instructions=(
        "Control a running standalone Tetris web app. Start a game, query state, "
        "and use the movement tools to play through the live HTTP server."
    ),
)


def summarize_state(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "game_id": state["game_id"],
        "player_id": state["player_id"],
        "score": state["score"],
        "level": state["level"],
        "lines_cleared": state["lines_cleared"],
        "move_count": state["move_count"],
        "game_over": state["game_over"],
        "current_piece": state["current_piece"],
        "current_position": state["current_position"],
        "current_rotation": state["current_rotation"],
        "next_queue": state["next_queue"],
        "board_text": state["board_text"],
        "message": state["message"],
    }


@mcp.tool(name="tetris_health", description="Check whether the web app is reachable.", structured_output=True)
def tetris_health() -> Dict[str, Any]:
    return client.health()


@mcp.tool(name="start_tetris_game", description="Start a new Tetris session in the running web app.", structured_output=True)
def start_tetris_game(player_id: str = "player-one", seed: Optional[int] = None) -> Dict[str, Any]:
    return summarize_state(client.start_game(player_id=player_id, seed=seed))


@mcp.tool(name="get_tetris_state", description="Fetch the current board and score for a game.", structured_output=True)
def get_tetris_state(game_id: str) -> Dict[str, Any]:
    return summarize_state(client.get_state(game_id))


def apply_control(game_id: str, action: TetrisAction) -> Dict[str, Any]:
    return summarize_state(client.action(game_id=game_id, action=action.value))


@mcp.tool(name="move_left", description="Move the current piece left by one column.", structured_output=True)
def move_left(game_id: str) -> Dict[str, Any]:
    return apply_control(game_id, TetrisAction.MOVE_LEFT)


@mcp.tool(name="move_right", description="Move the current piece right by one column.", structured_output=True)
def move_right(game_id: str) -> Dict[str, Any]:
    return apply_control(game_id, TetrisAction.MOVE_RIGHT)


@mcp.tool(name="soft_drop", description="Move the current piece down by one row.", structured_output=True)
def soft_drop(game_id: str) -> Dict[str, Any]:
    return apply_control(game_id, TetrisAction.MOVE_DOWN)


@mcp.tool(name="rotate_clockwise", description="Rotate the current piece clockwise.", structured_output=True)
def rotate_clockwise(game_id: str) -> Dict[str, Any]:
    return apply_control(game_id, TetrisAction.ROTATE_CW)


@mcp.tool(name="rotate_counterclockwise", description="Rotate the current piece counter-clockwise.", structured_output=True)
def rotate_counterclockwise(game_id: str) -> Dict[str, Any]:
    return apply_control(game_id, TetrisAction.ROTATE_CCW)


@mcp.tool(name="hard_drop", description="Drop the current piece to the stack immediately.", structured_output=True)
def hard_drop(game_id: str) -> Dict[str, Any]:
    return apply_control(game_id, TetrisAction.HARD_DROP)


@mcp.tool(name="advance_gravity", description="Advance the running game by one or more gravity steps.", structured_output=True)
def advance_gravity(game_id: str, steps: int = 1) -> Dict[str, Any]:
    return summarize_state(client.advance(game_id=game_id, steps=steps))


@mcp.tool(name="restart_tetris_game", description="Restart an existing game session.", structured_output=True)
def restart_tetris_game(game_id: str, seed: Optional[int] = None) -> Dict[str, Any]:
    return summarize_state(client.restart(game_id=game_id, seed=seed))


if __name__ == "__main__":
    mcp.run("stdio")
