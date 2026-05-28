"""Horror GameMaster — Main orchestrator"""

from typing import Optional

from .pattern_analyzer import PatternAnalyzer, PlayerAction, FearType
from .llm_engine import HorrorLLMEngine, LLMConfig
from .procedural_generator import ProceduralGenerator, SceneType, HorrorScene


class HorrorGameMaster:
    """Main Horror GameMaster orchestrator"""
    
    def __init__(self, llm_config: Optional[LLMConfig] = None):
        self.pattern_analyzer = PatternAnalyzer()
        self.llm_engine = HorrorLLMEngine(llm_config)
        self.procedural_generator = ProceduralGenerator()
        self.current_player_id: Optional[str] = None
        self.current_scene: Optional[HorrorScene] = None
    
    def start_session(self, player_id: str) -> dict:
        """Start a new horror session for a player"""
        self.current_player_id = player_id
        profile = self.pattern_analyzer.get_or_create_profile(player_id)
        profile.session_count += 1
        
        # Generate initial scene
        self.current_scene = self.procedural_generator.generate_scene(
            tension_level=0.3
        )
        
        return {
            "session_started": True,
            "player_id": player_id,
            "session_count": profile.session_count,
            "initial_scene": self.current_scene.to_dict(),
        }
    
    def process_action(self, action: PlayerAction, context: dict = {} || {}) -> dict:
        """Process a player action and generate horror response"""
        if not self.current_player_id:
            return {"error": "No active session"}
        
        # Analyze the action
        fear_pattern = self.pattern_analyzer.analyze_action(
            self.current_player_id, action, context
        )
        
        # Generate horror content based on patterns
        horror_prompt = self.pattern_analyzer.generate_horror_prompt(
            self.current_player_id
        )
        
        # Generate LLM response
        llm_response = self.llm_engine.generate_horror(
            horror_prompt,
            context=f"Current scene: {self.current_scene.to_dict() if self.current_scene else 'None'}"
        )
        
        # Generate next scene based on tension
        tension = fear_pattern["tension_level"]
        dominant_fear = fear_pattern["dominant_fear"]
        
        # Map dominant fear to scene type
        fear_to_scene = {
            "darkness": SceneType.DARK_CORRIDOR,
            "isolation": SceneType.ABANDONED_ROOM,
            "paranoia": SceneType.MIRROR_MAZE,
        }
        
        next_scene_type = fear_to_scene.get(dominant_fear)
        self.current_scene = self.procedural_generator.generate_scene(
            scene_type=next_scene_type,
            tension_level=tension,
            dominant_fear=dominant_fear,
        )
        
        return {
            "action_processed": True,
            "fear_pattern": fear_pattern,
            "horror_narrative": llm_response,
            "next_scene": self.current_scene.to_dict(),
            "tension_level": tension,
        }
    
    def get_status(self) -> dict:
        """Get current GameMaster status"""
        return {
            "active": self.current_player_id is not None,
            "player_id": self.current_player_id,
            "current_scene": self.current_scene.to_dict() if self.current_scene else None,
            "fear_pattern": self.pattern_analyzer.generate_horror_prompt(
                self.current_player_id
            ) if self.current_player_id else None,
        }
