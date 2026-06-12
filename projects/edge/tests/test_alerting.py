"""Adversarial tests for situation_monitor.alerting.check_and_emit_alerts.

Covers:
- Threshold boundary (== triggers, just-below does not)
- Return value semantics (only triggered articles)
- Output format written to the stream
- StringIO as output target (no exception)
- Edge inputs: empty list, negative scores, threshold at extremes
"""
from __future__ import annotations

import io
import types

import pytest

from situation_monitor.alerting import Scorable, check_and_emit_alerts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_article(title: str, score: float) -> types.SimpleNamespace:
    """Minimal Scorable-compatible object (no mocking the unit under test)."""
    return types.SimpleNamespace(title=title, score=score)


# ---------------------------------------------------------------------------
# Scorable protocol
# ---------------------------------------------------------------------------

class TestScorableProtocol:
    def test_object_with_score_and_title_is_scorable(self):
        obj = make_article("Item", 0.5)
        assert isinstance(obj, Scorable)

    def test_object_missing_score_is_not_scorable(self):
        obj = types.SimpleNamespace(title="Item")
        assert not isinstance(obj, Scorable)

    def test_object_missing_title_is_not_scorable(self):
        obj = types.SimpleNamespace(score=0.5)
        assert not isinstance(obj, Scorable)

    def test_object_with_extra_attrs_is_still_scorable(self):
        obj = types.SimpleNamespace(title="X", score=0.9, relevance_score=0.9, extra="y")
        assert isinstance(obj, Scorable)


# ---------------------------------------------------------------------------
# Threshold boundary — the critical acceptance criterion
# ---------------------------------------------------------------------------

class TestThresholdBoundary:
    def test_score_equal_to_threshold_triggers_alert(self):
        """score == threshold must fire; the docstring says 'meets or exceeds'."""
        article = make_article("Boundary Hit", score=0.75)
        triggered = check_and_emit_alerts([article], threshold=0.75, output=io.StringIO())
        assert len(triggered) == 1
        assert triggered[0] is article

    def test_score_just_above_threshold_triggers_alert(self):
        article = make_article("Above", score=0.751)
        triggered = check_and_emit_alerts([article], threshold=0.75, output=io.StringIO())
        assert len(triggered) == 1

    def test_score_just_below_threshold_does_not_trigger(self):
        article = make_article("Below", score=0.7499)
        triggered = check_and_emit_alerts([article], threshold=0.75, output=io.StringIO())
        assert triggered == []

    def test_threshold_zero_triggers_zero_score(self):
        article = make_article("Zero", score=0.0)
        triggered = check_and_emit_alerts([article], threshold=0.0, output=io.StringIO())
        assert len(triggered) == 1

    def test_threshold_one_blocks_all_below_one(self):
        articles = [make_article(f"a{i}", score=i * 0.1) for i in range(10)]
        triggered = check_and_emit_alerts(articles, threshold=1.0, output=io.StringIO())
        assert triggered == []

    def test_threshold_one_passes_score_of_exactly_one(self):
        article = make_article("Exact", score=1.0)
        triggered = check_and_emit_alerts([article], threshold=1.0, output=io.StringIO())
        assert len(triggered) == 1

    def test_negative_threshold_allows_negative_scores(self):
        article = make_article("Neg", score=-0.1)
        triggered = check_and_emit_alerts([article], threshold=-0.5, output=io.StringIO())
        assert len(triggered) == 1

    def test_score_at_negative_threshold_boundary(self):
        article = make_article("Neg boundary", score=-0.5)
        triggered = check_and_emit_alerts([article], threshold=-0.5, output=io.StringIO())
        assert len(triggered) == 1

    def test_score_below_negative_threshold_blocked(self):
        article = make_article("Neg blocked", score=-0.6)
        triggered = check_and_emit_alerts([article], threshold=-0.5, output=io.StringIO())
        assert triggered == []


# ---------------------------------------------------------------------------
# Return-value semantics
# ---------------------------------------------------------------------------

class TestReturnValue:
    def test_empty_input_returns_empty_list(self):
        result = check_and_emit_alerts([], threshold=0.5, output=io.StringIO())
        assert result == []

    def test_returns_list_not_generator(self):
        articles = [make_article("X", 0.9)]
        result = check_and_emit_alerts(articles, threshold=0.5, output=io.StringIO())
        assert isinstance(result, list)

    def test_returns_original_article_objects_not_copies(self):
        a1 = make_article("Orig", 0.8)
        result = check_and_emit_alerts([a1], threshold=0.5, output=io.StringIO())
        assert result[0] is a1

    def test_only_passing_articles_in_return_value(self):
        articles = [
            make_article("Pass", 0.9),
            make_article("Fail", 0.1),
            make_article("Pass2", 0.8),
        ]
        triggered = check_and_emit_alerts(articles, threshold=0.5, output=io.StringIO())
        assert len(triggered) == 2
        titles = {a.title for a in triggered}
        assert titles == {"Pass", "Pass2"}

    def test_return_order_preserves_input_order(self):
        articles = [make_article(f"item{i}", 0.9 - i * 0.01) for i in range(5)]
        triggered = check_and_emit_alerts(articles, threshold=0.5, output=io.StringIO())
        assert [a.title for a in triggered] == [a.title for a in articles]

    def test_all_below_threshold_returns_empty(self):
        articles = [make_article(f"low{i}", 0.1) for i in range(10)]
        result = check_and_emit_alerts(articles, threshold=0.9, output=io.StringIO())
        assert result == []

    def test_all_above_threshold_returns_all(self):
        articles = [make_article(f"hi{i}", 0.9) for i in range(5)]
        result = check_and_emit_alerts(articles, threshold=0.5, output=io.StringIO())
        assert len(result) == 5


