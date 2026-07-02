# Repository Contracts

> Every abstract repository interface in the Mastery Engine domain model with its method contracts.

---

## What is a Repository Interface?

A repository interface is an abstract base class (ABC) defining the contract for loading and saving aggregates. The domain layer defines the interface; the infrastructure layer provides the implementation (SQLAlchemy, Redis, etc.). No repository interface contains SQL, ORM code, or I/O logic.

---

## Repositories by Context

### Identity

#### UserRepository(ABC)
```python
async def get_by_id(id: UserId) -> User | None
async def get_by_email(email: Email) -> User | None
async def add(user: User) -> User
async def save(user: User) -> None
```
- **Contract:** `add` creates a new user; `save` updates an existing user. `get_by_email` is case-insensitive (email is normalized).

### Content

#### SubjectRepository(ABC)
```python
async def get_by_id(id: SubjectId) -> Subject | None
async def get_by_slug(slug: str) -> Subject | None
async def get_by_code(code: str) -> Subject | None
async def list_published() -> Sequence[Subject]
async def add(subject: Subject) -> Subject
async def save(subject: Subject) -> None
```

#### ConceptRepository(ABC)
```python
async def get_by_id(id: ConceptId) -> Concept | None
async def get_by_slug(subject_id: SubjectId, slug: str) -> Concept | None
async def list_by_subject(subject_id: SubjectId, include_archived: bool = False) -> Sequence[Concept]
async def add(concept: Concept) -> Concept
async def save(concept: Concept) -> None
```

#### QuestionTemplateRepository(ABC)
```python
async def get_by_id(id: QuestionTemplateId) -> QuestionTemplate | None
async def get_by_code(subject_id: SubjectId, code: str) -> QuestionTemplate | None
async def list_by_subject(subject_id: SubjectId) -> Sequence[QuestionTemplate]
async def add(template: QuestionTemplate) -> QuestionTemplate
async def save(template: QuestionTemplate) -> None
```

#### ContentVersionRepository(ABC)
```python
async def get_by_id(id: ContentVersionId) -> ContentVersion | None
async def get_active_by_subject(subject_id: SubjectId) -> ContentVersion | None
async def add(version: ContentVersion) -> ContentVersion
```

#### ContentPackRepository(ABC)
```python
async def get_by_id(id: ContentPackId) -> ContentPack | None
async def list_by_status(status: ContentStatus) -> Sequence[ContentPack]
async def add(pack: ContentPack) -> ContentPack
async def save(pack: ContentPack) -> None
```

### Assessment

#### QuestionInstanceRepository(ABC)
```python
async def get_by_id(id: QuestionInstanceId) -> QuestionInstance | None
async def add(instance: QuestionInstance) -> QuestionInstance
async def save(instance: QuestionInstance) -> None
async def list_by_session(session_id: StudySessionId) -> Sequence[QuestionInstance]
```

#### AttemptRepository(ABC)
```python
async def get_by_id(id: AttemptId) -> Attempt | None
async def add(attempt: Attempt) -> Attempt  # append-only — no save/update
async def list_by_enrollment(enrollment_id: LearnerEnrollmentId, limit: int = 100, offset: int = 0) -> Sequence[Attempt]
async def list_by_enrollment_and_concept(enrollment_id: LearnerEnrollmentId, concept_id: UUID) -> Sequence[Attempt]
async def count_by_enrollment(enrollment_id: LearnerEnrollmentId) -> int
```
- **Note:** No `save` method — attempts are append-only (I1 invariant). The `list_by_enrollment_and_concept` method is the primary query for mastery recompute.

### Mastery

#### MasteryScoreRepository(ABC)
```python
async def get_by_id(id: MasteryScoreId) -> MasteryScore | None
async def get_by_enrollment_and_concept(enrollment_id: LearnerEnrollmentId, concept_id: ConceptId) -> MasteryScore | None
async def list_by_enrollment(enrollment_id: LearnerEnrollmentId) -> Sequence[MasteryScore]
async def list_weak_by_enrollment(enrollment_id: LearnerEnrollmentId) -> Sequence[MasteryScore]
async def add(score: MasteryScore) -> MasteryScore
async def save(score: MasteryScore) -> None  # optimistic concurrency: checks version
async def count_by_algorithm_version(algorithm_version_id: AlgorithmVersionId) -> int
```
- **Note:** `save` must implement optimistic concurrency (check `version` field; raise on mismatch). Single-writer: only the Mastery Engine writes (M3 invariant).

#### ReviewRepository(ABC)
```python
async def get_by_id(id: ReviewId) -> Review | None
async def get_by_enrollment_and_concept(enrollment_id: LearnerEnrollmentId, concept_id: ConceptId) -> Review | None
async def list_due_by_enrollment(enrollment_id: LearnerEnrollmentId) -> Sequence[Review]
async def add(review: Review) -> Review
async def save(review: Review) -> None
```

#### AlgorithmVersionRepository(ABC)
```python
async def get_by_id(id: AlgorithmVersionId) -> AlgorithmVersion | None
async def get_active() -> AlgorithmVersion | None
async def list_all() -> Sequence[AlgorithmVersion]
async def add(version: AlgorithmVersion) -> AlgorithmVersion
async def save(version: AlgorithmVersion) -> None
```

### Learning

