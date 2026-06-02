from __future__ import annotations

import heapq


class MedianTracker:
    """Running median using two heaps (max-heap for lower half, min-heap for upper half)."""

    def __init__(self) -> None:
        self._lo: list[float] = []  # max-heap (stored negated)
        self._hi: list[float] = []  # min-heap

    def add(self, price: float) -> None:
        heapq.heappush(self._lo, -price)
        heapq.heappush(self._hi, -heapq.heappop(self._lo))
        if len(self._hi) > len(self._lo):
            heapq.heappush(self._lo, -heapq.heappop(self._hi))

    def median(self) -> float | None:
        if not self._lo:
            return None
        if len(self._lo) == len(self._hi):
            return (-self._lo[0] + self._hi[0]) / 2
        return -self._lo[0]
