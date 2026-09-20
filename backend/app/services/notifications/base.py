from abc import ABC, abstractmethod

from app.core.enums import NotificationChannel
from app.models import Notification, User


class NotificationProvider(ABC):
    channel: NotificationChannel

    @abstractmethod
    async def send(self, user: User, notification: Notification) -> bool:
        ...
