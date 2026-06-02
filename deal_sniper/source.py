from typing import Protocol

from deal_sniper.listing import Listing


class Source(Protocol):
    def fetch(self, query: str) -> list[Listing]:
        ...
