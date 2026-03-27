"""
AI prompt interpretation routes for MassEdit.

Converts natural language prompts into video edit plans using Claude.
"""

import logging
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.database import get_database, ProjectDB
from models.schemas import InterpretRequest, InterpretResponse, BoxMeta
from services.interpreter import PromptInterpreter

logger = logging.getLogger(__name__)

router = APIRouter()

db = get_database()

# Lazy-initialize Claude interpreter (don't fail at import if no key)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
_interpreter = None

def get_interpreter() -> PromptInterpreter:
    global _interpreter
    if _interpreter is None:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
        _interpreter = PromptInterpreter(api_key=key)
    return _interpreter


# ============================================================================
# Interpretation Endpoints
# ============================================================================

@router.post("/projects/{project_id}/interpret", response_model=InterpretResponse)
async def interpret_prompt(
    project_id: str,
    prompt: str,
    session: AsyncSession = Depends(db.get_session),
) -> InterpretResponse:
    """
    Interpret a natural language prompt into an edit plan.

    The AI analyzes the prompt and available clips to generate a detailed
    video edit plan with operations, transitions, and output settings.

    Args:
        project_id: Project ID
        prompt: Natural language prompt describing desired edits
        session: Database session

    Returns:
        InterpretResponse with edit plan and suggestions

    Raises:
        HTTPException: If project not found or interpretation fails
    """
    logger.info(f"Interpreting prompt for project {project_id}")
    logger.debug(f"Prompt: {prompt}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Build box metadata for Claude
    boxes_meta = []
    boxes = project_db.boxes or []

    for box in boxes:
        clips = box.get("clips", [])
        total_duration = sum(clip.get("duration", 0) for clip in clips)

        box_meta = BoxMeta(
            id=box["id"],
            name=box["name"],
            clip_count=len(clips),
            tags=[],  # Could extract from clips
            total_duration=total_duration,
        )
        boxes_meta.append(box_meta)

    # Create interpretation request
    interpret_request = InterpretRequest(
        prompt=prompt,
        boxes=boxes_meta,
    )

    try:
        # Call Claude interpreter
        response = await get_interpreter().interpret(interpret_request)

        # Save prompt and edit plan to project
        project_db.prompt = prompt
        project_db.edit_plan = response.edit_plan.dict()
        project_db.updated_at = datetime.utcnow()

        await session.commit()

        logger.info(f"Prompt interpreted successfully for project {project_id}")

        return response

    except ValueError as e:
        logger.error(f"Interpretation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Interpretation failed: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during interpretation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Interpretation service error",
        )


@router.post("/projects/{project_id}/interpret/refine", response_model=InterpretResponse)
async def refine_interpretation(
    project_id: str,
    refinement_prompt: str,
    session: AsyncSession = Depends(db.get_session),
) -> InterpretResponse:
    """
    Refine an existing interpretation with follow-up adjustments.

    Takes the current edit plan and a refinement prompt, then regenerates
    with the adjustments applied.

    Args:
        project_id: Project ID
        refinement_prompt: Follow-up prompt describing refinements
        session: Database session

    Returns:
        Updated InterpretResponse

    Raises:
        HTTPException: If project not found or refinement fails
    """
    logger.info(f"Refining interpretation for project {project_id}")
    logger.debug(f"Refinement: {refinement_prompt}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not project_db.prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No existing interpretation to refine",
        )

    # Combine original prompt with refinement
    combined_prompt = f"{project_db.prompt}\n\nRefinement: {refinement_prompt}"

    # Build box metadata
    boxes_meta = []
    boxes = project_db.boxes or []

    for box in boxes:
        clips = box.get("clips", [])
        total_duration = sum(clip.get("duration", 0) for clip in clips)

        box_meta = BoxMeta(
            id=box["id"],
            name=box["name"],
            clip_count=len(clips),
            tags=[],
            total_duration=total_duration,
        )
        boxes_meta.append(box_meta)

    # Create interpretation request
    interpret_request = InterpretRequest(
        prompt=combined_prompt,
        boxes=boxes_meta,
    )

    try:
        # Call Claude interpreter
        response = await get_interpreter().interpret(interpret_request)

        # Update project
        project_db.prompt = combined_prompt
        project_db.edit_plan = response.edit_plan.dict()
        project_db.updated_at = datetime.utcnow()

        await session.commit()

        logger.info(f"Interpretation refined for project {project_id}")

        return response

    except ValueError as e:
        logger.error(f"Refinement error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refinement failed: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during refinement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Interpretation service error",
        )


@router.get("/projects/{project_id}/plan", response_model=dict)
async def get_current_plan(
    project_id: str,
    session: AsyncSession = Depends(db.get_session),
):
    """
    Get the current edit plan for a project.

    Args:
        project_id: Project ID
        session: Database session

    Returns:
        Current edit plan or null if none exists

    Raises:
        HTTPException: If project not found
    """
    logger.info(f"Getting plan for project {project_id}")

    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project_db = result.scalar_one_or_none()

    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return {
        "prompt": project_db.prompt,
        "edit_plan": project_db.edit_plan,
        "updated_at": project_db.updated_at.isoformat(),
    }
