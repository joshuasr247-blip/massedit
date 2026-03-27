"""
Pydantic schemas for the MassEdit backend.
Defines all data structures for clips, boxes, edit operations, and rendering.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class EditOperationType(str, Enum):
    """Available video edit operations."""
    TRIM = "trim"
    SPEED = "speed"
    FADE = "fade"
    COLOR_GRADE = "color_grade"
    OVERLAY_TEXT = "overlay_text"
    TRANSITION = "transition"
    AUDIO_NORMALIZE = "audio_normalize"
    RESIZE = "resize"
    CROP = "crop"


class MatrixMode(str, Enum):
    """Variation matrix modes."""
    FIXED = "fixed"
    EACH = "each"
    RANDOM = "random"
    SEQUENCE = "sequence"


class RenderStatus(str, Enum):
    """Render job status."""
    QUEUED = "queued"
    RENDERING = "rendering"
    DONE = "done"
    FAILED = "failed"


class SuggestionType(str, Enum):
    """AI suggestion category."""
    QUALITY = "quality"
    PERFORMANCE = "performance"
    PLATFORM = "platform"
    CREATIVE = "creative"


# ============================================================================
# Clip & Box Models
# ============================================================================

class Clip(BaseModel):
    """A single video/audio clip."""
    id: str
    name: str
    file_path: str
    duration: float  # seconds
    width: int
    height: int
    fps: float
    tags: List[str] = Field(default_factory=list)
    thumbnail_path: Optional[str] = None
    file_size: int  # bytes

    class Config:
        from_attributes = True


class Box(BaseModel):
    """A named container of clips."""
    id: str
    name: str
    color: str = "#6B7280"  # hex color for UI
    clips: List[Clip] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Edit Operations & Plans
# ============================================================================

class EditOperation(BaseModel):
    """A single edit operation on a clip."""
    type: EditOperationType
    params: Dict[str, Any]
    description: Optional[str] = None

    class Config:
        from_attributes = True


class EditStep(BaseModel):
    """A step in the edit plan."""
    step_number: int
    source_box_id: str
    label: str
    description: str
    operations: List[EditOperation]
    ffmpeg_command: Optional[str] = None

    class Config:
        from_attributes = True


class EditPlan(BaseModel):
    """Complete edit plan generated from user prompt."""
    steps: List[EditStep]
    output_settings: Dict[str, Any]
    estimated_duration: float  # seconds

    class Config:
        from_attributes = True


# ============================================================================
# Variation Matrix
# ============================================================================

class MatrixVariable(BaseModel):
    """A variable in the variation matrix."""
    key: str  # e.g., "clip_source", "effects", "transitions", "text", "music"
    box_id: str
    mode: MatrixMode
    params: Dict[str, Any]

    class Config:
        from_attributes = True


class VariationMatrix(BaseModel):
    """Defines variations for multi-output rendering."""
    variables: List[MatrixVariable] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ============================================================================
# Render Jobs
# ============================================================================

class RenderJob(BaseModel):
    """A single render job for one output variation."""
    id: str
    project_id: str
    output_index: int  # which output variation (0-based)
    status: RenderStatus
    progress: int = 0  # 0-100
    output_path: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    clip_assignments: Dict[str, str]  # box_id -> clip_id

    class Config:
        from_attributes = True


# ============================================================================
# Projects
# ============================================================================

class Project(BaseModel):
    """A complete MassEdit project."""
    id: str
    name: str
    boxes: List[Box] = Field(default_factory=list)
    prompt: Optional[str] = None
    edit_plan: Optional[EditPlan] = None
    matrix: VariationMatrix = Field(default_factory=VariationMatrix)
    render_jobs: List[RenderJob] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# API Request/Response Models
# ============================================================================

class BoxMeta(BaseModel):
    """Lightweight box metadata for interpretation requests."""
    id: str
    name: str
    clip_count: int
    tags: List[str]
    total_duration: float


class InterpretRequest(BaseModel):
    """Request to interpret a prompt into an edit plan."""
    prompt: str
    boxes: List[BoxMeta]


class AISuggestion(BaseModel):
    """AI suggestion for improving the edit."""
    text: str
    type: SuggestionType
    auto_applicable: bool = False


class InterpretResponse(BaseModel):
    """Response from prompt interpretation."""
    edit_plan: EditPlan
    suggestions: List[AISuggestion] = Field(default_factory=list)


# ============================================================================
# API Request Models
# ============================================================================

class CreateProjectRequest(BaseModel):
    """Request to create a new project."""
    name: str


class UpdateProjectRequest(BaseModel):
    """Request to update a project."""
    name: Optional[str] = None
    prompt: Optional[str] = None


class CreateBoxRequest(BaseModel):
    """Request to create a box."""
    name: str
    color: Optional[str] = "#6B7280"


class UpdateBoxRequest(BaseModel):
    """Request to update a box."""
    name: Optional[str] = None
    color: Optional[str] = None


class RenderStartRequest(BaseModel):
    """Request to start rendering."""
    use_matrix: bool = True
    output_index_start: Optional[int] = None
    output_index_end: Optional[int] = None
