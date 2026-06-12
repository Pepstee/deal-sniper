"""Listing model: field validation, defaults, equality — exercises deal_sniper.models directly."""
import pytest

from deal_sniper.models import Listing


class TestRequiredFields:
    def test_title_stored(self):
        listing = Listing(title="Vintage Sofa", price=149.99, url="http://ex.com/1", source="test")
        assert listing.title == "Vintage Sofa"

    def test_price_stored(self):
        listing = Listing(title="X", price=42.0, url="u", source="s")
        assert listing.price == 42.0

    def test_url_stored(self):
        listing = Listing(title="X", price=1.0, url="http://ex.com/99", source="s")
        assert listing.url == "http://ex.com/99"

    def test_source_stored(self):
        listing = Listing(title="X", price=1.0, url="u", source="mock_json")
        assert listing.source == "mock_json"

    def test_price_is_float(self):
        listing = Listing(title="X", price=5.0, url="u", source="s")
        assert isinstance(listing.price, float)

    def test_price_zero(self):
        listing = Listing(title="Free", price=0.0, url="u", source="s")
        assert listing.price == 0.0

    def test_price_negative_stored_as_given(self):
        listing = Listing(title="X", price=-10.0, url="u", source="s")
        assert listing.price == -10.0

    def test_title_empty_string(self):
        listing = Listing(title="", price=1.0, url="u", source="s")
        assert listing.title == ""

    def test_url_empty_string(self):
        listing = Listing(title="X", price=1.0, url="", source="s")
        assert listing.url == ""


class TestDefaults:
    def test_query_defaults_to_empty_string(self):
        listing = Listing(title="X", price=1.0, url="u", source="s")
        assert listing.query == ""

    def test_extra_defaults_to_empty_dict(self):
        listing = Listing(title="X", price=1.0, url="u", source="s")
        assert listing.extra == {}

    def test_extra_is_mutable_dict(self):
        listing = Listing(title="X", price=1.0, url="u", source="s")
        listing.extra["k"] = "v"
        assert listing.extra["k"] == "v"

    def test_extra_default_not_shared_between_instances(self):
        a = Listing(title="A", price=1.0, url="u1", source="s")
        b = Listing(title="B", price=2.0, url="u2", source="s")
        a.extra["key"] = "val"
        assert "key" not in b.extra

    def test_query_can_be_set(self):
        listing = Listing(title="X", price=1.0, url="u", source="s", query="bikes")
        assert listing.query == "bikes"

    def test_extra_can_be_set_at_construction(self):
        listing = Listing(title="X", price=1.0, url="u", source="s", extra={"img": "http://img", "views": 7})
        assert listing.extra["img"] == "http://img"
        assert listing.extra["views"] == 7


class TestEquality:
    def test_equal_when_all_fields_same(self):
        a = Listing(title="T", price=10.0, url="u", source="s")
        b = Listing(title="T", price=10.0, url="u", source="s")
        assert a == b

    def test_not_equal_different_title(self):
        a = Listing(title="A", price=10.0, url="u", source="s")
        b = Listing(title="B", price=10.0, url="u", source="s")
        assert a != b

    def test_not_equal_different_price(self):
        a = Listing(title="T", price=10.0, url="u", source="s")
        b = Listing(title="T", price=20.0, url="u", source="s")
        assert a != b

    def test_not_equal_different_url(self):
        a = Listing(title="T", price=10.0, url="u1", source="s")
        b = Listing(title="T", price=10.0, url="u2", source="s")
        assert a != b

    def test_not_equal_different_source(self):
        a = Listing(title="T", price=10.0, url="u", source="s1")
        b = Listing(title="T", price=10.0, url="u", source="s2")
        assert a != b

    def test_not_equal_different_query(self):
        a = Listing(title="T", price=10.0, url="u", source="s", query="bikes")
        b = Listing(title="T", price=10.0, url="u", source="s", query="sofas")
        assert a != b

    def test_not_equal_different_extra(self):
        a = Listing(title="T", price=10.0, url="u", source="s", extra={"x": 1})
        b = Listing(title="T", price=10.0, url="u", source="s", extra={"x": 2})
        assert a != b

    def test_not_equal_to_none(self):
        a = Listing(title="T", price=10.0, url="u", source="s")
        assert a != None  # noqa: E711

    def test_not_equal_to_string(self):
        a = Listing(title="T", price=10.0, url="u", source="s")
        assert a != "T"
