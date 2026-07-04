"""Tests for the new Task 026 ORM models + SQL migration.

Verifies:
- All 7 new ORM models can be imported
- The 05-beta-ops-tables.sql migration file exists and is valid
- The SQL migration contains the expected tables, indexes, and grants
- The ORM models match the SQL schema (column names, types, constraints)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("APP_ENV", "testing")

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
PROJECT_ROOT = BACKEND_DIR.parent                            # mastery-engine/
sys.path.insert(0, str(BACKEND_DIR))

INFRA_ROOT = PROJECT_ROOT / "infrastructure"


# ============================================================
# ORM model import tests
# ============================================================


class TestOrmModelsImportable:
    """Verify all 7 new ORM models can be imported."""

    def test_beta_feedback_vote_model_importable(self):
        from app.infrastructure.database.orm.beta_ops import BetaFeedbackVoteModel
        assert BetaFeedbackVoteModel.__tablename__ == "beta_feedback_votes"

    def test_beta_feedback_meta_model_importable(self):
        from app.infrastructure.database.orm.beta_ops import BetaFeedbackMetaModel
        assert BetaFeedbackMetaModel.__tablename__ == "beta_feedback_meta"

    def test_release_note_model_importable(self):
        from app.infrastructure.database.orm.beta_ops import ReleaseNoteModel
        assert ReleaseNoteModel.__tablename__ == "release_notes"

    def test_release_stage_model_importable(self):
        from app.infrastructure.database.orm.beta_ops import ReleaseStageModel
        assert ReleaseStageModel.__tablename__ == "release_stages"

    def test_experiment_model_importable(self):
        from app.infrastructure.database.orm.beta_ops import ExperimentModel
        assert ExperimentModel.__tablename__ == "experiments"

    def test_experiment_assignment_model_importable(self):
        from app.infrastructure.database.orm.beta_ops import ExperimentAssignmentModel
        assert ExperimentAssignmentModel.__tablename__ == "experiment_assignments"

    def test_experiment_result_model_importable(self):
        from app.infrastructure.database.orm.beta_ops import ExperimentResultModel
        assert ExperimentResultModel.__tablename__ == "experiment_results"

    def test_all_models_in___all__(self):
        from app.infrastructure.database.orm import beta_ops
        assert "BetaFeedbackVoteModel" in beta_ops.__all__
        assert "BetaFeedbackMetaModel" in beta_ops.__all__
        assert "ReleaseNoteModel" in beta_ops.__all__
        assert "ReleaseStageModel" in beta_ops.__all__
        assert "ExperimentModel" in beta_ops.__all__
        assert "ExperimentAssignmentModel" in beta_ops.__all__
        assert "ExperimentResultModel" in beta_ops.__all__


# ============================================================
# ORM schema tests
# ============================================================


class TestOrmSchemas:
    """Verify the ORM models declare the correct schema in their __table_args__.

    Note: the conftest strips schemas at runtime for SQLite compatibility, so
    we check the __table_args__ dict (the source of truth) rather than the
    runtime .schema attribute.
    """

    def _get_schema(self, model_cls):
        """Extract the schema from the model's __table_args__."""
        args = model_cls.__table_args__
        if isinstance(args, dict):
            return args.get("schema")
        # __table_args__ can be a tuple of (constraints..., dict)
        if isinstance(args, tuple) and args:
            last = args[-1]
            if isinstance(last, dict):
                return last.get("schema")
        return None

    def test_beta_feedback_votes_in_identity_schema(self):
        from app.infrastructure.database.orm.beta_ops import BetaFeedbackVoteModel
        assert self._get_schema(BetaFeedbackVoteModel) == "identity"

    def test_beta_feedback_meta_in_identity_schema(self):
        from app.infrastructure.database.orm.beta_ops import BetaFeedbackMetaModel
        assert self._get_schema(BetaFeedbackMetaModel) == "identity"

    def test_release_notes_in_administration_schema(self):
        from app.infrastructure.database.orm.beta_ops import ReleaseNoteModel
        assert self._get_schema(ReleaseNoteModel) == "administration"

    def test_release_stages_in_administration_schema(self):
        from app.infrastructure.database.orm.beta_ops import ReleaseStageModel
        assert self._get_schema(ReleaseStageModel) == "administration"

    def test_experiments_in_analytics_schema(self):
        from app.infrastructure.database.orm.beta_ops import ExperimentModel
        assert self._get_schema(ExperimentModel) == "analytics"

    def test_experiment_assignments_in_analytics_schema(self):
        from app.infrastructure.database.orm.beta_ops import ExperimentAssignmentModel
        assert self._get_schema(ExperimentAssignmentModel) == "analytics"

    def test_experiment_results_in_analytics_schema(self):
        from app.infrastructure.database.orm.beta_ops import ExperimentResultModel
        assert self._get_schema(ExperimentResultModel) == "analytics"


