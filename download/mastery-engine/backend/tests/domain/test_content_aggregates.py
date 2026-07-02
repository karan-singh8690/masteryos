"""Comprehensive unit tests for the Content context aggregates.

Tests cover:
- Subject: create, publish (with minimum-content gate), deprecate
- Concept: create, add_dependency (no self, no duplicate),
  remove_dependency, publish, deprecate
- ContentPack: create, submit_for_review, approve (per stage),
  request_changes, reject, publish

For each aggregate we test the happy path and the invalid-state
transitions and invariant violations.

These tests exercise only the pure-Python domain layer — no database,
HTTP or infrastructure.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.content.concept import Concept
from app.domain.content.content_pack import ContentPack
from app.domain.content.events import (
    ConceptCreated,
    ConceptDependencyAdded,
    ConceptDependencyRemoved,
    ConceptDeprecated,
    ConceptPublished,
    ContentPackApproved,
    ContentPackCreated,
    ContentPackPublished,
    ContentPackRejected,
    ContentPackSubmittedForReview,
    SubjectCreated,
    SubjectDeprecated,
    SubjectPublished,
)
from app.domain.content.exceptions import (
    ConceptAlreadyDeprecated,
    ConceptAlreadyPublished,
    ConceptDependencyNotFound,
    ConceptDuplicateDependency,
    ConceptSelfDependency,
    ContentPackAlreadyPublished,
    ContentPackAlreadyRejected,
    ContentPackAlreadySubmitted,
    ContentPackNotInReview,
    ContentPackReviewIncomplete,
    ContentPackStageAlreadyApproved,
    SubjectAlreadyDeprecated,
    SubjectAlreadyPublished,
    SubjectNotPublishable,
)
from app.domain.content.subject import Subject
from app.domain.shared.ids import (
    ConceptId,
    ContentPackId,
    ContentVersionId,
    SubjectId,
    TenantId,
    UserId,
)
from app.domain.shared.kernel import (
    ContentStatus,
    DependencyType,
    DependencyWeight,
    Difficulty,
    InvalidStateTransition,
    InvariantViolation,
    ReviewStage,
)


# ============================================================
# Helpers
# ============================================================


def _tenant_id() -> TenantId:
    return TenantId.generate()


def _subject_id() -> SubjectId:
    return SubjectId.generate()


def _user_id() -> UserId:
    return UserId.generate()


def _make_subject(
    *,
    code: str = "CS-101",
    name: str = "Algorithms",
    slug: str = "algorithms",
    description: str = "Algorithms and data structures.",
) -> Subject:
    return Subject.create(
        tenant_id=_tenant_id(),
        code=code,
        name=name,
        slug=slug,
        description=description,
    )


def _make_concept(
    *,
    subject_id: SubjectId | None = None,
    slug: str = "quicksort",
    name: str = "Quicksort",
    description: str = "The quicksort algorithm.",
    difficulty: Difficulty = Difficulty.MEDIUM,
) -> Concept:
    return Concept.create(
        subject_id=subject_id or _subject_id(),
        slug=slug,
        name=name,
        description=description,
        difficulty=difficulty,
        importance=__import__("app.domain.shared.kernel", fromlist=["Importance"]).Importance.HIGH,
    )


def _make_pack(
    *,
    subject_id: SubjectId | None = None,
    author_id: UserId | None = None,
    name: str = "Pack v1",
    description: str = "Initial pack",
) -> ContentPack:
    return ContentPack.create(
        subject_id=subject_id or _subject_id(),
        author_id=author_id or _user_id(),
        name=name,
        description=description,
    )


# ============================================================
# Subject
# ============================================================


class TestSubjectCreate:
    """Tests for the ``Subject.create()`` factory."""

    def test_create_returns_draft_subject(self) -> None:
        s = _make_subject()
        assert s.status == ContentStatus.DRAFT
        assert s.is_draft is True

    def test_create_generates_id(self) -> None:
        s = _make_subject()
        assert isinstance(s.id, SubjectId)

    def test_create_sets_tenant_id(self) -> None:
        tid = _tenant_id()
        s = Subject.create(
            tenant_id=tid,
            code="CS-101",
            name="Algorithms",
            slug="algorithms",
            description="desc",
        )
        assert s.tenant_id == tid

    def test_create_sets_code_name_slug_description(self) -> None:
        s = _make_subject(code="BIO-200", name="Biology", slug="biology", description="d")
        assert s.code == "BIO-200"
        assert s.name == "Biology"
        assert s.slug == "biology"
        assert s.description == "d"

    def test_create_default_minimum_content_ready_is_false(self) -> None:
        s = _make_subject()
        assert s.minimum_content_ready is False

    def test_create_default_no_published_at(self) -> None:
        s = _make_subject()
        assert s.published_at is None

    def test_create_records_subject_created_event(self) -> None:
        s = _make_subject()
        events = s.collect_events()
        assert len(events) == 1
        evt = events[0]
        assert isinstance(evt, SubjectCreated)
        assert evt.subject_id == s.id
        assert evt.code == s.code

    def test_create_rejects_empty_code(self) -> None:
        with pytest.raises(InvariantViolation):
            Subject.create(
                tenant_id=_tenant_id(),
                code="",
                name="Algorithms",
                slug="algorithms",
                description="d",
            )

    def test_create_rejects_empty_name(self) -> None:
        with pytest.raises(InvariantViolation):
            Subject.create(
                tenant_id=_tenant_id(),
                code="CS-101",
                name="",
                slug="algorithms",
                description="d",
            )

    def test_create_rejects_empty_slug(self) -> None:
        with pytest.raises(InvariantViolation):
            Subject.create(
                tenant_id=_tenant_id(),
                code="CS-101",
                name="Algorithms",
                slug="",
                description="d",
            )


class TestSubjectMinimumContentGate:
    """Tests for the minimum-content gate before publishing."""

    def test_mark_minimum_content_ready_sets_flag(self) -> None:
        s = _make_subject()
        s.mark_minimum_content_ready()
        assert s.minimum_content_ready is True

    def test_mark_minimum_content_ready_is_idempotent(self) -> None:
        s = _make_subject()
        s.mark_minimum_content_ready()
        s.mark_minimum_content_ready()  # second call is a no-op
        assert s.minimum_content_ready is True

    def test_publish_without_minimum_content_raises(self) -> None:
        s = _make_subject()
        with pytest.raises(SubjectNotPublishable):
            s.publish()


class TestSubjectPublish:
    """Tests for the ``publish()`` transition."""

    def test_publish_transitions_to_published(self) -> None:
        s = _make_subject()
        s.mark_minimum_content_ready()
        s.publish()
        assert s.status == ContentStatus.PUBLISHED
        assert s.is_published is True

    def test_publish_sets_published_at(self) -> None:
        s = _make_subject()
        s.mark_minimum_content_ready()
        when = datetime(2024, 6, 1, tzinfo=UTC)
        s.publish(now=when)
        assert s.published_at == when

    def test_publish_records_event(self) -> None:
        s = _make_subject()
        s.mark_minimum_content_ready()
        s.clear_events()
        s.publish()
        events = s.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], SubjectPublished)

    def test_publish_when_already_published_raises(self) -> None:
        s = _make_subject()
        s.mark_minimum_content_ready()
        s.publish()
        with pytest.raises(SubjectAlreadyPublished):
            s.publish()

    def test_publish_when_deprecated_raises(self) -> None:
        s = _make_subject()
        s.mark_minimum_content_ready()
        s.publish()
        s.deprecate()
        with pytest.raises(InvalidStateTransition):
            s.publish()


class TestSubjectDeprecate:
    """Tests for the ``deprecate()`` transition."""

    def test_deprecate_transitions_to_deprecated(self) -> None:
        s = _make_subject()
        s.mark_minimum_content_ready()
        s.publish()
        s.deprecate()
        assert s.status == ContentStatus.DEPRECATED
        assert s.is_deprecated is True

    def test_deprecate_sets_deprecated_at(self) -> None:
        s = _make_subject()
        s.mark_minimum_content_ready()
        s.publish()
        when = datetime(2024, 6, 1, tzinfo=UTC)
        s.deprecate(now=when)
        assert s.deprecated_at == when

    def test_deprecate_records_event(self) -> None:
        s = _make_subject()
        s.mark_minimum_content_ready()
        s.publish()
        s.clear_events()
        s.deprecate()
        events = s.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], SubjectDeprecated)

    def test_deprecate_when_draft_raises(self) -> None:
        s = _make_subject()
        with pytest.raises(InvalidStateTransition):
            s.deprecate()

    def test_deprecate_when_already_deprecated_raises(self) -> None:
        s = _make_subject()
        s.mark_minimum_content_ready()
        s.publish()
        s.deprecate()
        with pytest.raises(SubjectAlreadyDeprecated):
            s.deprecate()


# ============================================================
# Concept
# ============================================================


class TestConceptCreate:
    """Tests for the ``Concept.create()`` factory."""

    def test_create_returns_draft_concept(self) -> None:
        c = _make_concept()
        assert c.status == ContentStatus.DRAFT
        assert c.is_draft is True

    def test_create_generates_id(self) -> None:
        c = _make_concept()
        assert isinstance(c.id, ConceptId)

    def test_create_sets_subject_id(self) -> None:
        sid = _subject_id()
        c = _make_concept(subject_id=sid)
        assert c.subject_id == sid

    def test_create_default_no_dependencies(self) -> None:
        c = _make_concept()
        assert c.dependencies == []

    def test_create_records_concept_created_event(self) -> None:
        c = _make_concept()
        events = c.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], ConceptCreated)
        assert events[0].concept_id == c.id

    def test_create_rejects_empty_slug(self) -> None:
        with pytest.raises(InvariantViolation):
            Concept.create(
                subject_id=_subject_id(),
                slug="",
                name="X",
                description="d",
                difficulty=Difficulty.EASY,
                importance=__import__("app.domain.shared.kernel", fromlist=["Importance"]).Importance.LOW,
            )


class TestConceptAddDependency:
    """Tests for ``Concept.add_dependency()``."""

    def test_add_dependency_appends_to_dependency_list(self) -> None:
        c = _make_concept()
        target = ConceptId.generate()
        dep = c.add_dependency(
            target_concept_id=target,
            dependency_type=DependencyType.PREREQUISITE,
            weight=DependencyWeight.STRONG,
        )
        assert dep in c.dependencies
        assert dep.target_concept_id == target

    def test_add_dependency_records_event(self) -> None:
        c = _make_concept()
        c.clear_events()
        target = ConceptId.generate()
        c.add_dependency(
            target_concept_id=target,
            dependency_type=DependencyType.PREREQUISITE,
            weight=DependencyWeight.STRONG,
        )
        events = c.collect_events()
        assert len(events) == 1
        evt = events[0]
        assert isinstance(evt, ConceptDependencyAdded)
        assert evt.target_concept_id == target

    def test_add_dependency_rejects_self_dependency(self) -> None:
        c = _make_concept()
        with pytest.raises(ConceptSelfDependency):
            c.add_dependency(
                target_concept_id=c.id,
                dependency_type=DependencyType.PREREQUISITE,
                weight=DependencyWeight.STRONG,
            )

    def test_add_dependency_rejects_duplicate_pair(self) -> None:
        """Duplicate ``(target, type)`` is rejected even with different weight."""
        c = _make_concept()
        target = ConceptId.generate()
        c.add_dependency(
            target_concept_id=target,
            dependency_type=DependencyType.PREREQUISITE,
            weight=DependencyWeight.STRONG,
        )
        with pytest.raises(ConceptDuplicateDependency):
            c.add_dependency(
                target_concept_id=target,
                dependency_type=DependencyType.PREREQUISITE,
                weight=DependencyWeight.WEAK,
            )

    def test_add_dependency_allows_same_target_different_type(self) -> None:
        c = _make_concept()
        target = ConceptId.generate()
        c.add_dependency(
            target_concept_id=target,
            dependency_type=DependencyType.PREREQUISITE,
            weight=DependencyWeight.STRONG,
        )
        c.add_dependency(
            target_concept_id=target,
            dependency_type=DependencyType.RELATED,
            weight=DependencyWeight.WEAK,
        )
        assert len(c.dependencies) == 2

    def test_add_dependency_when_deprecated_raises(self) -> None:
        c = _make_concept()
        c.publish()
        c.deprecate()
        with pytest.raises(InvalidStateTransition):
            c.add_dependency(
                target_concept_id=ConceptId.generate(),
                dependency_type=DependencyType.PREREQUISITE,
                weight=DependencyWeight.STRONG,
            )


class TestConceptRemoveDependency:
    """Tests for ``Concept.remove_dependency()``."""

    def test_remove_dependency_removes_from_list(self) -> None:
        c = _make_concept()
        target = ConceptId.generate()
        c.add_dependency(
            target_concept_id=target,
            dependency_type=DependencyType.PREREQUISITE,
            weight=DependencyWeight.STRONG,
        )
        c.remove_dependency(
            target_concept_id=target,
            dependency_type=DependencyType.PREREQUISITE,
        )
        assert c.dependencies == []

    def test_remove_dependency_records_event(self) -> None:
        c = _make_concept()
        target = ConceptId.generate()
        c.add_dependency(
            target_concept_id=target,
            dependency_type=DependencyType.PREREQUISITE,
            weight=DependencyWeight.STRONG,
        )
        c.clear_events()
        c.remove_dependency(
            target_concept_id=target,
            dependency_type=DependencyType.PREREQUISITE,
        )
        events = c.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], ConceptDependencyRemoved)

    def test_remove_nonexistent_dependency_raises(self) -> None:
        c = _make_concept()
        with pytest.raises(ConceptDependencyNotFound):
            c.remove_dependency(
                target_concept_id=ConceptId.generate(),
                dependency_type=DependencyType.PREREQUISITE,
            )

    def test_remove_dependency_when_deprecated_raises(self) -> None:
        c = _make_concept()
        target = ConceptId.generate()
        c.add_dependency(
            target_concept_id=target,
            dependency_type=DependencyType.PREREQUISITE,
            weight=DependencyWeight.STRONG,
        )
        c.publish()
        c.deprecate()
        with pytest.raises(InvalidStateTransition):
            c.remove_dependency(
                target_concept_id=target,
                dependency_type=DependencyType.PREREQUISITE,
            )


class TestConceptPublish:
    """Tests for ``Concept.publish()``."""

    def test_publish_transitions_to_published(self) -> None:
        c = _make_concept()
        c.publish()
        assert c.status == ContentStatus.PUBLISHED
        assert c.is_published is True

    def test_publish_sets_published_at(self) -> None:
        c = _make_concept()
        when = datetime(2024, 6, 1, tzinfo=UTC)
        c.publish(now=when)
        assert c.published_at == when

    def test_publish_records_event(self) -> None:
        c = _make_concept()
        c.clear_events()
        c.publish()
        events = c.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], ConceptPublished)

    def test_publish_when_already_published_raises(self) -> None:
        c = _make_concept()
        c.publish()
        with pytest.raises(ConceptAlreadyPublished):
            c.publish()

    def test_publish_when_deprecated_raises(self) -> None:
        c = _make_concept()
        c.publish()
        c.deprecate()
        with pytest.raises(InvalidStateTransition):
            c.publish()


class TestConceptDeprecate:
    """Tests for ``Concept.deprecate()``."""

    def test_deprecate_transitions_to_deprecated(self) -> None:
        c = _make_concept()
        c.publish()
        c.deprecate()
        assert c.status == ContentStatus.DEPRECATED
        assert c.is_deprecated is True

    def test_deprecate_sets_deprecated_at(self) -> None:
        c = _make_concept()
        c.publish()
        when = datetime(2024, 6, 1, tzinfo=UTC)
        c.deprecate(now=when)
        assert c.deprecated_at == when

    def test_deprecate_records_event(self) -> None:
        c = _make_concept()
        c.publish()
        c.clear_events()
        c.deprecate()
        events = c.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], ConceptDeprecated)

    def test_deprecate_when_draft_raises(self) -> None:
        c = _make_concept()
        with pytest.raises(InvalidStateTransition):
            c.deprecate()

    def test_deprecate_when_already_deprecated_raises(self) -> None:
        c = _make_concept()
        c.publish()
        c.deprecate()
        with pytest.raises(ConceptAlreadyDeprecated):
            c.deprecate()


# ============================================================
# ContentPack
# ============================================================


class TestContentPackCreate:
    """Tests for ``ContentPack.create()``."""

    def test_create_returns_draft_pack(self) -> None:
        p = _make_pack()
        assert p.status == ContentStatus.DRAFT
        assert p.is_draft is True

    def test_create_generates_id(self) -> None:
        p = _make_pack()
        assert isinstance(p.id, ContentPackId)

    def test_create_sets_subject_and_author(self) -> None:
        sid = _subject_id()
        aid = _user_id()
        p = ContentPack.create(subject_id=sid, author_id=aid, name="N", description="D")
        assert p.subject_id == sid
        assert p.author_id == aid

    def test_create_default_no_artifacts_no_approvals(self) -> None:
        p = _make_pack()
        assert p.artifact_ids == {}
        assert p.approved_stages == frozenset()

    def test_create_default_no_content_version(self) -> None:
        p = _make_pack()
        assert p.content_version_id is None

    def test_create_records_content_pack_created_event(self) -> None:
        p = _make_pack()
        events = p.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], ContentPackCreated)
        assert events[0].content_pack_id == p.id

    def test_create_default_required_stages_are_all_three(self) -> None:
        p = _make_pack()
        assert p.required_stages == frozenset({
            ReviewStage.PEER_REVIEW,
            ReviewStage.EDITORIAL_REVIEW,
            ReviewStage.QA_PILOT,
        })


class TestContentPackSubmitForReview:
    """Tests for ``ContentPack.submit_for_review()``."""

    def test_submit_transitions_to_in_review(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        assert p.status == ContentStatus.IN_REVIEW
        assert p.is_in_review is True

    def test_submit_records_event(self) -> None:
        p = _make_pack()
        p.clear_events()
        p.submit_for_review()
        events = p.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], ContentPackSubmittedForReview)

    def test_submit_clears_prior_approvals(self) -> None:
        """A fresh submission cycle clears any stale approvals."""
        p = _make_pack()
        p.submit_for_review()
        p.approve(ReviewStage.PEER_REVIEW, _user_id())
        # Request changes → back to draft with approvals cleared
        p.request_changes(_user_id(), "fix typos")
        # Re-submit
        p.submit_for_review()
        assert p.approved_stages == frozenset()

    def test_submit_when_already_in_review_raises(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        with pytest.raises(ContentPackAlreadySubmitted):
            p.submit_for_review()

    def test_submit_when_published_raises(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        for stage in p.required_stages:
            p.approve(stage, _user_id())
        p.publish(ContentVersionId.generate())
        with pytest.raises(ContentPackAlreadyPublished):
            p.submit_for_review()

    def test_submit_when_rejected_raises(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        p.reject(_user_id(), "bad")
        with pytest.raises(ContentPackAlreadyRejected):
            p.submit_for_review()


class TestContentPackApprove:
    """Tests for ``ContentPack.approve()``."""

    def test_approve_adds_stage_to_approved_set(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        p.approve(ReviewStage.PEER_REVIEW, _user_id())
        assert ReviewStage.PEER_REVIEW in p.approved_stages

    def test_approve_records_event(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        p.clear_events()
        reviewer = _user_id()
        p.approve(ReviewStage.PEER_REVIEW, reviewer)
        events = p.collect_events()
        assert len(events) == 1
        evt = events[0]
        assert isinstance(evt, ContentPackApproved)
        assert evt.stage == ReviewStage.PEER_REVIEW
        assert evt.reviewer_id == reviewer

    def test_approve_same_stage_twice_raises(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        p.approve(ReviewStage.PEER_REVIEW, _user_id())
        with pytest.raises(ContentPackStageAlreadyApproved):
            p.approve(ReviewStage.PEER_REVIEW, _user_id())

    def test_approve_when_draft_raises(self) -> None:
        p = _make_pack()
        with pytest.raises(ContentPackNotInReview):
            p.approve(ReviewStage.PEER_REVIEW, _user_id())

    def test_approve_when_published_raises(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        for stage in p.required_stages:
            p.approve(stage, _user_id())
        p.publish(ContentVersionId.generate())
        with pytest.raises(ContentPackAlreadyPublished):
            p.approve(ReviewStage.PEER_REVIEW, _user_id())

    def test_missing_stages_reports_unapproved(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        p.approve(ReviewStage.PEER_REVIEW, _user_id())
        assert p.is_review_complete is False
        assert ReviewStage.PEER_REVIEW not in p.missing_stages
        assert ReviewStage.EDITORIAL_REVIEW in p.missing_stages
        assert ReviewStage.QA_PILOT in p.missing_stages


class TestContentPackPublish:
    """Tests for ``ContentPack.publish()``."""

    def test_publish_requires_all_stages_approved(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        p.approve(ReviewStage.PEER_REVIEW, _user_id())
        with pytest.raises(ContentPackReviewIncomplete):
            p.publish(ContentVersionId.generate())

    def test_publish_after_all_stages_approved(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        for stage in p.required_stages:
            p.approve(stage, _user_id())
        p.publish(ContentVersionId.generate())
        assert p.status == ContentStatus.PUBLISHED
        assert p.is_published is True

    def test_publish_binds_content_version_id(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        for stage in p.required_stages:
            p.approve(stage, _user_id())
        cv = ContentVersionId.generate()
        p.publish(cv)
        assert p.content_version_id == cv

    def test_publish_sets_published_at(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        for stage in p.required_stages:
            p.approve(stage, _user_id())
        when = datetime(2024, 6, 1, tzinfo=UTC)
        p.publish(ContentVersionId.generate(), now=when)
        assert p.published_at == when

    def test_publish_records_event(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        for stage in p.required_stages:
            p.approve(stage, _user_id())
        p.clear_events()
        cv = ContentVersionId.generate()
        p.publish(cv)
        events = p.collect_events()
        assert len(events) == 1
        evt = events[0]
        assert isinstance(evt, ContentPackPublished)
        assert evt.content_version_id == cv

    def test_publish_when_draft_raises(self) -> None:
        p = _make_pack()
        with pytest.raises(ContentPackNotInReview):
            p.publish(ContentVersionId.generate())

    def test_publish_when_already_published_raises(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        for stage in p.required_stages:
            p.approve(stage, _user_id())
        p.publish(ContentVersionId.generate())
        with pytest.raises(ContentPackAlreadyPublished):
            p.publish(ContentVersionId.generate())


class TestContentPackReject:
    """Tests for ``ContentPack.reject()``."""

    def test_reject_transitions_to_rejected(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        p.reject(_user_id(), "off-topic")
        assert p.status == ContentStatus.REJECTED
        assert p.is_rejected is True

    def test_reject_records_event_with_reason(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        p.clear_events()
        reviewer = _user_id()
        p.reject(reviewer, "off-topic")
        events = p.collect_events()
        assert len(events) == 1
        evt = events[0]
        assert isinstance(evt, ContentPackRejected)
        assert evt.reviewer_id == reviewer
        assert evt.reason == "off-topic"

    def test_reject_when_draft_raises(self) -> None:
        p = _make_pack()
        with pytest.raises(ContentPackNotInReview):
            p.reject(_user_id(), "x")

    def test_reject_when_already_rejected_raises(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        p.reject(_user_id(), "x")
        with pytest.raises(ContentPackAlreadyRejected):
            p.reject(_user_id(), "y")


class TestContentPackRequestChanges:
    """Tests for ``ContentPack.request_changes()``."""

    def test_request_changes_returns_to_draft(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        p.request_changes(_user_id(), "fix typos")
        assert p.status == ContentStatus.DRAFT

    def test_request_changes_clears_approvals(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        p.approve(ReviewStage.PEER_REVIEW, _user_id())
        p.request_changes(_user_id(), "fix typos")
        assert p.approved_stages == frozenset()

    def test_request_changes_attaches_notes(self) -> None:
        p = _make_pack()
        p.submit_for_review()
        p.request_changes(_user_id(), "fix typos")
        notes = p.change_request_notes
        assert len(notes) == 1
        assert notes[0]["notes"] == "fix typos"

    def test_request_changes_when_draft_raises(self) -> None:
        p = _make_pack()
        with pytest.raises(ContentPackNotInReview):
            p.request_changes(_user_id(), "x")
