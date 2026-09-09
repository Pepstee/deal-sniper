"""deal_sniper.loop.run_loop: stub source, capture notifier, dedup, rule filtering."""

from deal_sniper.config import Config
from deal_sniper.loop import run_loop
from deal_sniper.models import Listing
from deal_sniper.rules import RulesEngine
from deal_sniper.store import SQLiteStore
from deal_sniper.tracker import MedianTracker


def make_config(
    price_max=0.0,
    keywords=None,
    below_median_pct=0.0,
    poll_interval_s=0,
):
    return Config(
        price_max=price_max,
        keywords=keywords or [],
        below_median_pct=below_median_pct,
        poll_interval_s=poll_interval_s,
        db_path=":memory:",
    )


def make_listing(url, title="Widget", price=50.0, query=""):
    return Listing(title=title, price=price, url=url, source="test", query=query)


class StubSource:
    """Returns a fixed list of listings on every fetch; never touches the network."""

    def __init__(self, listings):
        self._listings = listings
        self.fetch_calls = 0

    def fetch(self, query):
        self.fetch_calls += 1
        return list(self._listings)


class CaptureNotifier:
    """Records every listing passed to alert()."""

    def __init__(self):
        self.alerted = []

    def alert(self, listing):
        self.alerted.append(listing)


def make_components(listings, *, price_max=0.0, keywords=None, below_median_pct=0.0):
    config = make_config(price_max=price_max, keywords=keywords, below_median_pct=below_median_pct)
    store = SQLiteStore(":memory:")
    tracker = MedianTracker()
    rules = RulesEngine(config, tracker)
    notifier = CaptureNotifier()
    source = StubSource(listings)
    return source, config, store, tracker, rules, notifier


# ---------------------------------------------------------------------------
# Basic iteration behaviour
# ---------------------------------------------------------------------------

class TestRunLoopBasics:
    def test_single_new_listing_is_alerted(self):
        listing = make_listing("http://ex.com/1")
        source, config, store, tracker, rules, notifier = make_components([listing])
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert len(notifier.alerted) == 1
        assert notifier.alerted[0].url == "http://ex.com/1"

    def test_zero_iterations_produces_no_alerts(self):
        listing = make_listing("http://ex.com/1")
        source, config, store, tracker, rules, notifier = make_components([listing])
        run_loop(source, config, store, tracker, rules, notifier, iterations=0)
        assert notifier.alerted == []

    def test_empty_source_no_alerts(self):
        source, config, store, tracker, rules, notifier = make_components([])
        run_loop(source, config, store, tracker, rules, notifier, iterations=3)
        assert notifier.alerted == []

    def test_multiple_listings_in_one_iteration_all_alerted(self):
        listings = [make_listing(f"http://ex.com/{i}") for i in range(4)]
        source, config, store, tracker, rules, notifier = make_components(listings)
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert len(notifier.alerted) == 4

    def test_source_fetched_once_per_iteration(self):
        source, config, store, tracker, rules, notifier = make_components([])
        run_loop(source, config, store, tracker, rules, notifier, iterations=5)
        assert source.fetch_calls == 5

    def test_notifier_as_single_object_not_list(self):
        listing = make_listing("http://ex.com/1")
        source, config, store, tracker, rules, _ = make_components([listing])
        notifier = CaptureNotifier()
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert len(notifier.alerted) == 1


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_second_iteration_suppresses_same_listing(self):
        listing = make_listing("http://ex.com/repeat")
        source, config, store, tracker, rules, notifier = make_components([listing])
        run_loop(source, config, store, tracker, rules, notifier, iterations=5)
        assert len(notifier.alerted) == 1

    def test_many_iterations_same_listing_alerted_once(self):
        listing = make_listing("http://ex.com/only-once")
        source, config, store, tracker, rules, notifier = make_components([listing])
        run_loop(source, config, store, tracker, rules, notifier, iterations=10)
        assert len(notifier.alerted) == 1

    def test_different_urls_each_alerted_once_across_iterations(self):
        listings = [make_listing(f"http://ex.com/{i}") for i in range(3)]
        source, config, store, tracker, rules, notifier = make_components(listings)
        run_loop(source, config, store, tracker, rules, notifier, iterations=4)
        assert len(notifier.alerted) == 3

    def test_dedup_is_url_based_same_title_different_url(self):
        a = make_listing("http://ex.com/1", title="Same Title")
        b = make_listing("http://ex.com/2", title="Same Title")
        source, config, store, tracker, rules, notifier = make_components([a, b])
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert len(notifier.alerted) == 2

    def test_pre_seen_listing_not_alerted(self):
        listing = make_listing("http://ex.com/old")
        _, config, store, tracker, rules, notifier = make_components([listing])
        store.mark_seen(listing)
        source = StubSource([listing])
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert notifier.alerted == []

    def test_mix_of_seen_and_new_only_new_alerted(self):
        seen = make_listing("http://ex.com/seen")
        new = make_listing("http://ex.com/new")
        _, config, store, tracker, rules, notifier = make_components([seen, new])
        store.mark_seen(seen)
        source = StubSource([seen, new])
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert len(notifier.alerted) == 1
        assert notifier.alerted[0].url == "http://ex.com/new"


