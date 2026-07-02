"""Infrastructure layer — connects the Application Layer to PostgreSQL and external systems.

This layer implements the interfaces defined by the Domain and Application layers.
It hides SQLAlchemy completely; the Application Layer never sees an ORM model.

Modules:
- database/engine.py: Async SQLAlchemy engine + session factory
- database/orm/: SQLAlchemy ORM models (persistence models only)
- database/mappers/: Bidirectional domain ⇄ ORM mappers
- database/repositories/: Repository implementations
- database/unit_of_work/: AsyncUnitOfWork (transaction management)
- events/outbox/: Transactional outbox dispatcher + serializer
- cache/: Redis + local cache abstractions
- clock/: Injectable clock (system + fixed for tests)
- ids/: UUID v7 generation
"""

from app.infrastructure.database.engine import (
    check_database_health,
    close_database,
    get_db_session,
    get_engine,
    get_session_factory,
    init_database,
)
from app.infrastructure.database.unit_of_work import AsyncUnitOfWork, OutboxEventWriter
from app.infrastructure.events.outbox.dispatcher import OutboxDispatcher
from app.infrastructure.events.outbox.serializer import EventSerializer
from app.infrastructure.clock import Clock, FixedClock, SystemClock
from app.infrastructure.ids import (
    DeterministicIdGenerator,
    IdGenerator,
    UuidV4Generator,
    UuidV7Generator,
)
from app.infrastructure.cache import Cache, LocalCache, RedisCache

__all__ = [
    # Database
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "init_database",
    "close_database",
    "check_database_health",
    # Unit of Work
    "AsyncUnitOfWork",
    "OutboxEventWriter",
    # Outbox
    "OutboxDispatcher",
    "EventSerializer",
    # Clock
    "Clock",
    "SystemClock",
    "FixedClock",
    # IDs
    "IdGenerator",
    "UuidV7Generator",
    "UuidV4Generator",
    "DeterministicIdGenerator",
    # Cache
    "Cache",
    "RedisCache",
    "LocalCache",
]
