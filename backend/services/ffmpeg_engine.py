"""
FFmpeg-based video processing engine for MassEdit.
Handles probing, thumbnail generation, and render command execution.
"""

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import ffmpeg
from PIL import Image

from models.schemas import EditOperation, EditStep, EditPlan, EditOperationType

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

class ClipMetadata:
    """Metadata extracted from a video clip."""

    def __init__(
        self,
        duration: float,
        width: int,
        height: int,
        fps: float,
        codec_video: str,
        codec_audio: Optional[str],
    ):
        self.duration = duration
        self.width = width
        self.height = height
        self.fps = fps
        self.codec_video = codec_video
        self.codec_audio = codec_audio

    def __repr__(self):
        return (
            f"ClipMetadata(duration={self.duration}s, {self.width}x{self.height}, "
            f"{self.fps}fps, video={self.codec_video}, audio={self.codec_audio})"
        )


# ============================================================================
# FFmpeg Engine
# ============================================================================

class FFmpegEngine:
    """Video processing engine using FFmpeg."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """
        Initialize FFmpeg engine.

        Args:
            ffmpeg_path: Path to ffmpeg executable
            ffprobe_path: Path to ffprobe executable
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    async def probe_clip(self, file_path: str) -> ClipMetadata:
        """
        Extract metadata from a video clip using ffprobe.

        Args:
            file_path: Path to video file

        Returns:
            ClipMetadata with duration, resolution, fps, codecs

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If ffprobe fails
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Clip not found: {file_path}")

        logger.info(f"Probing clip: {file_path}")

        try:
            # Run ffprobe in async context
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._probe_sync,
                file_path,
            )
            return result

        except Exception as e:
            logger.error(f"Failed to probe clip: {e}")
            raise RuntimeError(f"FFprobe failed for {file_path}: {e}")

    def _probe_sync(self, file_path: str) -> ClipMetadata:
        """Synchronous ffprobe operation."""
        try:
            probe = ffmpeg.probe(file_path)
        except ffmpeg.Error as e:
            logger.error(f"FFprobe error: {e}")
            raise

        # Extract video stream info
        video_stream = next(
            (s for s in probe["streams"] if s["codec_type"] == "video"),
            None,
        )
        if not video_stream:
            raise RuntimeError(f"No video stream found in {file_path}")

        audio_stream = next(
            (s for s in probe["streams"] if s["codec_type"] == "audio"),
            None,
        )

        duration = float(probe["format"].get("duration", 0))
        width = video_stream.get("width", 1920)
        height = video_stream.get("height", 1080)
        fps = 30.0  # default
        if "r_frame_rate" in video_stream:
            num, den = map(int, video_stream["r_frame_rate"].split("/"))
            fps = num / den
        elif "avg_frame_rate" in video_stream:
            num, den = map(int, video_stream["avg_frame_rate"].split("/"))
            fps = num / den

        codec_video = video_stream.get("codec_name", "unknown")
        codec_audio = audio_stream.get("codec_name") if audio_stream else None

        return ClipMetadata(
            duration=duration,
            width=width,
            height=height,
            fps=fps,
            codec_video=codec_video,
            codec_audio=codec_audio,
        )

    async def generate_thumbnail(
        self,
        file_path: str,
        output_path: str,
        timestamp: float = 1.0,
        size: Tuple[int, int] = (320, 180),
    ):
        """
        Extract a thumbnail frame from a video.

        Args:
            file_path: Input video path
            output_path: Output image path
            timestamp: Timestamp in seconds to extract
            size: Thumbnail size (width, height)

        Raises:
            RuntimeError: If thumbnail generation fails
        """
        logger.info(f"Generating thumbnail for {file_path} at {timestamp}s")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._generate_thumbnail_sync,
                file_path,
                output_path,
                timestamp,
                size,
            )
            logger.info(f"Thumbnail saved to {output_path}")

        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            raise RuntimeError(f"Thumbnail generation failed: {e}")

    def _generate_thumbnail_sync(self, file_path: str, output_path: str, timestamp: float, size: Tuple[int, int]):
        """Synchronous thumbnail generation."""
        try:
            (
                ffmpeg
                .input(file_path, ss=timestamp)
                .filter("scale", size[0], size[1])
                .output(output_path, vframes=1, format="image2")
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error: {e}")
            raise

    def build_render_command(
        self,
        steps: list[EditStep],
        clip_paths: Dict[str, str],
        output_path: str,
        output_settings: Dict,
    ) -> str:
        """
        Build an FFmpeg command from edit steps.

        This is simplified for demonstration. A real implementation would:
        - Handle complex filter graphs with multiple inputs
        - Manage intermediate file chains
        - Optimize for concurrent rendering
        - Support audio mixing, re-encoding, etc.

        Args:
            steps: List of edit steps
            clip_paths: Mapping of clip_id -> file path
            output_path: Output video path
            output_settings: Output codec, bitrate, resolution, etc.

        Returns:
            FFmpeg command string
        """
        logger.info(f"Building render command with {len(steps)} steps")

        # For simplicity, build a basic command structure
        # Real implementation would use filter_complex for advanced operations

        cmd_parts = [self.ffmpeg_path]

        # Input files
        for clip_id, clip_path in clip_paths.items():
            cmd_parts.extend(["-i", clip_path])

        # Build filter complex from operations
        filters = self._build_filter_complex(steps, clip_paths)
        if filters:
            cmd_parts.extend(["-filter_complex", filters])

        # Output settings
        width = output_settings.get("width", 1920)
        height = output_settings.get("height", 1080)
        fps = output_settings.get("frame_rate", 30)
        codec = output_settings.get("codec", "h264")
        bitrate = output_settings.get("bitrate_mbps", 8)
        format_ext = output_settings.get("format", "mp4")

        cmd_parts.extend(["-c:v", codec])
        cmd_parts.extend(["-b:v", f"{bitrate}M"])
        cmd_parts.extend(["-r", str(fps)])
        cmd_parts.extend(["-pix_fmt", "yuv420p"])

        # Audio settings
        cmd_parts.extend(["-c:a", "aac"])
        cmd_parts.extend(["-b:a", "128k"])

        # Output
        cmd_parts.extend(["-y", output_path])

        command = " ".join(cmd_parts)
        logger.debug(f"FFmpeg command: {command}")
        return command

    async def execute_render(
        self,
        command: str,
        job_id: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Execute an FFmpeg render command and track progress.

        Args:
            command: FFmpeg command to run
            job_id: Job ID for logging
            progress_callback: Optional callback for progress updates (0-100)

        Returns:
            Tuple of (success, error_message)
        """
        logger.info(f"Starting render for job {job_id}")

        try:
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                self._execute_render_sync,
                command,
                job_id,
                progress_callback,
            )
            return success, None

        except Exception as e:
            error_msg = f"Render failed: {e}"
            logger.error(f"Job {job_id} error: {error_msg}")
            return False, error_msg

    def _execute_render_sync(self, command: str, job_id: str, progress_callback: Optional[Callable]):
        """Synchronous render execution with progress tracking."""
        try:
            # Start FFmpeg process
            process = asyncio.run(self._run_ffmpeg_process(command, job_id, progress_callback))
            return process == 0

        except Exception as e:
            logger.error(f"Render process error: {e}")
            return False

    async def _run_ffmpeg_process(self, command: str, job_id: str, progress_callback: Optional[Callable]):
        """Run FFmpeg process with progress tracking."""
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Track progress from stderr
        stderr_task = asyncio.create_task(self._track_progress(process, job_id, progress_callback))
        await process.wait()
        await stderr_task

        return process.returncode

    async def _track_progress(self, process, job_id: str, progress_callback: Optional[Callable]):
        """Parse FFmpeg stderr for progress information."""
        if not progress_callback or not process.stderr:
            await process.stderr.read()
            return

        while True:
            line = await process.stderr.readline()
            if not line:
                break

            line_str = line.decode().strip()

            # Parse progress: time=HH:MM:SS.ms
            time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line_str)
            if time_match:
                hours, minutes, seconds = map(float, time_match.groups())
                elapsed = hours * 3600 + minutes * 60 + seconds
                # Progress would be elapsed / total_duration * 100
                # For now, estimate progress
                progress = min(int(elapsed * 10) % 100, 99)
                progress_callback(progress)

    def _build_filter_complex(self, steps: list[EditStep], clip_paths: Dict[str, str]) -> Optional[str]:
        """
        Build FFmpeg filter_complex string from edit steps.

        This is a simplified version. Real implementation would handle:
        - Multiple input sources
        - Complex routing (labels)
        - Concurrent filter operations
        """
        filters = []

        for step in steps:
            for operation in step.operations:
                filter_str = self._operation_to_ffmpeg_filter(operation)
                if filter_str:
                    filters.append(filter_str)

        if filters:
            return ",".join(filters)
        return None

    @staticmethod
    def _operation_to_ffmpeg_filter(operation: EditOperation) -> Optional[str]:
        """Convert an EditOperation to an FFmpeg filter string."""
        op_type = operation.type
        params = operation.params

        if op_type == EditOperationType.SPEED:
            multiplier = params.get("multiplier", 1.0)
            return f"setpts={1/multiplier}*PTS,atempo={multiplier}"

        elif op_type == EditOperationType.FADE:
            fade_type = "in" if params.get("type") == "in" else "out"
            duration = int(params.get("duration_seconds", 1.0) * 30)
            return f"fade=t={fade_type}:st=0:d={duration}"

        elif op_type == EditOperationType.COLOR_GRADE:
            filters = []
            if "exposure" in params:
                exp = params["exposure"]
                filters.append(f"eq=brightness={exp * 50}")
            if "saturation" in params:
                sat = params["saturation"] / 100.0
                filters.append(f"eq=saturation={sat}")
            if "contrast" in params:
                contrast = 1.0 + params["contrast"] / 100.0
                filters.append(f"eq=contrast={contrast}")
            return ",".join(filters) if filters else None

        elif op_type == EditOperationType.OVERLAY_TEXT:
            text = params.get("text", "")
            font_size = params.get("font_size", 60)
            font_color = params.get("font_color", "white")
            # Simplified; real implementation handles font path, positioning
            return f"drawtext=text='{text}':fontsize={font_size}:fontcolor={font_color}"

        elif op_type == EditOperationType.RESIZE:
            width = params.get("width", 1920)
            height = params.get("height", 1080)
            method = params.get("method", "scale")

            if method == "scale":
                return f"scale={width}:{height}"
            elif method == "crop":
                return f"scale={width}:{height}:force_original_aspect_ratio=decrease,crop={width}:{height}"
            elif method == "pad":
                return f"scale={width}:{height}:force_original_aspect_ratio=increase,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"

        elif op_type == EditOperationType.CROP:
            x = params.get("x", 0)
            y = params.get("y", 0)
            w = params.get("width", 1920)
            h = params.get("height", 1080)
            return f"crop={w}:{h}:{x}:{y}"

        elif op_type == EditOperationType.AUDIO_NORMALIZE:
            target_loudness = params.get("target_loudness", -14)
            return f"loudnorm=I={target_loudness}"

        # Other operations (trim, transition) handled differently
        return None