# ============================================================
# ORM column tests
# ============================================================


class TestOrmColumns:
    """Verify key columns exist on each model."""

    def test_beta_feedback_vote_has_vote_column(self):
        from app.infrastructure.database.orm.beta_ops import BetaFeedbackVoteModel
        assert "vote" in BetaFeedbackVoteModel.__table__.columns

    def test_beta_feedback_meta_has_priority_column(self):
        from app.infrastructure.database.orm.beta_ops import BetaFeedbackMetaModel
        assert "priority" in BetaFeedbackMetaModel.__table__.columns
        assert "roadmap_status" in BetaFeedbackMetaModel.__table__.columns
        assert "duplicate_of" in BetaFeedbackMetaModel.__table__.columns
        assert "tags" in BetaFeedbackMetaModel.__table__.columns

    def test_release_note_has_version_column(self):
        from app.infrastructure.database.orm.beta_ops import ReleaseNoteModel
        assert "version" in ReleaseNoteModel.__table__.columns
        assert "release_type" in ReleaseNoteModel.__table__.columns
        assert "feature_freeze" in ReleaseNoteModel.__table__.columns
        assert "published_at" in ReleaseNoteModel.__table__.columns
        assert "features" in ReleaseNoteModel.__table__.columns
        assert "bug_fixes" in ReleaseNoteModel.__table__.columns

    def test_release_stage_has_stage_column(self):
        from app.infrastructure.database.orm.beta_ops import ReleaseStageModel
        assert "stage" in ReleaseStageModel.__table__.columns
        assert "rollout_percentage" in ReleaseStageModel.__table__.columns

    def test_experiment_has_required_columns(self):
        from app.infrastructure.database.orm.beta_ops import ExperimentModel
        cols = ExperimentModel.__table__.columns
        assert "id" in cols
        assert "name" in cols
        assert "experiment_type" in cols
        assert "variant_a" in cols
        assert "variant_b" in cols
        assert "rollout_percentage" in cols
        assert "status" in cols
        assert "winner" in cols
        assert "min_sample_size" in cols

    def test_experiment_assignment_has_required_columns(self):
        from app.infrastructure.database.orm.beta_ops import ExperimentAssignmentModel
        cols = ExperimentAssignmentModel.__table__.columns
        assert "experiment_id" in cols
        assert "user_id" in cols
        assert "variant" in cols

    def test_experiment_result_has_required_columns(self):
        from app.infrastructure.database.orm.beta_ops import ExperimentResultModel
        cols = ExperimentResultModel.__table__.columns
        assert "experiment_id" in cols
        assert "variant" in cols
        assert "sample_size" in cols
        assert "metric_value" in cols
        assert "conversion_count" in cols


# ============================================================
# SQL migration tests
# ============================================================


