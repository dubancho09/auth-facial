import time


class InMemoryRateLimiter:

    def __init__(self):
        self._buckets = {}

    def allow(self, key, limit, window_seconds):
        now = time.monotonic()
        window_start = now - window_seconds

        bucket = self._buckets.setdefault(key, [])

        # Keep only entries in current window.
        while bucket and bucket[0] <= window_start:
            bucket.pop(0)

        if len(bucket) >= limit:
            retry_after = max(1, int(window_seconds - (now - bucket[0])))
            return False, retry_after

        bucket.append(now)
        return True, 0
