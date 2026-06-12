from abc import ABC, abstractmethod

from deal_sniper.models import Listing


class Source(ABC):
    @abstractmethod
    def parse_html(self, html: str) -> list[Listing]: ...

    @abstractmethod
    def parse_json(self, data: str) -> list[Listing]: ...