class TestSqlMigration:
    """Tests for 05-beta-ops-tables.sql."""

    def test_migration_file_exists(self):
        path = INFRA_ROOT / "postgres" / "init" / "05-beta-ops-tables.sql"
        assert path.exists(), "05-beta-ops-tables.sql must exist"

    def test_migration_creates_feedback_votes_table(self):
        path = INFRA_ROOT / "postgres" / "init" / "05-beta-ops-tables.sql"
        content = path.read_text()
        assert "CREATE TABLE IF NOT EXISTS identity.beta_feedback_votes" in content
        assert "vote" in content
        assert "CHECK (vote IN (-1, 1))" in content

    def test_migration_creates_feedback_meta_table(self):
        path = INFRA_ROOT / "postgres" / "init" / "05-beta-ops-tables.sql"
        content = path.read_text()
        assert "CREATE TABLE IF NOT EXISTS identity.beta_feedback_meta" in content
        assert "priority" in content
        assert "roadmap_status" in content
        assert "duplicate_of" in content

    def test_migration_creates_release_notes_table(self):
        path = INFRA_ROOT / "postgres" / "init" / "05-beta-ops-tables.sql"
        content = path.read_text()
        assert "CREATE TABLE IF NOT EXISTS administration.release_notes" in content
        assert "version" in content
        assert "release_type" in content
        assert "feature_freeze" in content
        assert "features" in content

    def test_migration_creates_release_stages_table(self):
        path = INFRA_ROOT / "postgres" / "init" / "05-beta-ops-tables.sql"
        content = path.read_text()
        assert "CREATE TABLE IF NOT EXISTS administration.release_stages" in content
        assert "stage" in content
        assert "rollout_percentage" in content

    def test_migration_creates_experiments_table(self):
        path = INFRA_ROOT / "postgres" / "init" / "05-beta-ops-tables.sql"
        content = path.read_text()
        assert "CREATE TABLE IF NOT EXISTS analytics.experiments" in content
        assert "experiment_type" in content
        assert "variant_a" in content
        assert "variant_b" in content

    def test_migration_creates_experiment_assignments_table(self):
        path = INFRA_ROOT / "postgres" / "init" / "05-beta-ops-tables.sql"
        content = path.read_text()
        assert "CREATE TABLE IF NOT EXISTS analytics.experiment_assignments" in content

    def test_migration_creates_experiment_results_table(self):
        path = INFRA_ROOT / "postgres" / "init" / "05-beta-ops-tables.sql"
        content = path.read_text()
        assert "CREATE TABLE IF NOT EXISTS analytics.experiment_results" in content

    def test_migration_has_unique_vote_index(self):
        path = INFRA_ROOT / "postgres" / "init" / "05-beta-ops-tables.sql"
        content = path.read_text()
        assert "idx_beta_feedback_votes_unique" in content

    def test_migration_has_unique_assignment_index(self):
        path = INFRA_ROOT / "postgres" / "init" / "05-beta-ops-tables.sql"
        content = path.read_text()
        assert "idx_experiment_assignments_unique" in content

    def test_migration_has_grants(self):
        path = INFRA_ROOT / "postgres" / "init" / "05-beta-ops-tables.sql"
        content = path.read_text()
        assert "GRANT" in content
        assert "mastery" in content

    def test_migration_has_check_constraints(self):
        path = INFRA_ROOT / "postgres" / "init" / "05-beta-ops-tables.sql"
        content = path.read_text()
        # Release type check
        assert "release_type IN ('major', 'minor', 'patch', 'hotfix', 'beta')" in content
        # Stage check
        assert "stage IN ('planned', 'building', 'canary', 'staged', 'live', 'rolled_back', 'abandoned')" in content
        # Experiment type check
        assert "experiment_type IN ('ab', 'feature_rollout', 'recommendation', 'queue', 'explanation', 'ai_vs_rule')" in content

    def test_migration_uses_idempotent_statements(self):
        path = INFRA_ROOT / "postgres" / "init" / "05-beta-ops-tables.sql"
        content = path.read_text()
        # All CREATE TABLE statements should use IF NOT EXISTS
        import re
        create_statements = re.findall(r"CREATE TABLE\s+(?!IF NOT EXISTS)(\w+\.\w+)", content)
        assert not create_statements, f"Non-idempotent CREATE TABLE: {create_statements}"


# ============================================================
# Init script ordering
# ============================================================


