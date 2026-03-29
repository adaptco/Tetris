"""
In-memory session manager for the standalone Tetris web app.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional
import uuid

from game.tetris_engine import TetrisAction, TetrisGame


@dataclass
class TetrisSession:
    game_id: str
    player_id: str
    game: TetrisGame
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def snapshot(self, message: str = "") -> Dict[str, object]:
        payload = self.game.snapshot(message=message)
        payload["game_id"] = self.game_id
        payload["player_id"] = self.player_id
        payload["created_at"] = self.created_at.isoformat()
        payload["updated_at"] = self.updated_at.isoformat()
        return payload


class TetrisSessionManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, TetrisSession] = {}

    def start_game(self, player_id: str, seed: Optional[int] = None) -> Dict[str, object]:
        game_id = str(uuid.uuid4())
        game = TetrisGame(seed=seed)
        session = TetrisSession(game_id=game_id, player_id=player_id, game=game)
        self._sessions[game_id] = session
        return session.snapshot(message="New run started. Survive the stack.")

    def get_state(self, game_id: str) -> Dict[str, object]:
        session = self.require_session(game_id)
        return session.snapshot()

    def apply_action(self, game_id: str, action_name: str) -> Dict[str, object]:
        session = self.require_session(game_id)
        action = TetrisAction(action_name)
        result = session.game.apply_action(action)
        session.updated_at = datetime.now(timezone.utc)
        return session.snapshot(message=result.message)

    def advance_game(self, game_id: str, steps: int) -> Dict[str, object]:
        session = self.require_session(game_id)
        result = session.game.advance(steps=steps)
        session.updated_at = datetime.now(timezone.utc)
        return session.snapshot(message=result.message)

    def restart_game(self, game_id: str, seed: Optional[int] = None) -> Dict[str, object]:
        session = self.require_session(game_id)
        session.game.reset(seed=seed)
        session.updated_at = datetime.now(timezone.utc)
        return session.snapshot(message="Run restarted.")

    def require_session(self, game_id: str) -> TetrisSession:
        session = self._sessions.get(game_id)
        if session is None:
            raise KeyError(game_id)
        return session
