from beanie import before_event, Replace, Save, Link
from pydantic import Field
from datetime import datetime, timezone
from typing import Optional
from eron.core.base.base import BaseCollection
from eron.users.models.user_models import UserModel

class LiveStreamModel(BaseCollection):
    host: Link[UserModel]
    agora_channel_name: str = Field(unique=True)
    is_premium: bool = False
    entry_fee: int = 0
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    total_like: int = 0
    total_comment: int = 0
    status: str = "live"

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Replace])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "livestreams"



class LiveViewerModel(BaseCollection):
    session: Link[LiveStreamModel]
    user: Link[UserModel]
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fee_paid: int = 0

    class Settings:
        name = "live_viewers"


class LiveCommentModel(BaseCollection):
    session: Link[LiveStreamModel]
    user: Link[UserModel]
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "live_comments"