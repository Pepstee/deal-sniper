from abc import ABC, abstractmethod

from deal_sniper.models import Listing


class Source(ABC):
    @abstractmethod
    def fetch(self, query: str) -> list[Listing]:
        ...
