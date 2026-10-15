# دانا — نسخه‌ی یکپارچه (بک‌اند نفر ۱ + RAG نفر ۲ + فرانت نفر ۳)

```
dana/
├── backend/    # FastAPI: auth + api-key (نفر ۱) + knowledge-base/chat/settings (نفر ۲)
└── frontend/   # صفحات HTML + js/ (اتصال به API) — توسط خود FastAPI سرو می‌شود
```

## اجرا
```bash
cd backend
pip install -r requirements.txt
python scripts/gen_env.py          # .env می‌سازد با SECRET_KEY و APP_ENCRYPTION_KEY تصادفی واقعی
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
python scripts/make_admin.py you@example.com   # (اختیاری) بعد از ثبت‌نام، حساب را ادمین کن
# یا ادمین اولیه خودکار: ADMIN_EMAIL و ADMIN_PASSWORD را در .env بگذار (یا python scripts/gen_env.py --admin-email you@example.com)
```
بعد بروید به <http://127.0.0.1:8000/login.html> (فرانت از همان سرور سرو می‌شود، پس CORS مشکلی نمی‌سازد).
مستندات API: <http://127.0.0.1:8000/docs>

## تست
```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest          # ۵۳ تست؛ دیتابیس/Chroma موقت و AI جعلی — به OpenAI وصل نمی‌شود
```

## مسیرهای API (واقعی)
| کار | مسیر |
|---|---|
| ثبت‌نام / ورود / من | `POST /auth/register` · `POST /auth/login` · `GET /auth/me` |
| API Key | `PUT/GET/DELETE /api-keys` |
| مخزن دانش | `GET/POST/DELETE /api/knowledge-base` · `GET/PUT/DELETE /api/knowledge-base/{id}` |
| تنظیمات | `GET/PUT /api/settings` · `POST /api/settings/test-connection` |
| آپلود فایل (TXT/MD/PDF/DOCX) | `POST /api/knowledge-base/upload` (multipart، فیلد `file`) |
| چت RAG / سرچ معنایی | `POST /api/chat` · `POST /api/chat/semantic-search` |
| آمار داشبورد | `GET /api/stats` |
| ویجت (عمومی، با کلید `gk_...`) | `GET /api/widget/config?key=` · `POST /api/widget/chat` |
| تعویض کلید ویجت | `POST /api/settings/widget-key/regenerate` |
| ادمین (فقط role=admin) | `GET /api/admin/stats` · `GET /api/admin/users` · `GET/PATCH /api/admin/users/{id}` · `GET /api/admin/logs` |

احراز هویت: هدر `Authorization: Bearer <token>` (توکن بعد از لاگین در `localStorage` با کلید `dana-token` ذخیره می‌شود؛ `frontend/js/api.js` خودش به همه‌ی درخواست‌ها اضافه‌اش می‌کند).

## تغییرات نسبت به فایل‌های تحویلی
**بک‌اند**
- `main.py`: routerهای نفر ۲ وصل شد (با alias برای `settings` چون با `app.config.settings` هم‌نام بود)، CORS و سرو فرانت اضافه شد؛ `/` به `/health` رفت.
- (فاز آخر) migration `0004_chat_log_content`، سرویس‌های `rate_limit` و `chat_log_service`، اسکریپت‌های `gen_env.py`/`preflight.py` و پوشه‌ی `tests/`.
- `models/__init__.py` و `alembic/env.py`: `Document` و `UserSettings` هم import می‌شوند؛ migration جدید `0002_documents_settings`.
- `alembic.ini` بخش logging نداشت و `alembic upgrade head` کرش می‌کرد → اضافه شد؛ `script.py.mako` هم اضافه شد.
- `config.py`: `CHROMA_PERSIST_DIR`, `CORS_ORIGINS`, `FRONTEND_DIR`. `requirements.txt`: `chromadb` و `email-validator` (برای `EmailStr`) اضافه شد.
- `PUT /api/knowledge-base/{id}`: اول embed می‌شود بعد بردارهای قدیمی پاک می‌شوند (قبلاً اگر embed شکست می‌خورد سند بی‌بردار می‌ماند)؛ تغییر فقط عنوان هم در Chroma هم‌گام می‌شود.
- اندپوینت جدید: `GET /api/knowledge-base/{id}` (متن کامل برای ویرایش) و `POST /api/settings/test-connection`.

