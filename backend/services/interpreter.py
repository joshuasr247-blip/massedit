"""
Claude-powered prompt interpreter for video edit plans.
The brain of the system — converts natural language prompts into structured edit operations.
"""

import json
import logging
from typing import Optional, List, Dict, Any

from anthropic import Anthropic, APIError
from pydantic import ValidationError

from models.schemas import (
    EditPlan,
    EditStep,
    EditOperation,
    EditOperationType,
    InterpretRequest,
    InterpretResponse,
    AISuggestion,
    SuggestionType,
    BoxMeta,
)

logger = logging.getLogger(__name__)


# ============================================================================
# System Prompt for Claude
# ============================================================================

SYSTEM_PROMPT = """You are an expert video editor assistant for MassEdit, a prompt-driven mass video editor.

## Your Role
Users provide natural language prompts describing how to process and combine video clips organized into "Boxes".
Your job is to interpret these prompts into detailed, executable video edit plans.

## The Data Model
- **Boxes**: Named containers of video clips (e.g., "Intro", "Main Footage", "B-Roll", "Outro")
- **Clips**: Individual video/audio files within a box
- **Edit Plan**: A sequence of operations applied to clips from boxes
- **Variation Matrix**: Defines what changes per output (which clips, effects, etc.)

## Available Edit Operations
Each operation has specific parameters:

1. **TRIM**: Cut clip to specific in/out points
   - Parameters: in_time (seconds), out_time (seconds)
   - Example: {"type": "trim", "params": {"in_time": 1.5, "out_time": 15.2}}

2. **SPEED**: Change playback speed (slow-motion, time-lapse, fast-forward)
   - Parameters: multiplier (0.25 to 4.0), direction ("forward"/"reverse")
   - Example: {"type": "speed", "params": {"multiplier": 0.5, "direction": "forward"}}

3. **FADE**: Fade in or out at clip edges
   - Parameters: type ("in"/"out"), duration_seconds (0.5 to 3.0)
   - Example: {"type": "fade", "params": {"type": "in", "duration_seconds": 1.0}}

4. **COLOR_GRADE**: Apply color corrections
   - Parameters: exposure (-4.0 to 4.0), contrast (-100 to 100), saturation (0 to 200),
     temperature (-100 to 100), tint (-100 to 100), vibrance (-100 to 100)
   - Example: {"type": "color_grade", "params": {"exposure": 0.5, "saturation": 120}}

5. **OVERLAY_TEXT**: Add text overlay to video
   - Parameters: text (string), position ("top", "center", "bottom", "top_left", "top_right", "bottom_left", "bottom_right"),
     font_size (20 to 120), font_color (hex), bg_color (hex, optional), duration_seconds
   - Example: {"type": "overlay_text", "params": {"text": "Summer 2024", "position": "center", "font_size": 60, "font_color": "#FFFFFF"}}

6. **TRANSITION**: Add transition between clips
   - Parameters: type ("cross_dissolve", "dip_to_black", "dip_to_white", "film_dissolve", "wipe", "slide", "push", "morph_cut"),
     duration_seconds (0.3 to 2.0)
   - Example: {"type": "transition", "params": {"type": "cross_dissolve", "duration_seconds": 0.5}}

7. **AUDIO_NORMALIZE**: Normalize audio levels
   - Parameters: target_loudness (-30 to -10 dB), mode ("integrated"/"short_term"/"momentary")
   - Example: {"type": "audio_normalize", "params": {"target_loudness": -14, "mode": "integrated"}}

8. **RESIZE**: Scale video to new resolution (handles aspect ratio)
   - Parameters: width, height, method ("scale", "crop", "pad")
   - scale: stretch to fit; crop: crop to fit; pad: add letterbox/pillarbox
   - Example: {"type": "resize", "params": {"width": 1920, "height": 1080, "method": "pad"}}

9. **CROP**: Crop video to specific region
   - Parameters: x (pixels), y (pixels), width (pixels), height (pixels)
   - Example: {"type": "crop", "params": {"x": 100, "y": 100, "width": 1920, "height": 1080}}

## Edit Plan Structure
An edit plan consists of sequential steps. Each step:
- Applies to one or more clips from a specific box
- Contains operations performed IN ORDER
- May reference clips from different boxes
- Produces output that can be input to the next step

Steps should follow a logical order:
1. Color grading / normalization (foundational)
2. Trimming / cropping (composition)
3. Effects / overlays (visual elements)
4. Transitions (between clips)
5. Audio processing (final pass)

## Output Settings
Include output_settings specifying:
- resolution (width, height)
- frame_rate (24, 30, 60 fps)
- codec ("h264", "h265", "prores")
- bitrate_mbps (5 to 100)
- format ("mp4", "mov", "webm")

## Variation Matrix Modes
When users want multiple outputs, use the variation matrix with modes:
- **fixed**: Use the same clip for all outputs
- **each**: Create output for every clip in the box (cartesian product with other "each" boxes)
- **random**: Randomly select N clips from the box
- **sequence**: Cycle through clips in order

## Examples

### Example 1: Simple video with transitions
User: "Create a video using clips from Intro box, then Main Footage, with dissolves between them"
- Step 1: Prep intro clips (color grade, fade in)
- Step 2: Prep main footage (color grade, audio normalize)
- Step 3: Concatenate with cross-dissolve transitions
- Output: One 1920x1080 mp4 at 30fps

### Example 2: Multi-variation template
User: "Create 10 variations of a highlight reel, each with a different B-Roll clip, all with the same music"
- Matrix: B-Roll clips mode="each" (selecting up to 10 clips)
- Each variation gets the same audio track + effects
- Output: 10 separate videos

### Example 3: Speed ramping
User: "Show clips from Footage box at 0.5x, 1x, and 2x speed"
- Matrix: Speed mode="sequence" with speeds [0.5, 1.0, 2.0]
- Output: 3 videos, same clips, different speeds

## Quality Guidelines
- Suggest practical optimizations for rendering speed (resolution, bitrate)
- Flag potential issues (e.g., clips with incompatible codecs, audio mismatches)
- Recommend platform-specific settings (vertical for TikTok, square for Instagram)
- Provide creative suggestions when relevant

## Your Response Format
Respond with a JSON object containing:
{
  "edit_plan": {
    "steps": [...],
    "output_settings": {...},
    "estimated_duration": <float>
  },
  "suggestions": [
    {"text": "...", "type": "quality|performance|platform|creative", "auto_applicable": false}
  ]
}

IMPORTANT: Return valid JSON that can be parsed. Do not include markdown code blocks or extra text.
"""


