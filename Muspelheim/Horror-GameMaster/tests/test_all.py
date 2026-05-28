"""
Comprehensive tests for the Horror GameMaster engine.

Tests all modules: Pattern Analyzer, Procedural Generator,
Tension Manager, Context Manager, NPC Intelligence, GameMaster.
"""

import json
import tempfile
import time
from pathlib import Path

import pytest

# ── Imports ──────────────────────────────────────────────────────────

from pattern_analyzer import (
    PatternAnalyzer,
    ExtendedAction,
    ExplorationStyle,
    BraveryIndex,
    FearVelocity,
    PredictionResult,
)
from procedural_generator import (
    ProceduralGenerator,
    SceneType,
    EventType,
    NarrativeAct,
    EntityBehavior,
    SceneTemplate,
    GameEvent2,
    ChainEvent,
    SafeRoom,
    EntitySpawn,
)
from tension_manager import (
    TensionManager,
    TensionState,
    CooldownState,
    DecisionType,
    TensionDecision,
)
from context_manager import (
    ContextManager,
    ThreadType,
    ForeshadowState,
    NarrativeThread,
    ForeshadowSeed,
    Callback,
    SessionContext,
)
from npc_intelligence import (
    NPCIntelligence,
    NPCRole,
    NPCBehavior,
    TrustLevel,
    NPCProfile,
    Doppelganger,
    TrustSystem,
)
from memory.player_memory import (
    FearDimension,
    FearFingerprint,
    PlayerFearProfile,
    PlayerMemoryStore,
    GameEvent,
    EventCategory,
    ActionType,
    HabituationTracker,
    SessionMemory,
)


# ═══════════════════════════════════════════════════════════════════
# Pattern Analyzer Tests
# ═══════════════════════════════════════════════════════════════════


class TestPatternAnalyzer:
    def test_record_action(self):
        pa = PatternAnalyzer()
        pa.record_action(ExtendedAction.MOVE, location="corridor")
        assert len(pa.action_history) == 1
        assert pa.action_history[0].action == ExtendedAction.MOVE

    def test_fear_response(self):
        pa = PatternAnalyzer()
        pa.record_fear_response(FearDimension.DARKNESS, 0.8, "dark room")
        fp = pa.get_fingerprint()
        assert fp.darkness > 0.5

    def test_exploration_style_default(self):
        pa = PatternAnalyzer()
        assert pa.get_exploration_style() == ExplorationStyle.BALANCED

    def test_exploration_style_thorough(self):
        pa = PatternAnalyzer()
        for _ in range(15):
            pa.record_action(ExtendedAction.EXAMINE)
        pa.record_action(ExtendedAction.MOVE)
        assert pa.get_exploration_style() == ExplorationStyle.THOROUGH

    def test_exploration_style_cautious(self):
        pa = PatternAnalyzer()
        for _ in range(10):
            pa.record_action(ExtendedAction.HIDE)
        assert pa.get_exploration_style() == ExplorationStyle.CAUTIOUS

    def test_bravery_index_default(self):
        pa = PatternAnalyzer()
        assert pa.get_bravery_index() == BraveryIndex.NERVOUS

    def test_bravery_index_panicking(self):
        pa = PatternAnalyzer()
        for _ in range(5):
            pa.record_action(ExtendedAction.PANIC)
        pa.record_action(ExtendedAction.FLEE)
        assert pa.get_bravery_index() in (BraveryIndex.PANICKING, BraveryIndex.FROZEN)

    def test_novelty_scores(self):
        pa = PatternAnalyzer()
        pa.record_fear_response(FearDimension.DARKNESS, 0.8)
        pa.record_fear_response(FearDimension.DARKNESS, 0.8)
        pa.record_fear_response(FearDimension.DARKNESS, 0.8)
        scores = pa.get_novelty_scores()
        assert scores[FearDimension.DARKNESS] < 1.0

    def test_fresh_fears(self):
        pa = PatternAnalyzer()
        fresh = pa.get_fresh_fears()
        assert len(fresh) == 7  # All fresh initially

    def test_recommend_rotation(self):
        pa = PatternAnalyzer()
        rotation = pa.recommend_fear_rotation()
        assert len(rotation) == 7
        assert isinstance(rotation[0], FearDimension)

    def test_prediction(self):
        pa = PatternAnalyzer()
        for _ in range(10):
            pa.record_action(ExtendedAction.MOVE)
        pred = pa.predict_next()
        assert isinstance(pred, PredictionResult)
        assert 0.0 <= pred.timing_score <= 1.0

    def test_session_stats(self):
        pa = PatternAnalyzer()
        pa.record_action(ExtendedAction.MOVE)
        pa.record_action(ExtendedAction.EXAMINE)
        stats = pa.get_session_stats()
        assert stats["total_actions"] == 2
        assert "exploration_style" in stats
        assert "bravery_index" in stats


