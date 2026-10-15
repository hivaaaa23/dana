import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.config import settings
# نکته: routers.settings با settings بالا هم‌نام است، پس alias می‌گیریم
from app.routers import admin, api_keys, auth, chat, knowledge_base, stats, widget
from app.routers import settings as settings_router

log = logging.getLogger("dana")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.APP_ENV == "production" and not settings.REDIS_URL:
        log.warning("REDIS_URL ست نشده: rate limit ویجت per-process است و با چند worker مشترک نیست.")
    if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
        from app.database import SessionLocal
        from app.services import bootstrap_admin
        with SessionLocal() as db:
            bootstrap_admin.ensure_admin(db)
    if settings.LOG_RETENTION_DAYS > 0:
        from app.database import SessionLocal
        from app.services import chat_log_service
        with SessionLocal() as db:
            chat_log_service.purge_old(db, force=True)
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    # توکن در هدر Authorization می‌آید نه کوکی، پس credentials لازم نیست
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def public_widget_cors(request: Request, call_next):
    """ویجت روی هر سایتی نشسته؛ فقط مسیرهای عمومی ویجت CORS باز دارند (نه بقیه‌ی API).
    کنترل دامنه با allowed_origins در خود اندپوینت انجام می‌شود."""
    if not (request.url.path.startswith("/api/widget/") or request.url.path == "/widget.js"):
        return await call_next(request)
    if request.method == "OPTIONS":
        resp = Response(status_code=204)
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Max-Age"] = "600"
    else:
        resp = await call_next(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


app.include_router(auth.router)
app.include_router(api_keys.router)
app.include_router(knowledge_base.router)
app.include_router(chat.router)
app.include_router(settings_router.router)
app.include_router(stats.router)
app.include_router(widget.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"message": "Dana API is running"}


# فرانت‌اند استاتیک (بعد از همه‌ی routerها mount می‌شود تا مسیرهای API را نپوشاند)
_frontend = Path(settings.FRONTEND_DIR)
if not _frontend.is_absolute():
    _frontend = (Path(__file__).resolve().parent.parent / _frontend).resolve()
if _frontend.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")
