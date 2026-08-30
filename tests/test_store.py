"""SQLiteStore: SQLite-backed deduplication store."""

from deal_sniper.models import Listing
from deal_sniper.store import SQLiteStore


def make_listing(url: str, price: float = 10.0) -> Listing:
    return Listing(title="T", price=price, url=url, source="test")


class TestIsNew:
    def test_unseen_url_is_new(self, tmp_path):
        store = SQLiteStore(tmp_path / "store.db")
        listing = make_listing("https://ex.com/1")
        assert store.is_new(listing) is True

    def test_after_mark_seen_not_new(self, tmp_path):
        store = SQLiteStore(tmp_path / "store.db")
        listing = make_listing("https://ex.com/1")
        store.mark_seen(listing)
        assert store.is_new(listing) is False

    def test_different_url_still_new(self, tmp_path):
        store = SQLiteStore(tmp_path / "store.db")
        a = make_listing("https://ex.com/1")
        b = make_listing("https://ex.com/2")
        store.mark_seen(a)
        assert store.is_new(b) is True

    def test_mark_seen_twice_does_not_raise(self, tmp_path):
        store = SQLiteStore(tmp_path / "store.db")
        listing = make_listing("https://ex.com/1")
        store.mark_seen(listing)
        store.mark_seen(listing)  # INSERT OR IGNORE — must not raise
        assert store.is_new(listing) is False

    def test_multiple_urls_tracked_independently(self, tmp_path):
        store = SQLiteStore(tmp_path / "store.db")
        urls = [f"https://ex.com/{i}" for i in range(5)]
        listings = [make_listing(u) for u in urls]
        for l in listings[:3]:
            store.mark_seen(l)
        for l in listings[:3]:
            assert store.is_new(l) is False
        for l in listings[3:]:
            assert store.is_new(l) is True


class TestPersistence:
    def test_seen_url_survives_reopen(self, tmp_path):
        db = tmp_path / "store.db"
        store = SQLiteStore(db)
        listing = make_listing("https://ex.com/persist")
        store.mark_seen(listing)
        store.close()

        store2 = SQLiteStore(db)
        assert store2.is_new(listing) is False

    def test_unseen_url_still_new_after_reopen(self, tmp_path):
        db = tmp_path / "store.db"
        store = SQLiteStore(db)
        seen = make_listing("https://ex.com/seen")
        unseen = make_listing("https://ex.com/unseen")
        store.mark_seen(seen)
        store.close()

        store2 = SQLiteStore(db)
        assert store2.is_new(unseen) is True

    def test_create_table_idempotent(self, tmp_path):
        db = tmp_path / "store.db"
        # Opening twice should not raise (CREATE TABLE IF NOT EXISTS)
        s1 = SQLiteStore(db)
        s1.close()
        s2 = SQLiteStore(db)
        s2.close()

    def test_data_written_by_first_session_visible_in_second(self, tmp_path):
        db = tmp_path / "store.db"
        s1 = SQLiteStore(db)
        for i in range(10):
            s1.mark_seen(make_listing(f"https://ex.com/{i}"))
        s1.close()

        s2 = SQLiteStore(db)
        for i in range(10):
            assert s2.is_new(make_listing(f"https://ex.com/{i}")) is False


class TestListSeenUrls:
    def test_returns_unique_urls_in_stable_order(self, tmp_path):
        store = SQLiteStore(tmp_path / "store.db")
        for url in (
            "https://ex.com/z-last",
            "https://ex.com/a-first",
            "https://ex.com/z-last",
        ):
            store.mark_seen(make_listing(url))

        assert store.list_seen_urls() == [
            "https://ex.com/a-first",
            "https://ex.com/z-last",
        ]

    def test_empty_store_returns_empty_list(self, tmp_path):
        store = SQLiteStore(tmp_path / "store.db")
        assert store.list_seen_urls() == []

    def test_urls_survive_reopen_for_enumeration(self, tmp_path):
        db = tmp_path / "store.db"
        first = SQLiteStore(db)
        first.mark_seen(make_listing("https://ex.com/persist"))
        first.close()

        second = SQLiteStore(db)
        assert second.list_seen_urls() == ["https://ex.com/persist"]


class TestEdgeCases:
    def test_empty_string_url(self, tmp_path):
        store = SQLiteStore(tmp_path / "store.db")
        listing = make_listing("")
        assert store.is_new(listing) is True
        store.mark_seen(listing)
        assert store.is_new(listing) is False

    def test_url_with_special_characters(self, tmp_path):
        url = "https://ex.com/item?a=1&b=2#frag"
        store = SQLiteStore(tmp_path / "store.db")
        listing = make_listing(url)
        store.mark_seen(listing)
        assert store.is_new(listing) is False

    def test_two_stores_on_different_paths_are_independent(self, tmp_path):
        s1 = SQLiteStore(tmp_path / "a.db")
        s2 = SQLiteStore(tmp_path / "b.db")
        listing = make_listing("https://ex.com/x")
        s1.mark_seen(listing)
        assert s2.is_new(listing) is True
