"""initial tenant support schema"""
import sqlalchemy as sa

from alembic import op

revision = "0001_initial"
down_revision = None


def upgrade():
    status = sa.Enum("open", "resolved", "escalated", name="conversationstatus")
    op.create_table("tenants", sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("slug", sa.String(80), nullable=False, unique=True), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("users", sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False), sa.Column("email", sa.String(320), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.UniqueConstraint("tenant_id", "email"))
    op.create_table("documents", sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False), sa.Column("filename", sa.String(255), nullable=False), sa.Column("content_type", sa.String(100), nullable=False), sa.Column("chunk_count", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("conversations", sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False), sa.Column("customer_email", sa.String(320)), sa.Column("status", status, nullable=False), sa.Column("escalation_reason", sa.Text()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_table("messages", sa.Column("id", sa.String(36), primary_key=True), sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id"), nullable=False), sa.Column("role", sa.String(20), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("decision", sa.String(20)), sa.Column("sources", sa.Text()), sa.Column("created_at", sa.DateTime(), nullable=False))
    for table, columns in {"tenants": ["slug"], "users": ["tenant_id", "email"], "documents": ["tenant_id"], "conversations": ["tenant_id", "status"], "messages": ["conversation_id"]}.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade():
    for table in ("messages", "conversations", "documents", "users", "tenants"):
        op.drop_table(table)
    sa.Enum(name="conversationstatus").drop(op.get_bind(), checkfirst=True)
