from __future__ import annotations

from fastapi.testclient import TestClient

from web.tetris_api import app


def test_sdk_plugin_manifest_and_assembly_are_exposed():
    client = TestClient(app)

    plugins_response = client.get("/api/sdk/plugins")
    assert plugins_response.status_code == 200
    plugins_payload = plugins_response.json()
    assert plugins_payload["count"] == 1
    assert plugins_payload["plugins"][0]["plugin_id"] == "tetris"

    manifest_response = client.get("/api/sdk/plugins/tetris")
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["frontend_shell"]["touch_controls"] is True
    assert manifest["mcp_server"]["module"] == "tetris_mcp_server.py"

    assembly_response = client.get("/api/sdk/plugins/tetris/assembly")
    assert assembly_response.status_code == 200
    assembly = assembly_response.json()
    assert assembly["assembly"]["kind"] == "web-shell"
    assert assembly["assembly"]["platform_targets"] == ["desktop", "mobile"]


def test_sdk_launch_endpoint_starts_a_game():
    client = TestClient(app)

    response = client.post(
        "/api/sdk/plugins/tetris/launch",
        json={"player_id": "sdk-test", "seed": 19},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["player_id"] == "sdk-test"
    assert payload["game_over"] is False
    assert payload["current_piece"] is not None
