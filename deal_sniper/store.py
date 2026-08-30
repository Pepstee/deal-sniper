import sqlite3
from pathlib import Path


class SQLiteStore:
    def __init__(self, db_path: str | Path) -> None:
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS seen_urls (url TEXT PRIMARY KEY)"
        )
        self._conn.commit()

    def is_new(self, listing) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM seen_urls WHERE url = ?", (listing.url,)
        ).fetchone()
        return row is None

    def mark_seen(self, listing) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO seen_urls (url) VALUES (?)", (listing.url,)
        )
        self._conn.commit()

    def list_seen_urls(self) -> list[str]:
        """Return every persisted deduplication identity in stable order."""

        rows = self._conn.execute("SELECT url FROM seen_urls ORDER BY url").fetchall()
        return [row[0] for row in rows]

    def close(self) -> None:
        self._conn.close()
