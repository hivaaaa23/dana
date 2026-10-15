"""شمارنده‌ی Redis با یک Redis جعلی (بدون نیاز به سرور واقعی) و رفتار fallback"""
import time

import pytest

from app.services import rate_limit


class FakePipeline:
    def __init__(self, r): self.r, self.ops = r, []
    def incr(self, k): self.ops.append(("incr", k)); return self
    def expire(self, k, s): self.ops.append(("expire", k, s)); return self
    def execute(self):
        out = []
        for op in self.ops:
            if op[0] == "incr":
                self.r.data[op[1]] = self.r.data.get(op[1], 0) + 1
                out.append(self.r.data[op[1]])
            else:
                self.r.ttl[op[1]] = op[2]; out.append(True)
        return out


class FakeRedis:
    def __init__(self): self.data, self.ttl = {}, {}
    def pipeline(self): return FakePipeline(self)


class DeadRedis:
    def pipeline(self): raise ConnectionError("redis down")


def test_memory_limiter_blocks_after_limit():
    assert [rate_limit.is_rate_limited("k", "1.1.1.1", limit=2, window=60) for _ in range(3)] == [False, False, True]
    assert rate_limit.is_rate_limited("k", "2.2.2.2", limit=2, window=60) is False  # IP دیگر


def test_memory_window_expires():
    assert rate_limit.is_rate_limited("k", "ip", limit=1, window=1) is False
    assert rate_limit.is_rate_limited("k", "ip", limit=1, window=1) is True
    time.sleep(1.1)
    assert rate_limit.is_rate_limited("k", "ip", limit=1, window=1) is False


def test_redis_limiter_is_shared_and_sets_ttl(monkeypatch, cfg):
    fake = FakeRedis()
    cfg(REDIS_URL="redis://fake")
    monkeypatch.setattr(rate_limit, "_get_redis", lambda: fake)
    assert [rate_limit.is_rate_limited("k", "ip", limit=2, window=60) for _ in range(3)] == [False, False, True]
    assert all(t > 60 for t in fake.ttl.values())  # کلیدها منقضی می‌شوند، رشد بی‌پایان ندارند
    assert not rate_limit._hits  # حافظه‌ی محلی استفاده نشده


def test_falls_back_to_memory_when_redis_down(monkeypatch, cfg):
    cfg(REDIS_URL="redis://fake")
    monkeypatch.setattr(rate_limit, "_get_redis", lambda: DeadRedis())
    assert [rate_limit.is_rate_limited("k", "ip", limit=1, window=60) for _ in range(2)] == [False, True]


def test_unreachable_redis_url_does_not_crash(cfg):
    cfg(REDIS_URL="redis://127.0.0.1:1/0")
    assert rate_limit.is_rate_limited("k", "ip", limit=1, window=60) is False
    assert rate_limit.is_rate_limited("k", "ip", limit=1, window=60) is True  # fallback حافظه


def test_works_with_real_redis_client(monkeypatch, cfg):
    """کلاینت واقعی redis-py (روی fakeredis): تضمین می‌کند API pipeline درست استفاده شده."""
    fakeredis = pytest.importorskip("fakeredis")
    r = fakeredis.FakeRedis(decode_responses=True)
    cfg(REDIS_URL="redis://fake")
    monkeypatch.setattr(rate_limit, "_get_redis", lambda: r)
    assert [rate_limit.is_rate_limited("k", "ip", limit=2, window=60) for _ in range(3)] == [False, False, True]
    (key,) = r.keys("dana:rl:*")
    assert 0 < r.ttl(key) <= 65
