"""Pytest fixtures for the Beta Operations Platform tests (Task 026).

Provides an in-memory SQLite database with all ORM tables created,
including the new Task 026 tables (feedback votes, release notes,
experiments, experiment assignments, experiment results).
"""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone as tz_utc
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Ensure backend/ is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Set test environment variables BEFORE importing app modules
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ARGON2_MEMORY_COST", "1024")
os.environ.setdefault("ARGON2_TIME_COST", "1")
os.environ.setdefault("ARGON2_PARALLELISM", "1")

# Now import app modules
from app.infrastructure.database.orm.base import Base  # noqa: E402
from app.infrastructure.database.orm.beta import (  # noqa: E402
    BetaEventModel,
    BetaFeedbackModel,
    BetaInviteModel,
)
from app.infrastructure.database.orm.beta_ops import (  # noqa: E402
    BetaFeedbackMetaModel,
    BetaFeedbackVoteModel,
    ExperimentAssignmentModel,
    ExperimentModel,
    ExperimentResultModel,
    ReleaseNoteModel,
    ReleaseStageModel,
)
from app.infrastructure.database.orm.background import (  # noqa: E402
    DeadLetterEventModel,
    EmailDeliveryLogModel,
    NotificationModel,
    ScheduledJobModel,
    WorkerHeartbeatModel,
)
from app.infrastructure.database.orm.content import (  # noqa: E402
    ConceptModel,
    SubjectModel,
)
from app.infrastructure.database.orm.core import (  # noqa: E402
    AttemptModel,
    LearnerEnrollmentModel,
    MasteryScoreModel,
    OutboxEventModel,
    QuestionInstanceModel,
    ReviewModel,
    StudySessionModel,
)
from app.infrastructure.database.orm.identity import (  # noqa: E402
    SessionModel,
    UserCredentialModel,
    UserModel,
    UserProfileModel,
)


# ============================================================
# SQLite type patching (mirror the auth conftest pattern)
# ============================================================


@pytest.fixture(scope="session")
def _patch_sqlite_types():
    """Patch SQLite to support PostgreSQL-specific types."""
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

    def _visit_JSONB(self, type_, **kw):
        return "JSON"

    def _visit_UUID(self, type_, **kw):
        return "CHAR(36)"

    def _visit_INET(self, type_, **kw):
        return "VARCHAR(45)"  # IPv6 max length

    SQLiteTypeCompiler.visit_JSONB = _visit_JSONB
    SQLiteTypeCompiler.visit_UUID = _visit_UUID
    SQLiteTypeCompiler.visit_INET = _visit_INET

    # Strip schemas from all tables (SQLite doesn't support them).
    for table in list(Base.metadata.tables.values()):
        table.schema = None

    yield


