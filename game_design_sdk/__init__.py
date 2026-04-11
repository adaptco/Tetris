"""SDK surface for Game Design Agent integrations."""

from .plugin_api import GameDesignAgentAPI, GamePluginManifest
from .tetris_plugin import TetrisPlugin

__all__ = ["GameDesignAgentAPI", "GamePluginManifest", "TetrisPlugin"]
