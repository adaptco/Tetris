"""
Thin client for controlling the running Tetris web app.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Dict, Optional
from urllib import error, request


class TetrisApiError(RuntimeError):
    """Raised when the running web app rejects a control request."""


@dataclass
class TetrisApiClient:
    base_url: str = os.environ.get("TETRIS_BASE_URL", "http://127.0.0.1:8001")

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health")

    def start_game(self, player_id: str = "player-one", seed: Optional[int] = None) -> Dict[str, Any]:
        return self._request("POST", "/api/game/start", {"player_id": player_id, "seed": seed})

    def list_plugins(self) -> Dict[str, Any]:
        return self._request("GET", "/api/sdk/plugins")

    def get_plugin_manifest(self, plugin_id: str = "tetris") -> Dict[str, Any]:
        return self._request("GET", f"/api/sdk/plugins/{plugin_id}")

    def get_web_assembly(self, plugin_id: str = "tetris") -> Dict[str, Any]:
        return self._request("GET", f"/api/sdk/plugins/{plugin_id}/assembly")

    def launch_plugin(
        self,
        plugin_id: str = "tetris",
        player_id: str = "player-one",
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._request("POST", f"/api/sdk/plugins/{plugin_id}/launch", {"player_id": player_id, "seed": seed})

    def get_state(self, game_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/game/{game_id}")

    def action(self, game_id: str, action: str) -> Dict[str, Any]:
        return self._request("POST", "/api/game/action", {"game_id": game_id, "action": action})

    def advance(self, game_id: str, steps: int = 1) -> Dict[str, Any]:
        return self._request("POST", "/api/game/advance", {"game_id": game_id, "steps": steps})

    def restart(self, game_id: str, seed: Optional[int] = None) -> Dict[str, Any]:
        return self._request("POST", "/api/game/restart", {"game_id": game_id, "seed": seed})

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        body = None
        headers = {}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = request.Request(f"{self.base_url}{path}", data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise TetrisApiError(detail or exc.reason) from exc
        except error.URLError as exc:
            raise TetrisApiError(
                f"Could not reach the Tetris web app at {self.base_url}. Start uvicorn first."
            ) from exc
