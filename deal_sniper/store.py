import json
import sqlite3
from pathlib import Path

from .models import Listing


class SQLiteStore:
    def __init__(self, db_path: str | Path) -> None:
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS seen_urls (url TEXT PRIMARY KEY)"
        )
        columns = {row[1] for row in self._conn.execute("PRAGMA table_info(seen_urls)")}
        if "listing_json" not in columns:
            self._conn.execute("ALTER TABLE seen_urls ADD COLUMN listing_json TEXT")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS seen_queries "
            "(query TEXT NOT NULL, url TEXT NOT NULL, PRIMARY KEY (query, url))"
        )
        self._conn.commit()

    def is_new(self, listing, *, query: str | None = None) -> bool:
        if query is None:
            row = self._conn.execute(
                "SELECT 1 FROM seen_urls WHERE url = ?", (listing.url,)
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT 1 FROM seen_queries WHERE query = ? AND url = ?",
                (query, listing.url),
            ).fetchone()
        return row is None

    def mark_seen(self, listing, *, query: str | None = None) -> None:
        # Serialize first so unsupported metadata cannot mark a listing seen.
        record = json.dumps(listing.to_dict(), allow_nan=False)
        with self._conn:
            self._conn.execute(
                "INSERT INTO seen_urls (url, listing_json) VALUES (?, ?) "
                "ON CONFLICT(url) DO UPDATE SET listing_json = excluded.listing_json "
                "WHERE seen_urls.listing_json IS NULL",
                (listing.url, record),
            )
            if query is not None:
                self._conn.execute(
                    "INSERT OR IGNORE INTO seen_queries (query, url) VALUES (?, ?)",
                    (query, listing.url),
                )

    def get_all(self) -> list[Listing]:
        """Return captured first-seen records in URL order.

        Legacy URL-only rows remain deduplicated but have no recoverable metadata.
        """
        rows = self._conn.execute(
            "SELECT listing_json FROM seen_urls "
            "WHERE listing_json IS NOT NULL ORDER BY url"
        ).fetchall()
        return [Listing.from_dict(json.loads(row[0])) for row in rows]

    def list_seen_urls(self) -> list[str]:
        """Return every persisted deduplication identity in stable order."""

        rows = self._conn.execute("SELECT url FROM seen_urls ORDER BY url").fetchall()
        return [row[0] for row in rows]

    def close(self) -> None:
        self._conn.close()
