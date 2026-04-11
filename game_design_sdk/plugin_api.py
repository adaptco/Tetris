from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class ControlBinding:
    action: str
    label: str
    desktop: str
    mobile: str


@dataclass(frozen=True)
class FrontendShellManifest:
    route: str
    renderer: str
    canvas_width: int
    canvas_height: int
    responsive: bool
    touch_controls: bool
    assets: Dict[str, str]


@dataclass(frozen=True)
class McpServerManifest:
    module: str
    transport: str
    tools: List[str]


@dataclass(frozen=True)
class GamePluginManifest:
    plugin_id: str
    name: str
    description: str
    version: str
    kernel_entrypoint: str
    plugin_entrypoint: str
    platforms: List[str]
    controls: List[ControlBinding]
    frontend_shell: FrontendShellManifest
    mcp_server: McpServerManifest

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["controls"] = [asdict(control) for control in self.controls]
        return payload


@runtime_checkable
class GamePlugin(Protocol):
    plugin_id: str

    def manifest(self) -> GamePluginManifest:
        """Return plugin metadata for the Game Design Agent API."""

    def launch(self, player_id: str, seed: Optional[int] = None) -> Dict[str, object]:
        """Start a new game session through the plugin."""


class GameDesignAgentAPI:
    def __init__(self, plugins: Optional[List[GamePlugin]] = None) -> None:
        self._plugins: Dict[str, GamePlugin] = {}
        for plugin in plugins or []:
            self.register(plugin)

    def register(self, plugin: GamePlugin) -> None:
        self._plugins[plugin.plugin_id] = plugin

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [
            {
                "plugin_id": manifest.plugin_id,
                "name": manifest.name,
                "description": manifest.description,
                "platforms": manifest.platforms,
                "renderer": manifest.frontend_shell.renderer,
            }
            for manifest in (plugin.manifest() for plugin in self._plugins.values())
        ]

    def get_manifest(self, plugin_id: str) -> Dict[str, Any]:
        return self._get_plugin(plugin_id).manifest().to_dict()

    def build_web_assembly(self, plugin_id: str) -> Dict[str, Any]:
        manifest = self._get_plugin(plugin_id).manifest()
        shell = manifest.frontend_shell
        return {
            **manifest.to_dict(),
            "assembly": {
                "kind": "web-shell",
                "entry_route": shell.route,
                "launch_endpoint": f"/api/sdk/plugins/{plugin_id}/launch",
                "state_endpoint": "/api/game/{game_id}",
                "action_endpoint": "/api/game/action",
                "advance_endpoint": "/api/game/advance",
                "restart_endpoint": "/api/game/restart",
                "health_endpoint": "/health",
                "platform_targets": manifest.platforms,
                "touch_controls": shell.touch_controls,
                "responsive_shell": shell.responsive,
            },
        }

    def launch(self, plugin_id: str, player_id: str, seed: Optional[int] = None) -> Dict[str, object]:
        return self._get_plugin(plugin_id).launch(player_id=player_id, seed=seed)

    def _get_plugin(self, plugin_id: str) -> GamePlugin:
        try:
            return self._plugins[plugin_id]
        except KeyError as exc:
            raise KeyError(f"Unknown plugin: {plugin_id}") from exc