# ---------------------------------------------------------------------------
# Rule filtering
# ---------------------------------------------------------------------------

class TestRuleFiltering:
    def test_price_max_blocks_expensive_listing(self):
        expensive = make_listing("http://ex.com/1", price=999.0)
        source, config, store, tracker, rules, notifier = make_components(
            [expensive], price_max=100.0
        )
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert notifier.alerted == []

    def test_price_max_passes_cheap_listing(self):
        cheap = make_listing("http://ex.com/1", price=49.0)
        source, config, store, tracker, rules, notifier = make_components(
            [cheap], price_max=100.0
        )
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert len(notifier.alerted) == 1

    def test_keyword_filter_blocks_non_matching_title(self):
        listing = make_listing("http://ex.com/1", title="Green Scooter")
        source, config, store, tracker, rules, notifier = make_components(
            [listing], keywords=["bicycle"]
        )
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert notifier.alerted == []

    def test_keyword_filter_passes_matching_title(self):
        listing = make_listing("http://ex.com/1", title="Red Bicycle XL")
        source, config, store, tracker, rules, notifier = make_components(
            [listing], keywords=["bicycle"]
        )
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert len(notifier.alerted) == 1

    def test_keyword_filter_is_case_insensitive(self):
        listing = make_listing("http://ex.com/1", title="ROAD BICYCLE XL")
        source, config, store, tracker, rules, notifier = make_components(
            [listing], keywords=["bicycle"]
        )
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert len(notifier.alerted) == 1

    def test_all_keywords_must_match(self):
        listing = make_listing("http://ex.com/1", title="Red Bicycle")
        source, config, store, tracker, rules, notifier = make_components(
            [listing], keywords=["red", "blue"]
        )
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert notifier.alerted == []

    def test_percent_below_median_blocks_listing_not_far_enough_below(self):
        # run_loop adds the listing's own price to tracker before checking rules.
        # Pre-seed with [100, 100] so after adding price=95 the sorted list is [95, 100, 100],
        # median=100, threshold=80; price 95 > 80 → blocked.
        listing = make_listing("http://ex.com/1", price=95.0, query="q")
        _, config, store, tracker, rules, notifier = make_components(
            [listing], below_median_pct=20.0
        )
        tracker.update("q", 100.0)
        tracker.update("q", 100.0)
        source = StubSource([listing])
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert notifier.alerted == []

    def test_percent_below_median_passes_listing_far_enough_below(self):
        # run_loop updates the tracker with the listing's own price before calling matches,
        # so the median shifts. Pre-seed with two high values so the median stays high
        # after the cheap listing is added: [70, 200, 200] → median=200, threshold=160.
        listing = make_listing("http://ex.com/1", price=70.0, query="q")
        _, config, store, tracker, rules, notifier = make_components(
            [listing], below_median_pct=20.0
        )
        tracker.update("q", 200.0)
        tracker.update("q", 200.0)
        source = StubSource([listing])
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert len(notifier.alerted) == 1

    def test_no_rules_all_new_listings_alerted(self):
        listings = [make_listing(f"http://ex.com/{i}", price=float(i * 100)) for i in range(5)]
        source, config, store, tracker, rules, notifier = make_components(listings)
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert len(notifier.alerted) == 5

    def test_filtered_listing_still_entered_into_dedup_store(self):
        expensive = make_listing("http://ex.com/filtered", price=999.0)
        source, config, store, tracker, rules, notifier = make_components(
            [expensive], price_max=100.0
        )
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert not store.is_new(expensive)


