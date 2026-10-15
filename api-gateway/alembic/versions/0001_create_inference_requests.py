"""create inference_requests table

Revision ID: 0001
Revises:
Create Date: 2026-01-01

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inference_requests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("model_name", sa.String(), nullable=False, index=True),
        sa.Column("request_status", sa.String(), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), index=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("prediction", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table("inference_requests")