# ═══════════════════════════════════════════════════════════════════
# Procedural Generator Tests
# ═══════════════════════════════════════════════════════════════════


class TestProceduralGenerator:
    def test_generate_scene(self):
        pg = ProceduralGenerator(seed=42)
        scene = pg.generate_scene(SceneType.MIRROR_MAZE)
        assert isinstance(scene, SceneTemplate)
        assert scene.scene_type == SceneType.MIRROR_MAZE

    def test_generate_random_scene(self):
        pg = ProceduralGenerator(seed=42)
        scene = pg.generate_scene()
        assert isinstance(scene, SceneTemplate)

    def test_generate_scene_by_fear(self):
        pg = ProceduralGenerator(seed=42)
        scene = pg.generate_scene_by_fear("darkness")
        assert "darkness" in scene.fear_types

    def test_generate_event(self):
        pg = ProceduralGenerator(seed=42)
        event = pg.generate_event(EventType.ESCALATION, intensity=0.7)
        assert isinstance(event, GameEvent2)
        assert event.event_type == EventType.ESCALATION
        assert event.intensity == 0.7

    def test_generate_red_herring(self):
        pg = ProceduralGenerator(seed=42)
        event = pg.generate_red_herring()
        assert event.event_type == EventType.RED_HERRING

    def test_safe_room(self):
        pg = ProceduralGenerator(seed=42)
        room = pg.create_safe_room("room1", "Closet", "A small closet")
        assert room.safety_level == 1.0
        assert not room.compromised

    def test_safe_room_degradation(self):
        pg = ProceduralGenerator(seed=42)
        room = pg.create_safe_room("room1", "Closet", "A small closet")
        for _ in range(25):
            pg.degrade_safe_room(room)
        assert room.safety_level < 1.0

    def test_entity_spawn(self):
        pg = ProceduralGenerator(seed=42)
        entity = pg.spawn_entity("Test", "A test entity", EntityBehavior.STALKING, "darkness")
        assert entity.name == "Test"
        assert entity.behavior == EntityBehavior.STALKING

    def test_entity_encounter(self):
        pg = ProceduralGenerator(seed=42)
        entity = pg.generate_entity_encounter("body_horror")
        assert isinstance(entity, EntitySpawn)
        assert entity.fear_type == "body_horror"

    def test_narrative_progression(self):
        pg = ProceduralGenerator(seed=42)
        assert pg.narrative.current_act == NarrativeAct.SETUP
        pg.advance_narrative()
        assert pg.narrative.current_act == NarrativeAct.RISING_TENSION

    def test_ending(self):
        pg = ProceduralGenerator(seed=42)
        ending = pg.generate_ending()
        assert len(ending) > 50

    def test_chain_events(self):
        pg = ProceduralGenerator(seed=42)
        events = [pg.generate_event(EventType.FORESHADOWING) for _ in range(3)]
        chain = pg.create_chain("test", "Test Chain", events)
        assert len(chain.events) == 3
        first = pg.advance_chain(chain)
        assert first is not None


# ═══════════════════════════════════════════════════════════════════
# Tension Manager Tests
# ═══════════════════════════════════════════════════════════════════


