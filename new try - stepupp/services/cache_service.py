import time
from threading import Lock

class SimpleCache:
    """
    Lightweight, thread-safe in-memory cache with TTL and prefix-based invalidation.
    Dramatically reduces remote MySQL roundtrip latency from seconds to under 1ms.
    """
    def __init__(self, default_ttl=60):
        self._cache = {}
        self._timestamps = {}
        self._lock = Lock()
        self.default_ttl = default_ttl

    def get(self, key):
        with self._lock:
            if key in self._cache:
                if time.time() < self._timestamps.get(key, 0):
                    return self._cache[key]
                else:
                    self._cache.pop(key, None)
                    self._timestamps.pop(key, None)
        return None

    def set(self, key, value, ttl=None):
        if ttl is None:
            ttl = self.default_ttl
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time() + ttl

    def invalidate(self, prefix=""):
        with self._lock:
            if not prefix:
                self._cache.clear()
                self._timestamps.clear()
            else:
                keys_to_del = [k for k in self._cache if k.startswith(prefix)]
                for k in keys_to_del:
                    self._cache.pop(k, None)
                    self._timestamps.pop(k, None)

    def stats(self):
        with self._lock:
            return {
                'active_keys': len(self._cache),
                'keys': list(self._cache.keys())
            }

# Global singleton cache instance for HOD APIs
api_cache = SimpleCache(default_ttl=45)
