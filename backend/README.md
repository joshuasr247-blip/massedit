# MassEdit Backend

A prompt-driven mass video editor powered by Claude AI and FFmpeg.

## Overview

MassEdit is a FastAPI-based backend that interprets natural language prompts into structured video edit plans and renders hundreds/thousands of video variations from a single prompt.

### Core Architecture

- **FastAPI** - REST API framework
- **Claude AI** - Natural language understanding for prompt interpretation
- **FFmpeg** - Video processing and rendering
- **SQLAlchemy + SQLite** - Project and render job persistence
- **Async/Await** - Concurrent render job processing

## Quick Start

### 1. Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
```

### 2. Configure

Edit `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-...  # Your Anthropic API key
MASSEDIT_STORAGE_PATH=./storage
MASSEDIT_MAX_CONCURRENT_RENDERS=3
MASSEDIT_MAX_OUTPUT_COUNT=5000
```

### 3. Run

```bash
# Development server with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production server
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Server will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs` (Swagger UI)

## API Endpoints

### Projects

**Create Project**
```
POST /api/projects
{
  "name": "Summer Highlights 2024"
}
```

**List Projects**
```
GET /api/projects
```

**Get Project**
```
GET /api/projects/{project_id}
```

**Update Project**
```
PUT /api/projects/{project_id}
{
  "name": "Updated Name",
  "prompt": "Create a video with..."
}
```

**Delete Project**
```
DELETE /api/projects/{project_id}
```

### Boxes & Clips

**Create Box**
```
POST /api/projects/{project_id}/boxes
{
  "name": "Intro",
  "color": "#FF6B6B"
}
```

**Update Box**
```
PUT /api/projects/{project_id}/boxes/{box_id}
{
  "name": "Intro Sequence",
  "color": "#FF6B6B"
}
```

**Delete Box**
```
DELETE /api/projects/{project_id}/boxes/{box_id}
```

**Upload Clips**
```
POST /api/projects/{project_id}/boxes/{box_id}/clips
(multipart/form-data with video files)
```

**Delete Clip**
```
DELETE /api/projects/{project_id}/boxes/{box_id}/clips/{clip_id}
```

### AI Interpretation

**Interpret Prompt**
```
POST /api/projects/{project_id}/interpret?prompt=...

Returns:
{
  "edit_plan": { ... },
  "suggestions": [ ... ]
}
```

**Refine Interpretation**
```
POST /api/projects/{project_id}/interpret/refine?refinement_prompt=...
```

**Get Current Plan**
```
GET /api/projects/{project_id}/plan
```

### Rendering

**Start Render**
```
POST /api/projects/{project_id}/render
{
  "use_matrix": true,
  "output_index_start": null,
  "output_index_end": null
}
```

**Get Render Status**
```
GET /api/projects/{project_id}/render/status

Returns:
{
  "total_jobs": 10,
  "completed": 3,
  "failed": 0,
  "rendering": 2,
  "overall_progress": 30,
  "jobs": [ ... ]
}
```

**Cancel Render**
```
POST /api/projects/{project_id}/render/cancel
```

**List Outputs**
```
GET /api/projects/{project_id}/render/outputs
```

**Generate Preview**
```
POST /api/projects/{project_id}/render/preview
```

### WebSocket

**Real-time Progress Updates**
```
ws://localhost:8000/ws/render/{job_id}

Receives:
{
  "type": "progress",
  "job_id": "job-123",
  "progress": 45
}

