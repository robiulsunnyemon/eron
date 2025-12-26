from fastapi import FastAPI
from eron.db.db import lifespan
from eron.core.exceptions_handler.global_exception_handler import global_exception_handler
from eron.core.exceptions_handler.http_exception_handler import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
import os


from eron.users.routers.auth_routers import router as auth_router
from eron.users.routers.user_routers import user_router


app = FastAPI(
    title="Eron API",
    description="FastAPI with Beanie and Motor",
    version="1.0.0",
    lifespan=lifespan
)

if not os.path.exists("uploads"):
    os.makedirs("uploads")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def read_root():
    return {"Hello": "World"}


app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)


app.include_router(auth_router,prefix="/api/v1")
app.include_router(user_router,prefix="/api/v1")

