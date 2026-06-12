"""Adversarial tests for poll_once and ConsoleNotifier."""
from __future__ import annotations


from deal_sniper.config import Config
from deal_sniper.listing import Listing
from deal_sniper.median import MedianTracker
from deal_sniper.notifier import ConsoleNotifier
from deal_sniper.poller import poll_once
from deal_sniper.rules import RulesEngine
from deal_sniper.store import ListingStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_listing(url: str, price: float = 50.0, title: str = "Widget") -> Listing:
    return Listing(title=title, price=price, url=url, source="test")


def make_config(
    *,
    price_max: float = 0.0,
    keywords: list[str] | None = None,
    percent_below_median: float = 0.0,
) -> Config:
    return Config(
        price_max=price_max,
        keywords=keywords or [],
        below_median_pct=percent_below_median,
        poll_interval_s=60,
        db_path=":memory:",  # not used by these tests directly
    )


class InMemorySource:
    """Test double: returns a fixed list of listings."""

    def __init__(self, listings: list[Listing]) -> None:
        self._listings = listings

    def fetch(self, query: str) -> list[Listing]:
        return list(self._listings)


class RecordingNotifier:
    """Captures every (listing, alert_text) pair passed to notify()."""

    def __init__(self) -> None:
        self.calls: list[tuple[Listing, str]] = []

    def notify(self, listing: Listing, alert_text: str) -> None:
        self.calls.append((listing, alert_text))


def make_components(
    listings: list[Listing],
    tmp_path,
    *,
    price_max: float = 0.0,
    keywords: list[str] | None = None,
    percent_below_median: float = 0.0,
):
    source = InMemorySource(listings)
    store = ListingStore(tmp_path / "test.db")
    config = make_config(
        price_max=price_max,
        keywords=keywords,
        percent_below_median=percent_below_median,
    )
    tracker = MedianTracker()
    engine = RulesEngine(config, tracker)
    notifier = RecordingNotifier()
    return source, store, engine, tracker, notifier


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_first_call_notifies_new_listing(self, tmp_path):
        listing = make_listing("https://ex.com/1", price=10.0)
        source, store, engine, tracker, notifier = make_components([listing], tmp_path)
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 1

    def test_second_call_does_not_renotify_same_listing(self, tmp_path):
        listing = make_listing("https://ex.com/1", price=10.0)
        source, store, engine, tracker, notifier = make_components([listing], tmp_path)
        poll_once(source, store, engine, tracker, notifier)
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 1  # only once despite two polls

    def test_many_polls_same_listing_notified_once(self, tmp_path):
        listing = make_listing("https://ex.com/only", price=5.0)
        source, store, engine, tracker, notifier = make_components([listing], tmp_path)
        for _ in range(10):
            poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 1

    def test_different_urls_each_notified_once(self, tmp_path):
        listings = [make_listing(f"https://ex.com/{i}", price=10.0) for i in range(4)]
        source, store, engine, tracker, notifier = make_components(listings, tmp_path)
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 4

        # Second poll: source still emits all four — none should fire again
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 4

    def test_empty_source_produces_no_notifications(self, tmp_path):
        source, store, engine, tracker, notifier = make_components([], tmp_path)
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 0

    def test_mix_of_seen_and_new_notifies_only_new(self, tmp_path):
        old = make_listing("https://ex.com/old", price=10.0)
        new = make_listing("https://ex.com/new", price=10.0)
        source, store, engine, tracker, notifier = make_components([old, new], tmp_path)

        # Mark old as seen before any poll
        store.mark_seen(old)

        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 1
        assert notifier.calls[0][0].url == "https://ex.com/new"

    def test_deduplication_is_url_based_not_title_based(self, tmp_path):
        """Two listings sharing a title but different URLs are both new."""
        a = make_listing("https://ex.com/1", title="Same Title")
        b = make_listing("https://ex.com/2", title="Same Title")
        source, store, engine, tracker, notifier = make_components([a, b], tmp_path)
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 2


# ---------------------------------------------------------------------------
# Rule matching
# ---------------------------------------------------------------------------

