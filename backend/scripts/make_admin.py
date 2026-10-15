"""استفاده: python scripts/make_admin.py user@example.com   (از داخل پوشه‌ی backend)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402

if len(sys.argv) != 2:
    sys.exit("usage: python scripts/make_admin.py <email>")
db = SessionLocal()
u = db.query(User).filter(User.email == sys.argv[1].lower()).first()
if not u:
    sys.exit("کاربری با این ایمیل پیدا نشد (اول ثبت‌نام کند).")
u.role = "admin"
db.commit()
print(f"{u.email} اکنون ادمین است.")
