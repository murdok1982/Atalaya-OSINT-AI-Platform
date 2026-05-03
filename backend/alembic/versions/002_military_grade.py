"""add military-grade fields

Revision ID: 002_military_grade
Revises: 001_initial
Create Date: 2026-05-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_military_grade"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("classification", sa.String(32), nullable=False, server_default="UNCLASSIFIED"))
    op.add_column("users", sa.Column("tenant_id", sa.String(64), nullable=False, server_default="default"))
    op.add_column("users", sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("department", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("clearance_level", sa.String(32), nullable=True))

    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    op.create_table(
        "token_blacklist",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("jti", sa.String(256), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("token_type", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_by", sa.String(36), nullable=True),
        sa.Column("reason", sa.String(256), nullable=True),
    )

    op.create_table(
        "audit_chain",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("index", sa.Integer(), nullable=False, index=True),
        sa.Column("timestamp", sa.Float(), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("resource", sa.String(256), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("previous_hash", sa.String(256), nullable=False),
        sa.Column("hash", sa.String(256), nullable=False, index=True),
    )

    op.create_table(
        "chain_of_custody",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("evidence_id", sa.String(36), nullable=False, index=True),
        sa.Column("evidence_hash", sa.String(256), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_by", sa.String(36), nullable=False),
        sa.Column("custody_chain", sa.JSON(), nullable=True),
        sa.Column("integrity_verified", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_verification", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "intelligence_fusion",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("fusion_id", sa.String(128), nullable=False, index=True),
        sa.Column("target", sa.String(256), nullable=False),
        sa.Column("timestamp", sa.Float(), nullable=False),
        sa.Column("input_sources", sa.JSON(), nullable=True),
        sa.Column("correlated_entities", sa.JSON(), nullable=True),
        sa.Column("relationships_found", sa.JSON(), nullable=True),
        sa.Column("threat_assessment", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=True),
        sa.Column("graph_data", sa.JSON(), nullable=True),
        sa.Column("classification", sa.String(32), nullable=False, server_default="UNCLASSIFIED"),
    )

    op.create_table(
        "stix_objects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("stix_id", sa.String(128), nullable=False, index=True),
        sa.Column("stix_type", sa.String(64), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("labels", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified", sa.DateTime(timezone=True), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=True),
        sa.Column("kill_chain_phases", sa.JSON(), nullable=True),
        sa.Column("external_references", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("stix_objects")
    op.drop_table("intelligence_fusion")
    op.drop_table("chain_of_custody")
    op.drop_table("audit_chain")
    op.drop_table("token_blacklist")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_column("users", "clearance_level")
    op.drop_column("users", "department")
    op.drop_column("users", "phone")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "tenant_id")
    op.drop_column("users", "classification")
