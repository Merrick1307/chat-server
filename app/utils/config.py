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

MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
MAIL_FROM: str = os.getenv("MAIL_FROM", "")
MAIL_PORT: int = int(os.getenv("MAIL_PORT", "587"))
MAIL_SERVER: str = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_STARTTLS: bool = bool(int(os.getenv("MAIL_STARTTLS", "1")))
MAIL_SSL_TLS: bool = bool(int(os.getenv("MAIL_SSL_TLS", "0")))

APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:8500")
CLIENT_BASE_URL: str = os.getenv("CLIENT_BASE_URL", "http://localhost:3005")