**فرانت**
- `style.css` ← `style-fixed.css` + قوانین تعویض تب (ورود/ثبت‌نام و Playground که در CSS بازطراحی نبودند) + toast/modal.
- `js/` جدید: `api.js` (توکن، fetch، محافظ صفحه، toast)، `login.js`، `dashboard.js`، `knowledge_base.js`، `connection.js`، `settings.js`، `playground.js`.
- داده‌های نمایشی حذف شد؛ ستون «وضعیت» سند حذف شد (بک‌اند همزمان پردازش می‌کند)؛ لینک «پنل مدیریت» برداشته شد؛ صفحات ادمین (`admin_*.html`) در `frontend/` هستند و فقط با نقش admin کار می‌کنند.


## ویجت
کد Embed در صفحه‌ی «شخصی‌سازی و ویجت» ساخته می‌شود:
```html
<script src="https://YOUR-HOST/widget.js" data-key="gk_..." defer></script>
```
کلید عمومی فقط اجازه‌ی چت با مخزن همان کاربر را می‌دهد. چون کلید داخل HTML سایت مقصد دیده می‌شود،
در همان صفحه «دامنه‌های مجاز» را پر کنید. **در production تا وقتی این فیلد خالی باشد ویجت جواب نمی‌دهد (۴۰۳)**؛ در توسعه
خالی = همه (با `WIDGET_REQUIRE_ALLOWED_ORIGINS=1/0` می‌شود این رفتار را دستی عوض کرد). هر کلید روی هر IP
حداکثر ۲۰ پیام در دقیقه می‌تواند بزند (`WIDGET_RATE_LIMIT` / `WIDGET_RATE_WINDOW`).
خطای سرویس هوش مصنوعی عمداً به بیننده‌ی ویجت نشان داده نمی‌شود.

## Tailwind لوکال
CDN حذف شده و `frontend/tailwind.css` از قبل ساخته شده است. اگر کلاس جدیدی به HTML/JS اضافه کردید:
```bash
cd tailwind
npx tailwindcss@3 -c tailwind.config.js -i input.css -o ../frontend/tailwind.css --minify
```

## قبل از ارائه / production
```bash
cd backend
python scripts/gen_env.py --production --cors https://dana.example.com \
       --redis redis://localhost:6379/0 --proxies 1      # (--force اگر .env هست؛ کلیدهای فعلی حفظ می‌شود)
python -m alembic upgrade head
python scripts/preflight.py                               # چک‌لیست خودکار؛ مورد ✗ = کد خروج ۱
```
- `--production` مقدار `APP_ENV=production` و `CORS_ORIGINS` را می‌نویسد و آدرس خالی، `*`، `http://` یا آدرس با مسیر را رد می‌کند.
  در `APP_ENV=production` هم `SECRET_KEY` ضعیف، `CORS_ORIGINS=*` و `APP_ENCRYPTION_KEY` نامعتبر باعث توقف اجرا می‌شوند.
- `--proxies N`: تعداد reverse proxy جلوی برنامه (nginx، Cloudflare…). اگر ۰ بماند و پشت proxy باشید، همه‌ی بینندگان
  یک IP دیده می‌شوند و rate limit برای همه مشترک می‌شود.
- **«دامنه‌های مجاز» ویجت را هر کاربر در صفحه‌ی «شخصی‌سازی و ویجت» پر می‌کند** (کلید ویجت در HTML سایت‌ها دیده می‌شود).
  `preflight.py` کاربرانی که پر نکرده‌اند را فهرست می‌کند.
