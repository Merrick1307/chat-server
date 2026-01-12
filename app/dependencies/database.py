from fastapi import Request, WebSocket


async def acquire_db_connection(request: Request):
    async with request.app.state.db_pool.acquire() as connection:
        yield connection


async def acquire_ws_db_connection(websocket: WebSocket):
    async with websocket.app.state.db_pool.acquire() as connection:
        yield connection
