import os
import tempfile
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_and_downgrade_on_clean_db():
    """Verify that Alembic migrations successfully build the full database schema from scratch

    and can roll back cleanly without touching the application's real database.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_file = os.path.join(tmpdir, "migration_verification.db")
        # Normalize Windows path for SQLite URI
        normalized_path = test_db_file.replace(os.sep, "/")
        test_db_url = f"sqlite:///{normalized_path}"

        # Initialize Alembic Config pointing to the temporary test DB
        ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"))
        assert os.path.exists(ini_path), f"alembic.ini must exist at {ini_path}"

        alembic_cfg = Config(ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

        # 1. Run migrations to head from a completely empty database
        command.upgrade(alembic_cfg, "head")

        # 2. Verify all tables exist and have expected structure
        engine = create_engine(test_db_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())

        expected_domain_tables = {
            "users",
            "projects",
            "project_scans",
            "project_files",
            "quality_analyses",
            "quality_issues",
            "security_analyses",
            "security_issues",
            "dependency_analyses",
            "project_dependencies",
            "architecture_analyses",
            "architecture_nodes",
            "architecture_edges",
            "health_analyses",
            "ai_explanations",
            "project_analysis_snapshots",
        }

        for table_name in expected_domain_tables:
            assert table_name in tables, f"Expected table '{table_name}' was not created by migrations"

        # Verify key user columns
        user_cols = {c["name"] for c in inspector.get_columns("users")}
        assert "id" in user_cols
        assert "email" in user_cols
        assert "password_hash" in user_cols
        assert "name" in user_cols

        # Verify key project columns
        project_cols = {c["name"] for c in inspector.get_columns("projects")}
        assert "user_id" in project_cols
        assert "source_type" in project_cols
        assert "status" in project_cols

        # Verify snapshot table columns
        snapshot_cols = {c["name"] for c in inspector.get_columns("project_analysis_snapshots")}
        assert "version_number" in snapshot_cols
        assert "overall_score" in snapshot_cols
        assert "technical_debt_hours" in snapshot_cols

        try:
            # 3. Test downgrade to base
            command.downgrade(alembic_cfg, "base")
            tables_after_downgrade = set(inspect(engine).get_table_names())

            # Domain tables should be removed
            for table_name in expected_domain_tables:
                assert table_name not in tables_after_downgrade, (
                    f"Table '{table_name}' should have been dropped on downgrade to base"
                )

            # 4. Re-upgrade to head to verify idempotent re-application
            command.upgrade(alembic_cfg, "head")
            tables_reup = set(inspect(engine).get_table_names())
            for table_name in expected_domain_tables:
                assert table_name in tables_reup, f"Table '{table_name}' missing after re-upgrade"
        finally:
            engine.dispose()
