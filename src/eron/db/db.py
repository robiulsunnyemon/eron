import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from eron.users.models.user_models import UserModel

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "eron")


MODELS = [
    UserModel
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncIOMotorClient(MONGODB_URL,uuidRepresentation="standard")
    await init_beanie(
        database=client[DATABASE_NAME],
        document_models=MODELS,
    )
    print(f"✅ Connected to MongoDB: {DATABASE_NAME}")

    yield

    client.close()
    print("👋 MongoDB connection closed.")