# ============================================================================
# Claude Tool Definition
# ============================================================================

CREATE_EDIT_PLAN_TOOL = {
    "name": "create_edit_plan",
    "description": "Create a detailed video edit plan from a user's natural language prompt",
    "input_schema": {
        "type": "object",
        "properties": {
            "edit_plan": {
                "type": "object",
                "description": "The complete edit plan",
                "properties": {
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "step_number": {"type": "integer"},
                                "source_box_id": {"type": "string"},
                                "label": {"type": "string"},
                                "description": {"type": "string"},
                                "operations": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "type": {"type": "string"},
                                            "params": {"type": "object"},
                                            "description": {"type": "string"},
                                        },
                                        "required": ["type", "params"],
                                    },
                                },
                            },
                            "required": ["step_number", "source_box_id", "label", "description", "operations"],
                        },
                    },
                    "output_settings": {
                        "type": "object",
                        "properties": {
                            "width": {"type": "integer"},
                            "height": {"type": "integer"},
                            "frame_rate": {"type": "number"},
                            "codec": {"type": "string"},
                            "bitrate_mbps": {"type": "integer"},
                            "format": {"type": "string"},
                        },
                    },
                    "estimated_duration": {"type": "number"},
                },
                "required": ["steps", "output_settings", "estimated_duration"],
            },
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "type": {"type": "string", "enum": ["quality", "performance", "platform", "creative"]},
                        "auto_applicable": {"type": "boolean"},
                    },
                    "required": ["text", "type"],
                },
            },
        },
        "required": ["edit_plan", "suggestions"],
    },
}


