from __future__ import annotations

from fastapi.testclient import TestClient

import tetris_mcp_server
from web.tetris_api import app


class LocalAppClient:
    def __init__(self, test_client: TestClient) -> None:
        self._client = test_client

    def health(self):
        return self._client.get("/health").json()

    def start_game(self, player_id="player-one", seed=None):
        return self._client.post("/api/game/start", json={"player_id": player_id, "seed": seed}).json()

    def get_state(self, game_id: str):
        return self._client.get(f"/api/game/{game_id}").json()

    def action(self, game_id: str, action: str):
        return self._client.post("/api/game/action", json={"game_id": game_id, "action": action}).json()

    def advance(self, game_id: str, steps: int = 1):
        return self._client.post("/api/game/advance", json={"game_id": game_id, "steps": steps}).json()

    def restart(self, game_id: str, seed=None):
        return self._client.post("/api/game/restart", json={"game_id": game_id, "seed": seed}).json()


def test_web_api_starts_a_playable_game():
    client = TestClient(app)

    response = client.post("/api/game/start", json={"player_id": "api-test", "seed": 7})
    assert response.status_code == 200

    payload = response.json()
    assert payload["player_id"] == "api-test"
    assert payload["game_over"] is False
    assert len(payload["board"]) == 20
    assert len(payload["board"][0]) == 10
    assert payload["current_piece"] is not None


def test_mcp_tools_drive_the_game(monkeypatch):
    web_client = TestClient(app)
    monkeypatch.setattr(tetris_mcp_server, "client", LocalAppClient(web_client))

    started = tetris_mcp_server.start_tetris_game(player_id="mcp-test", seed=11)
    assert started["player_id"] == "mcp-test"
    assert started["game_over"] is False

    game_id = started["game_id"]
    moved = tetris_mcp_server.move_left(game_id)
    assert moved["game_id"] == game_id
    assert moved["move_count"] == 1

    rotated = tetris_mcp_server.rotate_clockwise(game_id)
    assert rotated["move_count"] == 2

    dropped = tetris_mcp_server.hard_drop(game_id)
    assert dropped["move_count"] == 3
    assert len(dropped["board_text"]) == 20

    advanced = tetris_mcp_server.advance_gravity(game_id, steps=1)
    assert advanced["game_id"] == game_id
