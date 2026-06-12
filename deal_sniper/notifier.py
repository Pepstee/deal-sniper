from abc import ABC, abstractmethod

from deal_sniper.models import Listing


class Notifier(ABC):
    @abstractmethod
    def alert(self, listing: Listing) -> None: ...


class ConsoleNotifier(Notifier):
    def alert(self, listing: Listing) -> None:
        print(f"DEAL ALERT: {listing.title} | ${listing.price:.2f} | {listing.url}")
