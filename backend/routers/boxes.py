"""
Box and clip management routes for MassEdit.

Handles creation, updating, and deletion of boxes and clips.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
import aiofiles

from models.database import get_database, ProjectDB
from models.schemas import Box, Clip, CreateBoxRequest, UpdateBoxRequest
from services.ffmpeg_engine import FFmpegEngine
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()

db = get_database()
ffmpeg_engine = FFmpegEngine()

STORAGE_PATH = Path(os.getenv("MASSEDIT_STORAGE_PATH", "./storage"))
CLIPS_DIR = STORAGE_PATH / "clips"
THUMBNAILS_DIR = STORAGE_PATH / "thumbnails"


# ============================================================================
# Box Endpoints
# ============================================================================

@router.post("/projects/{project_id}/boxes", response_model=Box, status_code=status.HTTP_201_CREATED)
async def create_box(
    project_id: str,
    request: CreateBoxRequest,
    session: AsyncSession = Depends(db.get_session),
) -> Box:
    """
    Create a new box in a project.

    Args:
        project_id: Project ID
        request: Box creation request
        session: Database session

    Returns:
        Created box

    Raises:
        HTTPException: If project not found
    """
    logger.info(f"Creating box in project {project_id}: {request.name}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    box_id = str(uuid.uuid4())
    box_data = {
        "id": box_id,
        "name": request.name,
        "color": request.color or "#6B7280",
        "clips": [],
        "created_at": datetime.utcnow().isoformat(),
    }

    # Update project boxes
    boxes = project_db.boxes or []
    boxes.append(box_data)
    project_db.boxes = boxes
    flag_modified(project_db, "boxes")
    project_db.updated_at = datetime.utcnow()

    await session.commit()

    logger.info(f"Box created: {box_id}")

    return Box(
        id=box_data["id"],
        name=box_data["name"],
        color=box_data["color"],
        clips=[],
        created_at=datetime.fromisoformat(box_data["created_at"]),
    )


@router.put("/projects/{project_id}/boxes/{box_id}", response_model=Box)
async def update_box(
    project_id: str,
    box_id: str,
    request: UpdateBoxRequest,
    session: AsyncSession = Depends(db.get_session),
) -> Box:
    """
    Update a box.

    Args:
        project_id: Project ID
        box_id: Box ID
        request: Update request
        session: Database session

    Returns:
        Updated box

    Raises:
        HTTPException: If project or box not found
    """
    logger.info(f"Updating box {box_id} in project {project_id}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    boxes = project_db.boxes or []
    box_data = next((b for b in boxes if b["id"] == box_id), None)

    if not box_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Box not found")

    if request.name:
        box_data["name"] = request.name

    if request.color:
        box_data["color"] = request.color

    project_db.updated_at = datetime.utcnow()
    await session.commit()

    logger.info(f"Box updated: {box_id}")

    return Box(
        id=box_data["id"],
        name=box_data["name"],
        color=box_data["color"],
        clips=[],
        created_at=datetime.fromisoformat(box_data["created_at"]),
    )


@router.delete("/projects/{project_id}/boxes/{box_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_box(
    project_id: str,
    box_id: str,
    session: AsyncSession = Depends(db.get_session),
):
    """
    Delete a box and all its clips.

    Args:
        project_id: Project ID
        box_id: Box ID
        session: Database session

    Raises:
        HTTPException: If project or box not found
    """
    logger.info(f"Deleting box {box_id} from project {project_id}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    boxes = project_db.boxes or []
    box_data = next((b for b in boxes if b["id"] == box_id), None)

    if not box_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Box not found")

    # Delete clip files
    for clip in box_data.get("clips", []):
        clip_file = CLIPS_DIR / f"{clip['id']}.mp4"
        if clip_file.exists():
            clip_file.unlink()

        thumb_file = THUMBNAILS_DIR / f"{clip['id']}.jpg"
        if thumb_file.exists():
            thumb_file.unlink()

    # Remove box from project
    project_db.boxes = [b for b in boxes if b["id"] != box_id]
    project_db.updated_at = datetime.utcnow()

    await session.commit()

    logger.info(f"Box deleted: {box_id}")


# ============================================================================
# Clip Endpoints
# ============================================================================

@router.post("/projects/{project_id}/boxes/{box_id}/clips", status_code=status.HTTP_201_CREATED)
async def upload_clips(
    project_id: str,
    box_id: str,
    files: List[UploadFile] = File(...),
    session: AsyncSession = Depends(db.get_session),
):
    """
    Upload video clips to a box.

    Accepts multiple files, probes each for metadata, generates thumbnails.

    Args:
        project_id: Project ID
        box_id: Box ID
        files: List of video files to upload
        session: Database session

    Returns:
        List of created clips

    Raises:
        HTTPException: If project or box not found, or upload fails
    """
    logger.info(f"Uploading {len(files)} clips to box {box_id}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    boxes = project_db.boxes or []
    box_data = next((b for b in boxes if b["id"] == box_id), None)

    if not box_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Box not found")

    # Ensure directories exist
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

    uploaded_clips = []

    for file in files:
        try:
            clip_id = str(uuid.uuid4())

            # Save file
            file_path = CLIPS_DIR / f"{clip_id}.mp4"
            content = await file.read()
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)

            logger.info(f"Clip file saved: {file_path}")

            # Probe metadata
            metadata = await ffmpeg_engine.probe_clip(str(file_path))
            logger.info(f"Clip metadata: {metadata}")

            # Generate thumbnail
            thumbnail_path = THUMBNAILS_DIR / f"{clip_id}.jpg"
            await ffmpeg_engine.generate_thumbnail(str(file_path), str(thumbnail_path))
            logger.info(f"Thumbnail generated: {thumbnail_path}")

            # Create clip record
            clip_data = {
                "id": clip_id,
                "name": file.filename or f"clip_{clip_id}",
                "file_path": str(file_path),
                "duration": metadata.duration,
                "width": metadata.width,
                "height": metadata.height,
                "fps": metadata.fps,
                "tags": [],
                "thumbnail_path": f"/thumbnails/{clip_id}.jpg",
                "file_size": len(content),
            }

            box_data["clips"].append(clip_data)
            uploaded_clips.append(clip_data)

            logger.info(f"Clip created: {clip_id}")

        except Exception as e:
            logger.error(f"Failed to upload clip {file.filename}: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Upload failed: {e}")

    project_db.boxes = boxes
    flag_modified(project_db, "boxes")
    project_db.updated_at = datetime.utcnow()
    await session.commit()

    return {
        "message": f"Successfully uploaded {len(uploaded_clips)} clips",
        "clips": uploaded_clips,
    }


@router.delete("/projects/{project_id}/boxes/{box_id}/clips/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clip(
    project_id: str,
    box_id: str,
    clip_id: str,
    session: AsyncSession = Depends(db.get_session),
):
    """
    Delete a clip from a box.

    Args:
        project_id: Project ID
        box_id: Box ID
        clip_id: Clip ID
        session: Database session

    Raises:
        HTTPException: If project, box, or clip not found
    """
    logger.info(f"Deleting clip {clip_id} from box {box_id}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    boxes = project_db.boxes or []
    box_data = next((b for b in boxes if b["id"] == box_id), None)

    if not box_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Box not found")

    clips = box_data.get("clips", [])
    clip_data = next((c for c in clips if c["id"] == clip_id), None)

    if not clip_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found")

    # Delete files
    clip_file = CLIPS_DIR / f"{clip_id}.mp4"
    if clip_file.exists():
        clip_file.unlink()

    thumb_file = THUMBNAILS_DIR / f"{clip_id}.jpg"
    if thumb_file.exists():
        thumb_file.unlink()

    # Remove from box
    box_data["clips"] = [c for c in clips if c["id"] != clip_id]
    project_db.updated_at = datetime.utcnow()

    await session.commit()

    logger.info(f"Clip deleted: {clip_id}")
