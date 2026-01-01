
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status,HTTPException
from eron.users.models.user_models import UserModel
from eron.chats.models.chat_models import ChatMessageModel
from eron.chats.utils.manager import manager
from eron.users.utils.get_current_user import get_current_user
from eron.chats.schemas.chat_schemas import ChatSendMessage
from beanie.operators import Or, And
from uuid import UUID


chat_router = APIRouter(prefix="/chat", tags=["Chat"])


@chat_router.websocket("/ws")
async def websocket_endpoint(
        websocket: WebSocket,
        token: str = Query(...)
):
    try:

        current_user = await get_current_user(token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = str(current_user.id)
    await manager.connect(user_id, websocket)


    current_user.is_online = True
    await current_user.save()

    try:
        while True:
            data = await websocket.receive_json()


            try:
                chat_data = ChatSendMessage(**data)
            except Exception as e:
                await websocket.send_json({"error": "Invalid data format", "details": str(e)})
                continue

            receiver_id = chat_data.receiver_id
            text = chat_data.message


            target_user = await UserModel.get(receiver_id)

            if not target_user:
                await websocket.send_json({"error": "Target user not found"})
                continue


            new_msg = ChatMessageModel(
                sender=current_user,
                receiver=target_user,
                message=text
            )
            await new_msg.insert()


            payload = {
                "sender_id": user_id,
                "message": text,
                "timestamp": str(new_msg.timestamp),
                "is_read": new_msg.is_read
            }
            await manager.send_personal_message(payload, receiver_id)

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        current_user.is_online = False
        await current_user.save()


@chat_router.get("/history/{other_user_id}")
async def get_chat_history(other_user_id: UUID, current_user: UserModel = Depends(get_current_user)):
    my_id = current_user.id
    db_another_user=await UserModel.get(other_user_id)
    if not db_another_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User doesn't exist")

    messages = await ChatMessageModel.find(
        Or(
            And(ChatMessageModel.receiver["id"]==other_user_id,ChatMessageModel.sender["id"]==my_id),
            And(ChatMessageModel.sender["id"]==other_user_id,ChatMessageModel.receiver["id"]==my_id),

        ),
        fetch_links=True
    ).sort(+ChatMessageModel.timestamp).to_list()

    for msg in messages:
        if str(msg.receiver.id) == my_id and not msg.is_read:
            await msg.update({"$is_read":True})

    return messages


@chat_router.get("/active-users")
async def get_active_users(current_user: UserModel = Depends(get_current_user)):

    online_users = await UserModel.find(UserModel.is_online == True).to_list()


    following_ids = {str(link.ref.id) for link in current_user.following}


    online_users.sort(key=lambda u: str(u.id) in following_ids, reverse=True)


    return [
        {
            "user_id": str(user.id),
            "full_name": f"{user.first_name} {user.last_name}",
            "profile_image": user.profile_image,
            "is_following": str(user.id) in following_ids
        }
        for user in online_users if str(user.id) != str(current_user.id)
    ]



@chat_router.get("/all/chats",status_code=status.HTTP_200_OK)
async def get_chat_history():
    chats=await ChatMessageModel.find(fetch_links=True).to_list()
    return chats