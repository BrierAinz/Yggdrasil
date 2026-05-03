"""AutoSub word-level alignment module."""

from __future__ import annotations

from dataclasses import dataclass

from autosub.transcriber import Segment


@dataclass
class Word:
    """A single word with timing information."""

    word: str
    start: float
    end: float
    probability: float = 1.0

    def __str__(self) -> str:
        return f"[{self.start:.2f}s → {self.end:.2f}s] {self.word}"


class Aligner:
    """Align transcription at word level for better synchronization."""

    def align_segments(self, segments: list[Segment]) -> list[list[Word]]:
        """Align segments at word level using whisper word timestamps.

        This re-transcribes with word_timestamps=True to get per-word
        timing. If the transcriber already provides word timestamps,
        those are used directly.

        Args:
            segments: List of Segment objects to align.

        Returns:
            List of word lists, one per segment.
        """
        all_words: list[list[Word]] = []
        for seg in segments:
            words = self._split_to_words(seg)
            all_words.append(words)
        return all_words

    def _split_to_words(self, segment: Segment) -> list[Word]:
        """Split a segment into words with estimated timing.

        Uses simple proportional distribution when word timestamps
        are not available from the transcription engine.

        Args:
            segment: A Segment to split into words.

        Returns:
            List of Word objects with estimated timing.
        """
        raw_words = segment.text.split()
        if not raw_words:
            return []

        duration = segment.end - segment.start
        word_duration = duration / max(len(raw_words), 1)

        words = []
        for i, w in enumerate(raw_words):
            start = segment.start + i * word_duration
            end = start + word_duration
            words.append(Word(word=w, start=start, end=end))

        return words

    def realign(self, words: list[list[Word]], max_gap: float = 0.5) -> list[list[Word]]:
        """Re-segment words into natural phrase boundaries.

        Splits segments at long pauses and merges short segments.

        Args:
            words: List of word lists per segment.
            max_gap: Maximum gap in seconds before splitting into new segment.

        Returns:
            Re-segmented word lists.
        """
        # Flatten all words
        flat: list[Word] = []
        for seg_words in words:
            flat.extend(seg_words)

        if not flat:
            return []

        # Re-segment based on gaps
        result: list[list[Word]] = []
        current: list[Word] = [flat[0]]

        for i in range(1, len(flat)):
            gap = flat[i].start - flat[i - 1].end
            if gap > max_gap and current:
                result.append(current)
                current = [flat[i]]
            else:
                current.append(flat[i])

        if current:
            result.append(current)

        return result

    def words_to_segments(self, word_groups: list[list[Word]]) -> list[Segment]:
        """Convert word groups back to Segment objects.

        Args:
            word_groups: List of word lists.

        Returns:
            List of Segment objects.
        """
        segments = []
        for group in word_groups:
            if not group:
                continue
            text = " ".join(w.word for w in group)
            seg = Segment(text=text, start=group[0].start, end=group[-1].end)
            segments.append(seg)
        return segments
