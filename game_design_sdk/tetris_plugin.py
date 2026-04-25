from __future__ import annotations

from typing import Dict, Optional

from tetris_session_manager import TetrisSessionManager

from .plugin_api import (
    ControlBinding,
    FrontendShellManifest,
    GamePluginManifest,
    McpServerManifest,
)


class TetrisPlugin:
    plugin_id = "tetris"

    def __init__(self, manager: TetrisSessionManager) -> None:
        self._manager = manager

    def manifest(self) -> GamePluginManifest:
        return GamePluginManifest(
            plugin_id=self.plugin_id,
            name="Tetris",
            description=(
                "A Python-backed tetromino survival game exposed through an SDK-style plugin, "
                "responsive web shell, and MCP control surface."
            ),
            version="1.0.0",
            kernel_entrypoint="game.tetris_engine:TetrisGame",
            plugin_entrypoint="game_design_sdk.tetris_plugin:TetrisPlugin",
            platforms=["desktop", "mobile"],
            controls=[
                ControlBinding("MOVE_LEFT", "Move left", "Arrow Left", "Tap Left"),
                ControlBinding("MOVE_RIGHT", "Move right", "Arrow Right", "Tap Right"),
                ControlBinding("MOVE_DOWN", "Soft drop", "Arrow Down", "Tap Down"),
                ControlBinding("ROTATE_CW", "Rotate", "Arrow Up / X", "Tap Rotate"),
                ControlBinding("ROTATE_CCW", "Rotate back", "Z", "Tap Back"),
                ControlBinding("HARD_DROP", "Hard drop", "Space", "Tap Drop"),
            ],
            frontend_shell=FrontendShellManifest(
                route="/",
                renderer="html-canvas-shell",
                canvas_width=420,
                canvas_height=620,
                responsive=True,
                touch_controls=True,
                assets={
                    "html": "/static/index.html",
                    "script": "/static/app.js",
                    "stylesheet": "/static/styles.css",
                },
            ),
            mcp_server=McpServerManifest(
                module="tetris_mcp_server.py",
                transport="stdio",
                tools=[
                    "tetris_health",
                    "get_tetris_plugin_manifest",
                    "get_tetris_web_assembly",
                    "start_tetris_game",
                    "get_tetris_state",
                    "move_left",
                    "move_right",
                    "soft_drop",
                    "rotate_clockwise",
                    "rotate_counterclockwise",
                    "hard_drop",
                    "advance_gravity",
                    "restart_tetris_game",
                ],
            ),
        )

    def launch(self, player_id: str, seed: Optional[int] = None) -> Dict[str, object]:
        return self._manager.start_game(player_id=player_id, seed=seed)
