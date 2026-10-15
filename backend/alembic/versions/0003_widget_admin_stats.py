"""widget key, top_k, position, user role, chat logs

Revision ID: 0003_widget_admin_stats
Revises: 0002_documents_settings
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_widget_admin_stats"
down_revision = "0002_documents_settings"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("role", sa.String(20), nullable=False, server_default="user"))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    op.add_column("settings", sa.Column("top_k", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("settings", sa.Column("widget_position", sa.String(20), nullable=False, server_default="bottom-left"))
    op.add_column("settings", sa.Column("widget_key", sa.String(64), nullable=True))
    op.add_column("settings", sa.Column("allowed_origins", sa.Text(), nullable=True))
    op.create_index("ix_settings_widget_key", "settings", ["widget_key"], unique=True)

    op.create_table(
        "chat_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("sources_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_chat_logs_id", "chat_logs", ["id"])
    op.create_index("ix_chat_logs_user_id", "chat_logs", ["user_id"])
    op.create_index("ix_chat_logs_created_at", "chat_logs", ["created_at"])


def downgrade():
    op.drop_table("chat_logs")
    op.drop_index("ix_settings_widget_key", table_name="settings")
    with op.batch_alter_table("settings") as b:
        b.drop_column("allowed_origins"); b.drop_column("widget_key")
        b.drop_column("widget_position"); b.drop_column("top_k")
    with op.batch_alter_table("users") as b:
        b.drop_column("is_active"); b.drop_column("role")
