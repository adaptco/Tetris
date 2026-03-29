"""
Standalone Tetris engine for a Python-backed web app.

Simulation state stays server-side. The browser only renders snapshots and sends
explicit actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import random


BoardCell = Optional[str]
Board = List[List[BoardCell]]


class TetrisAction(str, Enum):
    MOVE_LEFT = "MOVE_LEFT"
    MOVE_RIGHT = "MOVE_RIGHT"
    MOVE_DOWN = "MOVE_DOWN"
    ROTATE_CW = "ROTATE_CW"
    ROTATE_CCW = "ROTATE_CCW"
    HARD_DROP = "HARD_DROP"


class Tetromino(str, Enum):
    I = "I"
    O = "O"
    T = "T"
    S = "S"
    Z = "Z"
    J = "J"
    L = "L"


PIECE_COLORS: Dict[Tetromino, str] = {
    Tetromino.I: "#49dbe6",
    Tetromino.O: "#f4d35e",
    Tetromino.T: "#c084fc",
    Tetromino.S: "#7ddf64",
    Tetromino.Z: "#ff6b6b",
    Tetromino.J: "#60a5fa",
    Tetromino.L: "#fb923c",
}


BASE_SHAPES: Dict[Tetromino, Tuple[Tuple[int, int], ...]] = {
    Tetromino.I: ((1, 0), (1, 1), (1, 2), (1, 3)),
    Tetromino.O: ((1, 1), (1, 2), (2, 1), (2, 2)),
    Tetromino.T: ((1, 1), (2, 0), (2, 1), (2, 2)),
    Tetromino.S: ((1, 1), (1, 2), (2, 0), (2, 1)),
    Tetromino.Z: ((1, 0), (1, 1), (2, 1), (2, 2)),
    Tetromino.J: ((1, 0), (2, 0), (2, 1), (2, 2)),
    Tetromino.L: ((1, 2), (2, 0), (2, 1), (2, 2)),
}


LINE_SCORES = {
    0: 0,
    1: 100,
    2: 300,
    3: 500,
    4: 800,
}


def rotate_cells(cells: Tuple[Tuple[int, int], ...], turns: int) -> Tuple[Tuple[int, int], ...]:
    rotated = list(cells)
    for _ in range(turns % 4):
        rotated = [(col, 3 - row) for row, col in rotated]
    return tuple(rotated)


def build_rotations() -> Dict[Tetromino, Tuple[Tuple[Tuple[int, int], ...], ...]]:
    rotations: Dict[Tetromino, Tuple[Tuple[Tuple[int, int], ...], ...]] = {}
    for piece, cells in BASE_SHAPES.items():
        if piece == Tetromino.O:
            rotations[piece] = (cells, cells, cells, cells)
            continue
        rotations[piece] = tuple(rotate_cells(cells, turns) for turns in range(4))
    return rotations


ROTATIONS = build_rotations()


@dataclass
class TetrisUpdate:
    message: str = ""
    lines_cleared: int = 0
    points_earned: int = 0
    moved: bool = False
    game_over: bool = False


@dataclass
class TetrisGame:
    rows: int = 20
    cols: int = 10
    board: Board = field(default_factory=list)
    current_piece: Optional[Tetromino] = None
    current_rotation: int = 0
    current_pos: Tuple[int, int] = (-2, 3)
    next_queue: List[Tetromino] = field(default_factory=list)
    score: int = 0
    lines_cleared: int = 0
    level: int = 1
    move_count: int = 0
    game_over: bool = False
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        if not self.board:
            self.reset(seed=self.seed)

    def reset(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            self.seed = seed
        self._rng = random.Random(self.seed)
        self.board = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        self.current_piece = None
        self.current_rotation = 0
        self.current_pos = (-2, 3)
        self.next_queue = []
        self.score = 0
        self.lines_cleared = 0
        self.level = 1
        self.move_count = 0
        self.game_over = False
        self._ensure_queue(7)
        self._spawn_piece()

    @property
    def gravity_ms(self) -> int:
        return max(120, 800 - (self.level - 1) * 55)

    def snapshot(self, message: str = "") -> Dict[str, object]:
        display_board = self.get_display_board()
        board_text = ["".join(cell or "." for cell in row) for row in display_board]
        return {
            "score": self.score,
            "lines_cleared": self.lines_cleared,
            "level": self.level,
            "move_count": self.move_count,
            "game_over": self.game_over,
            "current_piece": self.current_piece.value if self.current_piece else None,
            "current_rotation": self.current_rotation,
            "current_position": list(self.current_pos),
            "next_queue": [piece.value for piece in self.next_queue[:5]],
            "board": display_board,
            "board_text": board_text,
            "gravity_ms": self.gravity_ms,
            "message": message,
            "palette": {piece.value: color for piece, color in PIECE_COLORS.items()},
        }

    def apply_action(self, action: TetrisAction) -> TetrisUpdate:
        if self.game_over:
            return TetrisUpdate(message="Game over. Start a new run.", game_over=True)

        self.move_count += 1

        if action == TetrisAction.MOVE_LEFT:
            moved = self._attempt_move(0, -1)
            return TetrisUpdate(message="Slide left." if moved else "Left wall.", moved=moved)

        if action == TetrisAction.MOVE_RIGHT:
            moved = self._attempt_move(0, 1)
            return TetrisUpdate(message="Slide right." if moved else "Right wall.", moved=moved)

        if action == TetrisAction.MOVE_DOWN:
            if self._attempt_move(1, 0):
                self.score += 1
                return TetrisUpdate(message="Soft drop.", points_earned=1, moved=True)
            return self._lock_and_continue(extra_points=0, base_message="Piece locked.")

        if action == TetrisAction.ROTATE_CW:
            moved = self._attempt_rotate(1)
            return TetrisUpdate(message="Rotate clockwise." if moved else "Rotation blocked.", moved=moved)

        if action == TetrisAction.ROTATE_CCW:
            moved = self._attempt_rotate(-1)
            return TetrisUpdate(message="Rotate counter-clockwise." if moved else "Rotation blocked.", moved=moved)

        if action == TetrisAction.HARD_DROP:
            drop_distance = 0
            while self._attempt_move(1, 0):
                drop_distance += 1
            bonus = drop_distance * 2
            self.score += bonus
            return self._lock_and_continue(
                extra_points=bonus,
                base_message=f"Hard drop {drop_distance} rows." if drop_distance else "Hard drop.",
            )

        return TetrisUpdate(message="Unknown action.")

    def advance(self, steps: int = 1) -> TetrisUpdate:
        if self.game_over:
            return TetrisUpdate(message="Game over.", game_over=True)

        latest = TetrisUpdate(message="Ready.")
        for _ in range(max(1, steps)):
            if self._attempt_move(1, 0):
                latest = TetrisUpdate(message="Gravity tick.", moved=True)
                continue
            latest = self._lock_and_continue(extra_points=0, base_message="Gravity lock.")
            if latest.game_over:
                break
        return latest

    def get_display_board(self) -> Board:
        board = [row[:] for row in self.board]
        if not self.current_piece or self.game_over:
            return board

        row_offset, col_offset = self.current_pos
        for row, col in ROTATIONS[self.current_piece][self.current_rotation]:
            board_row = row_offset + row
            board_col = col_offset + col
            if 0 <= board_row < self.rows and 0 <= board_col < self.cols:
                board[board_row][board_col] = self.current_piece.value
        return board

    def _ensure_queue(self, minimum_size: int) -> None:
        while len(self.next_queue) < minimum_size:
            bag = list(Tetromino)
            self._rng.shuffle(bag)
            self.next_queue.extend(bag)

    def _spawn_piece(self) -> None:
        self._ensure_queue(7)
        self.current_piece = self.next_queue.pop(0)
        self.current_rotation = 0
        self.current_pos = (-2, 3)
        if self._collides(self.current_pos[0], self.current_pos[1], self.current_rotation):
            self.current_piece = None
            self.game_over = True

    def _attempt_move(self, row_delta: int, col_delta: int) -> bool:
        if not self.current_piece:
            return False
        next_row = self.current_pos[0] + row_delta
        next_col = self.current_pos[1] + col_delta
        if self._collides(next_row, next_col, self.current_rotation):
            return False
        self.current_pos = (next_row, next_col)
        return True

    def _attempt_rotate(self, delta: int) -> bool:
        if not self.current_piece:
            return False
        next_rotation = (self.current_rotation + delta) % 4
        kicks = ((0, 0), (0, -1), (0, 1), (-1, 0), (-1, -1), (-1, 1), (0, -2), (0, 2))
        for row_kick, col_kick in kicks:
            next_row = self.current_pos[0] + row_kick
            next_col = self.current_pos[1] + col_kick
            if not self._collides(next_row, next_col, next_rotation):
                self.current_rotation = next_rotation
                self.current_pos = (next_row, next_col)
                return True
        return False

    def _lock_and_continue(self, extra_points: int, base_message: str) -> TetrisUpdate:
        if not self.current_piece:
            return TetrisUpdate(message="No active piece.")

        for row, col in ROTATIONS[self.current_piece][self.current_rotation]:
            board_row = self.current_pos[0] + row
            board_col = self.current_pos[1] + col
            if board_row < 0:
                self.current_piece = None
                self.game_over = True
                return TetrisUpdate(message="Stack reached the ceiling.", game_over=True)
            self.board[board_row][board_col] = self.current_piece.value

        cleared_rows = [index for index, line in enumerate(self.board) if all(cell is not None for cell in line)]
        lines = len(cleared_rows)
        line_points = LINE_SCORES[lines] * self.level

        if cleared_rows:
            for row_index in reversed(cleared_rows):
                self.board.pop(row_index)
            for _ in cleared_rows:
                self.board.insert(0, [None] * self.cols)

        self.score += line_points
        self.lines_cleared += lines
        self.level = 1 + self.lines_cleared // 10

        self._spawn_piece()

        if self.game_over:
            return TetrisUpdate(
                message="Game over. The stack hit the spawn zone.",
                lines_cleared=lines,
                points_earned=line_points + extra_points,
                game_over=True,
            )

        if lines:
            label = "Tetris!" if lines == 4 else f"Cleared {lines} line{'s' if lines != 1 else ''}."
            return TetrisUpdate(
                message=f"{base_message} {label}",
                lines_cleared=lines,
                points_earned=line_points + extra_points,
                moved=True,
            )

        return TetrisUpdate(
            message=base_message,
            lines_cleared=0,
            points_earned=extra_points,
            moved=True,
        )

    def _collides(self, row_offset: int, col_offset: int, rotation: int) -> bool:
        if not self.current_piece:
            return False
        for row, col in ROTATIONS[self.current_piece][rotation]:
            board_row = row_offset + row
            board_col = col_offset + col
            if board_col < 0 or board_col >= self.cols or board_row >= self.rows:
                return True
            if board_row >= 0 and self.board[board_row][board_col] is not None:
                return True
        return False
