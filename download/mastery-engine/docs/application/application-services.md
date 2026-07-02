# Application Services

> Orchestration services for workflows that span multiple handlers.

---

## What are Application Services?

Application Services are thin orchestration classes that coordinate multiple command handlers and query handlers to implement end-to-end workflows. They do NOT contain business rules; they compose commands and queries.

## Planned Services

### LearningApplicationService

Coordinates the learning loop workflow:
1. Start study session (command)
2. Get adaptive queue (query)
3. Submit attempt (command)
4. Update mastery (command, triggered by event)
5. Get updated dashboard (query)

```python
class LearningApplicationService:
    def __init__(self, uow, event_publisher):
        self._start_session = StartStudySessionHandler(uow, event_publisher)
        self._submit_attempt = SubmitAttemptHandler(uow, event_publisher)
        self._update_mastery = UpdateMasteryHandler(uow, event_publisher)
        self._get_dashboard = GetDashboardHandler(uow)

    async def run_learning_session(self, enrollment_id, questions):
        """Run a complete study session with N questions."""
        session = await self._start_session.handle(
            StartStudySessionCommand(enrollment_id=enrollment_id)
        )
        for question in questions:
            result = await self._submit_attempt.handle(
                SubmitAttemptCommand(...)
            )
        await self._end_session.handle(
            EndStudySessionCommand(session_id=session.value.id)
        )
```

### ContentApplicationService

Coordinates content publishing workflow:
1. Create content pack (command)
2. Submit for review (command)
3. Approve at each stage (command)
4. Publish (command)

### IdentityApplicationService

Coordinates user lifecycle:
1. Register (command)
2. Verify email (command)
3. Enroll in subject (command)
4. Complete onboarding (command)

## When to Use Application Services

- **Multi-step workflows** that span multiple commands.
- **Saga-like flows** where each step depends on the previous.
- **Cross-context coordination** (e.g., SubmitAttempt in Assessment → UpdateMastery in Mastery).

## When NOT to Use Application Services

- Single command — use the handler directly.
- Simple queries — use the query handler directly.
- Business logic — belongs in the domain layer.
