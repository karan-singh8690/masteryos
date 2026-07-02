# Repository Implementation

> How repositories implement domain interfaces with SQLAlchemy 2.x async.

---

## Pattern

Each repository:
1. Implements the domain's abstract repository interface (ABC).
2. Takes an `AsyncSession` in its constructor.
3. Uses SQLAlchemy queries to load/save ORM models.
4. Uses mappers to convert between ORM models and domain entities.
5. Returns domain entities; never exposes ORM models.

```python
class SqlAlchemyUserRepository(UserRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UserId) -> User | None:
        model = await self._session.get(UserModel, id.value)
        return UserMapper.from_orm(model) if model else None

    async def add(self, user: User) -> User:
        model = UserMapper.to_orm(user)
        self._session.add(model)
        await self._session.flush()
        return user
```

## Implemented Repositories

| Repository | Domain Interface | ORM Model | Mapper |
|---|---|---|---|
| `SqlAlchemyUserRepository` | `UserRepository` | `UserModel` | `UserMapper` |
| `SqlAlchemyEnrollmentRepository` | `EnrollmentRepository` | `LearnerEnrollmentModel` | `EnrollmentMapper` |
| `SqlAlchemyStudySessionRepository` | `StudySessionRepository` | `StudySessionModel` | `StudySessionMapper` |
| `SqlAlchemyQuestionInstanceRepository` | `QuestionInstanceRepository` | `QuestionInstanceModel` | `QuestionInstanceMapper` |
| `SqlAlchemyAttemptRepository` | `AttemptRepository` | `AttemptModel` | `AttemptMapper` |
| `SqlAlchemyMasteryScoreRepository` | `MasteryScoreRepository` | `MasteryScoreModel` | `MasteryScoreMapper` |
| `SqlAlchemyReviewRepository` | `ReviewRepository` | `ReviewModel` | `ReviewMapper` |
| `SqlAlchemyAlgorithmVersionRepository` | `AlgorithmVersionRepository` | `AlgorithmVersionModel` | `AlgorithmVersionMapper` |

## Optimistic Concurrency

The `SqlAlchemyMasteryScoreRepository.save()` method implements optimistic concurrency:

```python
async def save(self, score: MasteryScore) -> None:
    stmt = (
        update(MasteryScoreModel)
        .where(
            MasteryScoreModel.id == model.id,
            MasteryScoreModel.version == model.version - 1,  # old version
        )
        .values(version=model.version, ...)
    )
    result = await self._session.execute(stmt)
    if result.rowcount == 0:
        raise ConcurrentUpdateError("Version conflict")
```

If another transaction updated the score between the read and the write, the `WHERE version = old` clause won't match, `rowcount` will be 0, and the repository raises `ConcurrentUpdateError`. The application layer retries (max 3).

## Append-Only Tables

The `SqlAlchemyAttemptRepository` has NO `save()` method — attempts are append-only (I1 invariant). The only way to add an attempt is `add()`; there is no update or delete.

This is enforced at three layers:
1. **Repository**: no `save()` method.
2. **Database**: REVOKE UPDATE, DELETE from the application role.
3. **Trigger**: BEFORE UPDATE/DELETE raises an exception.

## Query Optimization

- **Eager loading**: use `selectinload` for relationships when needed.
- **Pagination**: `LIMIT` + `OFFSET` with cursor-based pagination for large collections.
- **Batch loading**: `IN` clause for batch lookups.
- **Index usage**: queries use the indexes defined in Task 004.
- **Slow query logging**: queries > 100ms are logged as warnings.