class TestInitScriptOrdering:
    """Verify 05-beta-ops-tables.sql runs after 04-beta-tables.sql."""

    def test_05_runs_after_04(self):
        init_dir = INFRA_ROOT / "postgres" / "init"
        files = sorted(p.name for p in init_dir.glob("*.sql"))
        assert "04-beta-tables.sql" in files
        assert "05-beta-ops-tables.sql" in files
        idx_04 = files.index("04-beta-tables.sql")
        idx_05 = files.index("05-beta-ops-tables.sql")
        assert idx_05 > idx_04

    def test_05_is_last_init_script(self):
        init_dir = INFRA_ROOT / "postgres" / "init"
        files = sorted(p.name for p in init_dir.glob("*.sql"))
        assert files[-1] == "05-beta-ops-tables.sql"


# ============================================================
# Documentation tests
# ============================================================


class TestDocumentation:
    """Verify all 8 docs in docs/beta/ exist and are non-trivial."""

    def test_playbook_exists(self):
        path = PROJECT_ROOT / "docs" / "beta" / "closed-beta-playbook.md"
        assert path.exists()
        assert path.stat().st_size > 1000  # non-trivial

    def test_user_success_exists(self):
        path = PROJECT_ROOT / "docs" / "beta" / "user-success.md"
        assert path.exists()
        assert path.stat().st_size > 1000

    def test_analytics_guide_exists(self):
        path = PROJECT_ROOT / "docs" / "beta" / "analytics-guide.md"
        assert path.exists()
        assert path.stat().st_size > 1000

    def test_experimentation_exists(self):
        path = PROJECT_ROOT / "docs" / "beta" / "experimentation.md"
        assert path.exists()
        assert path.stat().st_size > 1000

    def test_release_management_exists(self):
        path = PROJECT_ROOT / "docs" / "beta" / "release-management.md"
        assert path.exists()
        assert path.stat().st_size > 1000

    def test_operations_handbook_exists(self):
        path = PROJECT_ROOT / "docs" / "beta" / "operations-handbook.md"
        assert path.exists()
        assert path.stat().st_size > 1000

    def test_support_playbook_exists(self):
        path = PROJECT_ROOT / "docs" / "beta" / "support-playbook.md"
        assert path.exists()
        assert path.stat().st_size > 1000

    def test_product_validation_exists(self):
        path = PROJECT_ROOT / "docs" / "beta" / "product-validation.md"
        assert path.exists()
        assert path.stat().st_size > 1000

    def test_all_8_docs_present(self):
        beta_docs_dir = PROJECT_ROOT / "docs" / "beta"
        all_docs = sorted(p.name for p in beta_docs_dir.glob("*.md"))
        # 3 pre-existing + 8 new = 11 total
        assert len(all_docs) >= 11
        expected = {
            "closed-beta-playbook.md",
            "user-success.md",
            "analytics-guide.md",
            "experimentation.md",
            "release-management.md",
            "operations-handbook.md",
            "support-playbook.md",
            "product-validation.md",
        }
        assert expected.issubset(set(all_docs))


# ============================================================
# Frontend files tests
# ============================================================


