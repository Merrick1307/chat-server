from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from asyncpg import Connection

from app.controllers.base import BaseController
from app.dependencies.database import acquire_db_connection
from app.services.auth import AuthService
from app.utils.logs import ErrorLogger, get_error_logger_dependency
from app.utils.jwts import verify_and_return_jwt_payload, VerifiedTokenData
from app.views.auth import (
    SignupRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    LogoutResponse,
    SessionResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class AuthController(BaseController):
    """
    Controller for authentication endpoints.
    Delegates business logic to AuthService.
    """
    
    def __init__(self, db: Connection, logger: ErrorLogger = None):
        super().__init__(db, logger)
        self._auth_service = AuthService(db, logger)
    
    @property
    def auth_service(self) -> AuthService:
        return self._auth_service
    
    async def signup(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str
    ) -> TokenResponse:
        """Handle user signup request."""
        try:
            result = await self.auth_service.signup(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            return TokenResponse(**result)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            await self.log_error(f"Signup error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred during signup"
            )
    
    async def login(self, username: str, password: str) -> TokenResponse:
        """Handle user login request."""
        try:
            result = await self.auth_service.login(username, password)
            return TokenResponse(**result)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )
        except Exception as e:
            await self.log_error(f"Login error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred during login"
            )
    
    async def logout(self, refresh_token: str) -> LogoutResponse:
        """Handle user logout request."""
        try:
            success = await self.auth_service.logout(refresh_token)
            return LogoutResponse(success=success)
        except Exception as e:
            await self.log_error(f"Logout error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred during logout"
            )
    
    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Handle token refresh request."""
        try:
            result = await self.auth_service.refresh(refresh_token)
            return TokenResponse(**result)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )
        except Exception as e:
            await self.log_error(f"Refresh error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred during token refresh"
            )
    
    async def check_session(self, user_id: UUID) -> SessionResponse:
        """Handle session check request."""
        try:
            result = await self.auth_service.check_session(user_id)
            return SessionResponse(**result)
        except Exception as e:
            await self.log_error(f"Session check error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred during session check"
            )


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    summary="Register new user"
)
async def signup(
    request: SignupRequest,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    logger: Annotated[ErrorLogger, Depends(get_error_logger_dependency)]
):
    """Register a new user account. Returns access and refresh tokens."""
    controller = AuthController(db, logger)
    return await controller.signup(
        username=request.username,
        email=request.email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name
    )


@router.post(
    "/login",
    summary="User login"
)
async def login(
    request: LoginRequest,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    logger: Annotated[ErrorLogger, Depends(get_error_logger_dependency)]
):
    """Authenticate user and return tokens. Accepts username or email."""
    controller = AuthController(db, logger)
    return await controller.login(
        username=request.username,
        password=request.password
    )


@router.post(
    "/logout",
    summary="User logout"
)
async def logout(
    request: LogoutRequest,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    logger: Annotated[ErrorLogger, Depends(get_error_logger_dependency)]
):
    """Invalidate the refresh token to logout user."""
    controller = AuthController(db, logger)
    return await controller.logout(refresh_token=request.refresh_token)


@router.post(
    "/session/refresh",
    summary="Refresh access token"
)
async def refresh_session(
    request: RefreshRequest,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    logger: Annotated[ErrorLogger, Depends(get_error_logger_dependency)]
):
    """Get new tokens using a valid refresh token. Implements token rotation."""
    controller = AuthController(db, logger)
    return await controller.refresh(refresh_token=request.refresh_token)


@router.get(
    "/session/check",
    summary="Check session validity"
)
async def check_session(
    token_data: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
    db: Annotated[Connection, Depends(acquire_db_connection)],
    logger: Annotated[ErrorLogger, Depends(get_error_logger_dependency)]
):
    """Verify current access token is valid and return user info."""
    controller = AuthController(db, logger)
    user_id = UUID(token_data.username) if token_data.username else None
    
    if not user_id:
        return SessionResponse(valid=False)
    
    return await controller.check_session(user_id)
