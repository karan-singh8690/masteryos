"""Content context — ContentPack aggregate root.

A :class:`ContentPack` is a curated bundle of content artifacts (Concept
revisions, new QuestionTemplates, new TemplateVersions, new
LearningObjectives/Misconceptions) staged for atomic publication as a
single :class:`ContentVersion`. It is the unit of editorial review: an
author assembles a pack, submits it for multi-stage review, and once
every stage has approved it the pack is published — atomically binding
its artifacts to a new (or existing) ContentVersion and marking that
version as the active one for the Subject.

Why packs exist:

Without a review gate, every individual artifact edit would either (a)
go live immediately, risking learner-visible mistakes, or (b) require
a separate out-of-band review process with no audit trail. ContentPack
makes the review first-class: each pack carries its own state machine,
records every reviewer decision as a domain event, and is the single
chokepoint through which content reaches learners.

Lifecycle (state machine)::

            submit_for_review()         approve(stage) (per stage)
        DRAFT ──────────────────► IN_REVIEW ───────────────────────► (all stages approved)
         ▲ ▲                         │ │                                  │
         │ │                         │ │                                  │ publish(content_version_id)
         │ │   request_changes()     │ │ reject(reviewer_id, reason)      │
         │ └─────────────────────────┘ ▼                                  ▼
         │                          REJECTED                            PUBLISHED
         │                          (terminal)                          (terminal)
         │
         └── (after rework, author submits again)

State semantics:

- ``draft`` — the author is still assembling the pack. Artifacts may be
  added/removed freely. No review decisions are recorded.
- ``in_review`` — the pack has been submitted and is being evaluated by
  reviewers. Each :class:`ReviewStage` (peer, editorial, QA pilot) must
  approve via :meth:`approve` before :meth:`publish` is allowed.
- ``published`` — terminal. The pack has been bound to a
  :class:`ContentVersion` and its artifacts are live.
- ``rejected`` — terminal. A reviewer has rejected the pack outright.
  The author must create a new ContentPack with the requested
  corrections; rejected packs cannot be re-opened.

Invariants enforced:
- A pack can only be submitted from ``draft``.
- ``approve``, ``request_changes``, and ``reject`` only apply to a pack
  in ``in_review``.
- A given review stage can only be approved once per submission cycle.
  After :meth:`request_changes` returns the pack to ``draft``, all
  stage approvals are cleared (a fresh review cycle is required).
- :meth:`publish` requires every required :class:`ReviewStage` to have
  approved. The required stages are the three enumerated in
  :class:`ReviewStage` (peer, editorial, QA pilot) by default; this is
  overridable via the ``required_stages`` argument to
  :meth:`__init__` for tenants with simpler workflows.
- :meth:`publish` requires a ``content_version_id`` to bind the pack
  to. The application service is responsible for creating or selecting
  the :class:`ContentVersion` and passing its id.
- ``published`` and ``rejected`` are terminal — no further transitions
  are allowed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain.content.events import (
    ContentPackApproved,
    ContentPackChangesRequested,
    ContentPackCreated,
    ContentPackPublished,
    ContentPackRejected,
    ContentPackSubmittedForReview,
)
from app.domain.content.exceptions import (
    ContentPackAlreadyPublished,
    ContentPackAlreadyRejected,
    ContentPackAlreadySubmitted,
    ContentPackNotInReview,
    ContentPackReviewIncomplete,
    ContentPackStageAlreadyApproved,
)
from app.domain.shared.ids import ContentPackId, ContentVersionId, SubjectId, UserId
from app.domain.shared.kernel import (
    AggregateRoot,
    ContentStatus,
    InvalidStateTransition,
    InvariantViolation,
    ReviewStage,
)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


#: The default set of review stages that must approve before a pack can
#: be published. Tenants with simpler workflows may override this via
#: the ``required_stages`` argument to :meth:`ContentPack.__init__`.
DEFAULT_REQUIRED_STAGES: frozenset[ReviewStage] = frozenset(
    {
        ReviewStage.PEER_REVIEW,
        ReviewStage.EDITORIAL_REVIEW,
        ReviewStage.QA_PILOT,
    }
)


class ContentPack(AggregateRoot):
    """The ContentPack aggregate root.

    Holds the pack's identity, lifecycle state, the set of artifact
    references it bundles (``artifact_ids``), the set of review stages
    that have approved it, and a log of change-request notes from
    reviewers. All mutations go through methods on this class, which
    enforce invariants and emit domain events via
    :meth:`AggregateRoot._record_event`.

    The public constructor is intended for **reconstitution** from
    persistence (the repository uses it to rebuild an aggregate from
    stored state). To create a *new* pack, use
    :meth:`ContentPack.create`.

    The ``artifact_ids`` dict maps an artifact-kind string (e.g.,
    ``"concept"``, ``"question_template"``, ``"template_version"``) to
    a list of typed-id values. The domain does not validate the
    contents of these lists — the application service is responsible
    for ensuring that every referenced artifact actually exists in the
    same Subject before publication.
    """

    #: Maximum length of the human-readable ``name``.
    MAX_NAME_LENGTH: int = 200

    #: Maximum length of the ``description``.
    MAX_DESCRIPTION_LENGTH: int = 4000

    #: Maximum length of a reviewer's ``notes`` (on request_changes).
    MAX_NOTES_LENGTH: int = 4000

    #: Maximum length of a rejection ``reason``.
    MAX_REASON_LENGTH: int = 4000

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        id: ContentPackId,
        subject_id: SubjectId,
        author_id: UserId,
        name: str,
        description: str,
        status: ContentStatus = ContentStatus.DRAFT,
        content_version_id: ContentVersionId | None = None,
        artifact_ids: dict[str, list[Any]] | None = None,
        approved_stages: list[ReviewStage] | None = None,
        change_request_notes: list[dict[str, Any]] | None = None,
        published_at: datetime | None = None,
        created_at: datetime | None = None,
        required_stages: frozenset[ReviewStage] | None = None,
    ) -> None:
        super().__init__()
        self._id: ContentPackId = id
        self._subject_id: SubjectId = subject_id
        self._author_id: UserId = author_id
        self._name: str = name
        self._description: str = description
        self._status: ContentStatus = status
        self._content_version_id: ContentVersionId | None = content_version_id
        self._artifact_ids: dict[str, list[Any]] = (
            {k: list(v) for k, v in artifact_ids.items()} if artifact_ids else {}
        )
        self._approved_stages: set[ReviewStage] = set(approved_stages) if approved_stages else set()
        self._change_request_notes: list[dict[str, Any]] = (
            list(change_request_notes) if change_request_notes else []
        )
        self._published_at: datetime | None = published_at
        self._created_at: datetime = created_at or _utcnow()
        self._required_stages: frozenset[ReviewStage] = (
            required_stages if required_stages is not None else DEFAULT_REQUIRED_STAGES
        )
        self._validate_invariants()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        subject_id: SubjectId,
        author_id: UserId,
        name: str,
        description: str,
    ) -> ContentPack:
        """Create a new ContentPack in ``draft`` status.

        The new pack has an empty artifact set and no review decisions.
        The author attaches artifacts via :meth:`add_artifact` and then
        submits via :meth:`submit_for_review`.

        Args:
            subject_id: The Subject this pack stages content for.
            author_id: The user assembling the pack. Recorded on every
                event for audit.
            name: A human-readable name (e.g.,
                ``"Algorithms v2 — add graph theory"``).
            description: A longer description of the pack's scope.

        Returns:
            A newly created, un-persisted :class:`ContentPack` in
            ``draft`` status. The caller must add it to the repository
            and then call :meth:`collect_events` to publish the
            recorded events.

        Raises:
            InvariantViolation: If any field fails validation.
        """
        pack_id = ContentPackId.generate()
        pack = cls(
            id=pack_id,
            subject_id=subject_id,
            author_id=author_id,
            name=name,
            description=description,
            status=ContentStatus.DRAFT,
            content_version_id=None,
            artifact_ids=None,
            approved_stages=None,
            change_request_notes=None,
            published_at=None,
            created_at=None,
            required_stages=None,
        )
        pack._record_event(
            ContentPackCreated(
                content_pack_id=pack.id,
                subject_id=pack.subject_id,
                author_id=pack.author_id,
                name=pack.name,
            )
        )
        return pack

    # ------------------------------------------------------------------
    # Properties (read-only views of state)
    # ------------------------------------------------------------------

    @property
    def id(self) -> ContentPackId:
        """The pack's unique identifier."""
        return self._id

    @property
    def subject_id(self) -> SubjectId:
        """The Subject this pack stages content for."""
        return self._subject_id

    @property
    def author_id(self) -> UserId:
        """The user who assembled the pack."""
        return self._author_id

    @property
    def name(self) -> str:
        """A human-readable name."""
        return self._name

    @property
    def description(self) -> str:
        """A longer description of the pack's scope."""
        return self._description

    @property
    def status(self) -> ContentStatus:
        """The pack's current lifecycle status."""
        return self._status

    @property
    def content_version_id(self) -> ContentVersionId | None:
        """The ContentVersion this pack was bound to on publication.

        ``None`` until :meth:`publish` is called.
        """
        return self._content_version_id

    @property
    def artifact_ids(self) -> dict[str, list[Any]]:
        """A snapshot of the pack's artifact references.

        Returns a deep copy so callers cannot mutate the aggregate's
        internal dict directly — artifact changes must go through
        :meth:`add_artifact` and :meth:`remove_artifact`.
        """
        return {k: list(v) for k, v in self._artifact_ids.items()}

    @property
    def approved_stages(self) -> frozenset[ReviewStage]:
        """The set of review stages that have approved this pack."""
        return frozenset(self._approved_stages)

    @property
    def change_request_notes(self) -> list[dict[str, Any]]:
        """A snapshot of the change-request notes left by reviewers.

        Each entry is a dict ``{"reviewer_id": ..., "notes": ..., "at": ...}``.
        """
        return [dict(n) for n in self._change_request_notes]

    @property
    def published_at(self) -> datetime | None:
        """When the pack was published, or ``None`` if not yet published."""
        return self._published_at

    @property
    def created_at(self) -> datetime:
        """When the pack was created."""
        return self._created_at

    @property
    def required_stages(self) -> frozenset[ReviewStage]:
        """The set of review stages that must approve before :meth:`publish`."""
        return self._required_stages

    @property
    def is_draft(self) -> bool:
        """True if the pack is in ``draft`` status."""
        return self._status == ContentStatus.DRAFT

    @property
    def is_in_review(self) -> bool:
        """True if the pack is in ``in_review`` status."""
        return self._status == ContentStatus.IN_REVIEW

    @property
    def is_published(self) -> bool:
        """True if the pack is in ``published`` status."""
        return self._status == ContentStatus.PUBLISHED

    @property
    def is_rejected(self) -> bool:
        """True if the pack is in ``rejected`` status."""
        return self._status == ContentStatus.REJECTED

    @property
    def missing_stages(self) -> list[ReviewStage]:
        """The review stages that have not yet approved this pack.

        Empty iff :meth:`is_review_complete` is ``True``.
        """
        return sorted(self._required_stages - self._approved_stages, key=lambda s: s.value)

    @property
    def is_review_complete(self) -> bool:
        """True iff every required review stage has approved this pack."""
        return self._required_stages.issubset(self._approved_stages)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_invariants(self) -> None:
        """Enforce field-level invariants."""
        if not isinstance(self._name, str) or not self._name.strip():
            raise InvariantViolation(
                "ContentPack",
                "name must be a non-empty string",
            )
        if len(self._name) > self.MAX_NAME_LENGTH:
            raise InvariantViolation(
                "ContentPack",
                f"name must be at most {self.MAX_NAME_LENGTH} characters",
            )
        self._name = self._name.strip()

        if not isinstance(self._description, str):
            raise InvariantViolation(
                "ContentPack",
                "description must be a string",
            )
        if len(self._description) > self.MAX_DESCRIPTION_LENGTH:
            raise InvariantViolation(
                "ContentPack",
                f"description must be at most {self.MAX_DESCRIPTION_LENGTH} characters",
            )

        if not isinstance(self._artifact_ids, dict):
            raise InvariantViolation(
                "ContentPack",
                "artifact_ids must be a dict",
            )
        for k, v in self._artifact_ids.items():
            if not isinstance(k, str) or not k:
                raise InvariantViolation(
                    "ContentPack",
                    f"artifact_ids key must be a non-empty string, got {k!r}",
                )
            if not isinstance(v, list):
                raise InvariantViolation(
                    "ContentPack",
                    f"artifact_ids[{k!r}] must be a list, got {type(v).__name__}",
                )

        if not isinstance(self._required_stages, (set, frozenset)) or not self._required_stages:
            raise InvariantViolation(
                "ContentPack",
                "required_stages must be a non-empty set of ReviewStage",
            )
        for s in self._required_stages:
            if not isinstance(s, ReviewStage):
                raise InvariantViolation(
                    "ContentPack",
                    f"required_stages contains non-ReviewStage value: {s!r}",
                )

        # Restrict the status to the values that make sense for a ContentPack.
        allowed = {
            ContentStatus.DRAFT,
            ContentStatus.IN_REVIEW,
            ContentStatus.PUBLISHED,
            ContentStatus.REJECTED,
        }
        if self._status not in allowed:
            raise InvariantViolation(
                "ContentPack",
                f"status must be one of {[s.value for s in allowed]}, got {self._status.value!r}",
            )

    def _assert_status(self, expected: ContentStatus, action: str) -> None:
        """Raise :class:`InvalidStateTransition` unless in ``expected`` status."""
        if self._status != expected:
            raise InvalidStateTransition(
                entity="ContentPack",
                current_state=self._status.value,
                attempted_action=action,
            )

    def _assert_not_terminal(self) -> None:
        """Refuse any action on a terminal-state pack (published or rejected).

        Called by :meth:`submit_for_review`, :meth:`approve`,
        :meth:`request_changes`, :meth:`reject`, and :meth:`publish` to
        short-circuit any operation on a pack that has already reached
        a terminal state.
        """
        if self._status == ContentStatus.PUBLISHED:
            raise ContentPackAlreadyPublished(self._id)
        if self._status == ContentStatus.REJECTED:
            raise ContentPackAlreadyRejected(self._id)

    # ------------------------------------------------------------------
    # Artifact management (only allowed in draft)
    # ------------------------------------------------------------------

    def add_artifact(self, kind: str, artifact_id: Any) -> None:
        """Add an artifact reference to the pack.

        Args:
            kind: The artifact kind (e.g., ``"concept"``,
                ``"question_template"``, ``"template_version"``).
            artifact_id: The typed id of the artifact.

        Raises:
            InvalidStateTransition: If the pack is not in ``draft``.
            InvariantViolation: If ``kind`` is empty or ``artifact_id``
                is already in the list for ``kind``.
        """
        self._assert_status(ContentStatus.DRAFT, "add_artifact")
        if not isinstance(kind, str) or not kind.strip():
            raise InvariantViolation(
                "ContentPack",
                "artifact kind must be a non-empty string",
            )
        bucket = self._artifact_ids.setdefault(kind, [])
        if artifact_id in bucket:
            raise InvariantViolation(
                "ContentPack",
                f"artifact {artifact_id!r} already in pack under kind {kind!r}",
            )
        bucket.append(artifact_id)

    def remove_artifact(self, kind: str, artifact_id: Any) -> None:
        """Remove an artifact reference from the pack.

        Args:
            kind: The artifact kind the id was added under.
            artifact_id: The typed id of the artifact to remove.

        Raises:
            InvalidStateTransition: If the pack is not in ``draft``.
            InvariantViolation: If ``kind`` is unknown or ``artifact_id``
                is not in the list for ``kind``.
        """
        self._assert_status(ContentStatus.DRAFT, "remove_artifact")
        bucket = self._artifact_ids.get(kind)
        if bucket is None or artifact_id not in bucket:
            raise InvariantViolation(
                "ContentPack",
                f"artifact {artifact_id!r} not in pack under kind {kind!r}",
            )
        bucket.remove(artifact_id)

    # ------------------------------------------------------------------
    # Lifecycle: submit / approve / request_changes / reject / publish
    # ------------------------------------------------------------------

    def submit_for_review(self) -> None:
        """Transition the pack from ``draft`` to ``in_review``.

        Pre-state: ``draft``.
        Post-state: ``in_review`` with no approved stages (a fresh
        review cycle starts here).

        Raises:
            ContentPackAlreadySubmitted: If the pack is already in
                ``in_review``.
            ContentPackAlreadyPublished: If the pack is published.
            ContentPackAlreadyRejected: If the pack is rejected.
            InvalidStateTransition: If the pack is in any other state.
        """
        self._assert_not_terminal()
        if self._status == ContentStatus.IN_REVIEW:
            raise ContentPackAlreadySubmitted(self._id)
        self._assert_status(ContentStatus.DRAFT, "submit_for_review")

        self._status = ContentStatus.IN_REVIEW
        # A fresh submission clears any stale approvals from a prior cycle.
        self._approved_stages = set()
        self._record_event(
            ContentPackSubmittedForReview(
                content_pack_id=self._id,
                subject_id=self._subject_id,
                author_id=self._author_id,
            )
        )

    def approve(self, stage: ReviewStage, reviewer_id: UserId) -> None:
        """Record a reviewer's approval at ``stage``.

        The pack stays in ``in_review`` status — multiple stages must
        approve (see :attr:`required_stages`) before :meth:`publish` is
        allowed.

        Args:
            stage: The review stage being approved. Must be in
                :attr:`required_stages`.
            reviewer_id: The user recording the approval. Recorded on
                the event for audit.

        Raises:
            ContentPackAlreadyPublished: If the pack is published.
            ContentPackAlreadyRejected: If the pack is rejected.
            ContentPackNotInReview: If the pack is in ``draft``.
            ContentPackStageAlreadyApproved: If ``stage`` has already
                approved this submission cycle.
            InvariantViolation: If ``stage`` is not in
                :attr:`required_stages`.
        """
        self._assert_not_terminal()
        if self._status != ContentStatus.IN_REVIEW:
            raise ContentPackNotInReview(self._id, self._status.value)
        if stage not in self._required_stages:
            raise InvariantViolation(
                "ContentPack",
                f"stage {stage!r} is not in required_stages {sorted(s.value for s in self._required_stages)!r}",
            )
        if stage in self._approved_stages:
            raise ContentPackStageAlreadyApproved(self._id, stage)

        self._approved_stages.add(stage)
        self._record_event(
            ContentPackApproved(
                content_pack_id=self._id,
                subject_id=self._subject_id,
                stage=stage,
                reviewer_id=reviewer_id,
            )
        )

    def request_changes(self, reviewer_id: UserId, notes: str) -> None:
        """Return the pack to ``draft`` with reviewer notes attached.

        Pre-state: ``in_review``.
        Post-state: ``draft`` with ``notes`` appended to
        :attr:`change_request_notes` and all stage approvals cleared
        (a fresh review cycle is required after the author re-submits).

        Args:
            reviewer_id: The user requesting the changes.
            notes: A human-readable description of the requested
                changes. Recorded for the author.

        Raises:
            ContentPackAlreadyPublished: If the pack is published.
            ContentPackAlreadyRejected: If the pack is rejected.
            ContentPackNotInReview: If the pack is in ``draft``.
            InvariantViolation: If ``notes`` is empty or too long.
        """
        self._assert_not_terminal()
        if self._status != ContentStatus.IN_REVIEW:
            raise ContentPackNotInReview(self._id, self._status.value)
        if not isinstance(notes, str) or not notes.strip():
            raise InvariantViolation(
                "ContentPack",
                "notes must be a non-empty string",
            )
        if len(notes) > self.MAX_NOTES_LENGTH:
            raise InvariantViolation(
                "ContentPack",
                f"notes must be at most {self.MAX_NOTES_LENGTH} characters",
            )
        cleaned = notes.strip()

        self._status = ContentStatus.DRAFT
        self._approved_stages = set()
        self._change_request_notes.append(
            {
                "reviewer_id": reviewer_id,
                "notes": cleaned,
                "at": _utcnow(),
            }
        )
        self._record_event(
            ContentPackChangesRequested(
                content_pack_id=self._id,
                subject_id=self._subject_id,
                reviewer_id=reviewer_id,
                notes=cleaned,
            )
        )

    def reject(self, reviewer_id: UserId, reason: str) -> None:
        """Transition the pack from ``in_review`` to ``rejected`` (terminal).

        Pre-state: ``in_review``.
        Post-state: ``rejected`` with ``reason`` recorded. The pack
        cannot be re-opened — the author must create a new ContentPack
        with the requested corrections.

        Args:
            reviewer_id: The user rejecting the pack.
            reason: A human-readable reason for the rejection.

        Raises:
            ContentPackAlreadyPublished: If the pack is published.
            ContentPackAlreadyRejected: If the pack is already rejected.
            ContentPackNotInReview: If the pack is in ``draft``.
            InvariantViolation: If ``reason`` is empty or too long.
        """
        self._assert_not_terminal()
        if self._status != ContentStatus.IN_REVIEW:
            raise ContentPackNotInReview(self._id, self._status.value)
        if not isinstance(reason, str) or not reason.strip():
            raise InvariantViolation(
                "ContentPack",
                "reason must be a non-empty string",
            )
        if len(reason) > self.MAX_REASON_LENGTH:
            raise InvariantViolation(
                "ContentPack",
                f"reason must be at most {self.MAX_REASON_LENGTH} characters",
            )
        cleaned = reason.strip()

        self._status = ContentStatus.REJECTED
        self._record_event(
            ContentPackRejected(
                content_pack_id=self._id,
                subject_id=self._subject_id,
                reviewer_id=reviewer_id,
                reason=cleaned,
            )
        )

    def publish(
        self,
        content_version_id: ContentVersionId,
        now: datetime | None = None,
    ) -> None:
        """Transition the pack from ``in_review`` to ``published`` and bind it to ``content_version_id``.

        Pre-state: ``in_review`` with every required :class:`ReviewStage`
        approved (see :attr:`is_review_complete`).
        Post-state: ``published`` with ``content_version_id`` and
        ``published_at`` set.

        The application service is responsible, in the same
        transaction, for marking the bound :class:`ContentVersion` as
        published (see :meth:`ContentVersion.publish`) — that step
        lives outside this aggregate because ContentVersion has its
        own repository and is not part of the ContentPack aggregate
        boundary.

        Args:
            content_version_id: The :class:`ContentVersion` to bind
                this pack's artifacts to. Must already exist (the
                application service creates it or selects an existing
                one).
            now: Optional timestamp (for testing); defaults to UTC now.

        Raises:
            ContentPackAlreadyPublished: If the pack is already
                ``published``.
            ContentPackAlreadyRejected: If the pack is ``rejected``.
            ContentPackNotInReview: If the pack is ``draft`` (must be
                submitted for review first).
            ContentPackReviewIncomplete: If not every required review
                stage has approved.
        """
        self._assert_not_terminal()
        if self._status != ContentStatus.IN_REVIEW:
            raise ContentPackNotInReview(self._id, self._status.value)
        if not self.is_review_complete:
            raise ContentPackReviewIncomplete(self._id, self.missing_stages)

        timestamp = now or _utcnow()
        self._status = ContentStatus.PUBLISHED
        self._content_version_id = content_version_id
        self._published_at = timestamp
        self._record_event(
            ContentPackPublished(
                content_pack_id=self._id,
                subject_id=self._subject_id,
                content_version_id=content_version_id,
                published_at=timestamp,
            )
        )

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"ContentPack(id={self._id}, subject_id={self._subject_id}, "
            f"author_id={self._author_id}, name={self._name!r}, "
            f"status={self._status.value!r}, "
            f"approved_stages={sorted(s.value for s in self._approved_stages)!r})"
        )


__all__ = ["DEFAULT_REQUIRED_STAGES", "ContentPack"]
