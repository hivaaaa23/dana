"""
Rate limit ویجت.

- اگر REDIS_URL ست باشد: شمارنده در Redis است و بین همه‌ی workerها و سرورها مشترک است
  (پنجره‌ی ثابت: INCR + EXPIRE روی کلید «کلید ویجت + IP + شماره‌ی پنجره»).
- اگر ست نباشد، یا Redis در دسترس نباشد: شمارنده‌ی داخل حافظه‌ی همین پروسه (پنجره‌ی لغزان).
  یعنی قطعی Redis ویجت را از کار نمی‌اندازد، فقط محدودیت موقتاً per-process می‌شود (در لاگ هشدار می‌دهیم).
"""
import logging
import threading
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import Request

from app.config import settings

log = logging.getLogger("dana.ratelimit")

_hits: dict[tuple[str, str], deque] = defaultdict(deque)
_lock = threading.Lock()

_redis = None
_redis_checked = False
_redis_failed_at = 0.0
_RETRY_AFTER_FAILURE = 30  # ثانیه: بعد از خطای Redis تا این مدت سراغش نمی‌رویم


def _get_redis():
    """کلاینت Redis یا None. اتصال تنبل است و بعد از خطا موقتاً کنار گذاشته می‌شود."""
    global _redis, _redis_checked
    if not settings.REDIS_URL:
        return None
    if _redis_failed_at and time.monotonic() - _redis_failed_at < _RETRY_AFTER_FAILURE:
        return None
    if not _redis_checked:
        _redis_checked = True
        try:
            import redis  # import تنبل: بدون REDIS_URL نیازی به نصب نیست

            _redis = redis.Redis.from_url(
                settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1, decode_responses=True
            )
        except Exception:
            log.exception("اتصال به Redis ساخته نشد؛ از شمارنده‌ی حافظه استفاده می‌شود.")
            _redis = None
    return _redis


def _mark_redis_failed(exc: Exception) -> None:
    global _redis_failed_at
    _redis_failed_at = time.monotonic()
    log.warning("Redis برای rate limit در دسترس نیست (%s)؛ موقتاً شمارنده‌ی حافظه.", exc)


def _limited_memory(key: str, ip: str, limit: int, window: int) -> bool:
    now = time.monotonic()
    with _lock:
        q = _hits[(key, ip)]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return True
        q.append(now)
        if len(_hits) > 10000:  # جلوگیری از رشد بی‌پایان حافظه
            for k in [k for k, v in _hits.items() if not v or now - v[-1] > window]:
                _hits.pop(k, None)
    return False


def _limited_redis(r, key: str, ip: str, limit: int, window: int) -> bool:
    bucket = int(time.time() // window)
    rkey = f"dana:rl:{key}:{ip}:{bucket}"
    pipe = r.pipeline()
    pipe.incr(rkey)
    pipe.expire(rkey, window + 5)
    count = pipe.execute()[0]
    return count > limit


def is_rate_limited(key: str, ip: str, limit: Optional[int] = None, window: Optional[int] = None) -> bool:
    limit = settings.WIDGET_RATE_LIMIT if limit is None else limit
    window = settings.WIDGET_RATE_WINDOW if window is None else window
    r = _get_redis()
    if r is not None:
        try:
            return _limited_redis(r, key, ip, limit, window)
        except Exception as e:  # خطای شبکه/Redis → fallback
            _mark_redis_failed(e)
    return _limited_memory(key, ip, limit, window)


def reset_for_tests() -> None:
    global _redis, _redis_checked, _redis_failed_at
    with _lock:
        _hits.clear()
    _redis, _redis_checked, _redis_failed_at = None, False, 0.0


def client_ip(request: Request) -> str:
    """IP بیننده. فقط وقتی TRUSTED_PROXY_COUNT>0 باشد X-Forwarded-For خوانده می‌شود
    (وگرنه هر کسی می‌تواند با جعل هدر، محدودیت را دور بزند)."""
    direct = request.client.host if request.client else "?"
    n = settings.TRUSTED_PROXY_COUNT
    if n <= 0:
        return direct
    parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    if len(parts) >= n:
        return parts[-n]   # n امین مورد از انتها = آخرین IP که proxy مورد اعتماد خودش دیده
    return direct
