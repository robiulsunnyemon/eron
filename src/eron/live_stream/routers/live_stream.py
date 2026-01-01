

import json
import time
import os
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from dotenv import load_dotenv
from eron.live_stream.models.live_stream import LiveStreamModel, LiveViewerModel, LiveCommentModel
from eron.users.models.user_models import UserModel
from eron.users.utils.get_current_user import get_current_user
from agora_token_builder import RtcTokenBuilder
from uuid import UUID

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

            # # --- ২. লাইভে জয়েন করা ---
            # elif action == "join_live":
            #     channel_name = data.get("channel_name")
            #     live = await LiveStreamModel.find_one(
            #         LiveStreamModel.agora_channel_name == channel_name,
            #         LiveStreamModel.status == "live"
            #     )
            #
            #     if live:
            #         current_channel = channel_name
            #         await livestream_manager.connect_to_room(websocket, channel_name)
            #
            #         new_viewer = LiveViewerModel(
            #             session=live,
            #             user=current_user,
            #             fee_paid=live.entry_fee if live.is_premium else 0
            #         )
            #         await new_viewer.insert()
            #
            #         live.total_views += 1
            #         await live.save()
            #
            #         # ভিউয়ারের ক্ষেত্রে UID ০ থাকবে (এগোরা নিজে থেকে ডাইনামিক আইডি দিবে)
            #         ##await websocket.send_json({"event": "joined_success", "channel": channel_name})
            #         viewer_uid = 0  # ০ দিলে এগোরা অটো আইডি দিবে, তবে টোকেন তৈরিতে ০ ব্যবহার করা নিরাপদ
            #         # ভিউয়ারের জন্য টোকেন তৈরি করুন
            #         viewer_token = RtcTokenBuilder.buildTokenWithUid(
            #             APP_ID, APP_CERTIFICATE, channel_name, viewer_uid, 2, int(time.time()) + 3600
            #         )
            #
            #         await websocket.send_json({
            #             "event": "joined_success",
            #             "channel": channel_name,
            #             "agora_token": viewer_token,  # টোকেনটি পাঠান
            #             "uid": viewer_uid
            #         })

            # --- ৩. লাইক পাঠানো ---

                # --- ২. লাইভে জয়েন করা (সংশোধিত লজিক) ---
            # elif action == "join_live":
            #     channel_name = data.get("channel_name")
            #     live = await LiveStreamModel.find_one(
            #         LiveStreamModel.agora_channel_name == channel_name,
            #         LiveStreamModel.status == "live",
            #         fetch_links=True
            #     )
            #
            #     if not live:
            #         await websocket.send_json({"event": "error", "message": "Live session not found or ended"})
            #         continue
            #
            #
            #     already_joined = await LiveViewerModel.find_one({
            #         "session.$id": live.id,
            #         "user.$id": current_user.id
            #     })
            #     # যদি আগে জয়েন না করে থাকে এবং লাইভটি প্রিমিয়াম হয়
            #     if not already_joined and live.is_premium and live.entry_fee > 0:
            #         # ইউজারের ব্যালেন্স চেক
            #         if current_user.coins < live.entry_fee:
            #             await websocket.send_json({
            #                 "event": "error",
            #                 "message": "আপনার পর্যাপ্ত কয়েন নেই। দয়া করে রিচার্জ করুন।"
            #             })
            #             continue
            #
            #         # ১. ইউজারের অ্যাকাউন্ট থেকে কয়েন কাটা
            #         current_user.coins -= live.entry_fee
            #         await current_user.save()
            #
            #         # ২. হোস্টের অ্যাকাউন্টে কয়েন যোগ করা
            #         host = live.host
            #         host.coins += live.entry_fee
            #         await host.save()
            #
            #         # ৩. ভিউয়ার রেকর্ড তৈরি করা (fee_paid সেভ করে রাখা)
            #         new_viewer = LiveViewerModel(
            #             session=live,
            #             user=current_user,
            #             fee_paid=live.entry_fee
            #         )
            #         await new_viewer.insert()
            #
            #     elif not already_joined:
            #         # ফ্রি লাইভ হলে শুধু রেকর্ড তৈরি করা
            #         new_viewer = LiveViewerModel(
            #             session=live,
            #             user=current_user,
            #             fee_paid=0
            #         )
            #         await new_viewer.insert()
            #
            #     # সেশন কানেক্ট করা এবং Agora টোকেন পাঠানো
            #     current_channel = channel_name
            #     await livestream_manager.connect_to_room(websocket, channel_name)
            #
            #     live.total_views += 1
            #     await live.save()
            #
            #     viewer_uid = 0
            #     viewer_token = RtcTokenBuilder.buildTokenWithUid(
            #         APP_ID, APP_CERTIFICATE, channel_name, viewer_uid, 2, int(time.time()) + 3600
            #     )
            #
            #     await websocket.send_json({
            #         "event": "joined_success",
            #         "channel": channel_name,
            #         "agora_token": viewer_token,
            #         "uid": viewer_uid,
            #         "new_balance": current_user.coins  # ইউজারকে তার আপডেট ব্যালেন্স জানানো
            #     })
            #
            #

            elif action == "join_live":
                channel_name = data.get("channel_name")
                live = await LiveStreamModel.find_one(
                    LiveStreamModel.agora_channel_name == channel_name,
                    LiveStreamModel.status == "live",
                    fetch_links=True
                )

                if not live:
                    await websocket.send_json({"event": "error", "message": "লাইভ সেশনটি পাওয়া যায়নি।"})
                    continue

                # ১. আগে জয়েন করেছে কি না চেক করুন
                already_joined = await LiveViewerModel.find_one({
                    "session.$id": live.id,
                    "user.$id": current_user.id
                })
                # ২. পেমেন্ট লজিক (যদি আগে জয়েন না করে থাকে)
                if not already_joined:
                    # প্রিমিয়াম লাইভ এবং ইউজার নিজে হোস্ট না হলে কয়েন কাটবে
                    if live.is_premium and live.entry_fee > 0 and str(live.host.id) != str(current_user.id):

                        # ব্যালেন্স চেক (Atomic ভাবে লেটেস্ট ডাটা দেখা)
                        if current_user.coins < live.entry_fee:
                            await websocket.send_json({"event": "error", "message": "আপনার পর্যাপ্ত কয়েন নেই!"})
                            continue

                        # --- ATOMIC UPDATE (Safe for Standalone Server) ---
                        # ইউজারের কয়েন কমানো
                        await current_user.update({"$inc": {"coins": -live.entry_fee}})

                        # হোস্টের কয়েন বাড়ানো (সরাসরি হোস্টের ID দিয়ে আপডেট)
                        # আপনার প্রোজেক্টের UserModel ইম্পোর্ট নিশ্চিত করুন
                        from eron.users.models.user_models import UserModel
                        await UserModel.find_one({"_id": live.host.id}).update(
                            {"$inc": {"coins": live.entry_fee}}
                        )

                        # ভিউয়ার রেকর্ড সেভ (যাতে পুনরায় কয়েন না কাটে)
                        new_viewer = LiveViewerModel(
                            session=live, user=current_user, fee_paid=live.entry_fee
                        )
                        await new_viewer.insert()

                        # লোকাল ইউজারের কয়েন সংখ্যা আপডেট (ফ্রন্টএন্ডে পাঠানোর জন্য)
                        current_user.coins -= live.entry_fee
                    else:
                        # ফ্রি লাইভ বা হোস্ট হলে সরাসরি রেকর্ড
                        new_viewer = LiveViewerModel(session=live, user=current_user, fee_paid=0)
                        await new_viewer.insert()

                # ৩. লাইভ ভিউ বাড়ানো এবং জয়েন করা
                await live.update({"$inc": {"total_views": 1}})
                current_channel = channel_name
                await livestream_manager.connect_to_room(websocket, channel_name)

                viewer_uid = 0
                viewer_token = RtcTokenBuilder.buildTokenWithUid(
                    APP_ID, APP_CERTIFICATE, channel_name, viewer_uid, 2, int(time.time()) + 3600
                )

                await websocket.send_json({
                    "event": "joined_success",
                    "channel": channel_name,
                    "agora_token": viewer_token,
                    "uid": viewer_uid,
                    "new_balance": current_user.coins
                })
                
                
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



