import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import NotificationChannel
from app.models import Notification, User
from app.services.notifications.base import NotificationProvider
from app.services.notifications.providers import (
    EmailNotificationProvider,
    InAppNotificationProvider,
)

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: AsyncSession, providers: Optional[list[NotificationProvider]] = None):
        self.db = db
        self.providers = providers or [
            InAppNotificationProvider(),
            EmailNotificationProvider(),
        ]

    async def create_and_send(
        self,
        user: User,
        title: str,
        body: str,
        link: Optional[str] = None,
        channels: Optional[list[NotificationChannel]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[Notification]:
        channels = channels or [NotificationChannel.IN_APP, NotificationChannel.EMAIL]
        created: list[Notification] = []
        for channel in channels:
            n = Notification(
                user_id=user.id,
                channel=channel,
                title=title,
                body=body,
                link=link,
                metadata_json=metadata or {},
            )
            self.db.add(n)
            await self.db.flush()
            provider = next((p for p in self.providers if p.channel == channel), None)
            if provider:
                await provider.send(user, n)
            created.append(n)
        return created

    async def mark_read(self, user: User, notification_id: UUID) -> Notification:
        from fastapi import HTTPException, status

        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user.id,
            )
        )
        n = result.scalar_one_or_none()
        if not n:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        n.is_read = True
        await self.db.flush()
        return n

    async def list_for_user(self, user: User, unread_only: bool = False) -> list[Notification]:
        q = select(Notification).where(Notification.user_id == user.id)
        if unread_only:
            q = q.where(Notification.is_read.is_(False))
        q = q.order_by(Notification.created_at.desc()).limit(100)
        return list((await self.db.execute(q)).scalars().all())
