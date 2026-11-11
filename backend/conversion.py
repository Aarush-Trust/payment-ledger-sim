from typing import Tuple

# Demo FX rates – deterministic and safe for development.
RATES: dict[tuple[str, str], float] = {
    ("USD", "EUR"): 0.9,
    ("EUR", "USD"): 1.1,
    ("CAD", "USD"): 0.7,
    ("USD", "CAD"): 1.4,
    ("USD", "BTC"): 1 / 50000,
    ("BTC", "USD"): 50000.0,
    ("EUR", "BTC"): 1 / 55000,
    ("BTC", "EUR"): 55000.0,
}


class UnsupportedPairError(ValueError):
    """Raised when a requested currency pair has no rate in RATES."""

    def __init__(self, source: str, target: str):
        self.source = source
        self.target = target
        super().__init__(f"Unsupported currency pair: {source} to {target}")


def normalize_currency(code: str) -> str:
    return code.strip().upper()


def convert(amount: float, source: str, target: str) -> Tuple[float, float]:
    """
    Deterministic conversion using a fixed rate table.
    Raises UnsupportedPairError if the pair is not in the table. It never
    falls back to a default rate.
    """
    s = normalize_currency(source)
    t = normalize_currency(target)

    if s == t:
        return 1.0, amount

    rate = RATES.get((s, t))
    if rate is None:
        raise UnsupportedPairError(s, t)
    return rate, amount * rate
