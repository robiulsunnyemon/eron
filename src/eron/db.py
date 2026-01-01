import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from eron.chats.models.chat_models import ChatMessageModel
from eron.live_stream.models.live_stream import LiveStreamModel, LiveViewerModel, LiveCommentModel
from eron.users.models.user_models import UserModel

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "eron")


MODELS = [
    UserModel,
ChatMessageModel,
LiveStreamModel,
LiveViewerModel,
LiveCommentModel

]


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncIOMotorClient(MONGODB_URL,uuidRepresentation="standard")
    await init_beanie(
        database=client[DATABASE_NAME],
        document_models=MODELS,
    )
    print(f"✅ Connected to MongoDB: {DATABASE_NAME}")

    # ----------------------------------------
    # try:
    #     await UserModel.get_settings().motor_collection.drop()
    #     print("🗑️ UserModel collection dropped successfully.")
    # except Exception as e:
    #     print(f"⚠️ Error dropping collection: {e}")
    # ----------------------------------------

    yield

    client.close()
    print("👋 MongoDB connection closed.")
