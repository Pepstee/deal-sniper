from abc import ABC, abstractmethod

from deal_sniper.models import Listing


class Source(ABC):
    """A listing source: return the current listings for a query."""

    @abstractmethod
    def fetch(self, query: str) -> list[Listing]: ...
