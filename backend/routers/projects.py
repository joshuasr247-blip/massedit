"""
Project management routes for MassEdit.

Handles CRUD operations for projects.
"""

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.database import get_database
from models.database import ProjectDB
from models.schemas import Project, CreateProjectRequest, UpdateProjectRequest, Box, Clip
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()

db = get_database()


# ============================================================================
# Helper Functions
# ============================================================================

def _deserialize_boxes(raw_boxes: list) -> List[Box]:
    """
    Convert raw JSON list from database into Box Pydantic models.

    Args:
        raw_boxes: Raw boxes list from database (or None/empty list)

    Returns:
        List of Box objects
    """
    if not raw_boxes:
        return []

    boxes = []
    for box_data in raw_boxes:
        try:
            # Convert clips if present
            clips = []
            if "clips" in box_data and box_data["clips"]:
                for clip_data in box_data["clips"]:
                    clips.append(Clip(**clip_data))

            # Create Box with deserialized clips
            box = Box(
                id=box_data.get("id"),
                name=box_data.get("name"),
                color=box_data.get("color"),
                clips=clips,
                created_at=box_data.get("created_at"),
            )
            boxes.append(box)
        except Exception as e:
            logger.warning(f"Failed to deserialize box: {e}")
            continue

    return boxes


# ============================================================================
# Project CRUD Endpoints
# ============================================================================

@router.post("/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: CreateProjectRequest,
    session: AsyncSession = Depends(db.get_session),
) -> Project:
    """
    Create a new project.

    Args:
        request: Project creation request
        session: Database session

    Returns:
        Created project
    """
    logger.info(f"Creating project: {request.name}")

    project_id = str(uuid.uuid4())
    now = datetime.utcnow()

    project_db = ProjectDB(
        id=project_id,
        name=request.name,
        boxes=[],
        matrix={},
        created_at=now,
        updated_at=now,
    )

    session.add(project_db)
    await session.commit()
    await session.refresh(project_db)

    logger.info(f"Project created: {project_id}")

    return Project(
        id=project_db.id,
        name=project_db.name,
        boxes=[],
        prompt=project_db.prompt,
        edit_plan=None,
        matrix={},
        render_jobs=[],
        created_at=project_db.created_at,
        updated_at=project_db.updated_at,
    )


@router.get("/projects", response_model=List[Project])
async def list_projects(
    session: AsyncSession = Depends(db.get_session),
) -> List[Project]:
    """
    List all projects.

    Returns:
        List of projects
    """
    logger.info("Listing projects")

    result = await session.execute(select(ProjectDB))
    projects_db = result.scalars().all()

    return [
        Project(
            id=p.id,
            name=p.name,
            boxes=_deserialize_boxes(p.boxes),
            prompt=p.prompt,
            edit_plan=None,
            matrix={},
            render_jobs=[],
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in projects_db
    ]


@router.get("/projects/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(db.get_session),
) -> Project:
    """
    Get a specific project with all data.

    Args:
        project_id: Project ID
        session: Database session

    Returns:
        Project data

    Raises:
        HTTPException: If project not found
    """
    logger.info(f"Getting project: {project_id}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return Project(
        id=project_db.id,
        name=project_db.name,
        boxes=_deserialize_boxes(project_db.boxes),
        prompt=project_db.prompt,
        edit_plan=None,
        matrix=project_db.matrix or {},
        render_jobs=[],
        created_at=project_db.created_at,
        updated_at=project_db.updated_at,
    )


@router.put("/projects/{project_id}", response_model=Project)
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    session: AsyncSession = Depends(db.get_session),
) -> Project:
    """
    Update a project.

    Args:
        project_id: Project ID
        request: Update request
        session: Database session

    Returns:
        Updated project

    Raises:
        HTTPException: If project not found
    """
    logger.info(f"Updating project: {project_id}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if request.name:
        project_db.name = request.name

    if request.prompt is not None:
        project_db.prompt = request.prompt

    project_db.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(project_db)

    logger.info(f"Project updated: {project_id}")

    return Project(
        id=project_db.id,
        name=project_db.name,
        boxes=_deserialize_boxes(project_db.boxes),
        prompt=project_db.prompt,
        edit_plan=None,
        matrix=project_db.matrix or {},
        render_jobs=[],
        created_at=project_db.created_at,
        updated_at=project_db.updated_at,
    )


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    session: AsyncSession = Depends(db.get_session),
):
    """
    Delete a project and all associated data.

    Args:
        project_id: Project ID
        session: Database session

    Raises:
        HTTPException: If project not found
    """
    logger.info(f"Deleting project: {project_id}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    await session.delete(project_db)
    await session.commit()

    logger.info(f"Project deleted: {project_id}")
