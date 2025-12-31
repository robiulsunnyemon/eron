from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class LiveStartRequest(BaseModel):
    is_premium: bool = False
    entry_fee: int = 0


class LiveJoinRequest(BaseModel):
    channel_name: str


class LiveStreamResponse(BaseModel):
    id: str
    host_id: str
    agora_channel_name: str
    token: str
    is_premium: bool
    entry_fee: int
    status: str
    start_time: datetime

    class Config:
        from_attributes = True