{
  "type": "complete",
  "job_id": "job-123",
  "success": true,
  "output_path": "/path/to/output.mp4"
}
```

## Data Model

### Project

```python
{
  "id": "uuid",
  "name": "Project Name",
  "boxes": [ ... ],           # Video clip containers
  "prompt": "Create a...",    # User's natural language prompt
  "edit_plan": { ... },       # AI-generated edit plan
  "matrix": { ... },          # Variation matrix for multi-output
  "render_jobs": [ ... ],     # Render job history
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:00:00"
}
```

### Box

```python
{
  "id": "uuid",
  "name": "Intro",
  "color": "#6B7280",
  "clips": [
    {
      "id": "uuid",
      "name": "intro_01.mp4",
      "file_path": "/storage/clips/...",
      "duration": 5.2,
      "width": 1920,
      "height": 1080,
      "fps": 30.0,
      "tags": ["intro"],
      "thumbnail_path": "/thumbnails/...",
      "file_size": 15728640
    }
  ],
  "created_at": "2024-01-01T12:00:00"
}
```

### EditPlan

```python
{
  "steps": [
    {
      "step_number": 1,
      "source_box_id": "box-1",
      "label": "Color Grade Intro",
      "description": "Apply warm color grade to intro clips",
      "operations": [
        {
          "type": "color_grade",
          "params": {
            "saturation": 120,
            "warmth": 15
          }
        }
      ]
    },
    ...
  ],
  "output_settings": {
    "width": 1920,
    "height": 1080,
    "frame_rate": 30,
    "codec": "h264",
    "bitrate_mbps": 8,
    "format": "mp4"
  },
  "estimated_duration": 45.0
}
```

### VariationMatrix

```python
{
  "variables": [
    {
      "key": "clip_source",
      "box_id": "box-1",
      "mode": "each",          # fixed, each, random, sequence
      "params": {}
    },
    {
      "key": "effects",
      "box_id": "box-2",
      "mode": "random",
      "params": {
        "sample_size": 5
      }
    }
  ]
}
```

## Edit Operations

Supported video edit operations:

| Operation | Parameters | Description |
|-----------|-----------|-------------|
| `trim` | `in_time`, `out_time` | Cut clip to specific points |
| `speed` | `multiplier`, `direction` | Change playback speed |
| `fade` | `type` (in/out), `duration_seconds` | Fade in/out |
| `color_grade` | `exposure`, `saturation`, `contrast`, etc. | Color corrections |
| `overlay_text` | `text`, `position`, `font_size`, `font_color` | Text overlay |
| `transition` | `type` (dissolve, wipe, etc.), `duration_seconds` | Transition effects |
| `audio_normalize` | `target_loudness`, `mode` | Audio level normalization |
| `resize` | `width`, `height`, `method` (scale/crop/pad) | Resolution scaling |
| `crop` | `x`, `y`, `width`, `height` | Crop to region |

## Variation Matrix Modes

### fixed
Use the same clip for all outputs
```python
"mode": "fixed",
"params": {"clip_id": "specific-clip-id"}
```

### each
Create output for every clip in the box (cartesian product)
```python
"mode": "each"
```

### random
Randomly sample clips from the box
```python
"mode": "random",
"params": {"sample_size": 5, "num_variations": 10}
```

### sequence
Cycle through clips in order
```python
"mode": "sequence",
"params": {"sequence": ["clip-1", "clip-2", "clip-3"]}
```

## Usage Example

### 1. Create Project
```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My Video Project"}'

# Response:
# {
#   "id": "proj-123",
#   "name": "My Video Project",
#   ...
# }
```

### 2. Create Box
```bash
curl -X POST http://localhost:8000/api/projects/proj-123/boxes \
  -H "Content-Type: application/json" \
  -d '{"name": "B-Roll", "color": "#FF6B6B"}'
```

### 3. Upload Clips
```bash
curl -X POST http://localhost:8000/api/projects/proj-123/boxes/box-123/clips \
  -F "files=@clip1.mp4" \
  -F "files=@clip2.mp4"
```

### 4. Interpret Prompt
```bash
curl -X POST "http://localhost:8000/api/projects/proj-123/interpret?prompt=Create%20a%20fast-paced%20video%20with%20transitions" \
  -H "Content-Type: application/json"

# Response:
# {
#   "edit_plan": { ... },
#   "suggestions": [
#     {
#       "text": "Consider 1080p output for faster rendering",
#       "type": "performance"
#     }
#   ]
# }
```

### 5. Start Render
```bash
curl -X POST http://localhost:8000/api/projects/proj-123/render \
  -H "Content-Type: application/json" \
  -d '{"use_matrix": true}'
