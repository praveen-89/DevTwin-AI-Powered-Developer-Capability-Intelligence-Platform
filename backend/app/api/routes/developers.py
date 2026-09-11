import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthenticatedUser, get_current_user
from app.db.connection import get_db_session
from app.models.developer import Developer
from app.schemas.developer import DeveloperResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/developers", tags=["Developers"])


@router.post("/me", response_model=DeveloperResponse)
async def create_developer_me(
    response: Response,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """
    Creates or returns the Developer record for the currently authenticated user.

    Identity mapping:
      The verified JWT `sub` is converted to a UUID and mapped to `auth_user_id`.

    Idempotency:
      If the record already exists, returns 200 OK and the existing record.
      If it does not exist, attempts to create it, returning 201 Created.
      A unique constraint race condition is handled securely.
    """
    try:
        auth_user_uuid = uuid.UUID(current_user.sub)
    except ValueError:
        # Invalid sub in the JWT. This shouldn't happen with valid Supabase tokens.
        logger.warning("Verified JWT sub is not a valid UUID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed.",
        )

    # 1. Query existing record
    result = await session.execute(
        select(Developer).where(Developer.auth_user_id == auth_user_uuid)
    )
    existing_developer = result.scalar_one_or_none()

    if existing_developer:
        response.status_code = status.HTTP_200_OK
        return existing_developer

    # 2. Not found, attempt creation
    new_developer = Developer(auth_user_id=auth_user_uuid)
    session.add(new_developer)

    try:
        await session.commit()
        await session.refresh(new_developer)
        response.status_code = status.HTTP_201_CREATED
        return new_developer
    except IntegrityError:
        # 3. Race condition: Another request created the record concurrently.
        await session.rollback()
        
        # Re-query the now-existing record
        result = await session.execute(
            select(Developer).where(Developer.auth_user_id == auth_user_uuid)
        )
        existing_developer = result.scalar_one_or_none()
        
        if not existing_developer:
            # This would indicate a very unexpected DB state (e.g. deletion immediately after insert)
            logger.error("Failed to re-query developer after IntegrityError (auth_user_id=%s)", auth_user_uuid)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred while provisioning developer identity."
            )

        response.status_code = status.HTTP_200_OK
        return existing_developer