class TestTensionManager:
    def test_initial_state(self):
        tm = TensionManager()
        assert tm.state == TensionState.CALM
        assert tm.tension == 0.1

    def test_atmosphere_increases_tension(self):
        tm = TensionManager()
        initial = tm.tension
        tm.on_event("atmosphere", intensity=0.5)
        assert tm.tension > initial

    def test_scare_triggers_cooldown(self):
        tm = TensionManager()
        tm.on_event("scare", intensity=0.8)
        assert tm.cooldown.state in (CooldownState.ACTIVE, CooldownState.FADING)

    def test_cooldown_blocks_scares(self):
        tm = TensionManager()
        tm.on_event("scare", intensity=0.8)
        tension_before = tm.tension
        tm.on_event("scare", intensity=0.5)  # Should be blocked
        assert tm.tension <= tension_before + 0.1

    def test_false_security(self):
        tm = TensionManager()
        tm.on_event("atmosphere", intensity=0.5)
        tm.trigger_false_security()
        assert tm.false_security.active

    def test_escalation(self):
        tm = TensionManager()
        initial_level = tm.escalation_level
        for _ in range(10):
            tm.on_event("tension", intensity=0.5)
        assert tm.escalation_level >= initial_level

    def test_decide_returns_decision(self):
        tm = TensionManager()
        decision = tm.decide()
        assert isinstance(decision, TensionDecision)
        assert decision.decision in DecisionType.__members__.values()

    def test_state_summary(self):
        tm = TensionManager()
        summary = tm.get_state_summary()
        assert "tension" in summary
        assert "state" in summary
        assert "escalation_level" in summary

    def test_reset(self):
        tm = TensionManager()
        tm.on_event("scare", intensity=0.8)
        tm.reset()
        assert tm.tension == 0.1
        assert tm.state == TensionState.CALM


# ═══════════════════════════════════════════════════════════════════
# Context Manager Tests
# ═══════════════════════════════════════════════════════════════════


class TestContextManager:
    def test_update_scene(self):
        ctx = ContextManager("test")
        ctx.update_scene("Dark corridor", "corridor")
        assert ctx.session.current_scene == "Dark corridor"
        assert ctx.session.turn_count == 1

    def test_plant_foreshadow(self):
        ctx = ContextManager("test")
        seed = ctx.plant_foreshadow("A bell tolls", "The bell is here")
        assert seed.state == ForeshadowState.PLANTED
        assert len(ctx.get_active_foreshadows()) == 1

    def test_foreshadow_ready(self):
        ctx = ContextManager("test")
        seed = ctx.plant_foreshadow("A bell", "Bell here", deliver_after=1)
        ctx.update_scene("Room 1")
        ctx.update_scene("Room 2")  # 2 events, seed needs 1
        assert seed.is_ready

    def test_deliver_foreshadow(self):
        ctx = ContextManager("test")
        seed = ctx.plant_foreshadow("A bell", "Bell here", deliver_after=0)
        payoff = ctx.deliver_foreshadow(seed)
        assert payoff == "Bell here"
        assert seed.state == ForeshadowState.DELIVERED

    def test_callbacks(self):
        ctx = ContextManager("test")
        cb = ctx.add_callback("Found a key", "The key you found")
        assert cb.original_event == "Found a key"
        callbacks = ctx.get_callbacks()
        assert len(callbacks) == 1

    def test_narrative_threads(self):
        ctx = ContextManager("test")
        thread = ctx.create_thread("Mystery", "What happened", ThreadType.MAIN)
        ctx.add_to_thread(thread, "Found a clue")
        assert len(thread.events) == 1
        assert len(ctx.get_active_threads()) == 1

    def test_resolve_thread(self):
        ctx = ContextManager("test")
        thread = ctx.create_thread("Mystery", "What happened")
        ctx.resolve_thread(thread)
        assert thread.resolved
        assert len(ctx.get_active_threads()) == 0

    def test_build_context_prompt(self):
        ctx = ContextManager("test")
        ctx.update_scene("Dark room", "room")
        ctx.record_action("I look around")
        prompt = ctx.build_context_prompt()
        assert "Dark room" in prompt
        assert "I look around" in prompt

    def test_auto_seed(self):
        ctx = ContextManager("test")
        seed = ctx.auto_seed_foreshadow("darkness")
        assert seed is not None
        assert seed.fear_type == "darkness"

    def test_summary(self):
        ctx = ContextManager("test")
        summary = ctx.get_summary()
        assert "session_id" in summary
        assert "turn" in summary


