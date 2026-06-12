from dataclasses import dataclass, field


@dataclass
class Listing:
    title: str
    price: float
    url: str
    source: str
    query: str = ""
    extra: dict = field(default_factory=dict)
