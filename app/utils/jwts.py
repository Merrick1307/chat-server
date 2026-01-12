from collections import namedtuple
from typing import Optional
from fastapi import Request, HTTPException, status, Depends, Query
import logging

import jwt
from starlette.websockets import WebSocket

from .config import JWT_SECRET
from .logs import ErrorLogger, get_error_logger

logger = logging.getLogger(__name__)

VerifiedTokenData = namedtuple(
    "VerifiedTokenData",
    ["user_id", "email", "username", "exp", "iat"]
)


async def create_jwt_token(payload: dict, secret_key: str):
    jwt_token = jwt.encode(payload, secret_key, algorithm='HS256')
    return jwt_token


def decode_purpose_token(
        token: str,
        secret_key: str,
        algorithm: str = "HS256",
        expected_purpose: Optional[str] = None
) -> dict:
    """
    Decode and validate a purpose token.

    Args:
        token: JWT token string
        secret_key: JWT signing secret
        algorithm: Signing algorithm
        expected_purpose: If provided, validates the 'purpose' claim matches

    Returns:
        Decoded payload dict

    Raises:
        jwt.PyJWTError: If token is invalid or expired
        ValueError: If purpose doesn't match expected
    """
    payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    if expected_purpose and payload.get("purpose") != expected_purpose:
        raise ValueError(f"Invalid token purpose. Expected '{expected_purpose}'")
    return payload


class VerifyToken:
    def __init__(self, error_logger: Optional[ErrorLogger] = None):
        self.error_logger = error_logger

    def __call__(self, token: str) -> VerifiedTokenData:
        """Verify JWT and return token data."""
        try:
            payload = jwt.decode(
                jwt=token,
                key=JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_exp": True}
            )

            user_id: Optional[str] = payload.get("user_id")
            email: Optional[str] = payload.get("sub")
            username: Optional[str] = payload.get("username") or payload.get("sub")
            exp = payload.get("exp")
            iat = payload.get("iat")

            if not user_id:
                logger.warning(f"Token missing 'user_id': {token[:10]}...")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing required 'user_id' field"
                )
            if not email:
                logger.warning(f"Token missing 'sub': {token[:10]}...")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing required 'sub' field"
                )

            return VerifiedTokenData(
                user_id=user_id,
                email=email,
                username=username,
                exp=exp,
                iat=iat
            )

        except jwt.ExpiredSignatureError:
            logger.warning(f"Expired token: {token[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidSignatureError:
            logger.warning(f"Invalid signature: {token[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature"
            )
        except jwt.DecodeError:
            logger.warning(f"Decode error: {token[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format"
            )
        except jwt.InvalidTokenError:
            logger.warning(f"Invalid token: {token[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except jwt.InvalidKeyError:
            logger.error("JWT secret key configuration error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Token error: {type(e).__name__}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )


async def extract_token(request: Request, error_logger: ErrorLogger = Depends(get_error_logger)) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        error_logger.error("Authorization header missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    try:
        scheme, token = auth_header.split(" ", 1)
        if scheme.lower() != "bearer":
            error_logger.error("Invalid auth scheme, expected 'Bearer'")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme. Expected 'Bearer'"
            )
        return token
    except ValueError:
        error_logger.error("Malformed Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed Authorization header. Expected 'Bearer <token>'"
        )
    except Exception as e:
        error_logger.error(f"Header error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


async def verify_and_return_jwt_payload(
        request: Request,
        error_logger: ErrorLogger = Depends(get_error_logger)
) -> VerifiedTokenData:
    token = await extract_token(request, error_logger)
    return VerifyToken(error_logger)(token)


async def verify_and_return_jwt_payload_ws(
        websocket: WebSocket,
        token: str = Query(...)
) -> VerifiedTokenData:
    """Verify JWT from WebSocket query parameter."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token query parameter missing"
        )
    return VerifyToken()(token)