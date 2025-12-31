import json
import time
import os
from datetime import datetime, timezone
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

    async def connect(self, websocket: WebSocket, channel_name: str):
        if channel_name not in self.active_rooms:
            self.active_rooms[channel_name] = []
        self.active_rooms[channel_name].append(websocket)

    def disconnect(self, websocket: WebSocket, channel_name: str):
        if channel_name in self.active_rooms:
            if websocket in self.active_rooms[channel_name]:
                self.active_rooms[channel_name].remove(websocket)
            if not self.active_rooms[channel_name]:
                del self.active_rooms[channel_name]

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


            if action == "start_live":
                if current_channel: continue

                channel_name = f"live_{user_id}_{int(time.time())}"
                agora_token = RtcTokenBuilder.buildTokenWithUid(
                    APP_ID, APP_CERTIFICATE, channel_name, 0, 1, int(time.time()) + 3600
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
                await livestream_manager.connect(websocket, channel_name)
                await websocket.send_json({
                    "event": "live_started",
                    "channel_name": channel_name,
                    "agora_token": agora_token
                })


            elif action == "join_live":
                channel_name = data.get("channel_name")
                live = await LiveStreamModel.find_one(LiveStreamModel.agora_channel_name == channel_name)

                if live and live.status == "live":
                    current_channel = channel_name
                    await livestream_manager.connect(websocket, channel_name)


                    new_viewer = LiveViewerModel(
                        session=live,
                        user=current_user,
                        fee_paid=live.entry_fee if live.is_premium else 0
                    )
                    await new_viewer.insert()

                    await websocket.send_json({"event": "joined_success", "channel": channel_name})


            elif action == "send_like":
                if current_channel:
                    live = await LiveStreamModel.find_one(
                        LiveStreamModel.agora_channel_name == current_channel,
                        LiveStreamModel.status == "live"
                    )
                    if live:
                        live.total_like += 1
                        await live.save()


                        await livestream_manager.broadcast(current_channel, {
                            "event": "new_like",
                            "user_id": user_id,
                            "total_likes": live.total_like
                        })


            elif action == "send_comment":
                if current_channel:
                    live = await LiveStreamModel.find_one(
                        LiveStreamModel.agora_channel_name == current_channel,
                        LiveStreamModel.status == "live"
                    )
                    if live:

                        new_comment = LiveCommentModel(
                            session=live,
                            user=current_user,
                            content=data.get("message", "")
                        )
                        await new_comment.insert()


                        live.total_comment += 1
                        await live.save()

                        await livestream_manager.broadcast(current_channel, {
                            "event": "new_comment",
                            "user_id": user_id,
                            "message": data.get("message")
                        })

    except WebSocketDisconnect:
        if current_channel:
            livestream_manager.disconnect(websocket, current_channel)
            live = await LiveStreamModel.find_one(
                LiveStreamModel.agora_channel_name == current_channel,
                LiveStreamModel.status == "live"
            )

            if live and str(live.host.ref.id) == user_id:
                live.status = "ended"
                live.end_time = datetime.now(timezone.utc)
                await live.save()
                await livestream_manager.broadcast(current_channel, {"event": "live_ended"})