@router.get("/session/{session_id}/viewers", response_model=List[dict])
async def get_live_viewers(session_id: UUID):
    """
    একটি নির্দিষ্ট লাইভ সেশনের সকল ভিউয়ারদের তালিকা দেখার ফাংশন।
    """
    # ১. ওই সেশনের সকল ভিউয়ার খুঁজে বের করা (fetch_links=True ইউজারের ডাটা পাওয়ার জন্য)
    viewers = await LiveViewerModel.find(
        {"session.$id": session_id},
        fetch_links=True
    ).to_list()

    if not viewers:
        return []

    # ২. ডাটাকে সুন্দরভাবে সাজিয়ে রিটার্ন করা
    viewer_list = []
    for viewer in viewers:
        # যেহেতু user একটি Link, তাই viewer.user সরাসরি UserModel অবজেক্ট দিবে
        user_data = viewer.user
        viewer_list.append({
            "user_id": user_data.id,
            "full_name": user_data.full_name, # আপনার UserModel এ যে ফিল্ড আছে
            "username": user_data.username,
            "profile_pic": user_data.profile_pic if hasattr(user_data, 'profile_pic') else None,
            "joined_at": viewer.joined_at,
            "fee_paid": viewer.fee_paid
        })

    return viewer_list


@router.get("/viewers",status_code=status.HTTP_200_OK)
async def get_all_viewers():
    return await LiveViewerModel.find_all().to_list()