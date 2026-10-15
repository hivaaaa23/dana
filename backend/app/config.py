from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "دانا"
    DATABASE_URL: str = "sqlite:///./rakan.db"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    # عمر توکن «ورود به جای کاربر» (دقیقه)؛ عمداً کوتاه و بدون امکان تمدید
    IMPERSONATION_TOKEN_MINUTES: int = 15
    APP_ENCRYPTION_KEY: str
    # مسیر ذخیره‌سازی ChromaDB (نفر ۲)
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    # اگر فرانت از origin دیگری سرو شد، اینجا با کاما جدا کنید. "*" = همه (فقط برای توسعه)
    CORS_ORIGINS: str = "*"
    # مسیر پوشه‌ی فرانت‌اند؛ اگر وجود داشته باشد توسط خود FastAPI سرو می‌شود
    FRONTEND_DIR: str = "../frontend"
    # development | production — در production کلید ضعیف و CORS="*" رد می‌شود
    APP_ENV: str = "development"

    # --- Rate limit ویجت ---
    # اگر ست شود (مثلاً redis://localhost:6379/0) شمارنده‌ها بین همه‌ی workerها/سرورها مشترک است.
    # خالی = شمارنده در حافظه‌ی همان پروسه (فقط برای توسعه یا یک worker).
    REDIS_URL: str = ""
    WIDGET_RATE_LIMIT: int = 20     # تعداد پیام مجاز
    WIDGET_RATE_WINDOW: int = 60    # در این چند ثانیه، برای هر (کلید ویجت، IP)
    # پشت reverse proxy (nginx، Cloudflare، ...) IP واقعی بیننده در X-Forwarded-For است.
    # تعداد proxyهای مورد اعتماد جلوی برنامه را بگذار (۰ = هدر را نادیده بگیر و IP اتصال را بخوان).
    TRUSTED_PROXY_COUNT: int = 0

    # --- لاگ مکالمات (تصمیم حریم خصوصی؛ پیش‌فرض: فقط متادیتا) ---
    # ۰ = متن سوال/پاسخ ذخیره نمی‌شود. ۱ = ذخیره می‌شود (رمزنگاری‌شده با APP_ENCRYPTION_KEY).
    # قبل از روشن کردن، به کاربران نهایی ویجت اطلاع‌رسانی حریم خصوصی لازم است.
    LOG_CHAT_CONTENT: bool = False
    LOG_CONTENT_MAX_CHARS: int = 2000   # متن‌های بلندتر بریده می‌شوند
    # لاگ‌های قدیمی‌تر از این تعداد روز پاک می‌شوند (۰ = هرگز). با LOG_CHAT_CONTENT=1 حتماً مقدار بده.
    LOG_RETENTION_DAYS: int = 0

    # --- تشخیص Prompt Injection ---
    # off = خاموش | log = فقط ثبت در لاگ و ادامه | block = ثبت + پاسخ امن بدون فراخوانی مدل
    PROMPT_INJECTION_MODE: str = "block"

    # --- ادمین اولیه (اختیاری) ---
    # اگر هر دو ست باشند، موقع راه‌اندازی در صورت نبودنِ این ایمیل یک حساب ادمین ساخته می‌شود.
    # پیش‌فرض ثابت وجود ندارد؛ رمز را خودت می‌دهی (scripts/gen_env.py --admin-email رمز تصادفی می‌سازد).
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""

    # ویجت در production فقط وقتی جواب می‌دهد که «دامنه‌های مجاز» پر شده باشد
    WIDGET_REQUIRE_ALLOWED_ORIGINS: bool | None = None  # None = فقط در production اجباری
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()


def widget_origins_required() -> bool:
    if settings.WIDGET_REQUIRE_ALLOWED_ORIGINS is None:
        return settings.APP_ENV == "production"
    return settings.WIDGET_REQUIRE_ALLOWED_ORIGINS


if settings.PROMPT_INJECTION_MODE not in ("off", "log", "block"):
    raise RuntimeError("PROMPT_INJECTION_MODE باید یکی از off / log / block باشد.")

if settings.APP_ENV == "production":
    if settings.SECRET_KEY.startswith("change-this") or len(settings.SECRET_KEY) < 32:
        raise RuntimeError("SECRET_KEY ضعیف یا پیش‌فرض است (حداقل ۳۲ کاراکتر تصادفی لازم است؛ scripts/gen_env.py را اجرا کن).")
    if settings.CORS_ORIGINS.strip() == "*":
        raise RuntimeError("در production مقدار CORS_ORIGINS نباید * باشد.")
    if settings.LOG_CHAT_CONTENT and settings.LOG_RETENTION_DAYS <= 0:
        raise RuntimeError("با LOG_CHAT_CONTENT=1 در production باید LOG_RETENTION_DAYS را هم مثبت بگذاری.")
    if bool(settings.ADMIN_EMAIL) != bool(settings.ADMIN_PASSWORD):
        raise RuntimeError("ADMIN_EMAIL و ADMIN_PASSWORD باید با هم ست شوند (یا هر دو خالی باشند).")
    if settings.ADMIN_PASSWORD and len(settings.ADMIN_PASSWORD) < 12:
        raise RuntimeError("ADMIN_PASSWORD در production باید حداقل ۱۲ کاراکتر باشد.")
    try:
        from cryptography.fernet import Fernet
        Fernet(settings.APP_ENCRYPTION_KEY.encode())
    except Exception:
        raise RuntimeError("APP_ENCRYPTION_KEY یک کلید Fernet معتبر نیست (scripts/gen_env.py را اجرا کن).")
