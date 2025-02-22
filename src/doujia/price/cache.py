import threading
from dataclasses import dataclass
from datetime import datetime

from beancount.core.data import Amount


@dataclass
class PriceCache:
    price: Amount
    timestamp: datetime  # last update time
    price_date: datetime  # actual price date from source


class SymbolPriceCache:
    def __init__(self):
        self._cache: dict[str, PriceCache] = {}
        self._lock = threading.Lock()

    def get(self, symbol: str) -> PriceCache | None:
        with self._lock:
            return self._cache.get(symbol)

    def update(self, symbol: str, price: Amount, timestamp: datetime, price_date: datetime):
        with self._lock:
            self._cache[symbol] = PriceCache(price=price, timestamp=timestamp, price_date=price_date)

    def update_batch(self, prices: dict[str, Amount], price_dates: dict[str, datetime]):
        now = datetime.now()
        with self._lock:
            for symbol, price in prices.items():
                price_date = price_dates.get(symbol, now)  # fallback to now if no date provided
                self._cache[symbol] = PriceCache(price=price, timestamp=now, price_date=price_date)


# 全局单例
symbol_price_cache = SymbolPriceCache()
