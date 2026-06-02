from typing import Protocol

from deal_sniper.listing import Listing


class Notifier(Protocol):
    def notify(self, listing: Listing, alert_text: str) -> None:
        ...


class ConsoleNotifier:
    def notify(self, listing: Listing, alert_text: str) -> None:
        print(alert_text)
