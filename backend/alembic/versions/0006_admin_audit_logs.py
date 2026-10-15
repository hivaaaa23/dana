"""admin audit logs (impersonation)

Revision ID: 0006_admin_audit_logs
Revises: 0005_chat_log_injection_flag
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_admin_audit_logs"
down_revision = "0005_chat_log_injection_flag"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("admin_email", sa.String(320), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("target_email", sa.String(320), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for col in ("id", "admin_id", "action", "target_user_id", "created_at"):
        op.create_index(f"ix_admin_audit_logs_{col}", "admin_audit_logs", [col])


def downgrade():
    op.drop_table("admin_audit_logs")
