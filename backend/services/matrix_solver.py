"""
Combinatorial matrix solver for generating render job variations.
Expands variation matrices into concrete clip assignments for each output.
"""

import logging
import random
from typing import List, Dict, Any

from models.schemas import Box, VariationMatrix, MatrixVariable, MatrixMode, RenderJob, RenderStatus
import uuid

logger = logging.getLogger(__name__)


# ============================================================================
# Matrix Solver
# ============================================================================

class MatrixSolver:
    """Solves variation matrices to generate render job combinations."""

    def __init__(self, max_output_count: int = 5000):
        """
        Initialize solver.

        Args:
            max_output_count: Maximum number of outputs to generate (safety limit)
        """
        self.max_output_count = max_output_count

    def solve(
        self,
        matrix: VariationMatrix,
        boxes: List[Box],
        project_id: str,
    ) -> List[RenderJob]:
        """
        Solve variation matrix into concrete render jobs.

        Each render job contains a specific assignment of clip_id for each box.

        Args:
            matrix: Variation matrix defining how to vary outputs
            boxes: List of boxes with available clips
            project_id: Project ID for the jobs

        Returns:
            List of RenderJob objects with clip assignments

        Raises:
            ValueError: If configuration would exceed max_output_count
        """
        logger.info(f"Solving matrix with {len(matrix.variables)} variables for project {project_id}")

        # Calculate expected output count
        expected_count = self.calculate_output_count(matrix, boxes)
        logger.info(f"Expected output count: {expected_count}")

        if expected_count > self.max_output_count:
            raise ValueError(
                f"Matrix configuration would generate {expected_count} outputs, "
                f"exceeding limit of {self.max_output_count}. Adjust variation settings."
            )

        # Generate assignments
        assignments = self._generate_assignments(matrix, boxes)
        logger.info(f"Generated {len(assignments)} assignments")

        # Create RenderJob objects
        jobs = []
        for idx, assignment in enumerate(assignments):
            job = RenderJob(
                id=str(uuid.uuid4()),
                project_id=project_id,
                output_index=idx,
                status=RenderStatus.QUEUED,
                progress=0,
                clip_assignments=assignment,
            )
            jobs.append(job)

        logger.info(f"Created {len(jobs)} render jobs")
        return jobs

    def calculate_output_count(self, matrix: VariationMatrix, boxes: List[Box]) -> int:
        """
        Calculate expected number of outputs from matrix configuration.

        Args:
            matrix: Variation matrix
            boxes: List of boxes

        Returns:
            Number of output combinations
        """
        if not matrix.variables:
            return 1

        box_map = {box.id: box for box in boxes}
        counts = {}

        for var in matrix.variables:
            box = box_map.get(var.box_id)
            if not box:
                logger.warning(f"Box {var.box_id} not found")
                continue

            if var.mode == MatrixMode.FIXED:
                # Fixed doesn't increase count
                counts[var.box_id] = 1

            elif var.mode == MatrixMode.EACH:
                # Each creates count per available clip
                counts[var.box_id] = len(box.clips) if box.clips else 1

            elif var.mode == MatrixMode.RANDOM:
                # Random: sample_size or all clips
                sample_size = var.params.get("sample_size", len(box.clips) if box.clips else 1)
                counts[var.box_id] = min(sample_size, len(box.clips) if box.clips else 1)

            elif var.mode == MatrixMode.SEQUENCE:
                # Sequence: number of sequence steps
                sequence = var.params.get("sequence", [])
                counts[var.box_id] = len(sequence) if sequence else 1

        # Cartesian product of all "each" modes
        total = 1
        for count in counts.values():
            total *= count

        return min(total, self.max_output_count)

    # ========================================================================
    # Private Methods
    # ========================================================================

    def _generate_assignments(
        self,
        matrix: VariationMatrix,
        boxes: List[Box],
    ) -> List[Dict[str, str]]:
        """
        Generate clip assignments for each output.

        Returns:
            List of assignment dicts: {box_id -> clip_id}
        """
        if not matrix.variables:
            # No matrix defined, use first clip from each box
            return [self._get_default_assignment(boxes)]

        box_map = {box.id: box for box in boxes}

        # Separate variables by mode
        fixed_vars = {}
        each_vars = []
        random_vars = []
        sequence_vars = {}

        for var in matrix.variables:
            if var.mode == MatrixMode.FIXED:
                fixed_vars[var.box_id] = var
            elif var.mode == MatrixMode.EACH:
                each_vars.append(var)
            elif var.mode == MatrixMode.RANDOM:
                random_vars.append(var)
            elif var.mode == MatrixMode.SEQUENCE:
                sequence_vars[var.box_id] = var

        # Generate combinations from "each" variables (cartesian product)
        each_combinations = self._generate_each_combinations(each_vars, box_map)

        if not each_combinations:
            each_combinations = [{}]

        # Expand with random/sequence variations
        assignments = []

        for base_assignment in each_combinations:
            # Add fixed assignments
            current = dict(base_assignment)
            for box_id, var in fixed_vars.items():
                box = box_map.get(box_id)
                if box and box.clips:
                    # Use first clip or specified clip
                    clip_id = var.params.get("clip_id")
                    if not clip_id and box.clips:
                        clip_id = box.clips[0].id
                    if clip_id:
                        current[box_id] = clip_id

            # Add sequence assignments
            for idx, (box_id, var) in enumerate(sequence_vars.items()):
                sequence = var.params.get("sequence", [])
                if sequence:
                    # Assign from sequence (will be distributed across outputs)
                    seq_idx = idx % len(sequence)
                    current[box_id] = sequence[seq_idx]

            assignments.append(current)

        # Apply random sampling if configured
        if random_vars:
            assignments = self._apply_random_variations(assignments, random_vars, box_map)

        return assignments

    def _generate_each_combinations(
        self,
        each_vars: List[MatrixVariable],
        box_map: Dict[str, Box],
    ) -> List[Dict[str, str]]:
        """
        Generate cartesian product of "each" mode variables.

        Args:
            each_vars: Variables with mode="each"
            box_map: Map of box_id -> Box

        Returns:
            List of partial assignments
        """
        if not each_vars:
            return []

        # Build list of clip options for each "each" variable
        clip_options = []
        for var in each_vars:
            box = box_map.get(var.box_id)
            if box and box.clips:
                clip_options.append([(var.box_id, clip.id) for clip in box.clips])
            else:
                # Box has no clips, skip
                logger.warning(f"No clips in box {var.box_id}")

        if not clip_options:
            return []

        # Generate cartesian product
        assignments = []

        def cartesian_product(options, current=None):
            if current is None:
                current = {}

            if not options:
                assignments.append(dict(current))
                return

            for box_id, clip_id in options[0]:
                current[box_id] = clip_id
                cartesian_product(options[1:], current)
                del current[box_id]

        cartesian_product(clip_options)
        return assignments

    def _apply_random_variations(
        self,
        assignments: List[Dict[str, str]],
        random_vars: List[MatrixVariable],
        box_map: Dict[str, Box],
    ) -> List[Dict[str, str]]:
        """
        Expand assignments with random clip sampling.

        Args:
            assignments: Base assignments
            random_vars: Variables with mode="random"
            box_map: Map of box_id -> Box

        Returns:
            Expanded list of assignments
        """
        result = []

        for assignment in assignments:
            current = dict(assignment)

            # For each random variable, generate multiple variations
            for var in random_vars:
                box = box_map.get(var.box_id)
                if not box or not box.clips:
                    continue

                sample_size = var.params.get("sample_size", len(box.clips))
                num_variations = var.params.get("num_variations", 1)

                # Generate num_variations with random sampling
                for _ in range(num_variations):
                    variation = dict(current)
                    clip_id = random.choice(box.clips).id
                    variation[var.box_id] = clip_id
                    result.append(variation)

                # Update current for next iteration
                if result:
                    current = dict(result[-1])

            if not result:
                result.append(current)

        return result

    @staticmethod
    def _get_default_assignment(boxes: List[Box]) -> Dict[str, str]:
        """
        Get default assignment using first clip from each box.

        Args:
            boxes: List of boxes

        Returns:
            Assignment dict
        """
        assignment = {}

        for box in boxes:
            if box.clips:
                assignment[box.id] = box.clips[0].id

        return assignment


# ============================================================================
# Example Usage
# ============================================================================

def example_matrix_setup():
    """
    Example: Create a variation matrix for 3 "B-Roll" variations
    while keeping "Intro" and "Music" fixed.

    Setup:
    - Box "intro": 1 clip (fixed)
    - Box "broll": 3 clips (each mode)
    - Box "music": 1 clip (fixed)

    Expected output: 3 render jobs (one per B-Roll clip combination)
    """
    pass
