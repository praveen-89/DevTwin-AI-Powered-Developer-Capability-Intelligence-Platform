"""
DevTwin Backend — Projects Routes
"""

import uuid
from typing import List
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies.auth import get_current_developer
from app.db.connection import get_db_session
from app.models.developer import Developer
from app.models.project import Project

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreateRequest(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Project name must not be empty or whitespace only")
        return v


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    # We do not return developer_id to the client as it's internal.

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Create a new project for the authenticated developer.
    """
    new_project = Project(
        developer_id=developer.id,
        name=request.name.strip(),
    )
    
    session.add(new_project)
    try:
        await session.commit()
        await session.refresh(new_project)
        logger.info("Project created: %s for developer: %s", new_project.id, developer.id)
    except Exception as e:
        await session.rollback()
        logger.error("Failed to create project: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project."
        )

    return new_project


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session)
):
    """
    List all projects belonging to the authenticated developer.
    """
    try:
        query = select(Project).where(Project.developer_id == developer.id)
        result = await session.execute(query)
        projects = result.scalars().all()
        return list(projects)
    except Exception as e:
        logger.error("Failed to list projects: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch projects."
        )