class TestRuleMatching:
    def test_listing_below_price_max_is_notified(self, tmp_path):
        listing = make_listing("https://ex.com/cheap", price=49.99)
        source, store, engine, tracker, notifier = make_components(
            [listing], tmp_path, price_max=50.0
        )
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 1

    def test_listing_above_price_max_is_not_notified(self, tmp_path):
        listing = make_listing("https://ex.com/expensive", price=100.0)
        source, store, engine, tracker, notifier = make_components(
            [listing], tmp_path, price_max=50.0
        )
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 0

    def test_listing_exactly_at_price_max_is_not_notified(self, tmp_path):
        # price > price_max is the guard — equal must pass (not exceed)
        listing = make_listing("https://ex.com/exact", price=50.0)
        source, store, engine, tracker, notifier = make_components(
            [listing], tmp_path, price_max=50.0
        )
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 1

    def test_keyword_match_notifies(self, tmp_path):
        listing = make_listing("https://ex.com/k", title="Red Bicycle")
        source, store, engine, tracker, notifier = make_components(
            [listing], tmp_path, keywords=["bicycle"]
        )
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 1

    def test_keyword_no_match_does_not_notify(self, tmp_path):
        listing = make_listing("https://ex.com/k", title="Green Scooter")
        source, store, engine, tracker, notifier = make_components(
            [listing], tmp_path, keywords=["bicycle"]
        )
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 0

    def test_keyword_match_is_case_insensitive(self, tmp_path):
        listing = make_listing("https://ex.com/k", title="ROAD BICYCLE XL")
        source, store, engine, tracker, notifier = make_components(
            [listing], tmp_path, keywords=["bicycle"]
        )
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 1

    def test_all_keywords_must_match(self, tmp_path):
        listing = make_listing("https://ex.com/k", title="Red Bicycle")
        source, store, engine, tracker, notifier = make_components(
            [listing], tmp_path, keywords=["red", "blue"]
        )
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 0

    def test_only_matching_listings_in_mixed_batch_notified(self, tmp_path):
        cheap = make_listing("https://ex.com/cheap", price=20.0)
        expensive = make_listing("https://ex.com/expensive", price=200.0)
        source, store, engine, tracker, notifier = make_components(
            [cheap, expensive], tmp_path, price_max=50.0
        )
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 1
        assert notifier.calls[0][0].url == "https://ex.com/cheap"

    def test_no_rules_set_all_new_listings_notified(self, tmp_path):
        """price_max=0 and no keywords means no filters; everything passes."""
        listings = [make_listing(f"https://ex.com/{i}", price=float(i * 10)) for i in range(5)]
        source, store, engine, tracker, notifier = make_components(listings, tmp_path)
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 5

    def test_percent_below_median_filters_overpriced_after_warmup(self, tmp_path):
        """After seeing prices [100, 200], median=150; 10% below = 135 threshold.
        A listing at 140 should be rejected."""
        candidate = make_listing("https://ex.com/candidate", price=140.0)
        source, store, engine, tracker, notifier = make_components(
            [], tmp_path, percent_below_median=10.0
        )

        # Manually warm up the tracker without notifying (different store)
        tracker.add(100.0)
        tracker.add(200.0)
        # median is now 150.0; threshold = 150 * 0.9 = 135

        source2 = InMemorySource([candidate])
        poll_once(source2, store, engine, tracker, notifier)
        # 140 > 135 → filtered out
        assert len(notifier.calls) == 0

    def test_percent_below_median_passes_sufficiently_cheap(self, tmp_path):
        candidate = make_listing("https://ex.com/bargain", price=100.0)
        source, store, engine, tracker, notifier = make_components(
            [], tmp_path, percent_below_median=10.0
        )
        tracker.add(200.0)
        tracker.add(200.0)
        # median = 200; threshold = 200 * 0.9 = 180; 100 < 180 → passes

        source2 = InMemorySource([candidate])
        poll_once(source2, store, engine, tracker, notifier)
        assert len(notifier.calls) == 1


# ---------------------------------------------------------------------------
# Median tracker updates
# ---------------------------------------------------------------------------

class TestMedianTrackerUpdates:
    def test_tracker_receives_price_for_every_listing(self, tmp_path):
        listings = [make_listing(f"https://ex.com/{i}", price=float(i * 10 + 10)) for i in range(5)]
        source, store, engine, tracker, notifier = make_components(listings, tmp_path)

        assert tracker.median() is None  # nothing added yet
        poll_once(source, store, engine, tracker, notifier)
        assert tracker.median() is not None

    def test_tracker_updated_even_for_already_seen_listings(self, tmp_path):
        listing = make_listing("https://ex.com/seen", price=100.0)
        source, store, engine, tracker, notifier = make_components([listing], tmp_path)

        # First poll: listing is new, tracker gets price, notifier fires
        poll_once(source, store, engine, tracker, notifier)
        median_after_first = tracker.median()
        assert median_after_first == 100.0

        # Second poll: listing is seen, but tracker should still add it
        poll_once(source, store, engine, tracker, notifier)
        # Two calls to tracker.add(100.0) — median stays 100 but total heap
        # size grows: both heaps together must hold 2 prices.
        assert tracker.median() == 100.0
        assert len(tracker._lo) + len(tracker._hi) == 2  # both polls added the price

    def test_tracker_updated_even_for_rule_filtered_listings(self, tmp_path):
        """Listings that don't match rules still add to the tracker."""
        expensive = make_listing("https://ex.com/exp", price=9999.0)
        source, store, engine, tracker, notifier = make_components(
            [expensive], tmp_path, price_max=50.0
        )
        poll_once(source, store, engine, tracker, notifier)
        assert len(notifier.calls) == 0           # filtered by price_max
        assert tracker.median() == 9999.0         # but tracker was updated

    def test_tracker_receives_prices_in_source_order(self, tmp_path):
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        listings = [make_listing(f"https://ex.com/{i}", price=p) for i, p in enumerate(prices)]
        source, store, engine, tracker, notifier = make_components(listings, tmp_path)
        poll_once(source, store, engine, tracker, notifier)
        # Median of [10,20,30,40,50] is 30
        assert tracker.median() == 30.0

    def test_empty_source_leaves_tracker_empty(self, tmp_path):
        source, store, engine, tracker, notifier = make_components([], tmp_path)
        poll_once(source, store, engine, tracker, notifier)
        assert tracker.median() is None