- فونت Vazirmatn: سه فایل `.woff2` را طبق `frontend/fonts/README.md` در `frontend/fonts/` بگذارید (در zip نیستند).

## Rate limit ویجت و Redis
با `REDIS_URL` شمارنده‌ها بین همه‌ی workerها و سرورها مشترک است (پنجره‌ی ثابت، کلید = کلید ویجت + IP، با TTL).
بدون `REDIS_URL` شمارنده در حافظه‌ی همان پروسه است (برای توسعه/تک‌worker). اگر Redis قطع شود ویجت از کار نمی‌افتد:
تا ۳۰ ثانیه به شمارنده‌ی حافظه برمی‌گردد و هشدار لاگ می‌شود. در production بدون `REDIS_URL` هنگام استارت هشدار می‌دهد.

## لاگ مکالمات و حریم خصوصی (تصمیم تیم)
**پیش‌فرض: فقط متادیتا** (زمان، منبع، موفق/ناموفق، تعداد منبع)؛ متن پیام‌ها ذخیره نمی‌شود.
اگر تیم تصمیم گرفت متن هم لازم است، در `.env`:
```
LOG_CHAT_CONTENT=1
LOG_RETENTION_DAYS=30        # در production با روشن بودن متن، مقدار مثبت اجباری است
LOG_CONTENT_MAX_CHARS=2000   # متن بلندتر بریده می‌شود
```
- سوال و پاسخ با `APP_ENCRYPTION_KEY` رمزنگاری می‌شوند (در دیتابیس متن خام نیست)؛ فقط ادمین از `GET /api/admin/logs` می‌خواند.
  اگر `APP_ENCRYPTION_KEY` عوض شود متن‌های قبلی خوانا نمی‌مانند.
- لاگ‌های قدیمی‌تر از `LOG_RETENTION_DAYS` هنگام استارت و حداکثر ساعتی یک بار پاک می‌شوند.
- این سوال‌ها از بینندگان عمومی سایت‌هاست؛ قبل از روشن کردن، متن حریم خصوصی/اطلاع‌رسانی به آن‌ها لازم است (تصمیم حقوقی، نه فنی).

## هنوز نشده
- ادمین: «ورود به جای کاربر» و ویرایش System Prompt کاربر (بک‌اند ندارند و از صفحه‌ها حذف شدند).
- تشخیص Prompt Injection فقط قاعده‌محور است (الگوهای فارسی/انگلیسی در `services/injection_guard.py`)؛ حملات خلاقانه یا غیرمستقیم (از داخل اسناد) را نمی‌گیرد. حالت با `PROMPT_INJECTION_MODE=off|log|block` تنظیم می‌شود و مکالمات مشکوک در «گزارش و امنیت» با فیلتر جدا دیده می‌شوند.
- تست‌ها فقط بک‌اند را می‌پوشانند (`backend/tests`)؛ فرانت‌اند و OCR واقعی (tesseract) تست خودکار ندارند.
- Rate limit با Redis روی `fakeredis` تست شده، نه روی یک سرور Redis واقعی؛ قبل از ارائه یک بار با Redis واقعی امتحان کنید (`preflight.py` اتصال را چک می‌کند).

## OCR برای PDF اسکن‌شده
اگر PDF لایه‌ی متن نداشته باشد، سرور خودش OCR می‌زند (حداکثر ۲۰ صفحه). پیش‌نیاز روی سرور:
```bash
sudo apt install tesseract-ocr tesseract-ocr-fas      # فارسی؛ روی ویندوز: نصب Tesseract + فایل fas.traineddata
```
متغیرهای اختیاری `.env`: `OCR_ENABLED=0` (خاموش)، `OCR_LANGS=fas+eng`، `OCR_MAX_PAGES=20`.
اگر tesseract نصب نباشد، آپلود PDF اسکن‌شده خطای روشن می‌دهد و بقیه‌ی قابلیت‌ها سالم می‌مانند.
دقت OCR فارسی را حتماً با چند PDF واقعی خودتان بسنجید.
