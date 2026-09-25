"""In-process TTL cache for FastAPI read models. Not shared across workers."""

from __future__ import annotations

import copy
import threading
import time
from collections import OrderedDict
from typing import Any, Callable

Clock = Callable[[], float]


class TtlCache:
    """Bounded dict with monotonic TTL. Values are deep-copied on get/set."""

    def __init__(
        self,
        *,
        maxsize: int = 512,
        default_ttl: float = 30.0,
        clock: Clock | None = None,
    ) -> None:
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self._clock = clock or time.monotonic
        self._lock = threading.Lock()
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        now = self._clock()
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= now:
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return copy.deepcopy(value)

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        expires_at = self._clock() + (self.default_ttl if ttl is None else ttl)
        stored = copy.deepcopy(value)
        with self._lock:
            if key in self._store:
                del self._store[key]
            while len(self._store) >= self.maxsize:
                self._store.popitem(last=False)
            self._store[key] = (expires_at, stored)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def delete_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = [key for key in self._store if key.startswith(prefix)]
            for key in keys:
                del self._store[key]
            return len(keys)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def set_clock(self, clock: Clock) -> None:
        with self._lock:
            self._clock = clock

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


CACHE_VERSION = "v1"
PRODUCTS_LIST_KEY = f"{CACHE_VERSION}:inventory:products:list"
ORDERS_LIST_KEY = f"{CACHE_VERSION}:inventory:orders:list"
PRODUCTS_PREFIX = f"{CACHE_VERSION}:inventory:products:"
ORDERS_PREFIX = f"{CACHE_VERSION}:inventory:orders:"

INVENTORY_TTL_SECONDS = 30.0

response_cache = TtlCache(maxsize=512, default_ttl=INVENTORY_TTL_SECONDS)


def product_item_key(supply_id: int) -> str:
    return f"{CACHE_VERSION}:inventory:products:id:{supply_id}"


def invalidate_products(*, supply_id: int | None = None) -> None:
    response_cache.delete(PRODUCTS_LIST_KEY)
    if supply_id is not None:
        response_cache.delete(product_item_key(supply_id))
    else:
        response_cache.delete_prefix(PRODUCTS_PREFIX)


def invalidate_orders() -> None:
    response_cache.delete_prefix(ORDERS_PREFIX)


def invalidate_inventory_writes(*, supply_id: int | None = None) -> None:
    invalidate_products(supply_id=supply_id)
    invalidate_orders()
