from beanie import Link
from pydantic import Field
from datetime import datetime, timezone
from eron.core.base.base import BaseCollection
from eron.users.models.user_models import UserModel


class ChatMessageModel(BaseCollection):

    sender: Link[UserModel]
    receiver: Link[UserModel]

    message: str
    is_read: bool = Field(default=False)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "chat_messages"