"""MockHtmlSource and MockJsonSource must parse fixture files; no network permitted."""
import json
import socket
from pathlib import Path

import pytest

from deal_sniper.listing import Listing
from deal_sniper.sources.mock_html import MockHtmlSource
from deal_sniper.sources.mock_json import MockJsonSource

FIXTURES = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Helper: block any real socket from being opened during these tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Raise if anything tries to open a real TCP/UDP socket."""
    _real_init = socket.socket.__init__

    def _blocked(self, *args, **kwargs):
        raise RuntimeError("Network access is forbidden in source tests")

    monkeypatch.setattr(socket.socket, "__init__", _blocked)
    yield


# ---------------------------------------------------------------------------
# MockHtmlSource
# ---------------------------------------------------------------------------

class TestMockHtmlSource:
    def test_returns_at_least_four_listings(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        listings = source.fetch("anything")
        assert len(listings) >= 4

    def test_all_items_are_listing_instances(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        for item in source.fetch("q"):
            assert isinstance(item, Listing)

    def test_title_is_str(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        for item in source.fetch("q"):
            assert isinstance(item.title, str)
            assert item.title  # non-empty

    def test_price_is_float(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        for item in source.fetch("q"):
            assert isinstance(item.price, float)

    def test_url_is_str(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        for item in source.fetch("q"):
            assert isinstance(item.url, str)

    def test_source_field_is_mock_html(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        for item in source.fetch("q"):
            assert item.source == "mock_html"

    def test_known_prices_present(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        prices = {item.price for item in source.fetch("q")}
        assert 149.99 in prices
        assert 49.00 in prices
        assert 299.50 in prices
        assert 25.00 in prices

    def test_known_titles_present(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        titles = {item.title for item in source.fetch("q")}
        assert "Vintage Leather Sofa" in titles
        assert "Standing Desk Lamp" in titles

    def test_known_urls_present(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        urls = {item.url for item in source.fetch("q")}
        assert "https://example.com/item/1" in urls

    def test_ignores_non_listing_li_elements(self, tmp_path):
        html = (
            "<html><body><ul>"
            '<li class="other" data-url="http://x.com/0" data-price="1.0">'
            '<span class="title">Noise</span></li>'
            '<li class="listing" data-url="http://x.com/1" data-price="10.0">'
            '<span class="title">Signal</span></li>'
            "</ul></body></html>"
        )
        f = tmp_path / "test.html"
        f.write_text(html)
        source = MockHtmlSource(f)
        listings = source.fetch("q")
        assert len(listings) == 1
        assert listings[0].title == "Signal"

    def test_listing_without_title_span_gets_empty_title(self, tmp_path):
        html = (
            "<html><body><ul>"
            '<li class="listing" data-url="http://x.com/1" data-price="50.0">'
            "</li>"
            "</ul></body></html>"
        )
        f = tmp_path / "test.html"
        f.write_text(html)
        source = MockHtmlSource(f)
        listings = source.fetch("q")
        assert len(listings) == 1
        assert listings[0].price == 50.0

    def test_missing_price_defaults_to_zero(self, tmp_path):
        html = (
            "<html><body><ul>"
            '<li class="listing" data-url="http://x.com/1">'
            '<span class="title">No Price</span></li>'
            "</ul></body></html>"
        )
        f = tmp_path / "test.html"
        f.write_text(html)
        source = MockHtmlSource(f)
        listings = source.fetch("q")
        assert listings[0].price == 0.0

    def test_query_arg_ignored(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        result_a = source.fetch("bikes")
        result_b = source.fetch("sofas")
        assert [l.url for l in result_a] == [l.url for l in result_b]


# ---------------------------------------------------------------------------
# MockJsonSource
# ---------------------------------------------------------------------------

class TestMockJsonSource:
    def test_returns_at_least_four_listings(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        listings = source.fetch("anything")
        assert len(listings) >= 4

    def test_all_items_are_listing_instances(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        for item in source.fetch("q"):
            assert isinstance(item, Listing)

    def test_title_is_str(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        for item in source.fetch("q"):
            assert isinstance(item.title, str)

    def test_price_is_float(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        for item in source.fetch("q"):
            assert isinstance(item.price, float)

    def test_url_is_str(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        for item in source.fetch("q"):
            assert isinstance(item.url, str)

    def test_source_field_is_mock_json(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        for item in source.fetch("q"):
            assert item.source == "mock_json"

    def test_known_prices_present(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        prices = {item.price for item in source.fetch("q")}
        assert 149.99 in prices
        assert 49.00 in prices
        assert 299.50 in prices
        assert 25.00 in prices

    def test_known_titles_present(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        titles = {item.title for item in source.fetch("q")}
        assert "Trek Mountain Bike 2021" in titles
        assert "Cast Iron Skillet 12in" in titles

    def test_price_coerced_to_float_from_integer_json(self, tmp_path):
        data = [{"title": "Item", "price": 100, "url": "http://x.com/1"}]
        f = tmp_path / "int_price.json"
        f.write_text(json.dumps(data))
        source = MockJsonSource(f)
        listings = source.fetch("q")
        assert isinstance(listings[0].price, float)
        assert listings[0].price == 100.0

    def test_query_arg_ignored(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        result_a = source.fetch("bikes")
        result_b = source.fetch("lamps")
        assert [l.url for l in result_a] == [l.url for l in result_b]

    def test_empty_json_array_returns_empty_list(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("[]")
        source = MockJsonSource(f)
        assert source.fetch("q") == []
