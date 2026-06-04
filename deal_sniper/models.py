from dataclasses import dataclass


@dataclass
class Listing:
    id: str
    title: str
    price: float
    url: str
    source: str
