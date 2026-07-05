"""WebSocket endpoint for real-time notifications.

Provides:
- Live notification delivery
- Dashboard updates
- Session expiration warnings
- Achievement unlocks

Endpoint: GET /api/v1/ws  (WebSocket upgrade)
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy import select, and_
from app.application.shared import UnitOfWork
from app.infrastructure.database.orm.identity import UserModel, SessionModel
from app.infrastructure.database.orm.background import NotificationModel
from app.shared.config import get_settings
from app.shared.logging import get_logger
import jwt

logger = get_logger(__name__)
router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self._connections: dict[UUID, WebSocket] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket):
        await websocket.accept()
        self._connections[user_id] = websocket
        logger.info("ws_connected", user_id=str(user_id))
        await self._send_initial_data(user_id, websocket)

    def disconnect(self, user_id: UUID):
        if user_id in self._connections:
            del self._connections[user_id]
        logger.info("ws_disconnected", user_id=str(user_id))

    async def send_to_user(self, user_id: UUID, message: dict):
        ws = self._connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(user_id)

    async def broadcast(self, message: dict):
        for user_id, ws in list(self._connections.items()):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(user_id)

    @property
    def connected_count(self) -> int:
        return len(self._connections)

    async def _send_initial_data(self, user_id: UUID, websocket: WebSocket):
        """Send initial data on connect."""
        try:
            await websocket.send_json({
                "type": "connection_ack",
                "payload": {
                    "user_id": str(user_id),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": "Connected to MasteryOS real-time server",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            pass


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """WebSocket endpoint for real-time updates.

    Connect with: wss://api.example.com/api/v1/ws?token=YOUR_JWT_TOKEN

    The token is validated as a RS256 JWT. Once connected, the server sends:
    - connection_ack: Initial connection confirmation
    - notification: New notifications as they're created
    - ping: Heartbeat every 30 seconds (respond with pong)
    """
    # Validate JWT token
    settings = get_settings()
    user_id = None

    try:
        # Decode JWT — verify_access_token returns a TokenClaims dataclass.
        from app.infrastructure.security.jwt_service import JWTService, JWTKeyManager
        key_manager = JWTKeyManager(keys_dir=settings.jwt_keys_dir) if settings.jwt_keys_dir else None
        jwt_service = JWTService(
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            key_manager=key_manager,
        )
        claims = jwt_service.verify_access_token(token)
        # TokenClaims is a dataclass — access .user_id, NOT .get("sub")
        if claims is not None and claims.user_id is not None:
            user_id = UUID(str(claims.user_id))
    except Exception as exc:
        logger.warning("ws_auth_failed", error=str(exc))
        await websocket.close(code=4001, reason="Authentication failed")
        return

    if not user_id:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Accept connection
    await manager.connect(user_id, websocket)

    # Start heartbeat task
    async def heartbeat():
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_json({
                    "type": "ping",
                    "payload": {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                break

    heartbeat_task = asyncio.create_task(heartbeat())

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")

                if msg_type == "pong":
                    continue  # Heartbeat response
                elif msg_type == "subscribe":
                    # Client subscribing to specific event types
                    await websocket.send_json({
                        "type": "subscription_ack",
                        "payload": {"channels": msg.get("payload", {}).get("channels", [])},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                elif msg_type == "get_notifications":
                    # Fetch unread notifications
                    engine = None
                    try:
                        from sqlalchemy.ext.asyncio import create_async_engine
                        from sqlalchemy.ext.asyncio import AsyncSession
                        engine = create_async_engine(settings.database_url)
                        async with AsyncSession(engine) as session:
                            result = await session.execute(
                                select(NotificationModel)
                                .where(
                                    and_(
                                        NotificationModel.user_id == user_id,
                                        NotificationModel.status.in_(["queued", "sent", "delivered"]),
                                    )
                                )
                                .order_by(NotificationModel.created_at.desc())
                                .limit(10)
                            )
                            notifications = result.scalars().all()
                            await websocket.send_json({
                                "type": "notifications",
                                "payload": {
                                    "notifications": [
                                        {
                                            "id": str(n.id),
                                            "type": n.notification_type,
                                            "title": n.title,
                                            "message": n.body,
                                            "priority": n.priority,
                                            "created_at": n.created_at.isoformat() if n.created_at else None,
                                        }
                                        for n in notifications
                                    ]
                                },
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })
                    except Exception as exc:
                        logger.warning("ws_fetch_notifications_failed", error=str(exc))
                        await websocket.send_json({
                            "type": "notifications",
                            "payload": {"notifications": []},
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                    finally:
                        if engine:
                            await engine.dispose()
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "payload": {"message": "Invalid JSON"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        heartbeat_task.cancel()
    except Exception as exc:
        logger.warning("ws_error", error=str(exc))
        manager.disconnect(user_id)
        heartbeat_task.cancel()


def get_connection_manager() -> ConnectionManager:
    """Get the singleton WebSocket connection manager."""
    return manager
