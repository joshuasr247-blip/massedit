# MassEdit Backend - File Index

## Project Structure

```
backend/
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment configuration template
├── README.md                 # Complete documentation
├── INDEX.md                  # This file
│
├── models/
│   ├── __init__.py
│   ├── schemas.py            # Pydantic data models (20+ types)
│   └── database.py           # SQLAlchemy ORM setup
│
├── services/
│   ├── __init__.py
│   ├── interpreter.py        # Claude AI prompt interpretation
│   ├── ffmpeg_engine.py      # Video processing with FFmpeg
│   ├── matrix_solver.py      # Combinatorial variation engine
│   └── render_queue.py       # Async job queue management
│
├── routers/
│   ├── __init__.py
│   ├── projects.py           # Project CRUD endpoints
│   ├── boxes.py              # Box & clip management
│   ├── interpret.py          # AI interpretation endpoints
│   └── render.py             # Render job management
│
└── storage/                  # Created at runtime
    ├── clips/               # Uploaded video files
    ├── thumbnails/          # Generated thumbnails
    └── outputs/             # Rendered output videos
```

## File Descriptions

### Core Application

#### main.py (342 lines)
**Purpose**: FastAPI application entry point and configuration

**Key Components**:
- FastAPI app factory with lifespan management
- CORS middleware setup
- Database initialization
- Storage directory creation
- WebSocket endpoint for real-time progress
- Static file serving for outputs and thumbnails
- Health check and root endpoints
- ConnectionManager for WebSocket broadcasting

**Entry Point**: `uvicorn main:app --reload`

### Data Models

#### models/schemas.py (470 lines)
**Purpose**: Pydantic validation models for entire system

**Data Models**:
- `EditOperationType` - Enum of 9 edit operations
- `MatrixMode` - Enum for variation modes
- `RenderStatus` - Enum for job lifecycle
- `SuggestionType` - Enum for AI suggestions
- `Clip` - Video clip metadata
- `Box` - Container for clips
- `EditOperation` - Single edit action
- `EditStep` - Workflow step
- `EditPlan` - Complete edit workflow
- `MatrixVariable` - Variation matrix entry
- `VariationMatrix` - Multi-output configuration
- `RenderJob` - Render task with status
- `Project` - Complete project entity
- Request/Response models for all API endpoints

**Usage**: All FastAPI routes use these for request validation and response serialization

#### models/database.py (250 lines)
**Purpose**: SQLAlchemy async database setup and models

**Key Components**:
- `ProjectDB` - Database model for projects with JSON columns
- `RenderJobDB` - Database model for render jobs
- `Database` class - Async engine and session manager
- `get_database()` - Global instance accessor
- Automatic table creation on startup

**Database Schema**:
- projects: id, name, prompt, boxes (JSON), edit_plan (JSON), matrix (JSON), created_at, updated_at
- render_jobs: id, project_id (FK), output_index, status, progress, output_path, error, started_at, completed_at, clip_assignments (JSON), created_at

### Services

#### services/interpreter.py (500+ lines)
**Purpose**: Claude AI-powered prompt interpretation

**Key Components**:
- `SYSTEM_PROMPT` (800+ words) - Comprehensive AI instructions
- `CREATE_EDIT_PLAN_TOOL` - Tool schema for Claude
- `PromptInterpreter` class:
  - `interpret()` - Convert prompt to EditPlan
  - `generate_ffmpeg_commands()` - Plan to FFmpeg
  - `_build_box_context()` - Prepare metadata for Claude
  - `_extract_tool_result()` - Parse Claude response
  - `_operation_to_filter()` - Convert ops to FFmpeg filters

**AI Model**: Claude Sonnet 4 (claude-sonnet-4-20250514)

**Operations Supported**:
1. trim - Cut clips to specific points
2. speed - Change playback speed
3. fade - Fade in/out
4. color_grade - Color corrections
5. overlay_text - Text overlays
6. transition - Transition effects
7. audio_normalize - Audio levels
8. resize - Resolution scaling
9. crop - Crop regions

#### services/ffmpeg_engine.py (400+ lines)
**Purpose**: Video processing with FFmpeg and ffprobe

**Key Classes**:
- `ClipMetadata` - Video file metadata
- `FFmpegEngine` class:
  - `probe_clip()` - Extract video metadata
  - `generate_thumbnail()` - Extract frame as image
  - `build_render_command()` - Create FFmpeg command
  - `execute_render()` - Run FFmpeg with progress tracking
  - `_track_progress()` - Parse FFmpeg stderr

