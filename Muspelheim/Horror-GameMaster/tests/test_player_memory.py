"""Tests for the player memory system."""

import tempfile
from pathlib import Path

import pytest

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


class TestFearFingerprint:
    def test_defaults_are_half(self):
        fp = FearFingerprint()
        for d in FearDimension:
            assert fp.get(d) == 0.5

    def test_set_clamps(self):
        fp = FearFingerprint()
        fp.set(FearDimension.DARKNESS, 1.5)
        assert fp.get(FearDimension.DARKNESS) == 1.0
        fp.set(FearDimension.DARKNESS, -0.5)
        assert fp.get(FearDimension.DARKNESS) == 0.0

    def test_dominant_fear(self):
        fp = FearFingerprint()
        fp.set(FearDimension.PARANOIA, 0.95)
        assert fp.dominant_fear() == FearDimension.PARANOIA

    def test_top_fears(self):
        fp = FearFingerprint()
        fp.set(FearDimension.DARKNESS, 0.9)
        fp.set(FearDimension.ISOLATION, 0.8)
        fp.set(FearDimension.PSYCHOLOGICAL, 0.7)
        top = fp.top_fears(2)
        assert top[0][0] == FearDimension.DARKNESS
        assert top[1][0] == FearDimension.ISOLATION

    def test_to_vector(self):
        fp = FearFingerprint()
        vec = fp.to_vector()
        assert vec.shape == (7,)
        assert all(v == 0.5 for v in vec)


class TestHabituationTracker:
    def test_exposure_increases_habituation(self):
        ht = HabituationTracker(fear_type=FearDimension.DARKNESS)
        assert ht.habituation_score == 0.0
        ht.record_exposure(0.8)
        assert ht.habituation_score > 0.0

    def test_diminishing_returns(self):
        ht = HabituationTracker(fear_type=FearDimension.DARKNESS)
        ht.record_exposure(0.8)
        first = ht.habituation_score
        ht.record_exposure(0.8)
        second = ht.habituation_score
        assert second - first < first  # diminishing returns

    def test_should_escalate(self):
        ht = HabituationTracker(fear_type=FearDimension.DARKNESS)
        assert not ht.should_escalate()
        for _ in range(10):
            ht.record_exposure(0.9)
        assert ht.should_escalate()

    def test_cooldown(self):
        ht = HabituationTracker(fear_type=FearDimension.DARKNESS)
        ht.record_exposure(0.9)
        assert ht.is_cooling_down()


class TestPlayerFearProfile:
    def test_record_response_updates_fingerprint(self):
        profile = PlayerFearProfile(player_id="test")
        old_val = profile.fingerprint.get(FearDimension.DARKNESS)
        profile.record_response(
            fear_type=FearDimension.DARKNESS,
            stimulus="dark corridor",
            action=ActionType.FLEE,
            intensity=0.9,
        )
        new_val = profile.fingerprint.get(FearDimension.DARKNESS)
        assert new_val != old_val

    def test_fresh_and_stale_fears(self):
        profile = PlayerFearProfile(player_id="test")
        # Habituate to darkness
        for _ in range(15):
            profile.record_response(
                fear_type=FearDimension.DARKNESS,
                stimulus="dark",
                action=ActionType.FLEE,
                intensity=0.9,
            )
        stale = profile.get_stale_fears()
        assert FearDimension.DARKNESS in stale
        fresh = profile.get_fresh_fears()
        assert FearDimension.DARKNESS not in fresh


class TestPlayerMemoryStore:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "test.db"
            store = PlayerMemoryStore(db)
            profile = PlayerFearProfile(player_id="player1")
            store.save_profile(profile)
            loaded = store.load_profile("player1")
            assert loaded is not None
            assert loaded.player_id == "player1"

    def test_get_or_create(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "test.db"
            store = PlayerMemoryStore(db)
            p1 = store.get_or_create("new_player")
            assert p1.player_id == "new_player"
            p2 = store.get_or_create("new_player")
            assert p2.player_id == "new_player"

    def test_save_and_get_events(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "test.db"
            store = PlayerMemoryStore(db)
            store.get_or_create("player1")
            event = GameEvent(
                event_id="evt1",
                category=EventCategory.SCENE_DESCRIPTION,
                description="A dark corridor",
                fear_types=[FearDimension.DARKNESS],
                intensity=0.7,
            )
            store.save_event("player1", event)
            events = store.get_recent_events("player1")
            assert len(events) == 1
            assert events[0].event_id == "evt1"

    def test_list_players(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "test.db"
            store = PlayerMemoryStore(db)
            store.get_or_create("a")
            store.get_or_create("b")
            players = store.list_players()
            assert set(players) == {"a", "b"}
