from deal_sniper.listing import Listing


class ConsoleNotifier:
    def notify(self, listing: Listing, alert_text: str) -> None:
        print(alert_text)
