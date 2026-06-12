"""Notifier: abstract base cannot be instantiated; ConsoleNotifier.notify() prints ALERT line."""
import pytest

from deal_sniper.models import Listing
from deal_sniper.notifier import ConsoleNotifier, Notifier


def make_listing(**overrides):
    defaults = dict(title="Widget", price=50.0, url="http://ex.com/1", source="test")
    defaults.update(overrides)
    return Listing(**defaults)


# ---------------------------------------------------------------------------
# Notifier is abstract
# ---------------------------------------------------------------------------

class TestNotifierIsAbstract:
    def test_cannot_instantiate_notifier_directly(self):
        with pytest.raises(TypeError):
            Notifier()

    def test_subclass_missing_alert_is_still_abstract(self):
        class Incomplete(Notifier):
            pass
        with pytest.raises(TypeError):
            Incomplete()

    def test_concrete_subclass_with_alert_can_be_instantiated(self):
        class Concrete(Notifier):
            def alert(self, listing: Listing) -> None:
                pass

        n = Concrete()
        assert isinstance(n, Notifier)

    def test_abstract_alert_signature_accepts_listing(self):
        class Concrete(Notifier):
            def alert(self, listing: Listing) -> None:
                self.last = listing

        n = Concrete()
        listing = make_listing()
        n.alert(listing)
        assert n.last is listing


# ---------------------------------------------------------------------------
# ConsoleNotifier.notify() prints the supplied alert text
# ---------------------------------------------------------------------------

class TestConsoleNotifierNotify:
    def test_notify_prints_alert_text(self, capsys):
        n = ConsoleNotifier()
        listing = make_listing(title="Blue Chair", price=42.99, url="http://ex.com/1")
        n.notify(listing, "ALERT: Blue Chair $42.99 http://ex.com/1")
        out = capsys.readouterr().out
        assert "ALERT: Blue Chair $42.99 http://ex.com/1" in out

    def test_notify_prints_exactly_what_is_passed(self, capsys):
        n = ConsoleNotifier()
        listing = make_listing()
        alert_text = "DEAL ALERT: Widget | $50.00 | http://ex.com/1"
        n.notify(listing, alert_text)
        assert capsys.readouterr().out.strip() == alert_text

    def test_notify_writes_to_stdout_not_stderr(self, capsys):
        n = ConsoleNotifier()
        n.notify(make_listing(), "some alert")
        captured = capsys.readouterr()
        assert "some alert" in captured.out
        assert captured.err == ""

    def test_notify_multiple_calls_produce_separate_lines(self, capsys):
        n = ConsoleNotifier()
        n.notify(make_listing(), "alert one")
        n.notify(make_listing(), "alert two")
        lines = capsys.readouterr().out.splitlines()
        assert len(lines) == 2
        assert lines[0] == "alert one"
        assert lines[1] == "alert two"

    def test_notify_empty_alert_text_prints_blank_line(self, capsys):
        n = ConsoleNotifier()
        n.notify(make_listing(), "")
        out = capsys.readouterr().out
        assert out == "\n"

    def test_notify_does_not_add_extra_content(self, capsys):
        n = ConsoleNotifier()
        alert = "CUSTOM ALERT TEXT"
        n.notify(make_listing(), alert)
        assert capsys.readouterr().out.strip() == alert


# ---------------------------------------------------------------------------
# ConsoleNotifier.alert() formats the listing itself
# ---------------------------------------------------------------------------

class TestConsoleNotifierAlert:
    def test_alert_contains_title(self, capsys):
        n = ConsoleNotifier()
        n.alert(make_listing(title="Leather Sofa"))
        assert "Leather Sofa" in capsys.readouterr().out

    def test_alert_contains_url(self, capsys):
        n = ConsoleNotifier()
        n.alert(make_listing(url="http://ex.com/unique"))
        assert "http://ex.com/unique" in capsys.readouterr().out

    def test_alert_formats_price_to_two_decimals(self, capsys):
        n = ConsoleNotifier()
        n.alert(make_listing(price=7.5))
        assert "7.50" in capsys.readouterr().out

    def test_alert_contains_deal_alert_prefix(self, capsys):
        n = ConsoleNotifier()
        n.alert(make_listing())
        assert "DEAL ALERT" in capsys.readouterr().out

    def test_alert_writes_to_stdout_not_stderr(self, capsys):
        n = ConsoleNotifier()
        n.alert(make_listing())
        captured = capsys.readouterr()
        assert captured.err == ""
        assert captured.out

    def test_alert_is_single_line(self, capsys):
        n = ConsoleNotifier()
        n.alert(make_listing(title="T", price=1.0, url="http://u"))
        lines = capsys.readouterr().out.splitlines()
        assert len(lines) == 1

    def test_alert_format_contains_pipe_separators(self, capsys):
        n = ConsoleNotifier()
        n.alert(make_listing(title="Item", price=9.99, url="http://ex.com/x"))
        out = capsys.readouterr().out
        assert "|" in out
