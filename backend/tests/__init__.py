"""Backend test suite.

Tests are organized by layer:
- unit/: domain services, use case services (fakes, no I/O)
- integration/: repository tests against real PostgreSQL
- api/: API endpoint tests against FastAPI TestClient

No business tests yet (per Task 007). Only infrastructure tests.
"""
