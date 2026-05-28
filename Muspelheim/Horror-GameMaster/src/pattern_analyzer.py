"""Pattern Analyzer — Detects player fear patterns"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FearType(Enum):
    """Types of fear the system can detect"""
    DARKNESS = "darkness"
    ISOLATION = "isolation"
    JUMPSCARE = "jumpscare"
    PSYCHOLOGICAL = "psychological"
    BODY_HORROR = "body_horror"
    UNKNOWN = "unknown"
    PARANOIA = "paranoia"
    LOSS_OF_CONTROL = "loss_of_control"


class PlayerAction(Enum):
    """Types of player actions"""
    EXPLORE = "explore"
    HIDE = "hide"
    RUN = "run"
    FIGHT = "fight"
    FREEZE = "freeze"
    INVESTIGATE = "investigate"
    AVOID = "avoid"
    PANIC = "panic"


@dataclass
class PlayerProfile:
    """Psychological profile of the player"""
    fear_scores: dict[FearType, float] = field(default_factory=lambda: {f: 0.0 for f in FearType})
    action_history: list[PlayerAction] = field(default_factory=list)
    tension_level: float = 0.0  # 0.0 to 1.0
    session_count: int = 0
    dominant_fear: Optional[FearType] = None
    
    def update_fear(self, fear_type: FearType, score: float):
        """Update fear score"""
        self.fear_scores[fear_type] = min(1.0, max(0.0, score))
        self.dominant_fear = max(self.fear_scores, key=lambda k: self.fear_scores[k])
    
    def add_action(self, action: PlayerAction):
        """Record player action"""
        self.action_history.append(action)
        # Keep last 100 actions
        if len(self.action_history) > 100:
            self.action_history = self.action_history[-100:]
    
    def get_fear_pattern(self) -> dict:
        """Analyze fear patterns"""
        return {
            "dominant_fear": self.dominant_fear.value if self.dominant_fear else None,
            "fear_scores": {k.value: v for k, v in self.fear_scores.items()},
            "tension_level": self.tension_level,
            "action_pattern": self._analyze_action_pattern(),
        }
    
    def _analyze_action_pattern(self) -> str:
        """Analyze recent action patterns"""
        if not self.action_history:
            return "unknown"
        
        recent = self.action_history[-10:]
        hide_count = sum(1 for a in recent if a == PlayerAction.HIDE)
        run_count = sum(1 for a in recent if a == PlayerAction.RUN)
        freeze_count = sum(1 for a in recent if a == PlayerAction.FREEZE)
        
        if hide_count > 5:
            return "avoidant"
        elif run_count > 5:
            return "flight_response"
        elif freeze_count > 5:
            return "freeze_response"
        else:
            return "balanced"


class PatternAnalyzer:
    """Analyzes player behavior to detect fear patterns"""
    
    def __init__(self):
        self.profiles: dict[str, PlayerProfile] = {}
    
    def get_or_create_profile(self, player_id: str) -> PlayerProfile:
        """Get or create player profile"""
        if player_id not in self.profiles:
            self.profiles[player_id] = PlayerProfile()
        return self.profiles[player_id]
    
    def analyze_action(self, player_id: str, action: PlayerAction, context: dict = None):
        """Analyze a player action and update profile"""
        profile = self.get_or_create_profile(player_id)
        profile.add_action(action)
        
        # Update fear scores based on action
        if action == PlayerAction.HIDE:
            profile.update_fear(FearType.ISOLATION, profile.fear_scores[FearType.ISOLATION] + 0.1)
            profile.update_fear(FearType.PARANOIA, profile.fear_scores[FearType.PARANOIA] + 0.05)
        elif action == PlayerAction.RUN:
            profile.update_fear(FearType.JUMPSCARE, profile.fear_scores[FearType.JUMPSCARE] + 0.1)
        elif action == PlayerAction.FREEZE:
            profile.update_fear(FearType.PSYCHOLOGICAL, profile.fear_scores[FearType.PSYCHOLOGICAL] + 0.1)
            profile.update_fear(FearType.LOSS_OF_CONTROL, profile.fear_scores[FearType.LOSS_OF_CONTROL] + 0.1)
        elif action == PlayerAction.AVOID:
            profile.update_fear(FearType.DARKNESS, profile.fear_scores[FearType.DARKNESS] + 0.05)
            profile.update_fear(FearType.BODY_HORROR, profile.fear_scores[FearType.BODY_HORROR] + 0.05)
        
        # Update tension
        profile.tension_level = min(1.0, profile.tension_level + 0.02)
        
        return profile.get_fear_pattern()
    
    def generate_horror_prompt(self, player_id: str) -> str:
        """Generate a horror prompt based on player profile"""
        profile = self.get_or_create_profile(player_id)
        pattern = profile.get_fear_pattern()
        
        dominant = pattern["dominant_fear"] or "unknown"
        tension = pattern["tension_level"]
        action_pattern = pattern["action_pattern"]
        
        prompt = f"""Player Profile:
- Dominant Fear: {dominant}
- Tension Level: {tension:.1%}
- Action Pattern: {action_pattern}

Generate a horror scenario that:
1. Exploits the player's dominant fear ({dominant})
2. Maintains tension at {tension:.1%}
3. Adapts to their {action_pattern} behavior pattern
4. Creates psychological discomfort without relying on jumpscares
5. Builds mystery and unease gradually"""
        
        return prompt
