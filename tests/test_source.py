"""FixtureSource: parses HTML and JSON fixture files into Listing lists; no live HTTP."""
import json
import socket
from pathlib import Path

import pytest

from deal_sniper.models import Listing
from deal_sniper.sources.mock_html import MockHtmlSource
from deal_sniper.sources.mock_json import MockJsonSource

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Block any real socket creation so the tests provably never touch the network."""
    def _blocked(self, *args, **kwargs):
        raise RuntimeError("Live network access is forbidden in source tests")

    monkeypatch.setattr(socket.socket, "__init__", _blocked)
    yield


# ---------------------------------------------------------------------------
# JSON fixture source
# ---------------------------------------------------------------------------

class TestMockJsonSource:
    def test_returns_list(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        result = source.fetch("")
        assert isinstance(result, list)

    def test_all_elements_are_listing(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        for item in source.fetch(""):
            assert isinstance(item, Listing)

    def test_returns_four_items(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        assert len(source.fetch("")) == 4

    def test_title_is_nonempty_string(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        for item in source.fetch(""):
            assert isinstance(item.title, str)
            assert item.title

    def test_price_is_float(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        for item in source.fetch(""):
            assert isinstance(item.price, float)

    def test_url_is_string(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        for item in source.fetch(""):
            assert isinstance(item.url, str)

    def test_source_field_is_mock_json(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        for item in source.fetch(""):
            assert item.source == "mock_json"

    def test_known_titles_present(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        titles = {l.title for l in source.fetch("")}
        assert "Vintage Leather Sofa" in titles
        assert "Trek Mountain Bike 2021" in titles

    def test_known_prices_present(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        prices = {l.price for l in source.fetch("")}
        assert 149.99 in prices
        assert 25.00 in prices

    def test_known_urls_present(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        urls = {l.url for l in source.fetch("")}
        assert "https://example.com/item/1" in urls

    def test_query_arg_has_no_effect(self):
        source = MockJsonSource(FIXTURES / "sample.json")
        a = [l.url for l in source.fetch("bikes")]
        b = [l.url for l in source.fetch("sofas")]
        assert a == b

    def test_empty_json_array_returns_empty_list(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("[]")
        source = MockJsonSource(f)
        assert source.fetch("") == []

    def test_integer_price_coerced_to_float(self, tmp_path):
        data = [{"title": "Item", "price": 100, "url": "http://x.com/1"}]
        f = tmp_path / "int_price.json"
        f.write_text(json.dumps(data))
        source = MockJsonSource(f)
        listings = source.fetch("")
        assert isinstance(listings[0].price, float)
        assert listings[0].price == 100.0


# ---------------------------------------------------------------------------
# HTML fixture source
# ---------------------------------------------------------------------------

class TestMockHtmlSource:
    def test_returns_list(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        result = source.fetch("")
        assert isinstance(result, list)

    def test_all_elements_are_listing(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        for item in source.fetch(""):
            assert isinstance(item, Listing)

    def test_returns_four_items(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        assert len(source.fetch("")) == 4

    def test_title_is_string(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        for item in source.fetch(""):
            assert isinstance(item.title, str)

    def test_price_is_float(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        for item in source.fetch(""):
            assert isinstance(item.price, float)

    def test_url_is_string(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        for item in source.fetch(""):
            assert isinstance(item.url, str)

    def test_source_field_is_mock_html(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        for item in source.fetch(""):
            assert item.source == "mock_html"

    def test_known_titles_present(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        titles = {l.title for l in source.fetch("")}
        assert "Vintage Leather Sofa" in titles
        assert "Standing Desk Lamp" in titles

    def test_known_prices_present(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        prices = {l.price for l in source.fetch("")}
        assert 149.99 in prices
        assert 299.50 in prices

    def test_known_urls_present(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        urls = {l.url for l in source.fetch("")}
        assert "https://example.com/item/1" in urls

    def test_query_arg_has_no_effect(self):
        source = MockHtmlSource(FIXTURES / "sample.html")
        a = [l.url for l in source.fetch("bikes")]
        b = [l.url for l in source.fetch("lamps")]
        assert a == b

    def test_non_listing_li_elements_ignored(self, tmp_path):
        html = (
            "<ul>"
            '<li class="other" data-url="http://x.com/0" data-price="1.0">'
            '<span class="title">Noise</span></li>'
            '<li class="listing" data-url="http://x.com/1" data-price="10.0">'
            '<span class="title">Signal</span></li>'
            "</ul>"
        )
        f = tmp_path / "t.html"
        f.write_text(html)
        source = MockHtmlSource(f)
        results = source.fetch("")
        assert len(results) == 1
        assert results[0].title == "Signal"

    def test_listing_without_title_span_gets_empty_title(self, tmp_path):
        html = (
            "<ul>"
            '<li class="listing" data-url="http://x.com/1" data-price="50.0"></li>'
            "</ul>"
        )
        f = tmp_path / "t.html"
        f.write_text(html)
        source = MockHtmlSource(f)
        listings = source.fetch("")
        assert len(listings) == 1
        assert listings[0].price == 50.0
        assert listings[0].title == ""

    def test_missing_price_defaults_to_zero(self, tmp_path):
        html = (
            "<ul>"
            '<li class="listing" data-url="http://x.com/1">'
            '<span class="title">No Price</span></li>'
            "</ul>"
        )
        f = tmp_path / "t.html"
        f.write_text(html)
        source = MockHtmlSource(f)
        listings = source.fetch("")
        assert listings[0].price == 0.0

    def test_empty_html_returns_empty_list(self, tmp_path):
        f = tmp_path / "empty.html"
        f.write_text("<html><body></body></html>")
        source = MockHtmlSource(f)
        assert source.fetch("") == []
