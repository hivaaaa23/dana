# همه‌ی مدل‌ها باید اینجا import شوند تا Base.metadata و Alembic آن‌ها را ببینند
from app.models.user import User
from app.models.document import Document
from app.models.settings import UserSettings
from app.models.chat_log import ChatLog
from app.models.audit_log import AdminAuditLog

__all__ = ["User", "Document", "UserSettings", "ChatLog", "AdminAuditLog"]
