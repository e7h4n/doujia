import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

from beancount.core.data import Amount


@dataclass
class PriceCache:
    price: Amount
    timestamp: datetime


class SymbolPriceCache:
    def __init__(self):
        self._cache: Dict[str, PriceCache] = {}
        self._lock = threading.Lock()

    def get(self, symbol: str) -> PriceCache | None:
        with self._lock:
            return self._cache.get(symbol)

    def update(self, symbol: str, price: Amount, timestamp: datetime):
        with self._lock:
            self._cache[symbol] = PriceCache(price=price, timestamp=timestamp)

    def update_batch(self, prices: Dict[str, Amount]):
        now = datetime.now()
        with self._lock:
            for symbol, price in prices.items():
                self._cache[symbol] = PriceCache(price=price, timestamp=now)


# 全局单例
symbol_price_cache = SymbolPriceCache()
