import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")

_password_encoded = quote_plus(DATABASE_PASSWORD) if DATABASE_PASSWORD else ""
db_connection_string = f'postgresql://{DATABASE_USER}:{_password_encoded}@{DATABASE_URL}'

REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
REDIS_USER: str = os.getenv("REDIS_USER", "root")
REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")

JWT_SECRET: str = os.getenv("JWT_SECRET")
