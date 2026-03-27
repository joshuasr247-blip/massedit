"""
Rendering and job management routes for MassEdit.

Handles render job creation, execution, cancellation, and status tracking.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.database import get_database, ProjectDB, RenderJobDB
from models.schemas import RenderJob, RenderStatus, RenderStartRequest
from services.matrix_solver import MatrixSolver
from services.render_queue import get_render_queue

logger = logging.getLogger(__name__)

router = APIRouter()

db = get_database()
matrix_solver = MatrixSolver(max_output_count=int(os.getenv("MASSEDIT_MAX_OUTPUT_COUNT", "5000")))

STORAGE_PATH = Path(os.getenv("MASSEDIT_STORAGE_PATH", "./storage"))


# ============================================================================
# Render Endpoints
# ============================================================================

@router.post("/projects/{project_id}/render", status_code=status.HTTP_201_CREATED)
async def start_render(
    project_id: str,
    request: RenderStartRequest,
    session: AsyncSession = Depends(db.get_session),
):
    """
    Start rendering a project.

    Solves the variation matrix, creates render jobs, and begins processing.

    Args:
        project_id: Project ID
        request: Render start request
        session: Database session

    Returns:
        Render job information

    Raises:
        HTTPException: If project not found or render setup fails
    """
    logger.info(f"Starting render for project {project_id}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not project_db.edit_plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No edit plan defined. Run /interpret first.",
        )

    # Solve variation matrix
    try:
        from models.schemas import Box as BoxSchema, VariationMatrix

        # Convert box data to Box objects
        boxes = []
        for box_data in project_db.boxes or []:
            box = BoxSchema(
                id=box_data["id"],
                name=box_data["name"],
                color=box_data.get("color", "#6B7280"),
                clips=[],
                created_at=datetime.fromisoformat(box_data["created_at"]),
            )
            boxes.append(box)

        # Convert matrix data
        matrix = VariationMatrix(variables=project_db.matrix.get("variables", []))

        # Solve matrix
        render_jobs = matrix_solver.solve(matrix, boxes, project_id)
        output_count = len(render_jobs)

        logger.info(f"Generated {output_count} render jobs for project {project_id}")

        # Create render jobs in database
        for job in render_jobs:
            job_db = RenderJobDB(
                id=job.id,
                project_id=project_id,
                output_index=job.output_index,
                status=job.status.value,
                progress=job.progress,
                clip_assignments=job.clip_assignments,
            )
            session.add(job_db)

        project_db.updated_at = datetime.utcnow()
        await session.commit()

        # Start render queue processing
        queue = get_render_queue()

        # Convert to list of RenderJob with database IDs
        queue_jobs = render_jobs
        await queue.enqueue(queue_jobs)

        # Start processing if not already running
        if not queue.is_processing:
            await queue.start_processing()

        logger.info(f"Render started for project {project_id} with {output_count} jobs")

        return {
            "message": "Render started",
            "project_id": project_id,
            "total_jobs": output_count,
            "status": "processing",
        }

    except ValueError as e:
        logger.error(f"Matrix solve error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Render start error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Render initialization failed",
        )


@router.get("/projects/{project_id}/render/status")
async def get_render_status(
    project_id: str,
    session: AsyncSession = Depends(db.get_session),
):
    """
    Get render status for all jobs in a project.

    Args:
        project_id: Project ID
        session: Database session

    Returns:
        Render job statuses and overall progress

    Raises:
        HTTPException: If project not found
    """
    logger.info(f"Getting render status for project {project_id}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Get all render jobs for project
    jobs_result = await session.execute(
        select(RenderJobDB).where(RenderJobDB.project_id == project_id)
    )
    job_dbs = jobs_result.scalars().all()

    jobs = []
    for job_db in job_dbs:
        jobs.append({
            "id": job_db.id,
            "output_index": job_db.output_index,
            "status": job_db.status,
            "progress": job_db.progress,
            "output_path": job_db.output_path,
            "error": job_db.error,
            "started_at": job_db.started_at.isoformat() if job_db.started_at else None,
            "completed_at": job_db.completed_at.isoformat() if job_db.completed_at else None,
        })

    # Calculate overall progress
    total = len(jobs)
    completed = sum(1 for j in jobs if j["status"] == RenderStatus.DONE.value)
    failed = sum(1 for j in jobs if j["status"] == RenderStatus.FAILED.value)
    rendering = sum(1 for j in jobs if j["status"] == RenderStatus.RENDERING.value)

    progress = int((completed / total * 100) if total > 0 else 0)

    return {
        "project_id": project_id,
        "total_jobs": total,
        "completed": completed,
        "failed": failed,
        "rendering": rendering,
        "queued": total - completed - failed - rendering,
        "overall_progress": progress,
        "jobs": jobs,
    }


@router.post("/projects/{project_id}/render/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_render(
    project_id: str,
    session: AsyncSession = Depends(db.get_session),
):
    """
    Cancel all running and queued render jobs for a project.

    Args:
        project_id: Project ID
        session: Database session

    Raises:
        HTTPException: If project not found
    """
    logger.info(f"Cancelling render for project {project_id}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Get all render jobs
    jobs_result = await session.execute(
        select(RenderJobDB).where(RenderJobDB.project_id == project_id)
    )
    job_dbs = jobs_result.scalars().all()

    # Cancel each job
    queue = get_render_queue()

    for job_db in job_dbs:
        if job_db.status in [RenderStatus.QUEUED.value, RenderStatus.RENDERING.value]:
            await queue.cancel(job_db.id)
            job_db.status = RenderStatus.FAILED.value
            job_db.error = "Cancelled by user"

    await session.commit()

    logger.info(f"Render cancelled for project {project_id}")


@router.get("/projects/{project_id}/render/outputs")
async def get_render_outputs(
    project_id: str,
    session: AsyncSession = Depends(db.get_session),
):
    """
    List completed output files for a project.

    Args:
        project_id: Project ID
        session: Database session

    Returns:
        List of completed outputs with metadata

    Raises:
        HTTPException: If project not found
    """
    logger.info(f"Getting render outputs for project {project_id}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Get completed jobs with output paths
    jobs_result = await session.execute(
        select(RenderJobDB).where(
            (RenderJobDB.project_id == project_id) & (RenderJobDB.status == RenderStatus.DONE.value)
        )
    )
    job_dbs = jobs_result.scalars().all()

    outputs = []

    for job_db in job_dbs:
        if job_db.output_path and Path(job_db.output_path).exists():
            file_size = Path(job_db.output_path).stat().st_size
            outputs.append({
                "output_index": job_db.output_index,
                "file_path": job_db.output_path,
                "url": f"/outputs/{Path(job_db.output_path).name}",
                "file_size": file_size,
                "completed_at": job_db.completed_at.isoformat() if job_db.completed_at else None,
            })

    return {
        "project_id": project_id,
        "total_outputs": len(outputs),
        "outputs": outputs,
    }


@router.post("/projects/{project_id}/render/preview")
async def generate_preview(
    project_id: str,
    session: AsyncSession = Depends(db.get_session),
):
    """
    Generate a preview render (first output variation only).

    Useful for checking edit plan before rendering all variations.

    Args:
        project_id: Project ID
        session: Database session

    Returns:
        Preview render job information

    Raises:
        HTTPException: If project not found or preview fails
    """
    logger.info(f"Generating preview for project {project_id}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not project_db.edit_plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No edit plan defined",
        )

    try:
        # Create single preview job
        from models.schemas import Box as BoxSchema, VariationMatrix, RenderJob as RenderJobSchema
        import uuid

        boxes = []
        for box_data in project_db.boxes or []:
            box = BoxSchema(
                id=box_data["id"],
                name=box_data["name"],
                color=box_data.get("color", "#6B7280"),
                clips=[],
                created_at=datetime.fromisoformat(box_data["created_at"]),
            )
            boxes.append(box)

        matrix = VariationMatrix(variables=project_db.matrix.get("variables", []))

        # Solve but take only first result
        render_jobs = matrix_solver.solve(matrix, boxes, project_id)

        if not render_jobs:
            raise ValueError("No render jobs generated")

        preview_job = render_jobs[0]
        preview_job.id = str(uuid.uuid4())

        # Save to database
        job_db = RenderJobDB(
            id=preview_job.id,
            project_id=project_id,
            output_index=0,
            status=preview_job.status.value,
            progress=preview_job.progress,
            clip_assignments=preview_job.clip_assignments,
        )
        session.add(job_db)
        await session.commit()

        # Start preview rendering
        queue = get_render_queue()
        await queue.enqueue([preview_job])

        if not queue.is_processing:
            await queue.start_processing()

        logger.info(f"Preview render started for project {project_id}")

        return {
            "message": "Preview render started",
            "job_id": preview_job.id,
            "project_id": project_id,
        }

    except Exception as e:
        logger.error(f"Preview generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Preview generation failed",
        )
