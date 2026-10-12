"""Notification adapter for user communication."""

from datetime import datetime
from typing import Dict, List
from pydantic import BaseModel


class NotificationRecord(BaseModel):
    notification_id: str
    account_id: str
    channel: str  # IN_APP, EMAIL, SMS
    title: str
    message: str
    timestamp: datetime
    status: str = "DELIVERED_IN_SANDBOX"


class MockNotificationAdapter:
    """Mock notification service logging dispatches safely in prototype mode."""

    def __init__(self):
        self.sent_notifications: List[NotificationRecord] = []

    def dispatch(
        self,
        account_id: str,
        title: str,
        message: str,
        channel: str = "IN_APP",
    ) -> NotificationRecord:
        record = NotificationRecord(
            notification_id=f"NOTIF_{len(self.sent_notifications) + 1:05d}",
            account_id=account_id,
            channel=channel,
            title=title,
            message=message,
            timestamp=datetime.utcnow(),
            status="DELIVERED_IN_SANDBOX",
        )
        self.sent_notifications.append(record)
        return record


notification_adapter = MockNotificationAdapter()
