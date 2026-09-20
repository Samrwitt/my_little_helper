import logging

from app.core.config import get_settings
from app.core.enums import NotificationChannel
from app.models import Notification, User
from app.services.notifications.base import NotificationProvider

logger = logging.getLogger(__name__)


class InAppNotificationProvider(NotificationProvider):
    channel = NotificationChannel.IN_APP

    async def send(self, user: User, notification: Notification) -> bool:
        return True


class EmailNotificationProvider(NotificationProvider):
    channel = NotificationChannel.EMAIL

    def __init__(self) -> None:
        self.settings = get_settings()

    async def send(self, user: User, notification: Notification) -> bool:
        if not self.settings.smtp_host:
            logger.info(
                "EMAIL (console): to=%s subject=%s body=%s",
                user.email,
                notification.title,
                notification.body,
            )
            return True
        try:
            import aiosmtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg["From"] = self.settings.email_from
            msg["To"] = user.email
            msg["Subject"] = notification.title
            msg.set_content(notification.body)
            await aiosmtplib.send(
                msg,
                hostname=self.settings.smtp_host,
                port=self.settings.smtp_port,
                username=self.settings.smtp_user or None,
                password=self.settings.smtp_password or None,
                start_tls=True,
            )
            return True
        except Exception:
            logger.exception("Failed to send email notification")
            return False


class TelegramNotificationProvider(NotificationProvider):
    channel = NotificationChannel.TELEGRAM

    async def send(self, user: User, notification: Notification) -> bool:
        logger.debug("Telegram provider not configured")
        return False


class SMSNotificationProvider(NotificationProvider):
    channel = NotificationChannel.SMS

    async def send(self, user: User, notification: Notification) -> bool:
        logger.debug("SMS provider not configured")
        return False


class WhatsAppNotificationProvider(NotificationProvider):
    channel = NotificationChannel.WHATSAPP

    async def send(self, user: User, notification: Notification) -> bool:
        logger.debug("WhatsApp provider not configured")
        return False


class PushNotificationProvider(NotificationProvider):
    channel = NotificationChannel.PUSH

    async def send(self, user: User, notification: Notification) -> bool:
        logger.debug("Push provider not configured")
        return False


class GoogleCalendarNotificationProvider(NotificationProvider):
    channel = NotificationChannel.GOOGLE_CALENDAR

    async def send(self, user: User, notification: Notification) -> bool:
        logger.debug("Google Calendar provider not configured")
        return False
