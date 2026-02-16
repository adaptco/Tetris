"""
Tetris Game State - Event-Sourced Implementation
=================================================
Every move, rotation, and line clear becomes an auditable event
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum
import random


class TetrisAction(str, Enum):
    """Actions that generate events"""
    SPAWN_PIECE = "SPAWN_PIECE"
    MOVE_LEFT = "MOVE_LEFT"
    MOVE_RIGHT = "MOVE_RIGHT"
    MOVE_DOWN = "MOVE_DOWN"
    ROTATE_CW = "ROTATE_CW"
    ROTATE_CCW = "ROTATE_CCW"
    HARD_DROP = "HARD_DROP"
    LINE_CLEAR = "LINE_CLEAR"
    GAME_OVER = "GAME_OVER"


class Tetromino(str, Enum):
    """Tetris pieces"""
    I = "I"  # Line
    O = "O"  # Square
    T = "T"  # T-shape
    S = "S"  # S-shape
    Z = "Z"  # Z-shape
    J = "J"  # J-shape
    L = "L"  # L-shape


# Tetromino shapes (rotation state 0)
SHAPES = {
    Tetromino.I: [(0, 0), (0, 1), (0, 2), (0, 3)],
    Tetromino.O: [(0, 0), (0, 1), (1, 0), (1, 1)],
    Tetromino.T: [(0, 1), (1, 0), (1, 1), (1, 2)],
    Tetromino.S: [(0, 1), (0, 2), (1, 0), (1, 1)],
    Tetromino.Z: [(0, 0), (0, 1), (1, 1), (1, 2)],
    Tetromino.J: [(0, 0), (1, 0), (1, 1), (1, 2)],
    Tetromino.L: [(0, 2), (1, 0), (1, 1), (1, 2)],
}


@dataclass
class GameState:
    """
    Complete game state for Tetris
    
    This is NOT stored in events - it's reconstructed from event stream
    """
    board: List[List[Optional[str]]]  # 20x10 grid
    current_piece: Optional[Tetromino]
    current_pos: Tuple[int, int]  # (row, col)
    current_rotation: int  # 0, 1, 2, 3
    score: int
    lines_cleared: int
    game_over: bool
    move_count: int
    
    @staticmethod
    def new_game(rows: int = 20, cols: int = 10) -> "GameState":
        """Create new game state"""
        return GameState(
            board=[[None for _ in range(cols)] for _ in range(rows)],
            current_piece=None,
            current_pos=(0, 3),  # Start near top-center
            current_rotation=0,
            score=0,
            lines_cleared=0,
            game_over=False,
            move_count=0
        )


class TetrisEngine:
    """
    Core Tetris game mechanics
    
    Stateless - operates on GameState and produces new states + events
    """
    
    def __init__(self, rows: int = 20, cols: int = 10):
        self.rows = rows
        self.cols = cols
    
    def spawn_piece(self, state: GameState) -> Tuple[GameState, dict]:
        """
        Spawn new piece
        
        Returns:
            (new_state, event_payload)
        """
        piece = random.choice(list(Tetromino))
        
        new_state = GameState(
            board=state.board,
            current_piece=piece,
            current_pos=(0, 3),
            current_rotation=0,
            score=state.score,
            lines_cleared=state.lines_cleared,
            game_over=state.game_over,
            move_count=state.move_count
        )
        
        # Check if spawn position is blocked (game over)
        if self._check_collision(new_state):
            new_state.game_over = True
        
        event = {
            "action": TetrisAction.SPAWN_PIECE,
            "piece": piece.value,
            "position": new_state.current_pos,
            "game_over": new_state.game_over
        }
        
        return new_state, event
    
    def move(self, state: GameState, action: TetrisAction) -> Tuple[GameState, dict]:
        """
        Move current piece
        
        Returns:
            (new_state, event_payload) or (state, None) if invalid
        """
        if not state.current_piece or state.game_over:
            return state, None
        
        # Calculate new position
        row, col = state.current_pos
        
        if action == TetrisAction.MOVE_LEFT:
            new_pos = (row, col - 1)
        elif action == TetrisAction.MOVE_RIGHT:
            new_pos = (row, col + 1)
        elif action == TetrisAction.MOVE_DOWN:
            new_pos = (row + 1, col)
        else:
            return state, None
        
        # Check collision
        new_state = GameState(
            board=state.board,
            current_piece=state.current_piece,
            current_pos=new_pos,
            current_rotation=state.current_rotation,
            score=state.score,
            lines_cleared=state.lines_cleared,
            game_over=state.game_over,
            move_count=state.move_count + 1
        )
        
        if self._check_collision(new_state):
            # If moving down and collision, lock piece
            if action == TetrisAction.MOVE_DOWN:
                return self._lock_piece(state)
            else:
                # Invalid move
                return state, None
        
        event = {
            "action": action.value,
            "from": state.current_pos,
            "to": new_pos,
            "move_number": new_state.move_count
        }
        
        return new_state, event
    
    def rotate(self, state: GameState, clockwise: bool = True) -> Tuple[GameState, dict]:
        """Rotate current piece"""
        if not state.current_piece or state.game_over:
            return state, None
        
        new_rotation = (state.current_rotation + (1 if clockwise else -1)) % 4
        
        new_state = GameState(
            board=state.board,
            current_piece=state.current_piece,
            current_pos=state.current_pos,
            current_rotation=new_rotation,
            score=state.score,
            lines_cleared=state.lines_cleared,
            game_over=state.game_over,
            move_count=state.move_count + 1
        )
        
        if self._check_collision(new_state):
            return state, None  # Invalid rotation
        
        event = {
            "action": TetrisAction.ROTATE_CW if clockwise else TetrisAction.ROTATE_CCW,
            "from_rotation": state.current_rotation,
            "to_rotation": new_rotation,
            "move_number": new_state.move_count
        }
        
        return new_state, event
    
    def hard_drop(self, state: GameState) -> Tuple[GameState, dict]:
        """Drop piece to bottom immediately"""
        if not state.current_piece or state.game_over:
            return state, None
        
        # Find lowest valid position
        current_state = state
        drop_distance = 0
        
        while True:
            row, col = current_state.current_pos
            test_state = GameState(
                board=current_state.board,
                current_piece=current_state.current_piece,
                current_pos=(row + 1, col),
                current_rotation=current_state.current_rotation,
                score=current_state.score,
                lines_cleared=current_state.lines_cleared,
                game_over=current_state.game_over,
                move_count=current_state.move_count
            )
            
            if self._check_collision(test_state):
                break
            
            current_state = test_state
            drop_distance += 1
        
        # Lock piece at final position
        locked_state, lock_event = self._lock_piece(current_state)
        
        event = {
            "action": TetrisAction.HARD_DROP,
            "from": state.current_pos,
            "to": current_state.current_pos,
            "drop_distance": drop_distance,
            "bonus_points": drop_distance * 2
        }
        
        locked_state.score += drop_distance * 2
        
        return locked_state, event
    
    def _lock_piece(self, state: GameState) -> Tuple[GameState, dict]:
        """
        Lock current piece to board and check for line clears
        
        This is the "revenue event" - line clears = money!
        """
        # Add piece to board
        new_board = [row[:] for row in state.board]
        
        for dr, dc in self._get_piece_blocks(state.current_piece, state.current_rotation):
            row = state.current_pos[0] + dr
            col = state.current_pos[1] + dc
            if 0 <= row < self.rows and 0 <= col < self.cols:
                new_board[row][col] = state.current_piece.value
        
        # Check for completed lines
        lines_to_clear = []
        for row in range(self.rows):
            if all(cell is not None for cell in new_board[row]):
                lines_to_clear.append(row)
        
        # Clear lines (shift down)
        for line in sorted(lines_to_clear, reverse=True):
            new_board.pop(line)
            new_board.insert(0, [None] * self.cols)
        
        # Calculate score (Tetris scoring)
        line_count = len(lines_to_clear)
        points = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}  # Tetris = 4 lines
        
        new_state = GameState(
            board=new_board,
            current_piece=None,  # Cleared
            current_pos=(0, 3),
            current_rotation=0,
            score=state.score + points.get(line_count, 0),
            lines_cleared=state.lines_cleared + line_count,
            game_over=state.game_over,
            move_count=state.move_count
        )
        
        event = {
            "action": "PIECE_LOCKED",
            "piece": state.current_piece.value,
            "position": state.current_pos,
            "lines_cleared": line_count,
            "cleared_rows": lines_to_clear,
            "points_earned": points.get(line_count, 0),
            "total_score": new_state.score
        }
        
        return new_state, event
    
    def _check_collision(self, state: GameState) -> bool:
        """Check if current piece collides with board or boundaries"""
        if not state.current_piece:
            return False
        
        for dr, dc in self._get_piece_blocks(state.current_piece, state.current_rotation):
            row = state.current_pos[0] + dr
            col = state.current_pos[1] + dc
            
            # Check boundaries
            if row < 0 or row >= self.rows or col < 0 or col >= self.cols:
                return True
            
            # Check board collision
            if state.board[row][col] is not None:
                return True
        
        return False
    
    def _get_piece_blocks(self, piece: Tetromino, rotation: int) -> List[Tuple[int, int]]:
        """Get block positions for piece at given rotation"""
        blocks = SHAPES[piece]
        
        # Apply rotation (90° clockwise rotations)
        for _ in range(rotation):
            blocks = [(dc, -dr) for dr, dc in blocks]
        
        return blocks
