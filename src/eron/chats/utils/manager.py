from fastapi import WebSocket
from typing import Dict

class ConnectionManager:
    def __init__(self):
        # active_connections = { "user_id": websocket_object }
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)
            return True  # মেসেজ সরাসরি অনলাইনে ডেলিভার হয়েছে
        return False  # ইউজার অফলাইন

manager = ConnectionManager()