from __future__ import annotations

import sys
from typing import IO, Any, Protocol, runtime_checkable


@runtime_checkable
class Scorable(Protocol):
    score: float
    title: str


def check_and_emit_alerts(
    articles: list[Any],
    threshold: float,
    output: IO[str] = sys.stdout,
) -> list[Any]:
    """Emit an alert line for each article whose score meets or exceeds threshold."""
    triggered = []
    for article in articles:
        if article.score >= threshold:
            triggered.append(article)
            output.write(f"ALERT: {article.title} (score={article.score:.3f})\n")
    return triggered
