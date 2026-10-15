# Rakan Chat — Person 1

Implementation of the Person 1 checklist: FastAPI skeleton, environment config, SQLite/SQLAlchemy, Alembic, users, hashed passwords, JWT authentication, current-user dependency, and encrypted API-key storage.

## Setup
1. Create `.env` from `.env.example`.
2. Generate `APP_ENCRYPTION_KEY`:
   `py -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
3. Install: `py -m pip install -r requirements.txt`
4. Migrate: `py -m alembic upgrade head`
5. Run: `py -m uvicorn app.main:app --reload`
6. Open `http://127.0.0.1:8000/docs`.

Never commit `.env`.

### Endpoints
- POST `/auth/register`
- POST `/auth/login`
- GET `/auth/me`
- PUT `/api-keys`
- GET `/api-keys` (status only; raw key is never returned)
- DELETE `/api-keys`

### Team integration
The checklist requires every user-owned data table (documents, settings, chat history) to contain a user identifier and every query to be filtered by the authenticated user. Persons 2 and 3 must integrate with `get_current_user` and preserve those per-user boundaries.

### Production، rate limit، لاگ و تست
جزئیات کامل در `../README.md`. خلاصه:
- `python scripts/gen_env.py --production --cors https://... [--redis redis://...] [--proxies N]` سپس `python scripts/preflight.py`
- `REDIS_URL` برای rate limit مشترک بین workerها؛ `LOG_CHAT_CONTENT` / `LOG_RETENTION_DAYS` برای لاگ متن مکالمات (پیش‌فرض خاموش)
- `pip install -r requirements-dev.txt && python -m pytest`
