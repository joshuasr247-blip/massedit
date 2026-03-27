# MassEdit Backend - Quick Start Guide

## 60-Second Setup

### 1. Install Dependencies
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Run
```bash
uvicorn main:app --reload
```

**Server**: http://localhost:8000
**Docs**: http://localhost:8000/docs
**Health**: http://localhost:8000/health

---

## First API Call (5 minutes)

### Step 1: Create Project
```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My First Video"}'
```

Copy the `id` from the response (e.g., `project-123`)

### Step 2: Create a Box
```bash
curl -X POST http://localhost:8000/api/projects/PROJECT_ID/boxes \
  -H "Content-Type: application/json" \
  -d '{"name": "B-Roll", "color": "#FF6B6B"}'
```

Copy the box `id`

### Step 3: Upload a Video
```bash
curl -X POST http://localhost:8000/api/projects/PROJECT_ID/boxes/BOX_ID/clips \
  -F "files=@your_video.mp4"
```

### Step 4: Interpret a Prompt
```bash
curl -X POST "http://localhost:8000/api/projects/PROJECT_ID/interpret?prompt=Create%20a%20fast-paced%20video%20with%20fade%20transitions"
```

You'll get back an EditPlan!

### Step 5: Start Rendering
```bash
curl -X POST http://localhost:8000/api/projects/PROJECT_ID/render \
  -H "Content-Type: application/json" \
  -d '{"use_matrix": true}'
```

### Step 6: Check Status
```bash
curl http://localhost:8000/api/projects/PROJECT_ID/render/status
```

---

## File Structure

```
backend/
├── main.py                 # 💻 Run this
├── requirements.txt        # 📦 Dependencies
├── .env.example           # ⚙️  Config template
├── README.md              # 📖 Full docs
├── models/
│   ├── schemas.py         # 📋 Data models
│   └── database.py        # 💾 Database
├── services/
│   ├── interpreter.py     # 🤖 Claude AI
│   ├── ffmpeg_engine.py   # 🎬 Video processing
│   ├── matrix_solver.py   # 🧮 Combinatorics
│   └── render_queue.py    # 📊 Job queue
└── routers/
    ├── projects.py        # 📁 Project endpoints
    ├── boxes.py          # 📦 Clip endpoints
    ├── interpret.py      # 🤖 AI endpoints
    └── render.py         # 🎬 Render endpoints
```

---

## Understanding the System

### Data Model
- **Project**: Container for everything
- **Box**: Named folder of video clips (e.g., "B-Roll", "Intro")
- **Clip**: Individual video file
- **EditPlan**: AI-generated instructions on how to edit
- **RenderJob**: A single output video being processed

### How It Works

```
1. You organize clips into Boxes
   ↓
2. You write a prompt: "Create a fast video with transitions"
   ↓
3. Claude AI reads the prompt + your clips
   ↓
4. Claude generates an EditPlan (trimming, color grading, etc.)
   ↓
5. You optionally define variations (5 B-Roll clips = 5 outputs)
   ↓
6. System renders all variations
   ↓
7. You get multiple video files
```

### Example Workflow

**Your prompt**: "Create 5 versions of a highlight reel using different B-Roll clips with the same music"

**System does**:
1. Reads 5 B-Roll clips and 1 music track
2. Generates EditPlan (color grade, normalize audio, add titles)
3. Creates variation matrix: "use each B-Roll clip"
4. Generates 5 render jobs (one per clip)
5. Renders all 5 in parallel (up to 3 concurrent)
6. Produces 5 video files

---

## Key Concepts

### Edit Operations
The system can apply these to your clips:
- **trim** - Cut to specific time
- **speed** - Slow down or speed up
- **fade** - Smooth fade in/out
- **color_grade** - Adjust colors/brightness
- **overlay_text** - Add text/captions
- **transition** - Dissolve/wipe between clips
- **audio_normalize** - Standardize volume
- **resize** - Scale to different resolutions
- **crop** - Focus on specific area

### Variation Modes
When creating multiple outputs:
- **fixed** - Use the same clip for all
- **each** - Create output for EVERY clip (cartesian product!)
- **random** - Randomly pick clips
- **sequence** - Cycle through clips

---

## Troubleshooting

### "FFmpeg not found"
```bash
# Install FFmpeg
# Ubuntu/Debian:
sudo apt-get install ffmpeg

# macOS:
brew install ffmpeg

# Windows: Download from https://ffmpeg.org/
```

### "ANTHROPIC_API_KEY not set"
```bash
# 1. Get key from https://console.anthropic.com/
# 2. Edit .env file
# 3. Restart server
```

### "Port 8000 already in use"
```bash
# Use different port
uvicorn main:app --reload --port 8001
```

### "Database locked"
```bash
# SQLite can't handle concurrent writes
# Delete massedit.db and restart
rm massedit.db
```

---

## Next Steps

1. **Read the README** for full API documentation
2. **Check INDEX.md** for detailed file descriptions
3. **Review interpreter.py** to see the AI system prompt
4. **Build a frontend** that calls these endpoints
5. **Deploy to production** (see README for guide)

---

## Useful Curl Commands

```bash
# Health check
curl http://localhost:8000/health

# Swagger docs (in browser)
open http://localhost:8000/docs

# List all projects
curl http://localhost:8000/api/projects

# Get specific project
curl http://localhost:8000/api/projects/{id}

# Monitor render in real-time
# (requires WebSocket client)
# ws://localhost:8000/ws/render/{job_id}
```

---

## Architecture at a Glance

```
┌──────────────────────────────────────┐
│   Frontend (React/Vue) - Soon        │
└──────────────────────────────────────┘
              ↓ HTTP/WebSocket
┌──────────────────────────────────────┐
│      FastAPI Backend (Port 8000)     │
│  ├─ Projects Router                  │
│  ├─ Boxes Router                     │
│  ├─ Interpret Router (Claude AI)     │
│  └─ Render Router                    │
└──────────────────────────────────────┘
    ↓             ↓              ↓
┌────────┐   ┌─────────┐   ┌──────────┐
│SQLite  │   │FFmpeg   │   │Anthropic │
│Database│   │Rendering│   │Claude API│
└────────┘   └─────────┘   └──────────┘
```

---

## Key Features

✅ AI-powered prompt interpretation
✅ Automatic video metadata extraction
✅ Thumbnail generation
✅ Concurrent render jobs
✅ Real-time progress via WebSocket
✅ Variation matrix for bulk outputs
✅ Full async/await support
✅ Type-safe with Pydantic
✅ Production-ready code quality
✅ Comprehensive documentation

---

**Ready to build? Start with `uvicorn main:app --reload`** 🚀
