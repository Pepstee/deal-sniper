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


class TestFullRecords:
    def test_complete_metadata_survives_restart(self, tmp_path):
        from datetime import datetime, timezone

        path = tmp_path / "records.db"
        record = Listing(
            "Bike", 29.95, "https://example.com/1", "test", "bikes", {"images": ["one"]},
            id="item-1", timestamp=datetime(2026, 6, 1, 12, tzinfo=timezone.utc),
            raw={"seller": "Example"},
        )
        first = SQLiteStore(path)
        first.mark_seen(record)
        first.close()
        second = SQLiteStore(path)
        try:
            assert second.get_all() == [record]
            assert not second.is_new(record)
        finally:
            second.close()

    def test_additive_migration_keeps_legacy_urls_without_inventing_records(self, tmp_path):
        import sqlite3

        path = tmp_path / "legacy.db"
        with sqlite3.connect(path) as conn:
            conn.execute("CREATE TABLE seen_urls (url TEXT PRIMARY KEY)")
            conn.execute("INSERT INTO seen_urls VALUES (?)", ("https://example.com/old",))
        store = SQLiteStore(path)
        assert store.list_seen_urls() == ["https://example.com/old"]
        assert store.get_all() == []
        assert not store.is_new(make_listing("https://example.com/old"))
        new = make_listing("https://example.com/new")
        store.mark_seen(new)
        store.close()
        reopened = SQLiteStore(path)
        try:
            assert reopened.list_seen_urls() == [new.url, "https://example.com/old"]
            assert reopened.get_all() == [new]
        finally:
            reopened.close()

    def test_repeat_mark_keeps_first_record_and_url_identity(self, tmp_path):
        store = SQLiteStore(tmp_path / "records.db")
        original = make_listing("https://example.com/1", price=10.0)
        store.mark_seen(original)
        changed = make_listing(original.url, price=20.0)
        changed.id = "different-id"
        changed.source = "different-source"
        store.mark_seen(changed)
        assert store.get_all() == [original]
        assert not store.is_new(changed)
        store.close()

    def test_legacy_row_can_gain_observed_metadata(self, tmp_path):
        import sqlite3

        path = tmp_path / "legacy.db"
        record = make_listing("https://example.com/old")
        with sqlite3.connect(path) as conn:
            conn.execute("CREATE TABLE seen_urls (url TEXT PRIMARY KEY)")
            conn.execute("INSERT INTO seen_urls VALUES (?)", (record.url,))
        store = SQLiteStore(path)
        store.mark_seen(record)
        assert store.get_all() == [record]
        store.close()

    def test_serialization_failure_does_not_consume_url(self, tmp_path):
        import pytest

        store = SQLiteStore(tmp_path / "records.db")
        invalid = make_listing("https://example.com/invalid")
        invalid.extra = {"unsupported": object()}
        with pytest.raises(TypeError):
            store.mark_seen(invalid)
        assert store.is_new(invalid)
        assert store.get_all() == []
        store.close()


class TestQueryScopedDeduplication:
    def test_query_scopes_are_independent_and_survive_restart(self, tmp_path):
        path = tmp_path / "scoped.db"
        listing = make_listing("https://example.com/shared")
        first = SQLiteStore(path)
        assert first.is_new(listing, query="A")
        assert first.is_new(listing, query="B")
        first.mark_seen(listing, query="A")
        assert not first.is_new(listing, query="A")
        assert first.is_new(listing, query="B")
        assert not first.is_new(listing)
        first.close()

        second = SQLiteStore(path)
        assert not second.is_new(listing, query="A")
        assert second.is_new(listing, query="B")
        second.mark_seen(listing, query="B")
        second.close()

        third = SQLiteStore(path)
        try:
            assert not third.is_new(listing, query="A")
            assert not third.is_new(listing, query="B")
            assert third.is_new(listing, query="C")
            assert not third.is_new(listing)
            assert third.list_seen_urls() == [listing.url]
            assert third.get_all() == [listing]
        finally:
            third.close()

    def test_global_seen_does_not_invent_query_observations(self, tmp_path):
        store = SQLiteStore(tmp_path / "scoped.db")
        listing = make_listing("https://example.com/shared")
        store.mark_seen(listing)
        assert store.is_new(listing, query="A")
        assert store.is_new(listing, query="")
        store.mark_seen(listing, query="")
        assert not store.is_new(listing, query="")
        assert store.is_new(listing, query="A")
        store.close()

    def test_query_write_failure_rolls_back_global_record(self, tmp_path):
        import sqlite3
        import pytest

        store = SQLiteStore(tmp_path / "scoped.db")
        listing = make_listing("https://example.com/shared")
        store._conn.execute(
            "CREATE TRIGGER reject_scope BEFORE INSERT ON seen_queries "
            "BEGIN SELECT RAISE(ABORT, 'query write failed'); END"
        )
        with pytest.raises(sqlite3.IntegrityError, match="query write failed"):
            store.mark_seen(listing, query="A")
        assert store.is_new(listing)
        assert store.is_new(listing, query="A")
        assert store.get_all() == []
        store.close()
