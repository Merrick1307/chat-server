from app.utils.logs.errors import ErrorLogger, _current_error_logger


class LoggingMiddleware:

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            error_logger = ErrorLogger()

            error_token = _current_error_logger.set(error_logger)

            try:
                await self.app(scope, receive, send)
            finally:
                _current_error_logger.reset(error_token)
        else:
            await self.app(scope, receive, send)