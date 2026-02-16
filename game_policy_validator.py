"""
Game Policy Validator
======================
Maps to Revenue Policy Validator - enforces game rules as "business policies"

Line clears = Revenue events
Policy violations = Discount rejections
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class PolicyViolation(str, Enum):
    """Policy violation types"""
    MAX_MOVES_EXCEEDED = "MAX_MOVES_EXCEEDED"
    CONSECUTIVE_ROTATIONS = "CONSECUTIVE_ROTATIONS"
    SPAM_PREVENTION = "SPAM_PREVENTION"
    BONUS_FRAUD = "BONUS_FRAUD"
    BACKTRACK_LIMIT = "BACKTRACK_LIMIT"


@dataclass
class PolicyResult:
    """Result of policy check"""
    approved: bool
    reason: Optional[str] = None
    penalty_points: int = 0
    warning: Optional[str] = None


class GamePolicyValidator:
    """
    Validates game actions against policies
    
    This is the "constitutional layer" - like RevenuePolicy but for games:
    - Line clear bonuses must follow rules (like discount approvals)
    - Move limits prevent abuse (like transaction limits)
    - Fraud detection (like payment fraud)
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        
        # Policy limits (configurable per tenant)
        self.policies = {
            "max_moves_per_piece": 50,  # Prevent infinite loops
            "max_consecutive_rotations": 10,  # Prevent rotation spam
            "max_same_action_streak": 5,  # Prevent button mashing
            "max_backtrack_moves": 3,  # Limit "undo" behavior
            "bonus_fraud_threshold": 1000,  # Suspicious score jumps
        }
    
    async def validate_move(
        self,
        action: str,
        current_state: Dict[str, Any],
        history: List[Dict[str, Any]]
    ) -> PolicyResult:
        """
        Validate if action is allowed
        
        Args:
            action: TetrisAction being attempted
            current_state: Current game state snapshot
            history: Previous events in this execution
        
        Returns:
            PolicyResult (approved/rejected + reason)
        """
        
        # Policy 1: Max moves per piece
        piece_moves = self._count_moves_for_current_piece(history)
        if piece_moves >= self.policies["max_moves_per_piece"]:
            return PolicyResult(
                approved=False,
                reason=f"Max moves per piece exceeded ({piece_moves})",
                penalty_points=50
            )
        
        # Policy 2: Consecutive rotation spam
        if action in ["ROTATE_CW", "ROTATE_CCW"]:
            consecutive_rotations = self._count_consecutive_actions(
                history, ["ROTATE_CW", "ROTATE_CCW"]
            )
            if consecutive_rotations >= self.policies["max_consecutive_rotations"]:
                return PolicyResult(
                    approved=False,
                    reason=f"Rotation spam detected ({consecutive_rotations} consecutive)",
                    penalty_points=20
                )
        
        # Policy 3: Same action streak prevention
        if action in ["MOVE_LEFT", "MOVE_RIGHT"]:
            streak = self._count_consecutive_actions(history, [action])
            if streak >= self.policies["max_same_action_streak"]:
                return PolicyResult(
                    approved=False,
                    reason=f"Action spam: {action} repeated {streak} times",
                    penalty_points=10
                )
        
        # Policy 4: Backtrack detection
        if self._is_backtrack_move(action, history):
            backtrack_count = self._count_backtrack_moves(history)
            if backtrack_count >= self.policies["max_backtrack_moves"]:
                return PolicyResult(
                    approved=False,
                    reason=f"Backtrack limit exceeded ({backtrack_count})",
                    penalty_points=15
                )
        
        # All policies passed
        return PolicyResult(approved=True)
    
    async def validate_line_clear(
        self,
        lines_cleared: int,
        points_earned: int,
        history: List[Dict[str, Any]]
    ) -> PolicyResult:
        """
        Validate line clear bonus (this is the "revenue event")
        
        Like validating discount approvals:
        - Check if bonus is legitimate
        - Detect fraud patterns
        - Ensure scoring rules are followed
        """
        
        # Policy: Standard Tetris scoring
        expected_points = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}
        
        if points_earned != expected_points.get(lines_cleared, 0):
            return PolicyResult(
                approved=False,
                reason=f"Invalid scoring: {lines_cleared} lines should give {expected_points.get(lines_cleared, 0)} points, got {points_earned}",
                penalty_points=points_earned  # Revoke fraudulent points
            )
        
        # Policy: Detect suspicious scoring patterns
        recent_clears = self._get_recent_line_clears(history, limit=5)
        if len(recent_clears) >= 3:
            total_recent_points = sum(e.get("points_earned", 0) for e in recent_clears)
            if total_recent_points > self.policies["bonus_fraud_threshold"]:
                return PolicyResult(
                    approved=True,
                    warning=f"Suspicious scoring pattern detected (fraud review triggered)"
                )
        
        return PolicyResult(approved=True)
    
    def _count_moves_for_current_piece(self, history: List[Dict[str, Any]]) -> int:
        """Count moves since last SPAWN_PIECE"""
        moves = 0
        for event in reversed(history):
            if event.get("action") == "SPAWN_PIECE":
                break
            if event.get("action") in ["MOVE_LEFT", "MOVE_RIGHT", "MOVE_DOWN", "ROTATE_CW", "ROTATE_CCW"]:
                moves += 1
        return moves
    
    def _count_consecutive_actions(self, history: List[Dict[str, Any]], actions: List[str]) -> int:
        """Count consecutive occurrences of specified actions"""
        count = 0
        for event in reversed(history):
            if event.get("action") in actions:
                count += 1
            else:
                break
        return count
    
    def _is_backtrack_move(self, action: str, history: List[Dict[str, Any]]) -> bool:
        """Detect if move is a backtrack (undo previous move)"""
        if not history:
            return False
        
        last_event = history[-1]
        last_action = last_event.get("action")
        
        # Check for opposite moves
        opposites = {
            "MOVE_LEFT": "MOVE_RIGHT",
            "MOVE_RIGHT": "MOVE_LEFT",
            "ROTATE_CW": "ROTATE_CCW",
            "ROTATE_CCW": "ROTATE_CW"
        }
        
        return opposites.get(last_action) == action
    
    def _count_backtrack_moves(self, history: List[Dict[str, Any]]) -> int:
        """Count backtrack moves in recent history"""
        backtrack_count = 0
        for i in range(1, min(len(history), 20)):
            prev_action = history[-i-1].get("action")
            curr_action = history[-i].get("action")
            
            opposites = {
                "MOVE_LEFT": "MOVE_RIGHT",
                "MOVE_RIGHT": "MOVE_LEFT",
            }
            
            if opposites.get(prev_action) == curr_action:
                backtrack_count += 1
        
        return backtrack_count
    
    def _get_recent_line_clears(self, history: List[Dict[str, Any]], limit: int = 5) -> List[Dict]:
        """Get recent line clear events"""
        clears = []
        for event in reversed(history):
            if event.get("action") == "LINE_CLEAR" or event.get("lines_cleared", 0) > 0:
                clears.append(event)
                if len(clears) >= limit:
                    break
        return clears


# =============================================================================
# Policy Configuration per Tenant
# =============================================================================

TENANT_POLICIES = {
    "arcade_mode": {
        "max_moves_per_piece": 30,  # Strict for arcade
        "max_consecutive_rotations": 5,
        "max_same_action_streak": 3,
        "max_backtrack_moves": 2,
        "bonus_fraud_threshold": 500,
    },
    "casual_mode": {
        "max_moves_per_piece": 100,  # Relaxed
        "max_consecutive_rotations": 20,
        "max_same_action_streak": 10,
        "max_backtrack_moves": 5,
        "bonus_fraud_threshold": 2000,
    },
    "competitive_mode": {
        "max_moves_per_piece": 20,  # Very strict
        "max_consecutive_rotations": 3,
        "max_same_action_streak": 2,
        "max_backtrack_moves": 0,  # No backtracks
        "bonus_fraud_threshold": 300,
    }
}


def get_policy_validator(tenant_id: str, mode: str = "arcade_mode") -> GamePolicyValidator:
    """Factory function to create policy validator"""
    validator = GamePolicyValidator(tenant_id)
    validator.policies = TENANT_POLICIES.get(mode, TENANT_POLICIES["arcade_mode"])
    return validator