@pytest_asyncio.fixture
async def test_engine(_patch_sqlite_types):
    """Create an in-memory SQLite engine with all tables."""
    import uuid

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Register SQLite functions for gen_random_uuid(), now(), date_trunc()
    # so that ORM server_defaults + analytics queries work on SQLite.
    def _date_trunc(unit, timestamp_str):
        """SQLite implementation of PostgreSQL's date_trunc(unit, timestamp)."""
        if timestamp_str is None:
            return None
        # Parse ISO format timestamp
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
        if unit == "week":
            # Truncate to Monday of the week
            monday = dt - timedelta(days=dt.weekday())
            return monday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif unit == "day":
            return dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif unit == "hour":
            return dt.replace(minute=0, second=0, microsecond=0).isoformat()
        elif unit == "month":
            return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif unit == "year":
            return dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        return timestamp_str

    @event.listens_for(engine.sync_engine, "connect")
    def _register_functions(dbapi_conn, connection_record):
        dbapi_conn.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))
        dbapi_conn.create_function("now", 0, lambda: datetime.now(tz_utc.utc).isoformat())
        dbapi_conn.create_function("current_timestamp", 0, lambda: datetime.now(tz_utc.utc).isoformat())
        dbapi_conn.create_function("date_trunc", 2, _date_trunc)

    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            import logging
            logging.warning(f"create_all failed: {e}; trying one-by-one")
            from sqlalchemy.schema import CreateTable
            for table in Base.metadata.sorted_tables:
                try:
                    await conn.execute(CreateTable(table, if_not_exists=True))
                except Exception as te:
                    logging.warning(f"Failed to create {table.name}: {te}")

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(test_engine):
    """Create a session factory bound to the test engine."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def session(test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with test_session_factory() as session:
        yield session


# ============================================================
# Data seeding fixtures
# ============================================================


def _utcnow() -> datetime:
    return datetime.now(tz_utc.utc)


@pytest_asyncio.fixture
async def seeded_users(session: AsyncSession):
    """Seed 10 users: 5 verified, 3 unverified, 2 admin."""
    users = []
    now = _utcnow()

    # 5 verified regular users
    for i in range(5):
        u = UserModel(
            id=uuid4(),
            email=f"user{i+1}@example.com",
            email_verified_at=now - timedelta(days=10),
            status="active",
            role="learner",
            created_at=now - timedelta(days=10),
            last_login_at=now - timedelta(days=i),
        )
        session.add(u)
        users.append(u)

    # 3 unverified users
    for i in range(3):
        u = UserModel(
            id=uuid4(),
            email=f"unverified{i+1}@example.com",
            email_verified_at=None,
            status="pending_verification",
            role="learner",
            created_at=now - timedelta(days=i + 1),
        )
        session.add(u)
        users.append(u)

    # 2 admin users
    for i in range(2):
        u = UserModel(
            id=uuid4(),
            email=f"admin{i+1}@example.com",
            email_verified_at=now - timedelta(days=30),
            status="active",
            role="administrator",
            created_at=now - timedelta(days=30),
            last_login_at=now - timedelta(hours=i),
        )
        session.add(u)
        users.append(u)

    await session.commit()
    return users


@pytest_asyncio.fixture
async def seeded_invites(session: AsyncSession, seeded_users):
    """Seed 15 invites: 10 used, 5 unused."""
    admin = next(u for u in seeded_users if u.role == "administrator")
    now = _utcnow()
    invites = []
    for i in range(10):
        inv = BetaInviteModel(
            id=uuid4(),
            email=f"invited{i+1}@example.com",
            invite_token=f"token_{i}",
            expires_at=now + timedelta(days=7),
            used_at=now - timedelta(days=5),
            created_by=admin.id,
            notes=f"Invite {i}",
            created_at=now - timedelta(days=10),
        )
        session.add(inv)
        invites.append(inv)
    for i in range(5):
        inv = BetaInviteModel(
            id=uuid4(),
            email=f"unused{i+1}@example.com",
            invite_token=f"unused_token_{i}",
            expires_at=now + timedelta(days=7),
            used_at=None,
            created_by=admin.id,
            created_at=now - timedelta(days=2),
        )
        session.add(inv)
        invites.append(inv)
    await session.commit()
    return invites


@pytest_asyncio.fixture
async def seeded_feedback(session: AsyncSession, seeded_users):
    """Seed 12 feedback items: 4 bugs, 3 feature_requests, 3 ui_ux, 2 content."""
    users = [u for u in seeded_users if u.role == "learner"]
    now = _utcnow()
    feedback_items = []

    categories = ["bug", "bug", "bug", "bug",
                  "feature_request", "feature_request", "feature_request",
                  "ui_ux", "ui_ux", "ui_ux",
                  "content", "content"]
    ratings = [1, 2, 3, 5, 4, 5, 5, 3, 4, 5, 4, 5]
    comments = [
        "Login button doesn't work on mobile",
        "App crashes when I submit a code question",
        "Slow response on dashboard page",
        "Great platform, minor bug in profile",
        "Would love dark mode",
        "Add Python asyncio questions please",
        "Feature request: study streaks",
        "The study session layout is confusing",
        "Color contrast on buttons is low",
        "Mobile layout needs improvement",
        "The explanation for async/await is unclear",
        "Question about decorators was excellent",
    ]

    for i, (cat, rating, comment) in enumerate(zip(categories, ratings, comments)):
        f = BetaFeedbackModel(
            id=uuid4(),
            user_id=users[i % len(users)].id,
            rating=rating,
            category=cat,
            comment=comment,
            status="open",
            created_at=now - timedelta(days=i),
        )
        session.add(f)
        feedback_items.append(f)
    await session.commit()
    return feedback_items


@pytest_asyncio.fixture
async def seeded_beta_events(session: AsyncSession, seeded_users):
    """Seed beta_events: ~5 events per active user over the last 7 days."""
    users = [u for u in seeded_users if u.role == "learner"]
    now = _utcnow()
    events = []

    event_types = [
        "welcome_wizard_completed", "study_session_started", "question_answered",
        "recommendation_offered", "recommendation_accepted",
    ]

    for i, user in enumerate(users):
        # 5 events per user, spread over the last 7 days
        for j in range(5):
            e = BetaEventModel(
                id=uuid4(),
                user_id=user.id,
                event_type=event_types[j % len(event_types)],
                event_data={"session_id": str(uuid4())},
                created_at=now - timedelta(days=j, hours=i),
            )
            session.add(e)
            events.append(e)
    await session.commit()
    return events


@pytest_asyncio.fixture
async def seeded_enrollments(session: AsyncSession, seeded_users):
    """Seed enrollments for the 5 verified learners."""
    users = [u for u in seeded_users if u.role == "learner" and u.email_verified_at is not None]
    subject_id = uuid4()
    enrollments = []
    now = _utcnow()
    for u in users:
        e = LearnerEnrollmentModel(
            id=uuid4(),
            user_id=u.id,
            subject_id=subject_id,
            status="active",
            enrolled_at=now - timedelta(days=8),
            last_active_at=now - timedelta(days=1),
        )
        session.add(e)
        enrollments.append(e)
    await session.commit()
    return enrollments


@pytest_asyncio.fixture
async def seeded_study_sessions(session: AsyncSession, seeded_enrollments):
    """Seed 10 study sessions: 8 ended, 2 active."""
    now = _utcnow()
    sessions = []
    for i, enrollment in enumerate(seeded_enrollments):
        for j in range(2):
            s = StudySessionModel(
                id=uuid4(),
                learner_enrollment_id=enrollment.id,
                intent="mixed",
                started_at=now - timedelta(days=j + 1, hours=i),
                ended_at=now - timedelta(days=j + 1, hours=i, minutes=-20) if j == 0 else None,
                status="ended" if j == 0 else "active",
                question_count=5 if j == 0 else 0,
            )
            session.add(s)
            sessions.append(s)
    await session.commit()
    return sessions


@pytest_asyncio.fixture
async def seeded_attempts(session: AsyncSession, seeded_enrollments, seeded_study_sessions):
    """Seed 20 attempts: 12 correct, 6 incorrect, 2 partial."""
    now = _utcnow()
    attempts = []
    outcomes = (["correct"] * 12) + (["incorrect"] * 6) + (["partial"] * 2)
    for i, outcome in enumerate(outcomes):
        enrollment = seeded_enrollments[i % len(seeded_enrollments)]
        study_session = next(
            s for s in seeded_study_sessions if s.learner_enrollment_id == enrollment.id
        )
        a = AttemptModel(
            id=uuid4(),
            question_instance_id=uuid4(),
            learner_enrollment_id=enrollment.id,
            study_session_id=study_session.id,
            content_version_id=uuid4(),
            template_version_id=uuid4(),
            algorithm_version_id=uuid4(),
            scoring_outcome=outcome,
            partial_credit=0.5 if outcome == "partial" else None,
            time_to_answer_ms=30000 + i * 1000,
            hint_used=(i % 3 == 0),
            hint_tiers_used=[],
            misconception_id=uuid4() if outcome == "incorrect" else None,
            attempt_intent="practice",
            created_at=now - timedelta(hours=i),
        )
        session.add(a)
        attempts.append(a)
    await session.commit()
    return attempts


@pytest_asyncio.fixture
async def seeded_mastery_scores(session: AsyncSession, seeded_enrollments):
    """Seed mastery scores: 4 concepts per enrollment, mixed states."""
    now = _utcnow()
    scores = []
    concept_ids = [uuid4() for _ in range(4)]
    states = ["unseen", "novice", "developing", "proficient"]
    for enrollment in seeded_enrollments:
        for i, (concept_id, state) in enumerate(zip(concept_ids, states)):
            score = 0.1 + i * 0.2  # 0.1, 0.3, 0.5, 0.7
            m = MasteryScoreModel(
                id=uuid4(),
                learner_enrollment_id=enrollment.id,
                concept_id=concept_id,
                algorithm_version_id=uuid4(),
                memory_score=score,
                durable_mastery_score=score,
                mastery_score_combined=score,
                confidence_interval=0.3 - i * 0.05,
                evidence_count=i + 1,
                concept_state=state,
                weakness_severity="none" if state in ("proficient", "mastered") else "mild",
                version=1,
                last_attempt_at=now - timedelta(days=i),
                last_updated_at=now - timedelta(days=i),
            )
            session.add(m)
            scores.append(m)
    await session.commit()
    return scores


@pytest_asyncio.fixture
async def seeded_workers(session: AsyncSession):
    """Seed 3 worker heartbeats: 2 running, 1 stale."""
    now = _utcnow()
    workers = []
    for i in range(2):
        w = WorkerHeartbeatModel(
            id=uuid4(),
            worker_id=f"worker-{i+1}",
            worker_type="outbox_dispatcher",
            hostname="host1",
            process_id=1000 + i,
            status="running",
            last_seen_at=now - timedelta(seconds=10),
            started_at=now - timedelta(hours=1),
            jobs_processed=100 + i * 10,
            jobs_failed=i,
            current_job="dispatch_outbox" if i == 0 else None,
            shutdown_requested=False,
        )
        session.add(w)
        workers.append(w)
    # Stale worker
    w = WorkerHeartbeatModel(
        id=uuid4(),
        worker_id="worker-stale",
        worker_type="notification_processor",
        hostname="host2",
        process_id=2000,
        status="running",
        last_seen_at=now - timedelta(minutes=5),
        started_at=now - timedelta(hours=2),
        jobs_processed=50,
        jobs_failed=20,
        current_job=None,
        shutdown_requested=False,
    )
    session.add(w)
    workers.append(w)
    await session.commit()
    return workers


@pytest_asyncio.fixture
async def seeded_outbox(session: AsyncSession):
    """Seed 15 outbox events: 10 dispatched, 5 pending."""
    now = _utcnow()
    events = []
    for i in range(10):
        e = OutboxEventModel(
            id=uuid4(),
            event_type="user_registered",
            aggregate_id=uuid4(),
            aggregate_type="User",
            actor_user_id=uuid4(),
            payload={"test": i},
            payload_schema_version="1",
            originating_schema="identity",
            status="dispatched",
            dispatched_at=now - timedelta(hours=i),
        )
        session.add(e)
        events.append(e)
    for i in range(5):
        e = OutboxEventModel(
            id=uuid4(),
            event_type="study_session_started",
            aggregate_id=uuid4(),
            aggregate_type="StudySession",
            actor_user_id=uuid4(),
            payload={"test": i},
            payload_schema_version="1",
            originating_schema="learning",
            status="pending",
        )
        session.add(e)
        events.append(e)
    await session.commit()
    return events


@pytest_asyncio.fixture
async def seeded_release_notes(session: AsyncSession, seeded_users):
    """Seed 3 release notes: 2 published, 1 draft."""
    admin = next(u for u in seeded_users if u.role == "administrator")
    now = _utcnow()
    releases = []
    for i, version in enumerate(["v1.0.0", "v1.0.1", "v1.1.0-rc"]):
        r = ReleaseNoteModel(
            id=uuid4(),
            version=version,
            release_type="patch" if i < 2 else "minor",
            title=f"Release {version}",
            summary=f"Summary for {version}",
            body=f"Body text for {version}",
            features=[{"title": f"Feature {i}"}],
            bug_fixes=[{"title": f"Bug fix {i}"}],
            breaking_changes=[],
            known_issues=[],
            feature_freeze=False,
            published_at=now - timedelta(days=7 - i) if i < 2 else None,
            created_by=admin.id,
        )
        session.add(r)
        releases.append(r)
    await session.commit()
    return releases


@pytest_asyncio.fixture
async def seeded_experiments(session: AsyncSession, seeded_users):
    """Seed 3 experiments: 1 running, 1 completed, 1 draft."""
    now = _utcnow()
    learners = [u for u in seeded_users if u.role == "learner"]

    # Running experiment
    exp1 = ExperimentModel(
        id="exp_ai_v1",
        name="AI Explanations v1",
        description="Test AI vs rule-based explanations",
        experiment_type="ai_vs_rule",
        variant_a="rule_based",
        variant_b="ai_generated",
        rollout_percentage=50,
        status="running",
        target_metric="day_1_retention",
        min_sample_size=10,
        started_at=now - timedelta(days=7),
        metadata_={},
    )
    session.add(exp1)

    # Assign 8 users (4 to each variant)
    for i, user in enumerate(learners[:8]):
        a = ExperimentAssignmentModel(
            id=uuid4(),
            experiment_id="exp_ai_v1",
            user_id=user.id,
            variant="rule_based" if i < 4 else "ai_generated",
        )
        session.add(a)

    # Record some results
    session.add(ExperimentResultModel(
        id=uuid4(),
        experiment_id="exp_ai_v1",
        variant="rule_based",
        sample_size=4,
        metric_value=0.25,
        metric_std_error=0.05,
        conversion_count=1,
        metadata_={},
    ))
    session.add(ExperimentResultModel(
        id=uuid4(),
        experiment_id="exp_ai_v1",
        variant="ai_generated",
        sample_size=4,
        metric_value=0.50,
        metric_std_error=0.05,
        conversion_count=2,
        metadata_={},
    ))

    # Completed experiment
    exp2 = ExperimentModel(
        id="exp_queue_v1",
        name="Queue Algorithm v1",
        description="Compare queue algorithms",
        experiment_type="queue",
        variant_a="difficulty_based",
        variant_b="mastery_based",
        rollout_percentage=50,
        status="completed",
        target_metric="adaptive_queue_quality",
        min_sample_size=10,
        started_at=now - timedelta(days=30),
        ended_at=now - timedelta(days=10),
        winner="mastery_based",
        metadata_={},
    )
    session.add(exp2)

    # Draft experiment
    exp3 = ExperimentModel(
        id="exp_ui_v1",
        name="UI Color v1",
        description="Test button colors",
        experiment_type="ab",
        variant_a="blue",
        variant_b="purple",
        rollout_percentage=50,
        status="draft",
        target_metric="click_through_rate",
        min_sample_size=100,
        metadata_={},
    )
    session.add(exp3)
    await session.commit()
    return [exp1, exp2, exp3]