```

### 6. Monitor Progress
```bash
# Via WebSocket
ws://localhost:8000/ws/render/job-123

# Or via REST
curl http://localhost:8000/api/projects/proj-123/render/status
```

## Architecture

### Service Layers

#### 1. **PromptInterpreter** (`services/interpreter.py`)
- Converts natural language prompts to structured edit plans
- Uses Claude Sonnet model with custom system prompt
- Implements tool-use pattern for structured output
- Generates FFmpeg filter suggestions

#### 2. **FFmpegEngine** (`services/ffmpeg_engine.py`)
- Probes video files for metadata (duration, resolution, fps, codecs)
- Generates thumbnail frames
- Builds and executes FFmpeg render commands
- Parses progress output for job tracking

#### 3. **MatrixSolver** (`services/matrix_solver.py`)
- Solves variation matrices into concrete clip assignments
- Supports cartesian products (each mode)
- Handles combinatorial explosion prevention
- Calculates expected output counts

#### 4. **RenderQueue** (`services/render_queue.py`)
- Async job queue with configurable concurrency
- Manages job lifecycle (queued → rendering → done/failed)
- Implements progress callbacks for WebSocket updates
- Supports job cancellation

### Database

SQLAlchemy models with SQLite (async via aiosqlite):
- `ProjectDB` - Project metadata, boxes, edit plans
- `RenderJobDB` - Render job state and progress

### API Routers

- `routers/projects.py` - Project CRUD
- `routers/boxes.py` - Box and clip management
- `routers/interpret.py` - AI prompt interpretation
- `routers/render.py` - Render job management

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional (defaults shown)
MASSEDIT_STORAGE_PATH=./storage
MASSEDIT_MAX_CONCURRENT_RENDERS=3
MASSEDIT_MAX_OUTPUT_COUNT=5000
```

### Storage Structure

```
storage/
├── clips/              # Uploaded video files
│   └── {clip_id}.mp4
├── thumbnails/         # Generated thumbnails
│   └── {clip_id}.jpg
└── outputs/            # Rendered videos
    └── {project_id}_{output_index}.mp4
```

## Performance Tuning

### Render Concurrency
Adjust `MASSEDIT_MAX_CONCURRENT_RENDERS` based on:
- CPU cores (typically 1-2 per core)
- Available RAM (FFmpeg typically needs 500MB-2GB per render)
- Disk I/O capacity

```bash
# For 8-core system with 32GB RAM
MASSEDIT_MAX_CONCURRENT_RENDERS=4
```

### Output Limits
Prevent runaway cartesian products:

```bash
# Maximum outputs per project
MASSEDIT_MAX_OUTPUT_COUNT=5000
```

### Quality vs Speed Trade-offs

In Claude prompts, suggest:
- Reduce resolution (1280x720 vs 1920x1080)
- Lower bitrate (5Mbps vs 12Mbps)
- Shorter duration clips
- Fewer effects/transitions

## Troubleshooting

### FFmpeg Not Found
```bash
# Install FFmpeg
# Ubuntu/Debian:
sudo apt-get install ffmpeg

# macOS:
brew install ffmpeg

# Windows:
# Download from https://ffmpeg.org/download.html
```

### API Key Errors
```bash
# Verify API key in .env
echo $ANTHROPIC_API_KEY

# Check Anthropic console: https://console.anthropic.com/
```

### Database Locked
```bash
# SQLite concurrent write issue
# Increase timeout or use PostgreSQL for production
```

### Render Failures
Check logs:
```bash
# View error details
curl http://localhost:8000/api/projects/{id}/render/status

# Check system logs
tail -f server.log
```

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment

- Use PostgreSQL instead of SQLite for concurrent access
- Configure CloudFront or similar for output file delivery
- Use object storage (S3) for clips and outputs
- Implement job queue (Redis, RabbitMQ) for scaling

### Monitoring

- Track render queue depth and job duration
- Monitor FFmpeg process CPU/memory usage
- Log Claude API calls and costs
- Alert on failed renders

## License

Part of the MassEdit project.
