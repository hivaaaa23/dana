"""
بررسی آمادگی قبل از ارائه/استقرار:  python scripts/preflight.py
هر مورد ناموفق «✗» می‌گیرد و کد خروج ۱ برمی‌گردد؛ هشدارها «!» هستند و مانع نیستند.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

problems, warnings = [], []


def ok(msg): print("✓", msg)
def bad(msg): problems.append(msg); print("✗", msg)
def warn(msg): warnings.append(msg); print("!", msg)


if not (ROOT / ".env").exists():
    sys.exit("✗ فایل .env وجود ندارد (python scripts/gen_env.py --production --cors https://...).")

try:
    from app.config import settings, widget_origins_required
except Exception as e:  # اعتبارسنجی production در config.py خطا می‌دهد
    sys.exit(f"✗ تنظیمات معتبر نیستند: {e}")

if settings.APP_ENV == "production": ok("APP_ENV=production")
else: bad(f"APP_ENV={settings.APP_ENV!r} است؛ باید production باشد.")

if settings.CORS_ORIGINS.strip() not in ("", "*"): ok(f"CORS_ORIGINS={settings.CORS_ORIGINS}")
else: bad("CORS_ORIGINS روی آدرس واقعی داشبورد ست نشده.")
if "localhost" in settings.CORS_ORIGINS or "127.0.0.1" in settings.CORS_ORIGINS:
    warn("CORS_ORIGINS به localhost اشاره می‌کند.")

if settings.REDIS_URL:
    try:
        import redis
        redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2).ping()
        ok("Redis در دسترس است (rate limit مشترک).")
    except Exception as e:
        bad(f"REDIS_URL ست است ولی وصل نمی‌شود: {e}")
else:
    warn("REDIS_URL خالی است؛ rate limit فقط per-process است (با چند worker مشترک نیست).")

if settings.TRUSTED_PROXY_COUNT == 0:
    warn("TRUSTED_PROXY_COUNT=0؛ اگر پشت nginx/Cloudflare هستی همه‌ی بینندگان یک IP دیده می‌شوند (--proxies را ست کن).")

if settings.LOG_CHAT_CONTENT:
    warn(f"ذخیره‌ی متن مکالمات روشن است (نگهداری {settings.LOG_RETENTION_DAYS} روز) — اطلاع‌رسانی حریم خصوصی به کاربران نهایی لازم است.")
else:
    ok("لاگ مکالمات فقط متادیتا (متن ذخیره نمی‌شود).")

if widget_origins_required(): ok("ویجت بدون «دامنه‌های مجاز» بسته است.")
else: bad("WIDGET_REQUIRE_ALLOWED_ORIGINS خاموش است؛ ویجت بدون محدودیت دامنه باز می‌ماند.")

try:
    from app.database import SessionLocal
    from app.models.settings import UserSettings
    from app.models.user import User

    with SessionLocal() as db:
        rows = (
            db.query(User.email)
            .join(UserSettings, UserSettings.user_id == User.id)
            .filter((UserSettings.allowed_origins.is_(None)) | (UserSettings.allowed_origins == ""))
            .all()
        )
    if rows:
        warn(f"{len(rows)} کاربر «دامنه‌های مجاز» ویجت را پر نکرده‌اند (ویجتشان در production بسته است): "
             + ", ".join(r[0] for r in rows[:5]) + (" …" if len(rows) > 5 else ""))
    else:
        ok("همه‌ی کاربران «دامنه‌های مجاز» ویجت را پر کرده‌اند.")
except Exception as e:
    warn(f"دیتابیس بررسی نشد (migration اجرا شده؟): {e}")

from app.services.text_extract import OCR_ENABLED
if OCR_ENABLED:
    if shutil.which("tesseract"): ok("tesseract نصب است (OCR).")
    else: warn("tesseract نصب نیست؛ PDF اسکن‌شده خطا می‌دهد.")

fonts = ROOT.parent / "frontend" / "fonts"
if not list(fonts.glob("*.woff2")):
    warn("فونت‌های Vazirmatn در frontend/fonts نیستند (fonts/README.md).")

print()
if problems:
    print(f"{len(problems)} مورد باید رفع شود.")
    sys.exit(1)
print("آماده‌ی ارائه." + (f" ({len(warnings)} هشدار)" if warnings else ""))
