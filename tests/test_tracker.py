"""deal_sniper.tracker.MedianTracker: per-query median, odd/even correctness, isolation."""
import pytest

from deal_sniper.tracker import MedianTracker


class TestEmptyTracker:
    def test_unknown_query_returns_none(self):
        t = MedianTracker()
        assert t.median("bikes") is None

    def test_empty_string_query_returns_none(self):
        t = MedianTracker()
        assert t.median("") is None

    def test_update_one_query_does_not_affect_another(self):
        t = MedianTracker()
        t.update("bikes", 100.0)
        assert t.median("sofas") is None


class TestSingleValue:
    def test_one_value_returns_that_value(self):
        t = MedianTracker()
        t.update("q", 42.0)
        assert t.median("q") == 42.0

    def test_one_zero(self):
        t = MedianTracker()
        t.update("q", 0.0)
        assert t.median("q") == 0.0

    def test_one_negative(self):
        t = MedianTracker()
        t.update("q", -5.0)
        assert t.median("q") == -5.0


class TestOddCount:
    def test_three_ascending(self):
        t = MedianTracker()
        for v in [10.0, 20.0, 30.0]:
            t.update("q", v)
        assert t.median("q") == 20.0

    def test_three_descending(self):
        t = MedianTracker()
        for v in [30.0, 20.0, 10.0]:
            t.update("q", v)
        assert t.median("q") == 20.0

    def test_three_out_of_order(self):
        t = MedianTracker()
        for v in [30.0, 10.0, 20.0]:
            t.update("q", v)
        assert t.median("q") == 20.0

    def test_five_values(self):
        t = MedianTracker()
        for v in [5.0, 1.0, 4.0, 3.0, 2.0]:
            t.update("q", v)
        assert t.median("q") == 3.0

    def test_seven_values(self):
        t = MedianTracker()
        for v in range(1, 8):
            t.update("q", float(v))
        assert t.median("q") == 4.0


class TestEvenCount:
    def test_two_values_average(self):
        t = MedianTracker()
        t.update("q", 10.0)
        t.update("q", 20.0)
        assert t.median("q") == 15.0

    def test_two_values_reverse_order(self):
        t = MedianTracker()
        t.update("q", 20.0)
        t.update("q", 10.0)
        assert t.median("q") == 15.0

    def test_two_equal_values(self):
        t = MedianTracker()
        t.update("q", 7.0)
        t.update("q", 7.0)
        assert t.median("q") == 7.0

    def test_four_values(self):
        t = MedianTracker()
        for v in [1.0, 2.0, 3.0, 4.0]:
            t.update("q", v)
        assert t.median("q") == 2.5

    def test_six_values(self):
        t = MedianTracker()
        for v in [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]:
            t.update("q", v)
        assert t.median("q") == 35.0

    def test_all_same_values_even(self):
        t = MedianTracker()
        for _ in range(4):
            t.update("q", 9.0)
        assert t.median("q") == 9.0


class TestQueryIsolation:
    def test_two_queries_independent(self):
        t = MedianTracker()
        t.update("bikes", 100.0)
        t.update("sofas", 500.0)
        assert t.median("bikes") == 100.0
        assert t.median("sofas") == 500.0

    def test_adding_to_one_query_leaves_other_unchanged(self):
        t = MedianTracker()
        t.update("q1", 10.0)
        t.update("q1", 20.0)
        t.update("q2", 999.0)
        assert t.median("q1") == 15.0
        assert t.median("q2") == 999.0

    def test_empty_string_query_is_a_valid_key(self):
        t = MedianTracker()
        t.update("", 55.0)
        assert t.median("") == 55.0
        assert t.median("other") is None

    def test_many_queries_all_isolated(self):
        t = MedianTracker()
        queries = [f"q{i}" for i in range(5)]
        for i, q in enumerate(queries):
            t.update(q, float((i + 1) * 10))
        for i, q in enumerate(queries):
            assert t.median(q) == float((i + 1) * 10)


class TestMedianEvolution:
    def test_median_updates_incrementally(self):
        t = MedianTracker()
        t.update("q", 10.0)
        assert t.median("q") == 10.0
        t.update("q", 30.0)
        assert t.median("q") == 20.0
        t.update("q", 20.0)
        # sorted: [10, 20, 30] → median = 20
        assert t.median("q") == 20.0

    def test_duplicate_prices_handled_correctly(self):
        t = MedianTracker()
        for _ in range(3):
            t.update("q", 50.0)
        assert t.median("q") == 50.0

    def test_all_same_values_odd(self):
        t = MedianTracker()
        for _ in range(5):
            t.update("q", 7.0)
        assert t.median("q") == 7.0

    def test_large_even_dataset(self):
        t = MedianTracker()
        for v in range(1, 1001):
            t.update("q", float(v))
        # avg of 500 and 501
        assert t.median("q") == 500.5

    def test_large_odd_dataset(self):
        t = MedianTracker()
        for v in range(1, 1002):
            t.update("q", float(v))
        assert t.median("q") == 501.0
