"""Update schema to match current models

Revision ID: 002_update
Revises: 001_initial
Create Date: 2025-01-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002_update'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # 1. tax_decisions: alter nullable for optional fields
    op.alter_column('tax_decisions', 'project_type', existing_type=sa.String(20), nullable=True)
    op.alter_column('tax_decisions', 'activity_type', existing_type=sa.String(20), nullable=True)
    op.alter_column('tax_decisions', 'location', existing_type=sa.String(10), nullable=True)
    
    # 2. tax_decisions: add composite indexes
    op.create_index('ix_tax_decisions_created_decision', 'tax_decisions', ['created_at', 'decision'])
    op.create_index('ix_tax_decisions_project_type', 'tax_decisions', ['project_type'])
    
    # 3. audit_logs: change entity_id to UUID
    op.alter_column('audit_logs', 'entity_id', existing_type=sa.String(100), type_=postgresql.UUID(as_uuid=True), postgresql_using='entity_id::uuid')
    # Also drop old indexes and create new composite ones
    op.drop_index('ix_audit_logs_timestamp', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.create_index('ix_audit_logs_timestamp_action', 'audit_logs', ['timestamp', 'action'])
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])
    
    # 4. graph_nodes: change gmif_type length to 2
    op.alter_column('graph_nodes', 'gmif_type', existing_type=sa.String(10), type_=sa.String(2))
    # Add new indexes
    op.create_index('ix_graph_nodes_type_label', 'graph_nodes', ['node_type', 'label'])
    op.create_index('ix_graph_nodes_external_id', 'graph_nodes', ['external_id'])
    
    # 5. graph_edges: add missing columns
    op.add_column('graph_edges', sa.Column('source_file', sa.String(200), nullable=True))
    op.add_column('graph_edges', sa.Column('source_location', sa.String(100), nullable=True))
    op.add_column('graph_edges', sa.Column('evidence_type', sa.String(20), nullable=False, server_default='EXTRACTED'))
    op.add_column('graph_edges', sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True))
    op.add_column('graph_edges', sa.Column('valid_to', sa.DateTime(timezone=True), nullable=True))
    
    # 6. contradictions: change context to JSONB
    op.alter_column('contradictions', 'context', existing_type=sa.Text, type_=postgresql.JSONB(), postgresql_using='context::jsonb')
    # Add indexes
    op.create_index('ix_contradictions_claims', 'contradictions', ['claim_a', 'claim_b'])
    op.create_index('ix_contradictions_resolved', 'contradictions', ['resolved'])


def downgrade():
    # 6. contradictions: drop indexes and revert context
    op.drop_index('ix_contradictions_resolved', table_name='contradictions')
    op.drop_index('ix_contradictions_claims', table_name='contradictions')
    op.alter_column('contradictions', 'context', existing_type=postgresql.JSONB(), type_=sa.Text, postgresql_using='context::text')
    
    # 5. graph_edges: drop columns
    op.drop_column('graph_edges', 'valid_to')
    op.drop_column('graph_edges', 'valid_from')
    op.drop_column('graph_edges', 'evidence_type')
    op.drop_column('graph_edges', 'source_location')
    op.drop_column('graph_edges', 'source_file')
    
    # 4. graph_nodes: drop indexes and revert gmif_type
    op.drop_index('ix_graph_nodes_external_id', table_name='graph_nodes')
    op.drop_index('ix_graph_nodes_type_label', table_name='graph_nodes')
    op.alter_column('graph_nodes', 'gmif_type', existing_type=sa.String(2), type_=sa.String(10))
    
    # 3. audit_logs: revert entity_id and indexes
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_index('ix_audit_logs_timestamp_action', table_name='audit_logs')
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.alter_column('audit_logs', 'entity_id', existing_type=postgresql.UUID(as_uuid=True), type_=sa.String(100))
    
    # 1. tax_decisions: drop indexes and revert nullable
    op.drop_index('ix_tax_decisions_project_type', table_name='tax_decisions')
    op.drop_index('ix_tax_decisions_created_decision', table_name='tax_decisions')
    op.alter_column('tax_decisions', 'location', existing_type=sa.String(10), nullable=False)
    op.alter_column('tax_decisions', 'activity_type', existing_type=sa.String(20), nullable=False)
    op.alter_column('tax_decisions', 'project_type', existing_type=sa.String(20), nullable=False)