# ═══════════════════════════════════════════════════════════════════
# NPC Intelligence Tests
# ═══════════════════════════════════════════════════════════════════


class TestNPCIntelligence:
    def test_create_npc(self):
        npc_sys = NPCIntelligence()
        npc = npc_sys.create_npc("Elise", NPCRole.ALLY, "A survivor")
        assert npc.name == "Elise"
        assert npc.role == NPCRole.ALLY

    def test_npc_dialogue(self):
        npc_sys = NPCIntelligence()
        npc = npc_sys.create_npc("Test", NPCRole.ALLY, "Helper")
        dialogue = npc_sys.generate_dialogue(npc, "Hello")
        assert len(dialogue) > 0
        assert "Test" in dialogue

    def test_npc_behavior_misleading(self):
        npc_sys = NPCIntelligence()
        npc = npc_sys.create_npc("Liar", NPCRole.SUSPECT, "Suspicious")
        npc.behavior = NPCBehavior.MISLEADING
        dialogue = npc_sys.generate_dialogue(npc, "Is it safe?")
        assert "safe" in dialogue.lower() or "trust" in dialogue.lower() or "nothing" in dialogue.lower()

    def test_trust_system(self):
        npc_sys = NPCIntelligence()
        npc = npc_sys.create_npc("Test", NPCRole.ALLY, "Helper")
        assert npc_sys.trust_system.get_trust(npc.npc_id) == TrustLevel.UNKNOWN
        npc_sys.update_trust(npc, "I trust you")
        assert npc_sys.trust_system.get_trust(npc.npc_id) != TrustLevel.UNKNOWN

    def test_betrayal(self):
        npc_sys = NPCIntelligence()
        npc = npc_sys.create_npc("Traitor", NPCRole.ALLY, "Seems friendly")
        result = npc_sys.simulate_betrayal(npc)
        assert npc.revealed
        assert npc.role == NPCRole.HOSTILE
        assert npc_sys.trust_system.betrayals == 1

    def test_doppelganger(self):
        npc_sys = NPCIntelligence()
        dop = npc_sys.spawn_doppelganger("Player")
        assert dop.stage == 1
        desc = npc_sys.advance_doppelganger()
        assert dop.stage == 2
        assert len(desc) > 0

    def test_doppelganger_encounter(self):
        npc_sys = NPCIntelligence()
        npc_sys.spawn_doppelganger()
        encounter = npc_sys.generate_doppelganger_encounter()
        assert len(encounter) > 0

    def test_npc_learning(self):
        npc_sys = NPCIntelligence()
        npc = npc_sys.create_npc("Observer", NPCRole.SUSPECT, "Watches")
        initial_awareness = npc.awareness
        for _ in range(5):
            npc_sys.generate_dialogue(npc, "test")
        assert npc.awareness > initial_awareness

    def test_paranoia_level(self):
        npc_sys = NPCIntelligence()
        assert 0.0 <= npc_sys.trust_system.paranoia_level <= 1.0
        npc_sys.trust_system.record_betrayal()
        assert npc_sys.trust_system.paranoia_level > 0.3

    def test_summary(self):
        npc_sys = NPCIntelligence()
        npc_sys.create_npc("Test", NPCRole.ALLY, "Helper")
        summary = npc_sys.get_summary()
        assert summary["total_npcs"] == 1


# ═══════════════════════════════════════════════════════════════════
# Memory Module Tests
# ═══════════════════════════════════════════════════════════════════