**Features**:
- Async probe and rendering
- Thumbnail generation with PIL
- FFmpeg filter graph building
- Progress tracking (0-100%)
- Support for all 9 operation types
- Error handling and logging

#### services/matrix_solver.py (350+ lines)
**Purpose**: Combinatorial variation matrix solving

**Key Classes**:
- `MatrixSolver` class:
  - `solve()` - Generate render jobs from matrix
  - `calculate_output_count()` - Preview output count
  - `_generate_assignments()` - Clip assignment combinations
  - `_generate_each_combinations()` - Cartesian product
  - `_apply_random_variations()` - Random sampling

**Variation Modes**:
- **fixed** - Same clip for all outputs
- **each** - Cartesian product (exponential growth!)
- **random** - Random sampling
- **sequence** - Sequential cycling

**Safety**:
- Combinatorial explosion prevention
- `max_output_count` limit (default 5000)
- Output count validation before solving

#### services/render_queue.py (300+ lines)
**Purpose**: Async render job queue with concurrent processing

**Key Classes**:
- `RenderQueue` class:
  - `enqueue()` - Add jobs to queue
  - `start_processing()` - Begin async processing
  - `get_status()` - Check job status
  - `cancel()` - Cancel job
  - `get_overall_progress()` - Aggregate stats
  - `_process_queue()` - Main processing loop
  - `_render_job()` - Single job worker

**Features**:
- Configurable max concurrent jobs (default 3)
- Job lifecycle management
- Progress callbacks for WebSocket
- Job cancellation support
- Status change notifications
- Overall progress tracking
- Error handling and recovery

### API Routers

#### routers/projects.py (150+ lines)
**Purpose**: Project CRUD operations

**Endpoints**:
- `POST /api/projects` - Create new project
- `GET /api/projects` - List all projects
- `GET /api/projects/{project_id}` - Get project details
- `PUT /api/projects/{project_id}` - Update project
- `DELETE /api/projects/{project_id}` - Delete project

**Features**:
- UUID project IDs
- Timestamp tracking
- Proper error responses

#### routers/boxes.py (250+ lines)
**Purpose**: Box and clip management

**Endpoints**:
- `POST /api/projects/{id}/boxes` - Create box
- `PUT /api/projects/{id}/boxes/{box_id}` - Update box
- `DELETE /api/projects/{id}/boxes/{box_id}` - Delete box
- `POST /api/projects/{id}/boxes/{box_id}/clips` - Upload clips
- `DELETE /api/projects/{id}/boxes/{box_id}/clips/{clip_id}` - Delete clip

**Features**:
- Multipart file upload support
- Automatic ffprobe metadata extraction
- Thumbnail generation on upload
- File size tracking
- Async file operations with aiofiles

#### routers/interpret.py (200+ lines)
**Purpose**: AI prompt interpretation

**Endpoints**:
- `POST /api/projects/{id}/interpret` - Interpret prompt
- `POST /api/projects/{id}/interpret/refine` - Refine interpretation
- `GET /api/projects/{id}/plan` - Get current plan

**Features**:
- Box metadata aggregation
- Claude API integration
- Plan persistence
- Suggestion generation
- Refinement support

#### routers/render.py (250+ lines)
**Purpose**: Render job management and execution

**Endpoints**:
- `POST /api/projects/{id}/render` - Start rendering
- `GET /api/projects/{id}/render/status` - Get job status
- `POST /api/projects/{id}/render/cancel` - Cancel jobs
- `GET /api/projects/{id}/render/outputs` - List outputs
- `POST /api/projects/{id}/render/preview` - Generate preview

**Features**:
- Matrix solving integration
- Queue management
- Job status tracking
- Progress aggregation
- Output file listing

### Configuration

#### requirements.txt
**Purpose**: Python package dependencies

**Key Packages**:
- fastapi 0.115.0 - Web framework
- uvicorn 0.30.0 - ASGI server
- anthropic 0.39.0 - Claude API
- sqlalchemy 2.0.35 - ORM
- aiosqlite 0.20.0 - Async SQLite
- ffmpeg-python 0.2.0 - FFmpeg wrapper
- pydantic 2.9.0 - Data validation
- websockets 13.0 - WebSocket support
- aiofiles 24.1.0 - Async file I/O
- Pillow 10.4.0 - Image processing
- python-dotenv 1.0.1 - Env config
- python-multipart 0.0.9 - Multipart form

