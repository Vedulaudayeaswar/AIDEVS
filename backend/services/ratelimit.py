"""Rate limiting backends.

* MemoryLimiter (default): sliding window per process. Correct for one API
  instance (the default Render setup) and for local development.
* RedisLimiter (REDIS_URL set): fixed-window counters shared by every worker
  and instance. If Redis becomes unreachable the limiter fails *open* and logs
  a warning (availability over strictness); AI spend is still bounded by the
  database-backed daily quotas in services/limits.py, which do not depend on Redis.
"""
import logging
import os
import threading
import time
from collections import defaultdict, deque

log = logging.getLogger("aidevs.ratelimit")


class MemoryLimiter:
    name = "memory"

    def __init__(self):
        self._buckets = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key, limit, window):
        t = time.monotonic()
        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] <= t - window:
                bucket.popleft()
            if len(bucket) >= limit:
                return False, int(window - (t - bucket[0])) + 1
            bucket.append(t)
            return True, 0

    def reset(self):
        with self._lock:
            self._buckets.clear()


class RedisLimiter:
    name = "redis"

    def __init__(self, client):
        self.client = client

    def hit(self, key, limit, window):
        slot = int(time.time() // window)
        rkey = f"aidevs:rl:{key}:{slot}"
        try:
            pipe = self.client.pipeline()
            pipe.incr(rkey)
            pipe.expire(rkey, window + 1)
            count = pipe.execute()[0]
        except Exception as exc:  # fail open, but never silently
            log.warning("redis rate limiter unavailable, allowing request: %s", exc.__class__.__name__)
            return True, 0
        if count > limit:
            return False, int(window - (time.time() % window)) + 1
        return True, 0

    def reset(self):
        try:
            for key in self.client.scan_iter("aidevs:rl:*"):
                self.client.delete(key)
        except Exception as exc:
            log.warning("redis reset failed: %s", exc)


_limiter = None
_hits = defaultdict(int)  # blocked-request counters for the admin dashboard (per process)
_hits_lock = threading.Lock()


def get_limiter():
    global _limiter
    if _limiter is None:
        url = os.getenv("REDIS_URL", "").strip()
        if url:
            import redis
            _limiter = RedisLimiter(redis.Redis.from_url(url, socket_timeout=1, socket_connect_timeout=1))
            log.info("rate limiting backend: redis")
        else:
            _limiter = MemoryLimiter()
    return _limiter


def set_limiter(limiter):
    global _limiter
    _limiter = limiter


def check(key, limit, window):
    ok, retry = get_limiter().hit(key, limit, window)
    if not ok:
        with _hits_lock:
            _hits[key.split(":", 1)[0]] += 1
    return ok, retry


def blocked_counts():
    with _hits_lock:
        return dict(_hits)
