from fastapi import FastAPI

from app.database import lifespan
from app.utils.logs.middleware import LoggingMiddleware
from app.controllers.auth import router as auth_router
from app.controllers.messaging import router as message_router, group_router
from app.controllers.websocket import router as websocket_router

app: FastAPI = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.include_router(message_router)
app.include_router(group_router)
app.include_router(websocket_router)
app.add_middleware(LoggingMiddleware)