#### .env.example
**Purpose**: Configuration template

**Variables**:
- `ANTHROPIC_API_KEY` - Claude API key (required)
- `MASSEDIT_STORAGE_PATH` - Storage directory path
- `MASSEDIT_MAX_CONCURRENT_RENDERS` - Concurrent job limit
- `MASSEDIT_MAX_OUTPUT_COUNT` - Maximum outputs per project

#### README.md
**Purpose**: Comprehensive documentation

**Sections**:
- Quick start guide
- API endpoint reference
- Data model documentation
- Architecture overview
- Usage examples
- Production deployment
- Troubleshooting

## Code Statistics

| Component | Lines | Purpose |
|-----------|-------|---------|
| main.py | 342 | App initialization |
| models/schemas.py | 470 | Data models |
| models/database.py | 250 | ORM setup |
| services/interpreter.py | 500+ | AI interpretation |
| services/ffmpeg_engine.py | 400+ | Video processing |
| services/matrix_solver.py | 350+ | Combinatorics |
| services/render_queue.py | 300+ | Job queue |
| routers/projects.py | 150+ | Projects API |
| routers/boxes.py | 250+ | Boxes API |
| routers/interpret.py | 200+ | Interpret API |
| routers/render.py | 250+ | Render API |
| **TOTAL** | **3,500+** | **Production code** |

## Data Flow

```
Request → Router → Service → Database/API → Response
         ↓
    Validation
         ↓
    Business Logic
         ↓
    Persistence
```

## Typical Workflow

### 1. Create Project
```
POST /api/projects → creates ProjectDB → returns Project
```

### 2. Add Content
```
POST /api/projects/{id}/boxes → creates box in project
POST /api/projects/{id}/boxes/{id}/clips → uploads videos
  → ffprobe extracts metadata
  → thumbnail generated
  → clip stored
```

### 3. Interpret Prompt
```
POST /api/projects/{id}/interpret → builds box metadata
  → calls Claude with system prompt
  → Claude uses create_edit_plan tool
  → validates EditPlan with Pydantic
  → saves to ProjectDB
  → returns EditPlan + suggestions
```

### 4. Configure Variations
```
PUT /api/projects/{id} → updates VariationMatrix
  Matrix defines how clips vary across outputs
```

### 5. Render
```
POST /api/projects/{id}/render → matrix_solver.solve()
  → generates RenderJobs
  → creates RenderJobDB entries
  → enqueues jobs
  → starts RenderQueue workers
```

### 6. Monitor Progress
```
GET /api/projects/{id}/render/status → aggregates all jobs
WS /ws/render/{job_id} → receives progress updates
```

## Key Design Decisions

1. **Async Throughout** - All I/O is async for scalability
2. **Type Hints** - 100% coverage for IDE support and validation
3. **Pydantic Validation** - Request/response validation at boundaries
4. **Service Layer** - Business logic separate from routing
5. **Tool Use** - Claude tool calls for structured output
6. **SQLite** - Development-ready, PostgreSQL for production
7. **WebSocket** - Real-time progress without polling
8. **JSON Columns** - Store complex structures in SQLite

## Security Considerations

- CORS limited to localhost (dev) - configure for production
- API key validation on Claude calls
- Input validation via Pydantic
- No SQL injection (SQLAlchemy ORM)
- File upload validation and size limits
- Error messages don't expose internals
- Async prevents blocking attacks

## Performance Characteristics

- **Project Creation**: O(1) - Single DB insert
- **Box/Clip Upload**: O(n) - Per clip: ffprobe + thumbnail
- **Prompt Interpretation**: O(1) - Single Claude call (~2-5s)
- **Matrix Solving**: O(k^n) - k clips, n boxes in "each" mode
- **Rendering**: O(m*d) - m clips, d duration per job
- **Status Checking**: O(1) - Direct DB query

## Testing Recommendations

1. **Unit Tests**
   - Pydantic model validation
   - FFmpeg filter generation
   - Matrix solving combinatorics
   - Edit operation handling

2. **Integration Tests**
   - API endpoint round-trips
   - Database persistence
   - File upload/download
   - Queue processing

3. **Load Tests**
   - Concurrent renders
   - Large project sizes
   - High-frequency status polling
   - WebSocket connection limits

4. **E2E Tests**
   - Full workflow from prompt to video
   - Error recovery
   - Cancellation handling

---

**Ready for**: Development, deployment, and scaling
