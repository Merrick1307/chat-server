import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.database import lifespan
from app.utils.logs.middleware import LoggingMiddleware
from app.controllers.auth import router as auth_router
from app.controllers.messaging import router as message_router, group_router
from app.controllers.websocket import router as websocket_router
from app.views.responses import OrjsonResponse

app: FastAPI = FastAPI(lifespan=lifespan, default_response_class=OrjsonResponse)

app.include_router(auth_router)
app.include_router(message_router)
app.include_router(group_router)
app.include_router(websocket_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(LoggingMiddleware)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy"}



if __name__ == "__main__":
    uvicorn.run(
        app="app.main:app",
        host="0.0.0.0",
        port=8500,
        log_level="info"
    )