# ============================================================================
# Prompt Interpreter Service
# ============================================================================

class PromptInterpreter:
    """Claude-powered video edit plan interpreter."""

    def __init__(self, api_key: str):
        """
        Initialize interpreter with Anthropic API key.

        Args:
            api_key: Anthropic API key
        """
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    async def interpret(self, request: InterpretRequest) -> InterpretResponse:
        """
        Interpret a natural language prompt into an edit plan.

        Args:
            request: Interpretation request with prompt and box metadata

        Returns:
            InterpretResponse with edit plan and suggestions

        Raises:
            APIError: If Claude API call fails
            ValidationError: If response doesn't match schema
        """
        logger.info(f"Interpreting prompt: {request.prompt[:100]}...")

        # Build box context for Claude
        box_context = self._build_box_context(request.boxes)

        # Build user message
        user_message = f"""Here are the available video boxes and clips:

{box_context}

User request:
"{request.prompt}"

Please analyze this request and create a detailed edit plan. Consider:
1. How to use the available clips effectively
2. What operations would produce the desired result
3. Appropriate output settings
4. Any creative suggestions or optimizations

Use the create_edit_plan tool to provide your response."""

        try:
            # Call Claude with tool use
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=[CREATE_EDIT_PLAN_TOOL],
                messages=[{"role": "user", "content": user_message}],
            )

            logger.debug(f"Claude response: {response}")

            # Extract tool use result
            plan_data = self._extract_tool_result(response)

            # Parse and validate
            edit_plan = EditPlan(**plan_data["edit_plan"])
            suggestions = [AISuggestion(**s) for s in plan_data.get("suggestions", [])]

            logger.info(f"Successfully interpreted prompt into plan with {len(edit_plan.steps)} steps")

            return InterpretResponse(
                edit_plan=edit_plan,
                suggestions=suggestions,
            )

        except APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        except (ValidationError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse Claude response: {e}")
            raise ValueError(f"Invalid response from Claude: {e}")

    def generate_ffmpeg_commands(
        self,
        edit_plan: EditPlan,
        clip_assignments: Dict[str, str],
        storage_path: str,
    ) -> List[str]:
        """
        Convert edit plan + clip assignments into FFmpeg commands.

        Args:
            edit_plan: The edit plan to render
            clip_assignments: Mapping of box_id -> clip_id
            storage_path: Base path where clips are stored

        Returns:
            List of FFmpeg command strings (one per output)

        Note:
            This is a simplified version. A full implementation would need to:
            - Handle complex filter graphs
            - Manage intermediate files
            - Support parallel processing
        """
        logger.info(f"Generating FFmpeg commands for {len(edit_plan.steps)} steps")

        # This is a placeholder structure; full implementation in ffmpeg_engine.py
        commands = []

        # Build complex filter graph from steps
        filter_graph_parts = []
        input_files = []

        for step in edit_plan.steps:
            # Map box_id to actual clip file
            if step.source_box_id in clip_assignments:
                clip_id = clip_assignments[step.source_box_id]
                # In real implementation, resolve clip_id to file path
                file_path = f"{storage_path}/clips/{clip_id}.mp4"
                input_files.append(file_path)

                # Build filter graph from operations
                for op in step.operations:
                    filter_part = self._operation_to_filter(op)
                    if filter_part:
                        filter_graph_parts.append(filter_part)

        logger.info(f"Generated {len(commands)} FFmpeg commands")
        return commands

    # ========================================================================
    # Private Methods
    # ========================================================================

    def _build_box_context(self, boxes: List[BoxMeta]) -> str:
        """Build readable context about available boxes for Claude."""
        context_lines = []

        for box in boxes:
            duration_str = f"{box.total_duration:.1f}s"
            clips_str = f"{box.clip_count} clip{'s' if box.clip_count != 1 else ''}"
            tags_str = f", tags: {', '.join(box.tags)}" if box.tags else ""

            context_lines.append(
                f"- Box '{box.id}' ({box.name}): {clips_str}, {duration_str}{tags_str}"
            )

        return "\n".join(context_lines) if context_lines else "No boxes available"

    def _extract_tool_result(self, response) -> Dict[str, Any]:
        """Extract and parse tool use result from Claude response."""
        for block in response.content:
            if block.type == "tool_use" and block.name == "create_edit_plan":
                try:
                    return json.loads(json.dumps(block.input))
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool input: {e}")
                    raise ValueError(f"Invalid JSON in tool response: {e}")

        raise ValueError("No create_edit_plan tool use found in response")

    def _operation_to_filter(self, operation: EditOperation) -> Optional[str]:
        """Convert an operation to an FFmpeg filter string fragment."""
        op_map = {
            EditOperationType.TRIM: self._trim_to_filter,
            EditOperationType.SPEED: self._speed_to_filter,
            EditOperationType.FADE: self._fade_to_filter,
            EditOperationType.COLOR_GRADE: self._color_grade_to_filter,
            EditOperationType.OVERLAY_TEXT: self._text_to_filter,
            EditOperationType.RESIZE: self._resize_to_filter,
            EditOperationType.CROP: self._crop_to_filter,
        }

        handler = op_map.get(operation.type)
        if handler:
            return handler(operation.params)

        logger.warning(f"No filter handler for operation type: {operation.type}")
        return None

    @staticmethod
    def _trim_to_filter(params: Dict[str, Any]) -> Optional[str]:
        """Trim is typically handled via input trimming, not a filter."""
        return None

    @staticmethod
    def _speed_to_filter(params: Dict[str, Any]) -> Optional[str]:
        """Convert speed operation to FFmpeg filter."""
        multiplier = params.get("multiplier", 1.0)
        # setpts adjusts video speed, atempo adjusts audio
        return f"setpts={1/multiplier}*PTS,atempo={multiplier}"

    @staticmethod
    def _fade_to_filter(params: Dict[str, Any]) -> str:
        """Convert fade operation to FFmpeg filter."""
        fade_type = params.get("type", "in")
        duration = int(params.get("duration_seconds", 1.0) * 30)  # Assume 30fps
        if fade_type == "in":
            return f"fade=t=in:d={duration}:alpha=1"
        else:
            return f"fade=t=out:d={duration}:alpha=1"

    @staticmethod
    def _color_grade_to_filter(params: Dict[str, Any]) -> Optional[str]:
        """Convert color grading to FFmpeg filter."""
        filters = []

        if "exposure" in params:
            exposure = params["exposure"]
            filters.append(f"eq=brightness={exposure * 50}")

        if "saturation" in params:
            sat = params["saturation"] / 100.0
            filters.append(f"eq=saturation={sat}")

        if "contrast" in params:
            contrast = 1.0 + params["contrast"] / 100.0
            filters.append(f"eq=contrast={contrast}")

        return ",".join(filters) if filters else None

    @staticmethod
    def _text_to_filter(params: Dict[str, Any]) -> Optional[str]:
        """Convert text overlay to FFmpeg filter."""
        text = params.get("text", "")
        font_size = params.get("font_size", 60)
        font_color = params.get("font_color", "white").replace("#", "0x")

        # Simplified; real implementation would handle font paths, positioning, etc.
        return f"drawtext=text='{text}':fontsize={font_size}:fontcolor={font_color}"

    @staticmethod
    def _resize_to_filter(params: Dict[str, Any]) -> str:
        """Convert resize to FFmpeg filter."""
        width = params.get("width", 1920)
        height = params.get("height", 1080)
        method = params.get("method", "scale")

        if method == "scale":
            return f"scale={width}:{height}"
        elif method == "crop":
            return f"scale={width}:{height}:force_original_aspect_ratio=decrease,crop={width}:{height}"
        elif method == "pad":
            return f"scale={width}:{height}:force_original_aspect_ratio=increase,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"

        return f"scale={width}:{height}"

    @staticmethod
    def _crop_to_filter(params: Dict[str, Any]) -> str:
        """Convert crop to FFmpeg filter."""
        x = params.get("x", 0)
        y = params.get("y", 0)
        width = params.get("width", 1920)
        height = params.get("height", 1080)

        return f"crop={width}:{height}:{x}:{y}"
