# Mapping Strategy

> How mappers convert between domain entities and ORM models.

---

## Principles

1. **Mappers are the ONLY boundary** where ORM models and domain entities interact.
2. **No ORM leakage** — the application layer never sees an ORM model.
3. **Bidirectional** — both `from_orm()` and `to_orm()` are provided.
4. **No mapping logic in handlers** — all conversion lives in mapper classes.
5. **Mappers are stateless** — they use static methods; no instances needed.

## Pattern

```python
class UserMapper:
    @staticmethod
    def from_orm(model: UserModel) -> User:
        """ORM → Domain"""
        user = User.__new__(User)
        AggregateRoot.__init__(user)  # Initialize event collection
        user._id = UserId(model.id)
        user._email = Email(model.email)
        user._status = UserStatus(model.status)
        ...
        return user

    @staticmethod
    def to_orm(user: User) -> UserModel:
        """Domain → ORM"""
        return UserModel(
            id=user.id.value,
            email=user.email.value,
            status=user.status.value,
            ...
        )
```

## Why `__new__` instead of `__init__`?

Domain aggregates have factory methods (e.g., `User.register()`) that enforce invariants and record events. When loading from the database, we need to reconstruct the aggregate WITHOUT re-running the factory (which would re-validate and re-emit events).

`__new__` creates the object without calling `__init__`, then we set the fields directly. The `AggregateRoot.__init__` is called to initialize the event collection (empty — events were already published when the aggregate was originally created).

## Implemented Mappers

| Mapper | Domain Entity | ORM Model |
|---|---|---|
| `UserMapper` | `User` | `UserModel` |
| `UserProfileMapper` | `UserProfile` | `UserProfileModel` |
| `EnrollmentMapper` | `LearnerEnrollment` | `LearnerEnrollmentModel` |
| `StudySessionMapper` | `StudySession` | `StudySessionModel` |
| `QuestionInstanceMapper` | `QuestionInstance` | `QuestionInstanceModel` |
| `AttemptMapper` | `Attempt` | `AttemptModel` |
| `MasteryScoreMapper` | `MasteryScore` | `MasteryScoreModel` |
| `ReviewMapper` | `Review` | `ReviewModel` |
| `AlgorithmVersionMapper` | `AlgorithmVersion` | `AlgorithmVersionModel` |

## Value Object Conversion

Value objects are converted at the mapper boundary:

| Domain Value Object | ORM Column Type | Conversion |
|---|---|---|
| `Email` | `Text` | `email.value` ↔ `Email(text)` |
| `Duration` | `Integer` (ms) | `duration.milliseconds` ↔ `Duration.from_milliseconds(ms)` |
| `ReviewInterval` | `Text` (ISO 8601) | `f"P{interval.days}D"` ↔ `ReviewInterval(int(...))` |
| `VersionNumber` | `Integer` | `version.value` ↔ `VersionNumber(int)` |
| Enum values | `String` + CHECK | `enum.value` ↔ `EnumClass(string)` |