#### EnrollmentRepository(ABC)
```python
async def get_by_id(id: LearnerEnrollmentId) -> LearnerEnrollment | None
async def get_by_user_and_subject(user_id: UserId, subject_id: SubjectId) -> LearnerEnrollment | None
async def list_by_user(user_id: UserId) -> Sequence[LearnerEnrollment]
async def add(enrollment: LearnerEnrollment) -> LearnerEnrollment
async def save(enrollment: LearnerEnrollment) -> None
```

#### StudySessionRepository(ABC)
```python
async def get_by_id(id: StudySessionId) -> StudySession | None
async def get_active_by_enrollment(enrollment_id: LearnerEnrollmentId) -> StudySession | None
async def list_by_enrollment(enrollment_id: LearnerEnrollmentId, limit: int = 50, offset: int = 0) -> Sequence[StudySession]
async def add(session: StudySession) -> StudySession
async def save(session: StudySession) -> None
```

#### LearningGoalRepository(ABC)
```python
async def get_by_id(id: LearningGoalId) -> LearningGoal | None
async def get_active_by_enrollment(enrollment_id: LearnerEnrollmentId) -> Sequence[LearningGoal]
async def add(goal: LearningGoal) -> LearningGoal
async def save(goal: LearningGoal) -> None
```

#### RecommendationRepository(ABC)
```python
async def get_by_id(id: RecommendationId) -> Recommendation | None
async def list_by_enrollment(enrollment_id: LearnerEnrollmentId, active_only: bool = False) -> Sequence[Recommendation]
async def add(recommendation: Recommendation) -> Recommendation
async def save(recommendation: Recommendation) -> None
```

#### AchievementRepository(ABC)
```python
async def get_by_enrollment_and_type(enrollment_id: LearnerEnrollmentId, achievement_type_id: AchievementTypeId) -> Achievement | None
async def list_by_enrollment(enrollment_id: LearnerEnrollmentId) -> Sequence[Achievement]
async def add(achievement: Achievement) -> Achievement
```

#### StreakRepository(ABC)
```python
async def get_by_enrollment(enrollment_id: LearnerEnrollmentId) -> Streak | None
async def save(streak: Streak) -> None
```

### Scheduling

#### SchedulingConfigRepository(ABC)
```python
async def get_by_id(id: SchedulingConfigId) -> SchedulingConfig | None
async def get_active_by_subject(subject_id: SubjectId) -> SchedulingConfig | None
async def add(config: SchedulingConfig) -> SchedulingConfig
async def save(config: SchedulingConfig) -> None
```

#### DailyQueueRepository(ABC)
```python
async def get_by_id(id: DailyQueueId) -> DailyQueue | None
async def get_by_enrollment_and_date(enrollment_id: LearnerEnrollmentId, queue_date: date) -> DailyQueue | None
async def add(queue: DailyQueue) -> DailyQueue
async def save(queue: DailyQueue) -> None
```

### Billing

#### BillingPlanRepository(ABC)
```python
async def get_by_id(id: BillingPlanId) -> BillingPlan | None
async def get_by_code(code: str, active_only: bool = True) -> BillingPlan | None
async def list_active() -> Sequence[BillingPlan]
async def add(plan: BillingPlan) -> BillingPlan
```

#### SubscriptionRepository(ABC)
```python
async def get_by_id(id: SubscriptionId) -> Subscription | None
async def get_active_by_user(user_id: UserId) -> Subscription | None
async def add(subscription: Subscription) -> Subscription
async def save(subscription: Subscription) -> None
```

#### InvoiceRepository(ABC)
```python
async def get_by_id(id: InvoiceId) -> Invoice | None
async def list_by_user(user_id: UserId, limit: int = 50) -> Sequence[Invoice]
async def add(invoice: Invoice) -> Invoice
async def save(invoice: Invoice) -> None
```

### Administration

#### AuditLogRepository(ABC)
```python
async def add(log: AuditLog) -> AuditLog  # append-only — no save/update
async def list_by_target(target_type: str, target_id: UUID, limit: int = 100) -> Sequence[AuditLog]
async def list_by_actor(actor_user_id: UUID, limit: int = 100) -> Sequence[AuditLog]
async def search(action: str | None = None, date_from: datetime | None = None, date_to: datetime | None = None, limit: int = 100) -> Sequence[AuditLog]
```
- **Note:** Append-only — no `save` or `update` method.

#### FeatureFlagRepository(ABC)
```python
async def get_by_id(id: FeatureFlagId) -> FeatureFlag | None
async def get_by_key(key: str) -> FeatureFlag | None
async def list_all(active_only: bool = False) -> Sequence[FeatureFlag]
async def add(flag: FeatureFlag) -> FeatureFlag
async def save(flag: FeatureFlag) -> None
```

#### NotificationRepository(ABC)
```python
async def get_by_id(id: NotificationId) -> Notification | None
async def list_by_user(user_id: UserId, status: str | None = None, limit: int = 50) -> Sequence[Notification]
async def list_queued(limit: int = 100) -> Sequence[Notification]
async def add(notification: Notification) -> Notification
async def save(notification: Notification) -> None
```

#### OrganizationRepository(ABC)
```python
async def get_by_id(id: OrganizationId) -> Organization | None
async def list_all() -> Sequence[Organization]
async def add(organization: Organization) -> Organization
async def save(organization: Organization) -> None
```