class TestMemoryModule:
    def test_fear_fingerprint(self):
        fp = FearFingerprint()
        for d in FearDimension:
            assert fp.get(d) == 0.5

    def test_fingerprint_clamps(self):
        fp = FearFingerprint()
        fp.set(FearDimension.DARKNESS, 1.5)
        assert fp.get(FearDimension.DARKNESS) == 1.0
        fp.set(FearDimension.DARKNESS, -0.5)
        assert fp.get(FearDimension.DARKNESS) == 0.0

    def test_dominant_fear(self):
        fp = FearFingerprint()
        fp.set(FearDimension.PARANOIA, 0.95)
        assert fp.dominant_fear() == FearDimension.PARANOIA

    def test_habituation(self):
        ht = HabituationTracker(fear_type=FearDimension.DARKNESS)
        assert ht.habituation_score == 0.0
        ht.record_exposure(0.8)
        assert ht.habituation_score > 0.0

    def test_player_memory_store(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "test.db"
            store = PlayerMemoryStore(db)
            profile = PlayerFearProfile(player_id="test")
            store.save_profile(profile)
            loaded = store.load_profile("test")
            assert loaded is not None
            assert loaded.player_id == "test"

    def test_player_memory_events(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "test.db"
            store = PlayerMemoryStore(db)
            store.get_or_create("player1")
            event = GameEvent(
                event_id="evt1",
                category=EventCategory.SCENE_DESCRIPTION,
                description="Test event",
                fear_types=[FearDimension.DARKNESS],
                intensity=0.7,
            )
            store.save_event("player1", event)
            events = store.get_recent_events("player1")
            assert len(events) == 1


# ═══════════════════════════════════════════════════════════════════
# GameMaster Integration Tests
# ═══════════════════════════════════════════════════════════════════


class TestGameMaster:
    def test_start(self):
        from gamemaster import GameMaster, GameConfig
        gm = GameMaster(GameConfig(session_id="test", enable_npc=False, enable_doppelganger=False))
        state = gm.start()
        assert state.scene != ""
        assert state.narrative != ""
        assert len(state.choices) > 0

    def test_process_action(self):
        from gamemaster import GameMaster, GameConfig
        gm = GameMaster(GameConfig(session_id="test", enable_npc=False, enable_doppelganger=False))
        state = gm.start()
        state = gm.process_action("I look around")
        assert state.turn == 1
        assert state.narrative != ""

    def test_classify_action(self):
        from gamemaster import GameMaster, GameConfig
        gm = GameMaster(GameConfig(session_id="test"))
        assert gm._classify_action("I open the door") == ExtendedAction.INTERACT
        assert gm._classify_action("I run away") == ExtendedAction.FLEE
        assert gm._classify_action("I hide") == ExtendedAction.HIDE
        assert gm._classify_action("I listen") == ExtendedAction.LISTEN

    def test_full_state(self):
        from gamemaster import GameMaster, GameConfig
        gm = GameMaster(GameConfig(session_id="test"))
        gm.start()
        state = gm.get_full_state()
        assert "game" in state
        assert "tension" in state
        assert "analyzer" in state


# ═══════════════════════════════════════════════════════════════════
# Dataset Quality Tests
# ═══════════════════════════════════════════════════════════════════


class TestDataset:
    @pytest.fixture
    def dataset_path(self):
        return Path(__file__).parent.parent / "data" / "dataset_final.jsonl"

    def test_dataset_exists(self, dataset_path):
        assert dataset_path.exists()

    def test_dataset_format(self, dataset_path):
        entries = []
        with open(dataset_path) as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    entries.append(obj)
        assert len(entries) >= 1000

    def test_dataset_fields(self, dataset_path):
        with open(dataset_path) as f:
            for i, line in enumerate(f):
                if i >= 10:
                    break
                obj = json.loads(line)
                assert "instruction" in obj
                assert "input" in obj
                assert "output" in obj
                assert "fear_type" in obj

    def test_dataset_fear_types(self, dataset_path):
        types = set()
        with open(dataset_path) as f:
            for line in f:
                obj = json.loads(line)
                types.add(obj["fear_type"])
        assert len(types) >= 5  # At least 5 fear types

    def test_dataset_no_filler(self, dataset_path):
        """Every output should be at least 100 characters."""
        with open(dataset_path) as f:
            for i, line in enumerate(f):
                if i >= 100:
                    break
                obj = json.loads(line)
                assert len(obj["output"]) >= 100, f"Entry {i} has short output: {len(obj['output'])} chars"

    def test_dataset_no_duplicates(self, dataset_path):
        seen = set()
        with open(dataset_path) as f:
            for line in f:
                obj = json.loads(line)
                key = obj["output"][:100]
                assert key not in seen, f"Duplicate found: {key[:50]}..."
                seen.add(key)
