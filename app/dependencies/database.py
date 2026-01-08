from fastapi import Request


async def acquire_db_connection(request: Request):
    async with request.app.state.db_pool.acquire() as connection:
        yield connection