"""
Standalone FastAPI app for the Python-backed Tetris web game.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Dict, List, Optional
from web.config import load_settings
=======
from web.config import load_settings
theirs

=======
from web.config import load_settings
theirs

=======

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from game_design_sdk import GameDesignAgentAPI, TetrisPlugin
from game.tetris_engine import TetrisAction
from tetris_session_manager import TetrisSessionManager


main
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Standalone Tetris",
    description="Python-backed Tetris served through a lightweight HTML frontend.",
    version="2.0.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

manager = TetrisSessionManager()
game_design_api = GameDesignAgentAPI([TetrisPlugin(manager)])


class StartGameRequest(BaseModel):
    player_id: str = "player-one"
    seed: Optional[int] = None


class GameActionRequest(BaseModel):
    game_id: str
    action: str


class GameAdvanceRequest(BaseModel):
    game_id: str
    steps: int = Field(default=1, ge=1, le=120)


class GameRestartRequest(BaseModel):
    game_id: str
    seed: Optional[int] = None


class PluginLaunchRequest(BaseModel):
    player_id: str = "player-one"
    seed: Optional[int] = None


class GameStateResponse(BaseModel):
    game_id: str
    player_id: str
    score: int
    lines_cleared: int
    level: int
    move_count: int
    game_over: bool
    current_piece: Optional[str]
    current_rotation: int
    current_position: List[int]
    next_queue: List[str]
    board: List[List[Optional[str]]]
    board_text: List[str]
    gravity_ms: int
    message: str = ""
    palette: Dict[str, str]
    created_at: str
    updated_at: str


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy", "service": "standalone-tetris"}

@app.on_event("startup")
async def startup():
    """Initialize database connection"""
    global event_store

    settings = load_settings()

    pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=1,
        max_size=settings.db_pool_size,
        ssl=settings.asyncpg_ssl,
    )

    # Initialize schema
    await initialize_schema(pool)

    event_store = PostgresEventStore(pool)
    print(
        "🎮 Tetris Event Store started "
        f"(pool={settings.db_pool_size}, ssl={settings.db_ssl_mode or 'default'})"
    )

theirs

    event_store = PostgresEventStore(pool)
    print(
        "🎮 Tetris Event Store started "
        f"(pool={settings.db_pool_size}, ssl={settings.db_ssl_mode or 'default'})"
    )
theirs

@app.post("/api/game/start", response_model=GameStateResponse)
async def start_game(request: StartGameRequest) -> Dict[str, object]:
    return manager.start_game(player_id=request.player_id, seed=request.seed)


@app.get("/api/game/{game_id}", response_model=GameStateResponse)
async def get_game(game_id: str) -> Dict[str, object]:
    try:
        return manager.get_state(game_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Game not found") from exc

=======

@app.get("/api/sdk/plugins")
async def list_game_plugins() -> Dict[str, object]:
    plugins = game_design_api.list_plugins()
    return {"plugins": plugins, "count": len(plugins)}


@app.get("/api/sdk/plugins/{plugin_id}")
async def get_game_plugin(plugin_id: str) -> Dict[str, object]:
    try:
        return game_design_api.get_manifest(plugin_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Plugin not found") from exc


@app.get("/api/sdk/plugins/{plugin_id}/assembly")
async def get_game_plugin_assembly(plugin_id: str) -> Dict[str, object]:
    try:
        return game_design_api.build_web_assembly(plugin_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Plugin not found") from exc


@app.post("/api/sdk/plugins/{plugin_id}/launch", response_model=GameStateResponse)
async def launch_game_plugin(plugin_id: str, request: PluginLaunchRequest) -> Dict[str, object]:
    try:
        return game_design_api.launch(plugin_id, player_id=request.player_id, seed=request.seed)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Plugin not found") from exc


@app.post("/api/game/start", response_model=GameStateResponse)
async def start_game(request: StartGameRequest) -> Dict[str, object]:
    return manager.start_game(player_id=request.player_id, seed=request.seed)


@app.get("/api/game/{game_id}", response_model=GameStateResponse)
async def get_game(game_id: str) -> Dict[str, object]:
    try:
        return manager.get_state(game_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Game not found") from exc


@app.post("/api/game/action", response_model=GameStateResponse)
async def game_action(request: GameActionRequest) -> Dict[str, object]:
    try:
        TetrisAction(request.action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}") from exc

    try:
        return manager.apply_action(game_id=request.game_id, action_name=request.action)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Game not found") from exc
main

@app.post("/api/game/action", response_model=GameStateResponse)
async def game_action(request: GameActionRequest) -> Dict[str, object]:
    try:
        TetrisAction(request.action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}") from exc

@app.post("/api/game/advance", response_model=GameStateResponse)
async def advance_game(request: GameAdvanceRequest) -> Dict[str, object]:
    try:
        return manager.advance_game(game_id=request.game_id, steps=request.steps)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Game not found") from exc


@app.post("/api/game/restart", response_model=GameStateResponse)
async def restart_game(request: GameRestartRequest) -> Dict[str, object]:
    try:
        return manager.restart_game(game_id=request.game_id, seed=request.seed)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Game not found") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web.tetris_api:app", host="0.0.0.0", port=8001, reload=False)
