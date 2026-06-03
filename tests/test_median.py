"""MedianTracker: running median using two heaps."""
import pytest

from deal_sniper.median import MedianTracker


class TestEmpty:
    def test_empty_returns_none(self):
        t = MedianTracker()
        assert t.median() is None


class TestSingleValue:
    def test_one_value_returns_that_value(self):
        t = MedianTracker()
        t.add(42.0)
        assert t.median() == 42.0

    def test_one_zero(self):
        t = MedianTracker()
        t.add(0.0)
        assert t.median() == 0.0

    def test_one_negative(self):
        t = MedianTracker()
        t.add(-5.0)
        assert t.median() == -5.0


class TestOddCount:
    def test_three_sorted_asc(self):
        t = MedianTracker()
        for v in [1.0, 2.0, 3.0]:
            t.add(v)
        assert t.median() == 2.0

    def test_three_sorted_desc(self):
        t = MedianTracker()
        for v in [3.0, 2.0, 1.0]:
            t.add(v)
        assert t.median() == 2.0

    def test_three_random_order(self):
        t = MedianTracker()
        for v in [3.0, 1.0, 2.0]:
            t.add(v)
        assert t.median() == 2.0

    def test_five_values(self):
        t = MedianTracker()
        for v in [5.0, 1.0, 3.0, 4.0, 2.0]:
            t.add(v)
        assert t.median() == 3.0

    def test_seven_values(self):
        t = MedianTracker()
        for v in range(1, 8):
            t.add(float(v))
        assert t.median() == 4.0


class TestEvenCount:
    def test_two_values_average(self):
        t = MedianTracker()
        t.add(1.0)
        t.add(3.0)
        assert t.median() == 2.0

    def test_two_equal_values(self):
        t = MedianTracker()
        t.add(5.0)
        t.add(5.0)
        assert t.median() == 5.0

    def test_four_values(self):
        t = MedianTracker()
        for v in [1.0, 2.0, 3.0, 4.0]:
            t.add(v)
        assert t.median() == 2.5

    def test_six_values(self):
        t = MedianTracker()
        for v in [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]:
            t.add(v)
        assert t.median() == 35.0

    def test_two_values_reverse_insert_order(self):
        t = MedianTracker()
        t.add(10.0)
        t.add(2.0)
        assert t.median() == 6.0


class TestMonotonicInserts:
    def test_all_same_values_odd(self):
        t = MedianTracker()
        for _ in range(5):
            t.add(7.0)
        assert t.median() == 7.0

    def test_all_same_values_even(self):
        t = MedianTracker()
        for _ in range(6):
            t.add(7.0)
        assert t.median() == 7.0

    def test_increasing_sequence(self):
        t = MedianTracker()
        for v in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]:
            t.add(v)
        assert t.median() == 4.0

    def test_decreasing_sequence(self):
        t = MedianTracker()
        for v in [7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0]:
            t.add(v)
        assert t.median() == 4.0


class TestNegativeAndMixedValues:
    def test_all_negative_odd(self):
        t = MedianTracker()
        for v in [-3.0, -1.0, -2.0]:
            t.add(v)
        assert t.median() == -2.0

    def test_mixed_positive_negative_odd(self):
        t = MedianTracker()
        for v in [-1.0, 0.0, 1.0]:
            t.add(v)
        assert t.median() == 0.0

    def test_mixed_positive_negative_even(self):
        t = MedianTracker()
        for v in [-2.0, -1.0, 1.0, 2.0]:
            t.add(v)
        assert t.median() == 0.0


class TestMedianEvolvesCorrectly:
    def test_median_updates_as_values_added(self):
        t = MedianTracker()
        t.add(10.0)
        assert t.median() == 10.0
        t.add(20.0)
        assert t.median() == 15.0
        t.add(30.0)
        assert t.median() == 20.0
        t.add(40.0)
        assert t.median() == 25.0

    def test_large_dataset(self):
        t = MedianTracker()
        for v in range(1, 1001):
            t.add(float(v))
        # 1000 values (even): median = avg(500, 501) = 500.5
        assert t.median() == 500.5

    def test_large_dataset_odd(self):
        t = MedianTracker()
        for v in range(1, 1002):
            t.add(float(v))
        # 1001 values (odd): median = 501.0
        assert t.median() == 501.0