# ---------------------------------------------------------------------------
# ConsoleNotifier
# ---------------------------------------------------------------------------

class TestConsoleNotifier:
    def test_notify_prints_alert_text_to_stdout(self, capsys):
        notifier = ConsoleNotifier()
        listing = make_listing("https://ex.com/1", price=42.99, title="Blue Chair")
        alert = "DEAL: Blue Chair — $42.99  https://ex.com/1"
        notifier.notify(listing, alert)
        captured = capsys.readouterr()
        assert "Blue Chair" in captured.out
        assert "42.99" in captured.out
        assert "https://ex.com/1" in captured.out

    def test_notify_prints_exact_alert_text(self, capsys):
        notifier = ConsoleNotifier()
        listing = make_listing("https://ex.com/2", price=10.0, title="Test Item")
        alert = "DEAL: Test Item — $10.00  https://ex.com/2"
        notifier.notify(listing, alert)
        captured = capsys.readouterr()
        assert captured.out.strip() == alert

    def test_notify_writes_to_stdout_not_stderr(self, capsys):
        notifier = ConsoleNotifier()
        listing = make_listing("https://ex.com/3", price=5.0)
        notifier.notify(listing, "some alert")
        captured = capsys.readouterr()
        assert captured.err == ""
        assert "some alert" in captured.out

    def test_notify_each_call_produces_separate_line(self, capsys):
        notifier = ConsoleNotifier()
        listing1 = make_listing("https://ex.com/a", title="A")
        listing2 = make_listing("https://ex.com/b", title="B")
        notifier.notify(listing1, "alert A")
        notifier.notify(listing2, "alert B")
        captured = capsys.readouterr()
        lines = captured.out.splitlines()
        assert len(lines) == 2
        assert lines[0] == "alert A"
        assert lines[1] == "alert B"

    def test_poll_once_alert_format_contains_required_fields(self, tmp_path, capsys):
        """Round-trip: poll_once with ConsoleNotifier, verify printed format."""
        listing = make_listing("https://ex.com/deal", price=29.99, title="Fancy Gadget")
        source = InMemorySource([listing])
        store = ListingStore(tmp_path / "test.db")
        config = make_config()
        tracker = MedianTracker()
        engine = RulesEngine(config, tracker)
        notifier = ConsoleNotifier()

        poll_once(source, store, engine, tracker, notifier)

        captured = capsys.readouterr()
        assert "Fancy Gadget" in captured.out
        assert "29.99" in captured.out
        assert "https://ex.com/deal" in captured.out

    def test_poll_once_alert_price_formatted_to_two_decimals(self, tmp_path, capsys):
        listing = make_listing("https://ex.com/price", price=7.5, title="Item")
        source = InMemorySource([listing])
        store = ListingStore(tmp_path / "test.db")
        config = make_config()
        tracker = MedianTracker()
        engine = RulesEngine(config, tracker)
        notifier = ConsoleNotifier()

        poll_once(source, store, engine, tracker, notifier)

        captured = capsys.readouterr()
        # price 7.5 must render as "7.50", not "7.5"
        assert "7.50" in captured.out

    def test_seen_listing_produces_no_output(self, tmp_path, capsys):
        listing = make_listing("https://ex.com/seen", price=10.0, title="Old Item")
        store = ListingStore(tmp_path / "test.db")
        store.mark_seen(listing)

        source = InMemorySource([listing])
        config = make_config()
        tracker = MedianTracker()
        engine = RulesEngine(config, tracker)
        notifier = ConsoleNotifier()

        poll_once(source, store, engine, tracker, notifier)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_rule_filtered_listing_produces_no_output(self, tmp_path, capsys):
        listing = make_listing("https://ex.com/pricey", price=500.0, title="Pricey Thing")
        source = InMemorySource([listing])
        store = ListingStore(tmp_path / "test.db")
        config = make_config(price_max=100.0)
        tracker = MedianTracker()
        engine = RulesEngine(config, tracker)
        notifier = ConsoleNotifier()

        poll_once(source, store, engine, tracker, notifier)
        captured = capsys.readouterr()
        assert captured.out == ""
