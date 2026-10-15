"""
ساخت فایل .env با کلیدهای تصادفی واقعی.

توسعه:      python scripts/gen_env.py
production: python scripts/gen_env.py --production --cors https://dana.example.com [--redis redis://localhost:6379/0]

با --production مقادیر APP_ENV=production و CORS_ORIGINS ست می‌شود و آدرس نامعتبر (خالی، *، بدون https) رد می‌شود.
"""
import argparse
import secrets
import sys
from pathlib import Path
from urllib.parse import urlparse

from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parent.parent
target = ROOT / ".env"


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--production", action="store_true", help="APP_ENV=production و CORS_ORIGINS واقعی")
    ap.add_argument("--cors", help="آدرس(های) داشبورد، با کاما جدا: https://dana.example.com")
    ap.add_argument("--redis", default="", help="REDIS_URL برای rate limit مشترک بین workerها")
    ap.add_argument("--proxies", type=int, default=0, help="تعداد reverse proxy جلوی برنامه (TRUSTED_PROXY_COUNT)")
    ap.add_argument("--force", action="store_true", help="اگر .env وجود دارد، کلیدهای فعلی را نگه دار و فقط بقیه را عوض کن")
    ap.add_argument("--admin-email", help="ایمیل ادمین اولیه؛ رمز تصادفی ساخته و فقط یک بار چاپ می‌شود")
    return ap.parse_args(argv)


def validate_cors(value: str) -> list[str]:
    origins = [o.strip().rstrip("/") for o in (value or "").split(",") if o.strip()]
    if not origins:
        raise SystemExit("برای --production باید --cors را با آدرس واقعی داشبورد بدهی.")
    for o in origins:
        u = urlparse(o)
        if o == "*" or u.scheme != "https" or not u.netloc or u.path:
            raise SystemExit(f"CORS نامعتبر: {o!r} — باید مثل https://dana.example.com باشد (بدون * و بدون مسیر).")
    return origins


def build_env(template: str, args, existing: dict[str, str] | None = None) -> str:
    existing = existing or {}
    cors = ",".join(validate_cors(args.cors)) if args.production else (args.cors or None)
    out, seen = [], set()
    for line in template.splitlines():
        key = line.split("=", 1)[0] if "=" in line and not line.startswith("#") else None
        if key == "SECRET_KEY":
            line = "SECRET_KEY=" + existing.get("SECRET_KEY", secrets.token_urlsafe(48))
        elif key == "APP_ENCRYPTION_KEY":
            line = "APP_ENCRYPTION_KEY=" + existing.get("APP_ENCRYPTION_KEY", Fernet.generate_key().decode())
        elif key == "APP_ENV" and args.production:
            line = "APP_ENV=production"
        elif key == "CORS_ORIGINS" and cors:
            line = "CORS_ORIGINS=" + cors
        elif key == "ADMIN_EMAIL" and args.admin_email:
            line = "ADMIN_EMAIL=" + args.admin_email.strip().lower()
        elif key == "ADMIN_PASSWORD" and args.admin_email:
            line = "ADMIN_PASSWORD=" + (existing.get("ADMIN_PASSWORD") or secrets.token_urlsafe(16))
        elif key == "REDIS_URL" and args.redis:
            line = "REDIS_URL=" + args.redis
        elif key == "TRUSTED_PROXY_COUNT" and args.proxies:
            line = f"TRUSTED_PROXY_COUNT={args.proxies}"
        if key:
            seen.add(key)
        out.append(line)
    return "\n".join(out) + "\n"


def main(argv=None):
    args = parse_args(argv)
    existing: dict[str, str] = {}
    if target.exists():
        if not args.force:
            raise SystemExit(f"{target} از قبل وجود دارد؛ برای جلوگیری از پاک‌شدن کلیدها دست نمی‌زنم (با --force کلیدهای فعلی حفظ می‌شوند).")
        for line in target.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()
    template = (ROOT / ".env.example").read_text(encoding="utf-8")
    target.write_text(build_env(template, args, existing), encoding="utf-8")
    print("ساخته شد:", target)
    if args.admin_email:
        pw = next(l.split("=", 1)[1] for l in target.read_text(encoding="utf-8").splitlines() if l.startswith("ADMIN_PASSWORD="))
        print(f"ادمین اولیه: {args.admin_email.strip().lower()}  |  رمز: {pw}  (در .env هم هست؛ بعد از اولین ورود عوضش کن)")
    if args.production:
        print("بعدش: python scripts/preflight.py  و در پنل، «دامنه‌های مجاز» ویجت را پر کن.")
    else:
        print("برای production: python scripts/gen_env.py --production --cors https://آدرس-واقعی --force")


if __name__ == "__main__":
    main(sys.argv[1:])
