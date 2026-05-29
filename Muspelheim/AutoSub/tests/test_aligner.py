"""Tests for autosub.aligner module."""

import pytest

from autosub.aligner import Aligner, Word
from autosub.transcriber import Segment


class TestWord:
    """Tests for the Word dataclass."""

    def test_word_fields(self):
        w = Word(word="hello", start=0.0, end=0.5)
        assert w.word == "hello"
        assert w.start == 0.0
        assert w.end == 0.5

    def test_word_str(self):
        w = Word(word="test", start=1.0, end=1.5)
        result = str(w)
        assert "test" in result

    def test_word_probability_default(self):
        w = Word(word="test", start=0.0, end=1.0)
        assert w.probability == 1.0

    def test_word_probability_custom(self):
        w = Word(word="test", start=0.0, end=1.0, probability=0.85)
        assert w.probability == 0.85


class TestAligner:
    """Tests for the Aligner class."""

    def test_align_segments_simple(self):
        segments = [Segment(text="hello world", start=0.0, end=2.0)]
        aligner = Aligner()
        result = aligner.align_segments(segments)
        assert len(result) == 1
        assert len(result[0]) == 2
        assert result[0][0].word == "hello"
        assert result[0][1].word == "world"

    def test_align_segments_proportional_timing(self):
        segments = [Segment(text="one two three", start=0.0, end=3.0)]
        aligner = Aligner()
        result = aligner.align_segments(segments)
        # Each word should get ~1 second
        assert result[0][0].start == pytest.approx(0.0)
        assert result[0][1].start == pytest.approx(1.0)
        assert result[0][2].start == pytest.approx(2.0)

    def test_align_empty_segment(self):
        segments = [Segment(text="", start=0.0, end=1.0)]
        aligner = Aligner()
        result = aligner.align_segments(segments)
        assert len(result) == 1
        assert len(result[0]) == 0

    def test_align_multiple_segments(self):
        segments = [
            Segment(text="hello world", start=0.0, end=2.0),
            Segment(text="goodbye", start=2.0, end=3.0),
        ]
        aligner = Aligner()
        result = aligner.align_segments(segments)
        assert len(result) == 2
        assert len(result[0]) == 2
        assert len(result[1]) == 1

    def test_realign_basic(self):
        words = [
            [
                Word(word="hello", start=0.0, end=0.5),
                Word(word="world", start=0.5, end=1.0),
            ]
        ]
        aligner = Aligner()
        result = aligner.realign(words)
        assert len(result) == 1
        assert len(result[0]) == 2

    def test_realign_with_gap(self):
        words = [
            [
                Word(word="hello", start=0.0, end=0.5),
                Word(word="world", start=5.0, end=5.5),
            ]
        ]
        aligner = Aligner()
        result = aligner.realign(words, max_gap=0.5)
        # Should split into 2 segments due to 4.5s gap
        assert len(result) == 2

    def test_realign_empty(self):
        aligner = Aligner()
        result = aligner.realign([])
        assert result == []

    def test_words_to_segments(self):
        word_groups = [
            [
                Word(word="hello", start=0.0, end=0.5),
                Word(word="world", start=0.5, end=1.0),
            ],
            [Word(word="goodbye", start=2.0, end=2.5)],
        ]
        aligner = Aligner()
        segments = aligner.words_to_segments(word_groups)
        assert len(segments) == 2
        assert segments[0].text == "hello world"
        assert segments[0].start == 0.0
        assert segments[0].end == 1.0
        assert segments[1].text == "goodbye"

    def test_words_to_segments_empty_group(self):
        word_groups = [
            [Word(word="test", start=0.0, end=1.0)],
            [],
        ]
        aligner = Aligner()
        segments = aligner.words_to_segments(word_groups)
        assert len(segments) == 1
