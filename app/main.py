from fastapi import FastAPI

from app.database import lifespan
from app.utils.logs.middleware import LoggingMiddleware
from app.controllers.auth import router as auth_router

app: FastAPI = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.add_middleware(LoggingMiddleware)