# ---------------------------------------------------------------------------
# StringIO file-like output — acceptance criterion
# ---------------------------------------------------------------------------

class TestFilelikeOutput:
    def test_stringio_does_not_raise(self):
        buf = io.StringIO()
        articles = [make_article("News Item", score=0.9)]
        check_and_emit_alerts(articles, threshold=0.5, output=buf)

    def test_stringio_captures_alert_line_for_triggered_article(self):
        buf = io.StringIO()
        check_and_emit_alerts(
            [make_article("Breaking Story", score=0.8)],
            threshold=0.5,
            output=buf,
        )
        out = buf.getvalue()
        assert "Breaking Story" in out

    def test_stringio_contains_score_formatted(self):
        buf = io.StringIO()
        check_and_emit_alerts(
            [make_article("Headline", score=0.756)],
            threshold=0.5,
            output=buf,
        )
        out = buf.getvalue()
        assert "0.756" in out

    def test_stringio_empty_when_no_articles_triggered(self):
        buf = io.StringIO()
        check_and_emit_alerts(
            [make_article("Low relevance", score=0.1)],
            threshold=0.9,
            output=buf,
        )
        assert buf.getvalue() == ""

    def test_stringio_one_line_per_triggered_article(self):
        buf = io.StringIO()
        articles = [
            make_article("A", 0.9),
            make_article("B", 0.1),
            make_article("C", 0.8),
        ]
        check_and_emit_alerts(articles, threshold=0.5, output=buf)
        lines = [l for l in buf.getvalue().splitlines() if l.strip()]
        assert len(lines) == 2

    def test_stringio_at_boundary_score_produces_exactly_one_line(self):
        buf = io.StringIO()
        check_and_emit_alerts(
            [make_article("Boundary", score=0.5)],
            threshold=0.5,
            output=buf,
        )
        lines = [l for l in buf.getvalue().splitlines() if l.strip()]
        assert len(lines) == 1

    def test_output_line_contains_alert_keyword(self):
        buf = io.StringIO()
        check_and_emit_alerts(
            [make_article("Urgent", score=0.99)],
            threshold=0.5,
            output=buf,
        )
        assert "ALERT" in buf.getvalue()

    def test_custom_file_object_receives_writes(self):
        class _Writer:
            def __init__(self):
                self.written = []

            def write(self, s):
                self.written.append(s)

        writer = _Writer()
        check_and_emit_alerts(
            [make_article("Story", score=0.7)],
            threshold=0.5,
            output=writer,
        )
        assert len(writer.written) > 0
        combined = "".join(writer.written)
        assert "Story" in combined

    def test_default_output_is_stdout(self):
        # The default arg `output=sys.stdout` is bound at import time; calling
        # without an explicit output must not raise and must return the triggered list.
        import inspect
        sig = inspect.signature(check_and_emit_alerts)
        default = sig.parameters["output"].default
        import sys as _sys
        # Default at definition time was sys.stdout (might differ from current sys.stdout
        # when pytest replaces it, but it must still be a valid stream).
        assert hasattr(default, "write")
        # Calling without explicit output must also not raise.
        result = check_and_emit_alerts([make_article("Live", score=0.9)], threshold=0.5)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Edge and mixed-score scenarios
# ---------------------------------------------------------------------------

class TestMixedScores:
    def test_single_below_no_alert_no_output(self):
        buf = io.StringIO()
        triggered = check_and_emit_alerts(
            [make_article("Quiet", score=0.2)], threshold=0.5, output=buf
        )
        assert triggered == []
        assert buf.getvalue() == ""

    def test_single_above_one_alert_one_line(self):
        buf = io.StringIO()
        triggered = check_and_emit_alerts(
            [make_article("Loud", score=0.8)], threshold=0.5, output=buf
        )
        assert len(triggered) == 1
        assert buf.getvalue().count("\n") >= 1

    def test_large_batch_correct_count(self):
        articles = [make_article(f"item{i}", score=i / 100) for i in range(100)]
        buf = io.StringIO()
        triggered = check_and_emit_alerts(articles, threshold=0.5, output=buf)
        # items 50..99 have score 0.50..0.99, all >= 0.5
        assert len(triggered) == 50

    def test_float_precision_boundary(self):
        """0.1 + 0.2 in floating-point != 0.3 exactly; test that >=, not ==, is used."""
        score = 0.1 + 0.2   # 0.30000000000000004 in IEEE754
        buf = io.StringIO()
        triggered = check_and_emit_alerts(
            [make_article("Float", score=score)], threshold=0.3, output=buf
        )
        # score > 0.3 due to float rounding: should trigger
        assert len(triggered) == 1

    def test_high_volume_no_side_effects_between_calls(self):
        buf1 = io.StringIO()
        buf2 = io.StringIO()
        articles = [make_article("X", 0.9)]
        check_and_emit_alerts(articles, threshold=0.5, output=buf1)
        check_and_emit_alerts(articles, threshold=0.5, output=buf2)
        assert buf1.getvalue() == buf2.getvalue()

    def test_score_exact_float_0_5_triggers_at_0_5_threshold(self):
        """Use a score that IS exactly 0.5 in floating-point to verify == path."""
        article = make_article("HalfScore", score=0.5)
        buf = io.StringIO()
        triggered = check_and_emit_alerts([article], threshold=0.5, output=buf)
        assert len(triggered) == 1
        assert "HalfScore" in buf.getvalue()
