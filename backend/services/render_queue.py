"""
Async render queue for managing concurrent video render jobs.
Handles job scheduling, progress tracking, and cancellation.
"""

import asyncio
import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional

from models.schemas import RenderJob, RenderStatus
from services.ffmpeg_engine import FFmpegEngine

logger = logging.getLogger(__name__)


# ============================================================================
# Render Queue
# ============================================================================

class RenderQueue:
    """Manages async render job queue with concurrent processing."""

    def __init__(
        self,
        max_concurrent: int = 3,
        ffmpeg_engine: Optional[FFmpegEngine] = None,
    ):
        """
        Initialize render queue.

        Args:
            max_concurrent: Maximum concurrent render jobs (default 3)
            ffmpeg_engine: FFmpegEngine instance for rendering
        """
        self.max_concurrent = max_concurrent
        self.ffmpeg_engine = ffmpeg_engine or FFmpegEngine()

        # Queue state
        self.queue: List[RenderJob] = []
        self.running: Dict[str, RenderJob] = {}
        self.completed: Dict[str, RenderJob] = {}
        self.failed: Dict[str, RenderJob] = {}

        # Processing state
        self.is_processing = False
        self.processing_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_progress: Optional[Callable[[str, int], None]] = None
        self.on_complete: Optional[Callable[[str, bool], None]] = None
        self.on_status_change: Optional[Callable[[str, RenderStatus], None]] = None

    async def enqueue(self, jobs: List[RenderJob]):
        """
        Add jobs to the render queue.

        Args:
            jobs: List of RenderJob objects to queue
        """
        logger.info(f"Enqueueing {len(jobs)} render jobs")

        for job in jobs:
            self.queue.append(job)

        logger.info(f"Queue now has {len(self.queue)} jobs")

    async def start_processing(self) -> None:
        """
        Start processing the render queue.

        Continuously processes queued jobs up to max_concurrent limit.
        Non-blocking — returns immediately.
        """
        if self.is_processing:
            logger.warning("Queue already processing")
            return

        logger.info("Starting render queue processing")
        self.is_processing = True

        self.processing_task = asyncio.create_task(self._process_queue())

    async def stop_processing(self) -> None:
        """Stop processing the queue and cancel running jobs."""
        logger.info("Stopping render queue")
        self.is_processing = False

        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass

        # Cancel all running jobs
        for job_id in list(self.running.keys()):
            await self.cancel(job_id)

    async def get_status(self, job_id: str) -> Optional[RenderJob]:
        """
        Get status of a render job.

        Args:
            job_id: Job ID

        Returns:
            RenderJob object or None if not found
        """
        # Check all states
        if job_id in self.running:
            return self.running[job_id]
        if job_id in self.completed:
            return self.completed[job_id]
        if job_id in self.failed:
            return self.failed[job_id]

        # Check queue
        for job in self.queue:
            if job.id == job_id:
                return job

        return None

    async def cancel(self, job_id: str) -> bool:
        """
        Cancel a queued or running job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if job was cancelled, False if not found
        """
        logger.info(f"Cancelling job {job_id}")

        # Remove from queue
        self.queue = [j for j in self.queue if j.id != job_id]

        # Mark running job as cancelled (actual process termination handled in worker)
        if job_id in self.running:
            job = self.running[job_id]
            job.status = RenderStatus.FAILED
            job.error = "Cancelled by user"
            del self.running[job_id]
            self.failed[job_id] = job
            self._notify_status_change(job_id, RenderStatus.FAILED)
            return True

        return False

    def get_overall_progress(self) -> Dict[str, any]:
        """
        Get overall queue progress.

        Returns:
            Dict with total, completed, failed, running counts and overall progress %
        """
        total = len(self.queue) + len(self.running) + len(self.completed) + len(self.failed)
        completed = len(self.completed)
        failed = len(self.failed)
        running = len(self.running)
        queued = len(self.queue)

        # Calculate average progress of running jobs
        avg_progress = 0
        if self.running:
            avg_progress = sum(j.progress for j in self.running.values()) / len(self.running)

        overall_progress = int((completed / total * 100) if total > 0 else 0)

        return {
            "total": total,
            "queued": queued,
            "running": running,
            "completed": completed,
            "failed": failed,
            "overall_progress": overall_progress,
            "avg_running_progress": avg_progress,
        }

    # ========================================================================
    # Private Methods
    # ========================================================================

    async def _process_queue(self) -> None:
        """
        Main queue processing loop.

        Continuously spawns workers up to max_concurrent limit.
        """
        workers = set()

        try:
            while self.is_processing:
                # Spawn workers for queued jobs
                while len(workers) < self.max_concurrent and self.queue:
                    job = self.queue.pop(0)
                    worker = asyncio.create_task(self._render_job(job))
                    workers.add(worker)
                    logger.info(f"Spawned worker for job {job.id}")

                # Wait for any worker to complete
                if workers:
                    done, workers = await asyncio.wait(workers, return_when=asyncio.FIRST_COMPLETED)

                    for task in done:
                        try:
                            await task
                        except Exception as e:
                            logger.error(f"Worker error: {e}")

                else:
                    # No workers running, queue is empty - wait before checking again
                    await asyncio.sleep(1)

            logger.info("Render queue processing stopped")

        except asyncio.CancelledError:
            logger.info("Render queue processing cancelled")
            # Clean up running workers
            for task in workers:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

    async def _render_job(self, job: RenderJob) -> None:
        """
        Render a single job.

        Args:
            job: RenderJob to render
        """
        logger.info(f"Starting render job {job.id} (output {job.output_index})")

        job.status = RenderStatus.RENDERING
        job.started_at = datetime.utcnow()
        self.running[job.id] = job
        self._notify_status_change(job.id, RenderStatus.RENDERING)

        try:
            # Simulate render (in real implementation, would call ffmpeg_engine)
            await self._simulate_render(job)

            # Mark as complete
            job.status = RenderStatus.DONE
            job.progress = 100
            job.completed_at = datetime.utcnow()
            self.completed[job.id] = job
            del self.running[job.id]

            logger.info(f"Job {job.id} completed successfully")
            self._notify_complete(job.id, True)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Job {job.id} failed: {error_msg}")

            job.status = RenderStatus.FAILED
            job.error = error_msg
            job.completed_at = datetime.utcnow()
            self.failed[job.id] = job
            del self.running[job.id]

            self._notify_complete(job.id, False)

    async def _simulate_render(self, job: RenderJob) -> None:
        """
        Simulate render progress (placeholder).

        In real implementation, would execute FFmpeg command.

        Args:
            job: Job being rendered
        """
        # Simulate 10-second render with progress updates
        for step in range(11):
            job.progress = step * 10
            self._notify_progress(job.id, job.progress)
            await asyncio.sleep(1)

    def _notify_progress(self, job_id: str, progress: int) -> None:
        """Notify progress callback."""
        if self.on_progress:
            try:
                self.on_progress(job_id, progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def _notify_complete(self, job_id: str, success: bool) -> None:
        """Notify completion callback."""
        if self.on_complete:
            try:
                self.on_complete(job_id, success)
            except Exception as e:
                logger.error(f"Completion callback error: {e}")

    def _notify_status_change(self, job_id: str, status: RenderStatus) -> None:
        """Notify status change callback."""
        if self.on_status_change:
            try:
                self.on_status_change(job_id, status)
            except Exception as e:
                logger.error(f"Status change callback error: {e}")


# ============================================================================
# Global Queue Instance
# ============================================================================

_queue_instance: Optional[RenderQueue] = None


def get_render_queue(max_concurrent: int = 3) -> RenderQueue:
    """
    Get or create the global render queue instance.

    Args:
        max_concurrent: Max concurrent jobs

    Returns:
        RenderQueue instance
    """
    global _queue_instance

    if _queue_instance is None:
        _queue_instance = RenderQueue(max_concurrent=max_concurrent)

    return _queue_instance
