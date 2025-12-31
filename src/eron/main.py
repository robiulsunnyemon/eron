from fastapi import FastAPI
from eron.db import lifespan
from eron.core.exceptions_handler.global_exception_handler import global_exception_handler
from eron.core.exceptions_handler.http_exception_handler import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
import os
from fastapi.middleware.cors import CORSMiddleware

from eron.users.routers.auth_routers import router as auth_router
from eron.users.routers.user_routers import user_router
from eron.users.routers.follow_routers import router as follow_router
from eron.chats.routers.chat_routers import chat_router
from eron.live_stream.routers.live_stream import router as livestream_router


app = FastAPI(
    title="Eron API",
    description="FastAPI with Beanie and Motor",
    version="1.0.0",
    lifespan=lifespan
)

if not os.path.exists("uploads"):
    os.makedirs("uploads")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")



origins = [
    "http://localhost:5173",
    "http://localhost:8000",
    "https://eron.mtscorporate.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Hello": "World"}


app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)


app.include_router(auth_router,prefix="/api/v1")
app.include_router(user_router,prefix="/api/v1")
app.include_router(follow_router,prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(livestream_router, prefix="/api/v1")
