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
from app.views.responses import APIResponse

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
    
    async def lookup_user(self, username: str) -> dict:
        """Look up a user by username."""
        result = await self.auth_service.lookup_user(username)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return result


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account with username, email, and password."
)
async def signup(
    request: SignupRequest,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    logger: Annotated[ErrorLogger, Depends(get_error_logger_dependency)]
):
    """
    Register a new user account.
    
    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: Password (minimum 8 characters)
    - **first_name**: User's first name
    - **last_name**: User's last name
    
    Returns access token, refresh token, and user_id on success.
    The access token expires in 15 minutes; use refresh endpoint to obtain new tokens.
    """
    controller = AuthController(db, logger)
    result = await controller.signup(
        username=request.username,
        email=request.email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name
    )
    return APIResponse(data=result, message="User registered successfully")


@router.post(
    "/login",
    summary="User login",
    description="Authenticate with username/email and password to receive access tokens."
)
async def login(
    request: LoginRequest,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    logger: Annotated[ErrorLogger, Depends(get_error_logger_dependency)]
):
    """
    Authenticate user and receive tokens.
    
    - **username**: Username or email address
    - **password**: User's password
    
    Returns access token (15 min expiry), refresh token (7 day expiry), and user_id.
    Store the refresh token securely to obtain new access tokens without re-authentication.
    """
    controller = AuthController(db, logger)
    result = await controller.login(
        username=request.username,
        password=request.password
    )
    return APIResponse(data=result, message="Login successful")


@router.post(
    "/logout",
    summary="User logout",
    description="Invalidate the refresh token to end the session."
)
async def logout(
    request: LogoutRequest,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    logger: Annotated[ErrorLogger, Depends(get_error_logger_dependency)]
):
    """
    Logout and invalidate refresh token.
    
    - **refresh_token**: The refresh token to invalidate
    
    After logout, the refresh token cannot be used to obtain new access tokens.
    The current access token remains valid until expiration but should be discarded.
    """
    controller = AuthController(db, logger)
    result = await controller.logout(refresh_token=request.refresh_token)
    return APIResponse(data=result, message="Logged out successfully")


@router.post(
    "/session/refresh",
    summary="Refresh access token",
    description="Exchange a valid refresh token for new access and refresh tokens."
)
async def refresh_session(
    request: RefreshRequest,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    logger: Annotated[ErrorLogger, Depends(get_error_logger_dependency)]
):
    """
    Refresh authentication tokens.
    
    - **refresh_token**: Current valid refresh token
    
    Implements token rotation: the old refresh token is invalidated and a new pair is issued.
    Use this endpoint before the access token expires to maintain the session.
    """
    controller = AuthController(db, logger)
    result = await controller.refresh(refresh_token=request.refresh_token)
    return APIResponse(data=result, message="Token refreshed")


@router.get(
    "/session/check",
    summary="Check session validity",
    description="Verify the current access token is valid and retrieve user information."
)
async def check_session(
    token_data: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
    db: Annotated[Connection, Depends(acquire_db_connection)],
    logger: Annotated[ErrorLogger, Depends(get_error_logger_dependency)]
):
    """
    Verify session and get user info.
    
    Requires valid access token in Authorization header.
    Returns user details if the session is valid, or valid=false if not.
    Use this endpoint to check if the user is still authenticated.
    """
    controller = AuthController(db, logger)
    user_id = UUID(token_data.username) if token_data.username else None
    
    if not user_id:
        return APIResponse(data=SessionResponse(valid=False))
    
    result = await controller.check_session(user_id)
    return APIResponse(data=result)


@router.get(
    "/users/lookup/{username}",
    summary="Look up user by username",
    description="Find a user by their username to get their user_id for messaging."
)
async def lookup_user(
    username: str,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """
    Look up a user by username.
    
    - **username**: The username to search for
    
    Returns user_id and display_name if found.
    Use this to find users before starting a conversation or adding to groups.
    Requires authentication.
    """
    controller = AuthController(db)
    result = await controller.lookup_user(username)
    return APIResponse(data=result)
