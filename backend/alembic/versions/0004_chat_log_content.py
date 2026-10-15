"""optional encrypted chat content columns

Revision ID: 0004_chat_log_content
Revises: 0003_widget_admin_stats
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_chat_log_content"
down_revision = "0003_widget_admin_stats"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("chat_logs", sa.Column("question_enc", sa.Text(), nullable=True))
    op.add_column("chat_logs", sa.Column("answer_enc", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("chat_logs") as b:
        b.drop_column("answer_enc")
        b.drop_column("question_enc")
