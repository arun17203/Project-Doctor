"""add_architecture_models

Revision ID: eaff71712afa
Revises: b0e3322f3b5b
Create Date: 2026-09-12 15:35:00.388650

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'eaff71712afa'
down_revision: Union[str, Sequence[str], None] = 'b0e3322f3b5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop legacy unused placeholder tables from Stage 1 if present
    # (they were empty placeholders with foreign keys to analyses.id)
    op.execute("DROP TABLE IF EXISTS architecture_edges")
    op.execute("DROP TABLE IF EXISTS architecture_nodes")

    # 2. Create architecture_analyses table
    op.create_table(
        'architecture_analyses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('scan_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('node_count', sa.Integer(), nullable=True, default=0),
        sa.Column('edge_count', sa.Integer(), nullable=True, default=0),
        sa.Column('cycle_count', sa.Integer(), nullable=True, default=0),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scan_id'], ['project_scans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_architecture_analyses_id'), 'architecture_analyses', ['id'], unique=False)
    op.create_index(op.f('ix_architecture_analyses_project_id'), 'architecture_analyses', ['project_id'], unique=False)
    op.create_index(op.f('ix_architecture_analyses_scan_id'), 'architecture_analyses', ['scan_id'], unique=False)

    # 3. Create architecture_nodes table
    op.create_table(
        'architecture_nodes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('analysis_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=True, default='Unknown'),
        sa.Column('layer', sa.String(length=50), nullable=True, default='Unknown'),
        sa.Column('node_type', sa.String(length=50), nullable=True, default='file'),
        sa.Column('directory', sa.String(length=255), nullable=True, default=''),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['architecture_analyses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_architecture_nodes_id'), 'architecture_nodes', ['id'], unique=False)
    op.create_index(op.f('ix_architecture_nodes_analysis_id'), 'architecture_nodes', ['analysis_id'], unique=False)
    op.create_index(op.f('ix_architecture_nodes_project_id'), 'architecture_nodes', ['project_id'], unique=False)
    op.create_index(op.f('ix_architecture_nodes_file_path'), 'architecture_nodes', ['file_path'], unique=False)
    op.create_index(op.f('ix_architecture_nodes_name'), 'architecture_nodes', ['name'], unique=False)
    op.create_index(op.f('ix_architecture_nodes_language'), 'architecture_nodes', ['language'], unique=False)
    op.create_index(op.f('ix_architecture_nodes_layer'), 'architecture_nodes', ['layer'], unique=False)
    op.create_index(op.f('ix_architecture_nodes_node_type'), 'architecture_nodes', ['node_type'], unique=False)
    op.create_index(op.f('ix_architecture_nodes_directory'), 'architecture_nodes', ['directory'], unique=False)

    # 4. Create architecture_edges table
    op.create_table(
        'architecture_edges',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('analysis_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('source_node_id', sa.String(length=36), nullable=False),
        sa.Column('target_node_id', sa.String(length=36), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=True, default='imports'),
        sa.Column('raw_import', sa.String(length=255), nullable=True),
        sa.Column('is_circular', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['architecture_analyses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_node_id'], ['architecture_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_node_id'], ['architecture_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_architecture_edges_id'), 'architecture_edges', ['id'], unique=False)
    op.create_index(op.f('ix_architecture_edges_analysis_id'), 'architecture_edges', ['analysis_id'], unique=False)
    op.create_index(op.f('ix_architecture_edges_project_id'), 'architecture_edges', ['project_id'], unique=False)
    op.create_index(op.f('ix_architecture_edges_source_node_id'), 'architecture_edges', ['source_node_id'], unique=False)
    op.create_index(op.f('ix_architecture_edges_target_node_id'), 'architecture_edges', ['target_node_id'], unique=False)
    op.create_index(op.f('ix_architecture_edges_relationship_type'), 'architecture_edges', ['relationship_type'], unique=False)
    op.create_index(op.f('ix_architecture_edges_is_circular'), 'architecture_edges', ['is_circular'], unique=False)


def downgrade() -> None:
    op.drop_table('architecture_edges')
    op.drop_table('architecture_nodes')
    op.drop_table('architecture_analyses')
