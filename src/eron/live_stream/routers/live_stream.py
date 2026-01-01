

import json
import time
import os
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from dotenv import load_dotenv
from eron.live_stream.models.live_stream import LiveStreamModel, LiveViewerModel, LiveCommentModel
from eron.users.utils.get_current_user import get_current_user
from agora_token_builder import RtcTokenBuilder

load_dotenv()

router = APIRouter(prefix="/live", tags=["Live Stream"])

APP_ID = os.getenv("AGORA_APP_ID")
APP_CERTIFICATE = os.getenv("AGORA_APP_CERTIFICATE")


class LiveConnectionManager:
    def __init__(self):
        self.active_rooms: dict = {}

    async def connect_to_room(self, websocket: WebSocket, channel_name: str):
        if channel_name not in self.active_rooms:
            self.active_rooms[channel_name] = []
        self.active_rooms[channel_name].append(websocket)
        await self.broadcast_viewer_count(channel_name)

    async def disconnect_from_room(self, websocket: WebSocket, channel_name: str):
        if channel_name in self.active_rooms:
            if websocket in self.active_rooms[channel_name]:
                self.active_rooms[channel_name].remove(websocket)
            if not self.active_rooms[channel_name]:
                del self.active_rooms[channel_name]
            else:
                await self.broadcast_viewer_count(channel_name)

    async def broadcast_viewer_count(self, channel_name: str):
        count = len(self.active_rooms.get(channel_name, []))
        await self.broadcast(channel_name, {
            "event": "viewer_count_update",
            "count": count
        })

    async def broadcast(self, channel_name: str, message: dict):
        if channel_name in self.active_rooms:
            for connection in self.active_rooms[channel_name]:
                try:
                    await connection.send_json(message)
                except:
                    pass


livestream_manager = LiveConnectionManager()


@router.websocket("/ws")
async def live_websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    await websocket.accept()
    current_channel = None
    user_id = None

    try:
        current_user = await get_current_user(token)
        user_id = str(current_user.id)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            # --- ১. লাইভ শুরু করা (সংশোধিত) ---
            if action == "start_live":
                if current_channel: continue

                # হোস্টের জন্য ১ নম্বর UID ফিক্সড করা হলো
                host_uid = 1
                channel_name = f"live_{user_id}_{int(time.time())}"

                # এখানে চতুর্থ প্যারামিটার ০ এর জায়গায় host_uid (১) ব্যবহার করা হয়েছে
                agora_token = RtcTokenBuilder.buildTokenWithUid(
                    APP_ID, APP_CERTIFICATE, channel_name, host_uid, 1, int(time.time()) + 3600
                )

                new_live = LiveStreamModel(
                    host=current_user,
                    agora_channel_name=channel_name,
                    is_premium=data.get("is_premium", False),
                    entry_fee=data.get("entry_fee", 0),
                    status="live"
                )
                await new_live.insert()

                current_channel = channel_name
                await livestream_manager.connect_to_room(websocket, channel_name)

                # ফ্রন্টএন্ডে uid পাঠিয়ে দেওয়া হচ্ছে যাতে অ্যাপ ঐ UID দিয়ে জয়েন করে
                await websocket.send_json({
                    "event": "live_started",
                    "channel_name": channel_name,
                    "agora_token": agora_token,
                    "uid": host_uid
                })

            # --- ২. লাইভে জয়েন করা ---
            elif action == "join_live":
                channel_name = data.get("channel_name")
                live = await LiveStreamModel.find_one(
                    LiveStreamModel.agora_channel_name == channel_name,
                    LiveStreamModel.status == "live"
                )

                if live:
                    current_channel = channel_name
                    await livestream_manager.connect_to_room(websocket, channel_name)

                    new_viewer = LiveViewerModel(
                        session=live,
                        user=current_user,
                        fee_paid=live.entry_fee if live.is_premium else 0
                    )
                    await new_viewer.insert()

                    live.total_views += 1
                    await live.save()

                    # ভিউয়ারের ক্ষেত্রে UID ০ থাকবে (এগোরা নিজে থেকে ডাইনামিক আইডি দিবে)
                    ##await websocket.send_json({"event": "joined_success", "channel": channel_name})
                    viewer_uid = 0  # ০ দিলে এগোরা অটো আইডি দিবে, তবে টোকেন তৈরিতে ০ ব্যবহার করা নিরাপদ
                    # ভিউয়ারের জন্য টোকেন তৈরি করুন
                    viewer_token = RtcTokenBuilder.buildTokenWithUid(
                        APP_ID, APP_CERTIFICATE, channel_name, viewer_uid, 2, int(time.time()) + 3600
                    )

                    await websocket.send_json({
                        "event": "joined_success",
                        "channel": channel_name,
                        "agora_token": viewer_token,  # টোকেনটি পাঠান
                        "uid": viewer_uid
                    })

            # --- ৩. লাইক পাঠানো ---
            elif action == "send_like" and current_channel:
                live = await LiveStreamModel.find_one(LiveStreamModel.agora_channel_name == current_channel)
                if live:
                    live.total_like += 1
                    await live.save()
                    await livestream_manager.broadcast(current_channel, {
                        "event": "new_like",
                        "total_likes": live.total_like
                    })


            elif action == "send_comment" and current_channel:
                live = await LiveStreamModel.find_one(LiveStreamModel.agora_channel_name == current_channel)
                if live:
                    content = data.get("message", "")
                    new_comment = LiveCommentModel(session=live, user=current_user, content=content)
                    await new_comment.insert()

                    live.total_comment += 1
                    await live.save()

                    await livestream_manager.broadcast(current_channel, {
                        "event": "new_comment",
                        "user": {
                            "id": str(current_user.id),
                            "name": current_user.first_name,
                            "avatar": current_user.profile_image if hasattr(current_user, 'profile_image') else None
                        },
                        "message": content
                    })

    except WebSocketDisconnect:
        if current_channel:
            await livestream_manager.disconnect_from_room(websocket, current_channel)
            live = await LiveStreamModel.find_one(LiveStreamModel.agora_channel_name == current_channel)

            if live and str(live.host.ref.id) == user_id:
                live.status = "ended"
                live.end_time = datetime.now(timezone.utc)
                await live.save()
                await livestream_manager.broadcast(current_channel, {"event": "live_ended"})


@router.get("/active", response_model=List[dict])
async def get_active_lives():
    active_lives = await LiveStreamModel.find(
        LiveStreamModel.status == "live",
        fetch_links=True  # Performance optimized
    ).to_list()

    response_data = []
    for live in active_lives:
        response_data.append({
            "id": str(live.id),
            "host": {
                "id": str(live.host.id),
                "name": live.host.first_name,
                "avatar": getattr(live.host, 'profile_image', None)
            },
            "channel_name": live.agora_channel_name,
            "is_premium": live.is_premium,
            "entry_fee": live.entry_fee,
            "status": live.status,
            "total_like": live.total_like,
            "total_comment": live.total_comment,
            "total_views": live.total_views
        })
    return response_data