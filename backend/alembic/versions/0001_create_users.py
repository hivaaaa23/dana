from alembic import op
import sqlalchemy as sa
revision = "0001_create_users"
down_revision = None
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email", sa.String(320), nullable=False), sa.Column("password_hash", sa.String(512), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("api_key_encrypted", sa.String(4096), nullable=True))
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
def downgrade():
    op.drop_index("ix_users_email", table_name="users"); op.drop_index("ix_users_id", table_name="users"); op.drop_table("users")
