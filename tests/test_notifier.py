"""Notifier: abstract base cannot be instantiated; ConsoleNotifier.alert() prints ALERT line."""
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