# ---------------------------------------------------------------------------
# Multiple notifiers
# ---------------------------------------------------------------------------

class TestMultipleNotifiers:
    def test_list_of_notifiers_all_receive_alert(self):
        listing = make_listing("http://ex.com/1")
        source, config, store, tracker, rules, _ = make_components([listing])
        n1, n2 = CaptureNotifier(), CaptureNotifier()
        run_loop(source, config, store, tracker, rules, [n1, n2], iterations=1)
        assert len(n1.alerted) == 1
        assert len(n2.alerted) == 1

    def test_three_notifiers_all_receive_alert(self):
        listing = make_listing("http://ex.com/1")
        source, config, store, tracker, rules, _ = make_components([listing])
        notifiers = [CaptureNotifier() for _ in range(3)]
        run_loop(source, config, store, tracker, rules, notifiers, iterations=1)
        for n in notifiers:
            assert len(n.alerted) == 1


# ---------------------------------------------------------------------------
# Median tracker updates
# ---------------------------------------------------------------------------

class TestTrackerUpdates:
    def test_tracker_receives_price_for_every_listing(self):
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        listings = [make_listing(f"http://ex.com/{i}", price=p) for i, p in enumerate(prices)]
        source, config, store, tracker, rules, notifier = make_components(listings)
        assert tracker.median("") is None
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        # Median of [10,20,30,40,50] is 30
        assert tracker.median("") == 30.0

    def test_tracker_updated_even_for_already_seen_listings(self):
        listing = make_listing("http://ex.com/seen", price=100.0)
        source, config, store, tracker, rules, notifier = make_components([listing])
        # First iteration: new, tracker gets the price, notifier fires.
        # Second iteration: seen, but the tracker must still record the price.
        run_loop(source, config, store, tracker, rules, notifier, iterations=2)
        assert len(notifier.alerted) == 1
        assert tracker.median("") == 100.0
        assert len(tracker._data[""]) == 2  # both iterations added the price

    def test_tracker_updated_even_for_rule_filtered_listings(self):
        expensive = make_listing("http://ex.com/exp", price=9999.0)
        source, config, store, tracker, rules, notifier = make_components(
            [expensive], price_max=50.0
        )
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert notifier.alerted == []          # filtered by price_max
        assert tracker.median("") == 9999.0    # but tracker was updated

    def test_tracker_keyed_by_listing_query(self):
        a = make_listing("http://ex.com/a", price=10.0, query="bikes")
        b = make_listing("http://ex.com/b", price=500.0, query="sofas")
        source, config, store, tracker, rules, notifier = make_components([a, b])
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert tracker.median("bikes") == 10.0
        assert tracker.median("sofas") == 500.0

    def test_empty_source_leaves_tracker_empty(self):
        source, config, store, tracker, rules, notifier = make_components([])
        run_loop(source, config, store, tracker, rules, notifier, iterations=1)
        assert tracker.median("") is None


def test_batch_median_is_independent_of_listing_order():
    results = []
    for prices in ([10, 100, 100], [100, 100, 10]):
        source, cfg, store, tracker, rules, notifier = make_components(
            [make_listing(str(i), price=p) for i, p in enumerate(prices)], below_median_pct=50)
        cfg.median_mode = "batch"
        assert run_loop(source, cfg, store, tracker, rules, notifier, iterations=1) == 1
        results.append([item.price for item in notifier.alerted])
        store.close()
    assert results == [[10], [10]]


def test_optional_observation_deduplication_handles_batch_and_repoll():
    item = make_listing("same", price=10)
    source, cfg, store, tracker, rules, notifier = make_components([item, item])
    cfg.median_mode = "batch"
    cfg.deduplicate_observations = True
    assert run_loop(source, cfg, store, tracker, rules, notifier, iterations=3) == 1
    assert tracker._data[""] == [10]
    store.close()


def test_any_keyword_mode_recovers_alternative_matching():
    source, cfg, store, tracker, rules, notifier = make_components(
        [make_listing("one", title="red bicycle")], keywords=["bicycle", "scooter"])
    cfg.keyword_mode = "any"
    assert run_loop(source, cfg, store, tracker, rules, notifier, iterations=1) == 1
    store.close()
