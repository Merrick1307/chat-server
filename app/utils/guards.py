from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.utils.jwts import verify_and_return_jwt_payload, VerifiedTokenData


async def require_admin(
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)]
) -> VerifiedTokenData:
    """
    Dependency that verifies the authenticated user has admin role.
    
    Usage:
        @router.get("/admin/users")
        async def list_users(
            auth: Annotated[VerifiedTokenData, Depends(require_admin)]
        ):
            ...
    
    Raises:
        HTTPException 403: If user does not have admin role
    """
    if auth.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return auth


async def require_role(required_roles: list[str]):
    """
    Factory for creating role-based guards with multiple allowed roles.
    
    Usage:
        @router.get("/moderator/action")
        async def mod_action(
            auth: Annotated[VerifiedTokenData, Depends(require_role(["admin", "moderator"]))]
        ):
            ...
    """
    async def role_checker(
        auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)]
    ) -> VerifiedTokenData:
        if auth.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(required_roles)}"
            )
        return auth
    return role_checker
