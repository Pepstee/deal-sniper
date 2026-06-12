import json
from pathlib import Path

from deal_sniper.models import Listing
from deal_sniper.source import Source


class MockJsonSource(Source):
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def fetch(self, query: str) -> list[Listing]:
        data = json.loads(self._path.read_text())
        return [
            Listing(
                title=item["title"],
                price=float(item["price"]),
                url=item["url"],
                source="mock_json",
            )
            for item in data
        ]
