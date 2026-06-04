"""
TTL Cache — In-memory cache đơn giản với thời gian hết hạn.
Dùng cho weather và places để tránh gọi API lặp lại.
"""
from __future__ import annotations

import time
from typing import Any

from logging_config import get_logger

logger = get_logger("cache")


class TTLCache:
    """
    Cache key-value đơn giản với TTL (Time To Live).

    Usage:
        cache = TTLCache(ttl_seconds=600)  # 10 phút
        cache.set("key", value)
        result = cache.get("key")  # None nếu hết hạn
    """

    def __init__(self, ttl_seconds: int = 600, max_size: int = 200):
        self._store: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size

    def get(self, key: str) -> Any | None:
        """Lấy giá trị từ cache. Trả None nếu hết hạn hoặc không tồn tại."""
        entry = self._store.get(key)
        if entry is None:
            return None

        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None

        return value

    def set(self, key: str, value: Any) -> None:
        """Lưu giá trị vào cache với TTL."""
        # Evict nếu đầy
        if len(self._store) >= self._max_size:
            self._evict_expired()
            if len(self._store) >= self._max_size:
                # Xóa entry cũ nhất
                oldest_key = min(self._store, key=lambda k: self._store[k][0])
                del self._store[oldest_key]

        self._store[key] = (time.monotonic() + self._ttl, value)

    def invalidate(self, key: str) -> None:
        """Xóa 1 key khỏi cache."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Xóa toàn bộ cache."""
        self._store.clear()

    def _evict_expired(self) -> None:
        """Xóa các entry đã hết hạn."""
        now = time.monotonic()
        expired = [k for k, (exp, _) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]

    def __len__(self) -> int:
        self._evict_expired()
        return len(self._store)


# ── Global cache instances ───────────────────────────

# Weather cache: 10 phút (thời tiết ít thay đổi)
weather_cache = TTLCache(ttl_seconds=600, max_size=50)

# Places cache: 5 phút (quán gần vị trí user)
places_cache = TTLCache(ttl_seconds=300, max_size=100)

# Address cache: 1 giờ (địa chỉ không thay đổi nhiều)
address_cache = TTLCache(ttl_seconds=3600, max_size=100)


def make_weather_key(lat: float, lon: float) -> str:
    """Tạo cache key cho weather (làm tròn 2 decimals)."""
    return f"weather:{round(lat, 2)}:{round(lon, 2)}"


def make_places_key(lat: float, lon: float, keyword: str = "") -> str:
    """Tạo cache key cho places search."""
    return f"places:{round(lat, 2)}:{round(lon, 2)}:{keyword.lower().strip()}"
