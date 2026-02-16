"""
Tetris Agent Loop - Event-Sourced Game Controller
==================================================
Integrates Tetris engine with settlement-grade event store

Every move → Event → Hash chain → Constitutional guarantees
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'settlement-grade-event-store', 'src'))

import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import asyncpg

from event_store_postgres import (
    PostgresEventStore,
    append_event_safe,
    Event
)
from verification import verify_execution
from core_fsm_states import State

# Import our game components
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from game.tetris_engine import TetrisEngine, GameState, TetrisAction
from policies.game_policy_validator import GamePolicyValidator, PolicyResult


@dataclass
class TetrisExecution:
    """
    Represents a single Tetris game execution
    
    Maps to event store execution:
    - tenant_id = player_id
    - execution_id = game_session_id
    - events = all moves, rotations, line clears
    """
    tenant_id: str
    execution_id: str
    game_state: GameState
    event_store: PostgresEventStore
    policy_validator: GamePolicyValidator
    engine: TetrisEngine


class TetrisAgent:
    """
    Agent controller for Tetris with event sourcing
    
    This is the "orchestrator" that:
    1. Receives player input
    2. Validates via GamePolicyValidator
    3. Applies game logic
    4. Appends event to store with hash chain
    5. Returns result
    """
    
    def __init__(
        self,
        event_store: PostgresEventStore,
        tenant_id: str,
        mode: str = "arcade_mode"
    ):
        self.event_store = event_store
        self.tenant_id = tenant_id
        self.mode = mode
        
        self.engine = TetrisEngine(rows=20, cols=10)
        self.policy_validator = GamePolicyValidator(tenant_id)
    
    async def start_game(self, execution_id: str) -> TetrisExecution:
        """
        Start new game execution
        
        Creates IDLE → RUNNING transition with SPAWN_PIECE
        """
        game_state = GameState.new_game()
        
        # Spawn first piece
        new_state, spawn_event = self.engine.spawn_piece(game_state)
        
        # Append to event store (RUNNING state)
        await append_event_safe(
            self.event_store,
            self.tenant_id,
            execution_id,
            State.RUNNING.value,
            {
                "stage": "game_start",
                "action": spawn_event["action"],
                "piece": spawn_event["piece"],
                "position": spawn_event["position"],
                "mode": self.mode
            }
        )
        
        return TetrisExecution(
            tenant_id=self.tenant_id,
            execution_id=execution_id,
            game_state=new_state,
            event_store=self.event_store,
            policy_validator=self.policy_validator,
            engine=self.engine
        )
    
    async def execute_action(
        self,
        execution: TetrisExecution,
        action: TetrisAction
    ) -> tuple[TetrisExecution, PolicyResult, Optional[dict]]:
        """
        Execute game action with policy validation
        
        Flow:
        1. Get execution history from event store
        2. Validate action via GamePolicyValidator
        3. If approved, apply game logic
        4. Append event with hash chain
        5. Return updated execution
        
        Returns:
            (updated_execution, policy_result, event_payload)
        """
        
        # Step 1: Get history (transaction-safe read)
        async with self.event_store.pool.acquire() as conn:
            history_events = await self.event_store.get_execution(
                conn, execution.tenant_id, execution.execution_id
            )
        
        # Convert to payload format for policy validator
        history = [e.payload for e in history_events]
        
        # Step 2: Policy validation
        current_state_dict = {
            "score": execution.game_state.score,
            "lines_cleared": execution.game_state.lines_cleared,
            "move_count": execution.game_state.move_count
        }
        
        policy_result = await execution.policy_validator.validate_move(
            action.value,
            current_state_dict,
            history
        )
        
        if not policy_result.approved:
            # Policy violation - append FAILED event
            await append_event_safe(
                self.event_store,
                execution.tenant_id,
                execution.execution_id,
                State.FAILED.value,
                {
                    "stage": "policy_violation",
                    "action": action.value,
                    "reason": policy_result.reason,
                    "penalty_points": policy_result.penalty_points
                }
            )
            
            execution.game_state.game_over = True
            return execution, policy_result, None
        
        # Step 3: Apply game logic
        if action in [TetrisAction.MOVE_LEFT, TetrisAction.MOVE_RIGHT, TetrisAction.MOVE_DOWN]:
            new_state, event_payload = self.engine.move(execution.game_state, action)
        elif action in [TetrisAction.ROTATE_CW, TetrisAction.ROTATE_CCW]:
            new_state, event_payload = self.engine.rotate(
                execution.game_state,
                clockwise=(action == TetrisAction.ROTATE_CW)
            )
        elif action == TetrisAction.HARD_DROP:
            new_state, event_payload = self.engine.hard_drop(execution.game_state)
        else:
            return execution, PolicyResult(approved=False, reason="Unknown action"), None
        
        if event_payload is None:
            # Invalid move (collision, etc.)
            return execution, PolicyResult(approved=False, reason="Invalid move (collision)"), None
        
        # Step 4: Check if piece was locked (line clear event)
        if event_payload.get("action") == "PIECE_LOCKED":
            lines_cleared = event_payload.get("lines_cleared", 0)
            points = event_payload.get("points_earned", 0)
            
            # Validate line clear (this is the "revenue event")
            line_clear_result = await execution.policy_validator.validate_line_clear(
                lines_cleared, points, history
            )
            
            if not line_clear_result.approved:
                # Fraud detected!
                await append_event_safe(
                    self.event_store,
                    execution.tenant_id,
                    execution.execution_id,
                    State.FAILED.value,
                    {
                        "stage": "fraud_detected",
                        "action": "LINE_CLEAR_FRAUD",
                        "reason": line_clear_result.reason,
                        "revoked_points": points
                    }
                )
                
                execution.game_state.game_over = True
                return execution, line_clear_result, None
        
        # Step 5: Append event to store
        await append_event_safe(
            self.event_store,
            execution.tenant_id,
            execution.execution_id,
            State.RUNNING.value,
            {
                "stage": "game_action",
                "action": event_payload.get("action"),
                **event_payload
            }
        )
        
        # Step 6: Spawn new piece if needed
        if event_payload.get("action") == "PIECE_LOCKED":
            new_state, spawn_event = self.engine.spawn_piece(new_state)
            
            await append_event_safe(
                self.event_store,
                execution.tenant_id,
                execution.execution_id,
                State.RUNNING.value,
                {
                    "stage": "spawn_piece",
                    "action": spawn_event["action"],
                    "piece": spawn_event["piece"],
                    "position": spawn_event["position"]
                }
            )
            
            # Check game over
            if new_state.game_over:
                await self._finalize_game(execution, new_state)
        
        # Update execution
        execution.game_state = new_state
        
        return execution, policy_result, event_payload
    
    async def _finalize_game(
        self,
        execution: TetrisExecution,
        final_state: GameState
    ):
        """
        Finalize game (append FINALIZED event)
        
        This triggers the constitutional constraint:
        - Only one FINALIZED per execution
        - Must be terminal state
        """
        await append_event_safe(
            self.event_store,
            execution.tenant_id,
            execution.execution_id,
            State.FINALIZED.value,
            {
                "stage": "game_over",
                "action": "GAME_FINALIZED",
                "final_score": final_state.score,
                "lines_cleared": final_state.lines_cleared,
                "move_count": final_state.move_count,
                "sealed_at": "2026-02-15T00:00:00Z"
            }
        )
    
    async def verify_game_integrity(
        self,
        execution_id: str
    ) -> tuple[bool, str, int]:
        """
        Verify game execution integrity
        
        Checks:
        1. Hash chain intact
        2. FSM transitions legal
        3. FINALIZED is terminal
        4. Policy violations recorded
        
        Returns:
            (valid, reason, event_count)
        """
        async with self.event_store.pool.acquire() as conn:
            events = await self.event_store.get_execution(
                conn, self.tenant_id, execution_id
            )
        
        result = verify_execution(events)
        
        return result.valid, result.reason or "Valid", result.event_count


# =============================================================================
# Example Usage
# =============================================================================

async def play_game_example():
    """
    Example: Play a game with event sourcing
    """
    # Connect to database
    pool = await asyncpg.create_pool(
        "postgresql://postgres:postgres@localhost:5432/event_store"
    )
    
    store = PostgresEventStore(pool)
    agent = TetrisAgent(store, tenant_id="player-001", mode="arcade_mode")
    
    # Start game
    execution = await agent.start_game("game-session-001")
    print(f"Game started: {execution.execution_id}")
    
    # Play some moves
    moves = [
        TetrisAction.MOVE_LEFT,
        TetrisAction.MOVE_LEFT,
        TetrisAction.ROTATE_CW,
        TetrisAction.MOVE_DOWN,
        TetrisAction.HARD_DROP,
    ]
    
    for move in moves:
        execution, policy_result, event = await agent.execute_action(execution, move)
        
        if not policy_result.approved:
            print(f"Move rejected: {policy_result.reason}")
            break
        
        print(f"Move {move.value}: Score={execution.game_state.score}")
    
    # Verify integrity
    valid, reason, count = await agent.verify_game_integrity("game-session-001")
    print(f"\nGame integrity: {valid} ({count} events)")
    if not valid:
        print(f"Violation: {reason}")
    
    await pool.close()


if __name__ == "__main__":
    asyncio.run(play_game_example())
