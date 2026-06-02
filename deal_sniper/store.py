import sqlite3
from pathlib import Path


class ListingStore:
    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._conn = sqlite3.connect(self._path)
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

    def close(self) -> None:
        self._conn.close()
