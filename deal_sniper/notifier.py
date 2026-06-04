from abc import ABC, abstractmethod

from deal_sniper.listing import Listing


class Notifier(ABC):
    @abstractmethod
    def notify(self, listing: Listing, alert_text: str) -> None: ...


class ConsoleNotifier(Notifier):
    def notify(self, listing: Listing, alert_text: str) -> None:
        print(f"ALERT: {alert_text}")
