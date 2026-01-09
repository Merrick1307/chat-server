from collections import namedtuple
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
import asyncio

import jwt

from .config import JWT_SECRET
from .logs import ErrorLogger, get_error_logger

VerifiedTokenData = namedtuple(
    "VerifiedTokenData",
    [
        "email", "role", "username", "exp", "iat"
    ]
)


async def create_jwt_token(payload: dict, secret_key: str):
    jwt_token = jwt.encode(
        payload, secret_key, algorithm='HS256'
    )
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
    def __init__(self, logger: ErrorLogger):
        self.logger = logger

    def __call__(self, token: str) -> VerifiedTokenData:
        """
        Verify JWT - offload async logs to tasks.
        """
        try:
            payload = jwt.decode(
                jwt=token,
                key=JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_exp": True}
            )

            # Extract fields
            email: Optional[str] = payload.get("sub")
            username: Optional[str] = payload.get("username") or payload.get("sub")
            role: Optional[str] = payload.get("role")
            exp = payload.get("exp")
            iat = payload.get("iat")

            if not email:
                asyncio.create_task(
                    self.logger.warning(
                        f"Token missing 'sub' for token: {token[:10]}..."
                    )
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing required 'sub' field"
                )
            if not username:
                asyncio.create_task(
                    self.logger.warning(
                        f"Token missing 'user_id' for token: {token[:10]}..."
                    )
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing required 'user_id' field"
                )

            return VerifiedTokenData(
                email=email,
                role=role,
                username=username,
                exp=exp,
                iat=iat
            )

        except jwt.ExpiredSignatureError:
            asyncio.create_task(
                self.logger.warning(f"Expired token: {token[:10]}...")
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidSignatureError:
            asyncio.create_task(
                self.logger.warning(f"Invalid signature: {token[:10]}...")
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature"
            )
        except jwt.DecodeError:
            asyncio.create_task(
                self.logger.warning(f"Decode error: {token[:10]}...")
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format"
            )
        except jwt.InvalidTokenError:
            asyncio.create_task(
                self.logger.warning(f"Invalid token: {token[:10]}...")
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except jwt.InvalidKeyError:
            asyncio.create_task(
                self.logger.error("JWT secret key error")
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error"
            )
        except (ValueError, Exception) as e:  # Catch-all
            asyncio.create_task(
                self.logger.warning(f"Token error: {type(e).__name__}: {str(e)}")
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED if "Invalid" in str(
                    e) else status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid token data" if "Invalid" in str(e) else "Internal server error"
            )


async def extract_token(request: Request, logger: ErrorLogger = Depends(get_error_logger)) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        await logger.error("Authorization header missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    try:
        scheme, token = auth_header.split(" ", 1)
        if scheme.lower() != "bearer":
            await logger.error("Invalid scheme. Expected 'Bearer'")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme. Expected 'Bearer'"
            )
        return token
    except ValueError:
        await logger.error("Malformed Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed Authorization header. Expected 'Bearer <token>'"
        )
    except Exception as e:
        await logger.error(f"Header error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


async def verify_and_return_jwt_payload(
        request: Request,
        logger: ErrorLogger = Depends(get_error_logger)
) -> VerifiedTokenData:
    token = await extract_token(request, logger)
    return VerifyToken(logger)(token)