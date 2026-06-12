"""RulesEngine: price threshold, keyword filter, percent-below-median, combined."""
import pytest

from deal_sniper.config import Config
from deal_sniper.listing import Listing
from deal_sniper.median import MedianTracker
from deal_sniper.rules import RulesEngine


def make_config(
    price_max: float = 0.0,
    keywords: list[str] | None = None,
    percent_below_median: float = 0.0,
) -> Config:
    return Config(
        price_max=price_max,
        keywords=keywords or [],
        below_median_pct=percent_below_median,
        poll_interval_s=60,
        db_path=":memory:",
    )


def make_listing(title: str = "Widget", price: float = 50.0, url: str = "u") -> Listing:
    return Listing(title=title, price=price, url=url, source="test")


def engine(config: Config, prices: list[float] | None = None) -> RulesEngine:
    tracker = MedianTracker()
    for p in (prices or []):
        tracker.add(p)
    return RulesEngine(config, tracker)


# ---------------------------------------------------------------------------
# Price threshold
# ---------------------------------------------------------------------------

class TestPriceThreshold:
    def test_price_below_max_passes(self):
        e = engine(make_config(price_max=100.0))
        assert e.matches(make_listing(price=99.99)) is True

    def test_price_equal_to_max_passes(self):
        e = engine(make_config(price_max=100.0))
        assert e.matches(make_listing(price=100.0)) is True

    def test_price_above_max_fails(self):
        e = engine(make_config(price_max=100.0))
        assert e.matches(make_listing(price=100.01)) is False

    def test_no_price_max_skips_check(self):
        # price_max=0.0 is falsy; even a very high price should pass
        e = engine(make_config(price_max=0.0))
        assert e.matches(make_listing(price=999999.0)) is True

    def test_price_zero_with_max_set(self):
        e = engine(make_config(price_max=50.0))
        assert e.matches(make_listing(price=0.0)) is True


# ---------------------------------------------------------------------------
# Keyword filter
# ---------------------------------------------------------------------------

class TestKeywordFilter:
    def test_all_keywords_present_passes(self):
        e = engine(make_config(keywords=["bike", "mountain"]))
        assert e.matches(make_listing(title="Trek Mountain Bike 2021")) is True

    def test_keyword_check_is_case_insensitive(self):
        e = engine(make_config(keywords=["BIKE"]))
        assert e.matches(make_listing(title="road bike")) is True

    def test_partial_keyword_match_fails(self):
        e = engine(make_config(keywords=["bike", "carbon"]))
        assert e.matches(make_listing(title="Trek Mountain Bike 2021")) is False

    def test_no_keyword_match_fails(self):
        e = engine(make_config(keywords=["sofa"]))
        assert e.matches(make_listing(title="Trek Mountain Bike 2021")) is False

    def test_empty_keywords_skips_check(self):
        e = engine(make_config(keywords=[]))
        assert e.matches(make_listing(title="Anything at all")) is True

    def test_single_keyword_passes(self):
        e = engine(make_config(keywords=["desk"]))
        assert e.matches(make_listing(title="Standing Desk Lamp")) is True

    def test_keyword_substring_within_word_passes(self):
        # "bike" is in "biker" — rule uses `in`, substring match
        e = engine(make_config(keywords=["bike"]))
        assert e.matches(make_listing(title="biker jacket")) is True


# ---------------------------------------------------------------------------
# Percent-below-median
# ---------------------------------------------------------------------------

class TestPercentBelowMedian:
    def test_price_below_threshold_passes(self):
        # median=100, 20% below -> threshold=80; price=70 passes
        e = engine(make_config(percent_below_median=20.0), prices=[100.0])
        assert e.matches(make_listing(price=70.0)) is True

    def test_price_at_threshold_passes(self):
        # rule: listing.price > threshold fails; price==threshold uses >, so it passes
        # median=100, 20% below -> threshold=80; price=80 exactly is NOT > 80
        e = engine(make_config(percent_below_median=20.0), prices=[100.0])
        assert e.matches(make_listing(price=80.0)) is True

    def test_price_one_cent_above_threshold_fails(self):
        # price=80.01 > threshold=80 -> fails
        e = engine(make_config(percent_below_median=20.0), prices=[100.0])
        assert e.matches(make_listing(price=80.01)) is False

    def test_price_above_threshold_fails(self):
        e = engine(make_config(percent_below_median=20.0), prices=[100.0])
        assert e.matches(make_listing(price=95.0)) is False

    def test_no_median_yet_skips_check(self):
        # tracker is empty -> median() is None -> rule skips
        e = engine(make_config(percent_below_median=20.0), prices=[])
        assert e.matches(make_listing(price=9999.0)) is True

    def test_zero_percent_skips_check(self):
        # percent_below_median=0.0 is falsy; rule never fires
        e = engine(make_config(percent_below_median=0.0), prices=[100.0])
        assert e.matches(make_listing(price=9999.0)) is True

    def test_threshold_computed_from_current_median(self):
        # median of [10, 20, 30] = 20; 50% below -> threshold=10; price=9 passes
        e = engine(make_config(percent_below_median=50.0), prices=[10.0, 20.0, 30.0])
        assert e.matches(make_listing(price=9.0)) is True
        assert e.matches(make_listing(price=11.0)) is False


# ---------------------------------------------------------------------------
# Combined multi-rule
# ---------------------------------------------------------------------------

class TestCombinedRules:
    def _engine(self):
        return engine(
            make_config(
                price_max=200.0,
                keywords=["bike"],
                percent_below_median=10.0,
            ),
            prices=[100.0],  # median=100, threshold=90
        )

    def test_all_rules_pass(self):
        e = self._engine()
        assert e.matches(make_listing(title="Road Bike", price=85.0)) is True

    def test_fails_price_max_despite_others_passing(self):
        e = self._engine()
        assert e.matches(make_listing(title="Road Bike", price=201.0)) is False

    def test_fails_keyword_despite_others_passing(self):
        e = self._engine()
        assert e.matches(make_listing(title="Road Sofa", price=85.0)) is False

    def test_fails_percent_below_median_despite_others_passing(self):
        e = self._engine()
        # price=95 > threshold=90 but <= 200 and keyword matches
        assert e.matches(make_listing(title="Road Bike", price=95.0)) is False

    def test_all_rules_fail_simultaneously(self):
        e = self._engine()
        assert e.matches(make_listing(title="Old Sofa", price=999.0)) is False

    def test_price_max_checked_before_keyword(self):
        # Verify short-circuit: if price_max fails there's no keyword check needed
        e = self._engine()
        assert e.matches(make_listing(title="Wrong Title", price=500.0)) is False