class TestFrontendFiles:
    """Verify the 10 beta-ops admin pages exist."""

    def test_dashboard_page_exists(self):
        path = PROJECT_ROOT / "frontend" / "app" / "(admin)" / "beta-ops" / "page.tsx"
        assert path.exists()

    def test_funnel_page_exists(self):
        path = PROJECT_ROOT / "frontend" / "app" / "(admin)" / "beta-ops" / "funnel" / "page.tsx"
        assert path.exists()

    def test_learning_page_exists(self):
        path = PROJECT_ROOT / "frontend" / "app" / "(admin)" / "beta-ops" / "learning" / "page.tsx"
        assert path.exists()

    def test_feedback_page_exists(self):
        path = PROJECT_ROOT / "frontend" / "app" / "(admin)" / "beta-ops" / "feedback" / "page.tsx"
        assert path.exists()

    def test_success_page_exists(self):
        path = PROJECT_ROOT / "frontend" / "app" / "(admin)" / "beta-ops" / "success" / "page.tsx"
        assert path.exists()

    def test_instructor_page_exists(self):
        path = PROJECT_ROOT / "frontend" / "app" / "(admin)" / "beta-ops" / "instructor" / "page.tsx"
        assert path.exists()

    def test_operations_page_exists(self):
        path = PROJECT_ROOT / "frontend" / "app" / "(admin)" / "beta-ops" / "operations" / "page.tsx"
        assert path.exists()

    def test_releases_page_exists(self):
        path = PROJECT_ROOT / "frontend" / "app" / "(admin)" / "beta-ops" / "releases" / "page.tsx"
        assert path.exists()

    def test_reports_page_exists(self):
        path = PROJECT_ROOT / "frontend" / "app" / "(admin)" / "beta-ops" / "reports" / "page.tsx"
        assert path.exists()

    def test_experiments_page_exists(self):
        path = PROJECT_ROOT / "frontend" / "app" / "(admin)" / "beta-ops" / "experiments" / "page.tsx"
        assert path.exists()

    def test_beta_ops_api_client_exists(self):
        path = PROJECT_ROOT / "frontend" / "lib" / "beta-ops-api.ts"
        assert path.exists()

    def test_beta_ops_hooks_exist(self):
        path = PROJECT_ROOT / "frontend" / "hooks" / "use-beta-ops.ts"
        assert path.exists()

    def test_admin_layout_has_beta_ops_nav(self):
        path = PROJECT_ROOT / "frontend" / "app" / "(admin)" / "layout.tsx"
        content = path.read_text()
        assert "BETA_OPS_NAV" in content
        assert "beta-ops" in content

    def test_all_frontend_pages_start_with_use_client(self):
        beta_ops_dir = PROJECT_ROOT / "frontend" / "app" / "(admin)" / "beta-ops"
        for page in beta_ops_dir.rglob("page.tsx"):
            content = page.read_text()
            assert content.startswith("'use client'") or content.startswith('"use client"'), \
                f"{page} must start with 'use client'"


# ============================================================
# Service module structure tests
# ============================================================


class TestServiceModuleStructure:
    """Verify the beta_ops service module is well-structured."""

    def test_service_module_exists(self):
        from app.application.beta_ops import service
        assert hasattr(service, "BetaOpsService")

    def test_service_module_exports_get_function(self):
        from app.application.beta_ops import service
        assert hasattr(service, "get_beta_ops_service")

    def test_service_module_exports_all_dataclasses(self):
        from app.application.beta_ops import service
        expected = [
            "BetaOpsDashboard", "FunnelStep", "RegistrationFunnel",
            "RetentionCohort", "LearningEffectiveness", "FeedbackItem",
            "FeedbackPlatformSummary", "UserSuccessSignal", "UserSuccessReport",
            "InstructorAnalytics", "OperationalHealth", "ReleaseNote",
            "ReleaseManagement", "BetaReport", "Experiment", "ExperimentResults",
        ]
        for name in expected:
            assert name in service.__all__, f"{name} missing from __all__"

    def test_service_has_all_10_part_methods(self):
        """Verify BetaOpsService has methods for all 10 parts."""
        from app.application.beta_ops import BetaOpsService
        methods = dir(BetaOpsService)
        # Part 1
        assert "get_dashboard" in methods
        # Part 2
        assert "get_registration_funnel" in methods
        assert "get_retention_cohorts" in methods
        # Part 3
        assert "get_learning_effectiveness" in methods
        # Part 4
        assert "get_feedback_platform" in methods
        # Part 5
        assert "get_user_success_report" in methods
        # Part 6
        assert "get_instructor_analytics" in methods
        # Part 7
        assert "get_operational_health" in methods
        # Part 8
        assert "get_release_management" in methods
        # Part 9
        assert "generate_report" in methods
        # Part 10
        assert "list_experiments" in methods
        assert "get_experiment_results" in methods
        assert "assign_variant" in methods
