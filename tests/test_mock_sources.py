"""MockHtmlSource and MockJsonSource must parse fixture files; no network permitted."""
import json
import socket
from pathlib import Path

import pytest

from deal_sniper.models import Listing
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


def test_recovered_html_formats_and_malformed_rows():
    from deal_sniper.sources.mock_html import parse_html
    raw = """
    <li class="listing featured" data-url="/a" data-price="$1,200"><span class="title">Road <b>bike</b></span></li>
    <div class="listing" data-id="d"><div><h2 class="listing-title">Desk</h2></div><span class="listing-price">$200</span><a class="listing-url" href="/b">Open</a></div>
    <tr class="listing" data-source="table"><td class="title">Chair</td><td class="price">30</td><td class="url">/c</td></tr>
    <li class="listing" data-url="/bad" data-price="oops"></li>
    <li class="listing" data-url="/last" data-price="4"></li>
    """
    rows = parse_html(raw, "furniture")
    assert [(r.url, r.price) for r in rows] == [("/a", 1200), ("/b", 200), ("/c", 30), ("/last", 4)]
    assert rows[0].title == "Road bike"
    assert rows[1].extra["id"] == "d"
    assert rows[2].source == "table"
    assert all(r.query == "furniture" for r in rows)


def test_recovered_json_keeps_valid_rows_and_metadata():
    from deal_sniper.sources.mock_json import parse_json
    item = {"title": "Bike", "price": "$1,200", "url": "/bike", "id": "b", "source": "donor", "timestamp": "2026-01-01", "raw": "original"}
    rows = parse_json(json.dumps([None, {"price": 2}, item, {**item, "price": "NaN"}, {**item, "price": None}]), "bikes")
    assert len(rows) == 1
    assert rows[0].extra == item
    assert rows[0].query == "bikes"
    assert rows[0].source == "donor"
    assert parse_json(json.dumps(item))[0].price == 1200
    with pytest.raises(ValueError):
        parse_json("not json")


def test_parsed_donor_metadata_survives_store_restart(tmp_path):
    from datetime import datetime
    from deal_sniper.sources.mock_json import parse_json
    from deal_sniper.sources.mock_html import parse_html
    from deal_sniper.store import SQLiteStore

    payload = {"title": "Bike", "price": 90, "url": "/bike", "id": "donor-7", "source": "donor", "timestamp": "2026-01-01T12:00:00+00:00", "raw": {"condition": "used"}, "category": "bicycles"}
    rows = parse_json(json.dumps([payload, {**payload, "timestamp": []}]), "bikes")
    assert len(rows) == 1
    html = '<div class="listing" data-id="html-8"><h2 class="listing-title">Desk</h2><span class="listing-price">40</span><a class="listing-url" href="/desk">open</a></div>'
    rows += parse_html(html)
    path = tmp_path / "captured.db"
    store = SQLiteStore(path)
    for row in rows:
        store.mark_seen(row)
    store.close()
    reopened = SQLiteStore(path)
    try:
        recovered = reopened.get_all()
        assert [row.to_dict() for row in recovered] == [row.to_dict() for row in rows]
        assert recovered[0].timestamp == datetime.fromisoformat(payload["timestamp"])
        assert recovered[0].raw == {"condition": "used"}
        assert recovered[0].extra["category"] == "bicycles"
        assert recovered[0].id == "donor-7"
        assert recovered[1].id == "html-8"
        assert recovered[1].timestamp is None
    finally:
        reopened.close()
