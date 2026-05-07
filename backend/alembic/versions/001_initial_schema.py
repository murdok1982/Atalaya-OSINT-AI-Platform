"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('username', sa.String(64), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('scopes', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_ip', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
    )

    op.create_table(
        'cases',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='OPEN'),
        sa.Column('priority', sa.String(16), nullable=False, server_default='MEDIUM'),
        sa.Column('classification', sa.String(32), nullable=False, server_default='UNCLASSIFIED'),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('operator_id', sa.String(36), nullable=True),
        sa.Column('scope_notes', sa.Text(), nullable=True),
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'entities',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('case_id', sa.String(36), nullable=False),
        sa.Column('entity_type', sa.String(32), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('label', sa.String(255), nullable=True),
        sa.Column('source', sa.String(255), nullable=True),
        sa.Column('attributes', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('is_target', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('merged_into_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['merged_into_id'], ['entities.id']),
    )
    op.create_index('ix_entities_case_id', 'entities', ['case_id'])
    op.create_index('ix_entities_type_value', 'entities', ['entity_type', 'value'])

    op.create_table(
        'evidence',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('case_id', sa.String(36), nullable=False),
        sa.Column('entity_id', sa.String(36), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('evidence_type', sa.String(32), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('source_name', sa.String(255), nullable=True),
        sa.Column('content_text', sa.Text(), nullable=True),
        sa.Column('content_file_path', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('collected_by', sa.String(36), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('is_sensitive', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('raw_data', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_evidence_case_id', 'evidence', ['case_id'])
    op.create_index('ix_evidence_hash', 'evidence', ['content_hash'])

    op.create_table(
        'jobs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('case_id', sa.String(36), nullable=True),
        sa.Column('job_type', sa.String(32), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='PENDING'),
        sa.Column('arq_job_id', sa.String(255), nullable=True),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('task_description', sa.Text(), nullable=True),
        sa.Column('agent_plan', postgresql.JSONB(), nullable=True),
        sa.Column('result_summary', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('findings_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('input_params', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('output_refs', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_jobs_case_id', 'jobs', ['case_id'])
    op.create_index('ix_jobs_status', 'jobs', ['status'])

    op.create_table(
        'reports',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('case_id', sa.String(36), nullable=True),
        sa.Column('job_id', sa.String(36), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('report_type', sa.String(32), nullable=False),
        sa.Column('format', sa.String(16), nullable=False, server_default='MARKDOWN'),
        sa.Column('status', sa.String(16), nullable=False, server_default='PENDING'),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('generated_by', sa.String(36), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('entity_ids', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='SET NULL'),
    )

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('user_id', sa.String(128), nullable=False, server_default=''),
        sa.Column('username', sa.String(64), nullable=False, server_default=''),
        sa.Column('action', sa.String(32), nullable=False),
        sa.Column('resource_type', sa.String(64), nullable=False),
        sa.Column('resource_id', sa.String(128), nullable=False, server_default=''),
        sa.Column('details', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('ip_address', sa.String(64), nullable=False, server_default=''),
        sa.Column('user_agent', sa.Text(), nullable=False, server_default=''),
        sa.Column('request_id', sa.String(64), nullable=False, server_default=''),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=False, server_default=''),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('reports')
    op.drop_table('jobs')
    op.drop_table('evidence')
    op.drop_table('entities')
    op.drop_table('cases')
    op.drop_table('users')
