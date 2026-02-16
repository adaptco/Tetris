"""
Tetris Web API - Playable Game with Event Sourcing
===================================================
FastAPI server for playing Tetris with settlement-grade audit trail
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict
import asyncpg
import uuid

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'settlement-grade-event-store', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from event_store_postgres import PostgresEventStore, initialize_schema
from agents.tetris_agent import TetrisAgent, TetrisExecution
from game.tetris_engine import TetrisAction


# =============================================================================
# Global State
# =============================================================================

event_store: Optional[PostgresEventStore] = None
active_games: Dict[str, TetrisExecution] = {}


# =============================================================================
# API Models
# =============================================================================

class StartGameRequest(BaseModel):
    player_id: str
    mode: str = "arcade_mode"  # arcade_mode, casual_mode, competitive_mode


class GameActionRequest(BaseModel):
    game_id: str
    action: str  # MOVE_LEFT, MOVE_RIGHT, MOVE_DOWN, ROTATE_CW, ROTATE_CCW, HARD_DROP


class GameStateResponse(BaseModel):
    game_id: str
    execution_id: str
    score: int
    lines_cleared: int
    move_count: int
    game_over: bool
    current_piece: Optional[str]
    board: list
    message: Optional[str] = None


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="Tetris Event Store",
    description="Tetris with settlement-grade event sourcing",
    version="1.0.0"
)


@app.on_event("startup")
async def startup():
    """Initialize database connection"""
    global event_store
    
    pool = await asyncpg.create_pool(
        "postgresql://postgres:postgres@localhost:5432/event_store"
    )
    
    # Initialize schema
    await initialize_schema(pool)
    
    event_store = PostgresEventStore(pool)
    print("🎮 Tetris Event Store started")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup"""
    if event_store:
        await event_store.pool.close()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve game UI"""
    return HTMLResponse(content=get_game_html(), status_code=200)


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "tetris-event-store"}


@app.post("/api/game/start", response_model=GameStateResponse)
async def start_game(request: StartGameRequest):
    """
    Start new game
    
    Creates new execution in event store with SPAWN_PIECE event
    """
    game_id = str(uuid.uuid4())
    execution_id = f"game-{game_id[:8]}"
    
    # Create agent and start game
    agent = TetrisAgent(event_store, request.player_id, request.mode)
    execution = await agent.start_game(execution_id)
    
    # Store in active games
    active_games[game_id] = execution
    
    return GameStateResponse(
        game_id=game_id,
        execution_id=execution_id,
        score=execution.game_state.score,
        lines_cleared=execution.game_state.lines_cleared,
        move_count=execution.game_state.move_count,
        game_over=execution.game_state.game_over,
        current_piece=execution.game_state.current_piece.value if execution.game_state.current_piece else None,
        board=execution.game_state.board,
        message=f"Game started in {request.mode}"
    )


@app.post("/api/game/action", response_model=GameStateResponse)
async def game_action(request: GameActionRequest):
    """
    Execute game action
    
    Flow:
    1. Get execution from active games
    2. Validate via GamePolicyValidator
    3. Apply game logic
    4. Append event to store
    5. Return updated state
    """
    if request.game_id not in active_games:
        raise HTTPException(404, "Game not found")
    
    execution = active_games[request.game_id]
    
    if execution.game_state.game_over:
        raise HTTPException(400, "Game is over")
    
    # Parse action
    try:
        action = TetrisAction(request.action)
    except ValueError:
        raise HTTPException(400, f"Invalid action: {request.action}")
    
    # Create agent
    agent = TetrisAgent(event_store, execution.tenant_id, mode="arcade_mode")
    
    # Execute action
    updated_execution, policy_result, event = await agent.execute_action(execution, action)
    
    # Update active games
    active_games[request.game_id] = updated_execution
    
    message = None
    if not policy_result.approved:
        message = f"Policy violation: {policy_result.reason}"
    elif event and event.get("lines_cleared", 0) > 0:
        message = f"Line clear! +{event.get('points_earned', 0)} points"
    
    return GameStateResponse(
        game_id=request.game_id,
        execution_id=updated_execution.execution_id,
        score=updated_execution.game_state.score,
        lines_cleared=updated_execution.game_state.lines_cleared,
        move_count=updated_execution.game_state.move_count,
        game_over=updated_execution.game_state.game_over,
        current_piece=updated_execution.game_state.current_piece.value if updated_execution.game_state.current_piece else None,
        board=updated_execution.game_state.board,
        message=message
    )


@app.get("/api/game/{game_id}/verify")
async def verify_game(game_id: str):
    """
    Verify game integrity
    
    Checks all constitutional invariants:
    - Hash chain intact
    - FSM transitions legal
    - FINALIZED is terminal
    """
    if game_id not in active_games:
        raise HTTPException(404, "Game not found")
    
    execution = active_games[game_id]
    agent = TetrisAgent(event_store, execution.tenant_id)
    
    valid, reason, count = await agent.verify_game_integrity(execution.execution_id)
    
    return {
        "valid": valid,
        "reason": reason,
        "event_count": count,
        "game_id": game_id,
        "execution_id": execution.execution_id
    }


# =============================================================================
# HTML Game UI
# =============================================================================

def get_game_html() -> str:
    """Simple Tetris UI"""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Tetris Event Store</title>
    <style>
        body {
            font-family: 'Courier New', monospace;
            background: #1a1a2e;
            color: #eee;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }
        .container {
            display: flex;
            gap: 30px;
        }
        .game-board {
            background: #0f3460;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,191,255,0.3);
        }
        .board {
            display: grid;
            grid-template-columns: repeat(10, 30px);
            grid-template-rows: repeat(20, 30px);
            gap: 1px;
            background: #16213e;
            border: 2px solid #00bfff;
        }
        .cell {
            width: 30px;
            height: 30px;
            background: #0a1128;
        }
        .cell.filled {
            background: #00bfff;
            box-shadow: inset 0 0 5px rgba(255,255,255,0.5);
        }
        .info {
            background: #0f3460;
            padding: 20px;
            border-radius: 10px;
            min-width: 250px;
        }
        .info h2 {
            color: #00bfff;
            margin-top: 0;
        }
        .stat {
            margin: 15px 0;
            font-size: 18px;
        }
        button {
            background: #00bfff;
            color: #1a1a2e;
            border: none;
            padding: 12px 24px;
            font-size: 16px;
            font-weight: bold;
            border-radius: 5px;
            cursor: pointer;
            margin: 10px 0;
            width: 100%;
        }
        button:hover {
            background: #0099cc;
        }
        button:disabled {
            background: #555;
            cursor: not-allowed;
        }
        .controls {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 20px;
        }
        .controls button {
            padding: 15px;
            font-size: 20px;
        }
        .message {
            margin: 15px 0;
            padding: 10px;
            background: #16213e;
            border-radius: 5px;
            min-height: 60px;
        }
        .error {
            color: #ff4444;
        }
        .success {
            color: #44ff44;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="game-board">
            <div id="board" class="board"></div>
        </div>
        <div class="info">
            <h2>🎮 Tetris Event Store</h2>
            <div class="stat">Score: <span id="score">0</span></div>
            <div class="stat">Lines: <span id="lines">0</span></div>
            <div class="stat">Moves: <span id="moves">0</span></div>
            <div class="message" id="message">Press Start Game to begin</div>
            
            <button id="startBtn" onclick="startGame()">Start Game</button>
            <button id="verifyBtn" onclick="verifyGame()" disabled>Verify Integrity</button>
            
            <div class="controls">
                <button onclick="move('ROTATE_CCW')">↺</button>
                <button onclick="move('MOVE_UP')">↑</button>
                <button onclick="move('ROTATE_CW')">↻</button>
                <button onclick="move('MOVE_LEFT')">←</button>
                <button onclick="move('HARD_DROP')">DROP</button>
                <button onclick="move('MOVE_RIGHT')">→</button>
                <button></button>
                <button onclick="move('MOVE_DOWN')">↓</button>
                <button></button>
            </div>
            
            <div style="margin-top: 20px; font-size: 12px; opacity: 0.7;">
                <strong>Constitutional Guarantees:</strong><br>
                ✓ Every move auditable<br>
                ✓ Hash chain integrity<br>
                ✓ Policy violations tracked<br>
                ✓ Line clears verified
            </div>
        </div>
    </div>
    
    <script>
        let gameId = null;
        let executionId = null;
        let gameState = null;
        
        function renderBoard(board) {
            const boardEl = document.getElementById('board');
            boardEl.innerHTML = '';
            
            for (let row of board) {
                for (let cell of row) {
                    const cellEl = document.createElement('div');
                    cellEl.className = 'cell' + (cell ? ' filled' : '');
                    boardEl.appendChild(cellEl);
                }
            }
        }
        
        function updateUI(response) {
            document.getElementById('score').textContent = response.score;
            document.getElementById('lines').textContent = response.lines_cleared;
            document.getElementById('moves').textContent = response.move_count;
            
            if (response.message) {
                const msgEl = document.getElementById('message');
                msgEl.textContent = response.message;
                msgEl.className = 'message ' + (response.message.includes('violation') ? 'error' : 'success');
            }
            
            if (response.board) {
                renderBoard(response.board);
            }
            
            if (response.game_over) {
                document.getElementById('message').textContent = 'Game Over! Final Score: ' + response.score;
                document.getElementById('startBtn').disabled = false;
            }
        }
        
        async function startGame() {
            const response = await fetch('/api/game/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    player_id: 'player-' + Math.random().toString(36).substr(2, 9),
                    mode: 'arcade_mode'
                })
            });
            
            const data = await response.json();
            gameId = data.game_id;
            executionId = data.execution_id;
            gameState = data;
            
            updateUI(data);
            
            document.getElementById('startBtn').disabled = true;
            document.getElementById('verifyBtn').disabled = false;
            document.getElementById('message').textContent = 'Game started! Use controls to play.';
        }
        
        async function move(action) {
            if (!gameId) {
                alert('Start a game first!');
                return;
            }
            
            const response = await fetch('/api/game/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    game_id: gameId,
                    action: action
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                updateUI(data);
            } else {
                const error = await response.json();
                document.getElementById('message').textContent = 'Error: ' + error.detail;
                document.getElementById('message').className = 'message error';
            }
        }
        
        async function verifyGame() {
            if (!gameId) return;
            
            const response = await fetch(`/api/game/${gameId}/verify`);
            const data = await response.json();
            
            const msgEl = document.getElementById('message');
            if (data.valid) {
                msgEl.textContent = `✓ Integrity verified! ${data.event_count} events, hash chain intact`;
                msgEl.className = 'message success';
            } else {
                msgEl.textContent = `✗ Integrity violation: ${data.reason}`;
                msgEl.className = 'message error';
            }
        }
        
        // Keyboard controls
        document.addEventListener('keydown', (e) => {
            if (!gameId) return;
            
            const keyMap = {
                'ArrowLeft': 'MOVE_LEFT',
                'ArrowRight': 'MOVE_RIGHT',
                'ArrowDown': 'MOVE_DOWN',
                'ArrowUp': 'ROTATE_CW',
                'z': 'ROTATE_CCW',
                'x': 'ROTATE_CW',
                ' ': 'HARD_DROP'
            };
            
            const action = keyMap[e.key];
            if (action) {
                e.preventDefault();
                move(action);
            }
        });
        
        // Initialize empty board
        renderBoard(Array(20).fill(null).map(() => Array(10).fill(null)));
    </script>
</body>
</html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
