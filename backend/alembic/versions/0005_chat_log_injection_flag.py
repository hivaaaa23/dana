"""prompt injection flag on chat logs

Revision ID: 0005_chat_log_injection_flag
Revises: 0004_chat_log_content
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_chat_log_injection_flag"
down_revision = "0004_chat_log_content"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("chat_logs", sa.Column("flagged", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("chat_logs", sa.Column("flag_reason", sa.String(40), nullable=True))
    op.create_index("ix_chat_logs_flagged", "chat_logs", ["flagged"])


def downgrade():
    op.drop_index("ix_chat_logs_flagged", table_name="chat_logs")
    with op.batch_alter_table("chat_logs") as b:
        b.drop_column("flag_reason")
        b.drop_column("flagged")
