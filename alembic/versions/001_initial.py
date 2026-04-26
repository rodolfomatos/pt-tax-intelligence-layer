"""Initial database schema

Revision ID: 001_initial
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Tax Decisions table
    op.create_table(
        'tax_decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('operation_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('amount', sa.Float, nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='EUR'),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('project_type', sa.String(50), nullable=False),
        sa.Column('activity_type', sa.String(50), nullable=False),
        sa.Column('location', sa.String(10), nullable=False),
        sa.Column('decision', sa.String(50), nullable=False),
        sa.Column('confidence', sa.Float, nullable=False),
        sa.Column('risk_level', sa.String(10), nullable=False),
        sa.Column('legal_version_timestamp', sa.String(50), nullable=False),
        sa.Column('legal_basis', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('explanation', sa.Text, nullable=False),
        sa.Column('risks', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('assumptions', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('required_followup', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('processing_time_ms', sa.Integer, nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB, nullable=True),
    )
    op.create_index('ix_tax_decisions_created_at', 'tax_decisions', ['created_at'])
    op.create_index('ix_tax_decisions_decision', 'tax_decisions', ['decision'])
    op.create_index('ix_tax_decisions_entity_type', 'tax_decisions', ['entity_type'])
    
    # Audit Logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', sa.String(100), nullable=True),
        sa.Column('user', sa.String(100), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('details', postgresql.JSONB, nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
    )
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    
    # Graph Nodes table
    op.create_table(
        'graph_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('node_type', sa.String(50), nullable=False),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('properties', postgresql.JSONB, nullable=True),
        sa.Column('gmif_type', sa.String(10), nullable=True),
        sa.Column('external_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_to', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_graph_nodes_type', 'graph_nodes', ['node_type'])
    op.create_index('ix_graph_nodes_gmif', 'graph_nodes', ['gmif_type'])
    
    # Graph Edges table
    op.create_table(
        'graph_edges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relation_type', sa.String(50), nullable=False),
        sa.Column('confidence', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_graph_edges_source', 'graph_edges', ['source_id'])
    op.create_index('ix_graph_edges_target', 'graph_edges', ['target_id'])
    
    # Contradictions table
    op.create_table(
        'contradictions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('claim_a', sa.Text, nullable=False),
        sa.Column('claim_b', sa.Text, nullable=False),
        sa.Column('context', sa.Text, nullable=True),
        sa.Column('severity', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('resolved', sa.Boolean, nullable=False, server_default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('contradictions')
    op.drop_table('graph_edges')
    op.drop_table('graph_nodes')
    op.drop_table('audit_logs')
    op.drop_table('tax_decisions')