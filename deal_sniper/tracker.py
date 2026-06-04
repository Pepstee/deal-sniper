from __future__ import annotations

import bisect


class MedianTracker:
    def __init__(self) -> None:
        self._data: dict[str, list[float]] = {}

    def update(self, query: str, price: float) -> None:
        prices = self._data.setdefault(query, [])
        bisect.insort(prices, price)

    def median(self, query: str) -> float | None:
        prices = self._data.get(query)
        if not prices:
            return None
        n = len(prices)
        mid = n // 2
        if n % 2 == 1:
            return prices[mid]
        return (prices[mid - 1] + prices[mid]) / 2
