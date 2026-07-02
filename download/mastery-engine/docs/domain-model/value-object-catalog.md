# Value Object Catalog

> Every value object in the Mastery Engine domain model with its validation rules and immutability guarantees.

---

## What is a Value Object?

A value object is immutable, compared by value (not identity), and has no lifecycle. Two value objects with the same attributes are interchangeable. All value objects use `@dataclass(frozen=True)`.

---

## Score Value Objects (ADR-0008)

### MasteryValue
- **Purpose:** Durable mastery estimate [0.0, 1.0]. Slower to rise and fall.
- **Validation:** Must be 0.0–1.0; raises `InvariantViolation` otherwise.
- **Methods:** `zero()`, `full()`, `is_above(threshold)`, `is_below(threshold)`, `clamp(min, max)`.
- **Immutability:** Frozen dataclass; `AttributeError` on mutation.

### MemoryValue
- **Purpose:** Short-term recall probability [0.0, 1.0]. Decays with time.
- **Validation:** Must be 0.0–1.0.
- **Methods:** `zero()`, `full()`, `is_below(threshold)`, `decay(rate, days)`.
- **Immutability:** Frozen dataclass.

### Confidence
- **Purpose:** Uncertainty around a mastery estimate [0.0, 1.0]. Narrower = more certain.
- **Validation:** Must be 0.0–1.0.
- **Methods:** `full()`, `none()`, `is_significant(threshold=0.15)`.

---

## Quantitative Value Objects

### Percentage
- **Purpose:** A percentage [0.0, 100.0].
- **Validation:** Must be 0.0–100.0.
- **Methods:** `from_fraction(float)`, `to_fraction() → float`.

### Duration
- **Purpose:** A time duration in seconds. Always non-negative.
- **Validation:** Must be ≥ 0.
- **Methods:** `from_milliseconds(int)`, `from_minutes(int)`, `from_hours(int)`, `.milliseconds`, `.minutes`, `.hours`, `__add__`, `__sub__`.

### ReviewInterval
- **Purpose:** Duration between reviews (days). Bounded [1, 365].
- **Validation:** Must be 1–365 days.
- **Methods:** `minimum()`, `maximum()`, `expand(factor)`, `contract(factor)`, `to_timedelta()`.

---

## Identity Value Objects

### Email
- **Purpose:** Validated, normalized email address.
- **Validation:** Must match RFC-like pattern; normalized to lowercase; whitespace stripped.
- **Properties:** `.domain`, `.local_part`.
- **Immutability:** Frozen dataclass.

### CorrelationId
- **Purpose:** Tracing ID for cross-service requests.
- **Validation:** Must not be empty.

### RequestId
- **Purpose:** Unique request identifier.
- **Validation:** Must not be empty.

---

## Versioning Value Objects

### VersionNumber
- **Purpose:** Monotonically increasing version (starts at 1).
- **Validation:** Must be ≥ 1.
- **Methods:** `next()`, `is_after(other)`.

---

## Money Value Object

### Money
- **Purpose:** Monetary amount with currency (stored as integer cents).
- **Validation:** `cents` ≥ 0; `currency` must be 3-char ISO 4217.
- **Methods:** `from_dollars(float, currency)`, `to_dollars()`, `__add__`, `__sub__` (same currency only).

---

## Date Range Value Object

### DateRange
- **Purpose:** Inclusive date range [start, end].
- **Validation:** `start_date` must be ≤ `end_date`.
- **Properties:** `.days` (inclusive count).
- **Methods:** `contains(date)`, `overlaps(other)`.

---

## Content Value Objects

### DifficultyEstimate
- **Purpose:** Authored prior of a question's difficulty (easy/medium/hard).
- **Methods:** `easy()`, `medium()`, `hard()`, `.numeric` (0.25/0.50/0.75).

### DiscriminationEstimate
- **Purpose:** Authored prior of how well a template separates mastered from non-mastered learners.
- **Validation:** Must be 0.0–1.0.

---

## Typed Identifiers (Value Objects)

All typed IDs inherit from `_BaseId(ValueObject)` and are frozen dataclasses wrapping a UUID.

### Identity IDs
- `UserId`, `SessionId`, `CredentialId`

### Content IDs
- `TenantId`, `SubjectId`, `LearningPathId`, `ConceptId`, `LearningObjectiveId`, `MisconceptionId`, `QuestionTemplateId`, `TemplateVersionId`, `ContentVersionId`, `ContentPackId`

### Learning IDs
- `LearnerEnrollmentId`, `StudySessionId`, `LearningSessionId`, `LearningGoalId`, `StudyPlanId`, `RecommendationId`, `AchievementId`, `AchievementTypeId`

### Assessment IDs
- `QuestionInstanceId`, `AttemptId`, `AnswerId`

### Mastery IDs
- `MasteryScoreId`, `ReviewId`, `AlgorithmVersionId`, `LearnerMisconceptionId`

### Scheduling IDs
- `SchedulingConfigId`, `DailyQueueId`

### Billing IDs
- `BillingPlanId`, `SubscriptionId`, `InvoiceId`

### Administration IDs
- `AuditLogId`, `FeatureFlagId`, `GdprRequestId`, `OrganizationId`, `NotificationId`

All IDs have:
- `generate()` → creates with a random UUID v4.
- `from_string(str)` → creates from a UUID string.
- `__str__` → returns the UUID string.
- Type safety: `UserId(uuid) != ConceptId(uuid)` (different dataclass types).
