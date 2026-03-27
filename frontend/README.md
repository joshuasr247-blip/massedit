# MassEdit Frontend

A React-based frontend for MassEdit — a prompt-driven mass video editor. Users organize video clips into "Boxes" and write natural language prompts that Claude AI interprets into structured video editing operations, producing hundreds or thousands of unique videos.

## Architecture

### Three-Panel Design
- **Left Sidebar (320px)**: Box and clip management panel
- **Center Panel**: Content view switcher (Prompt, Matrix, Outputs)
- **Top Bar**: Navigation, view controls, render button
- **Bottom Bar**: Status and statistics

### Views
1. **Prompt**: Write natural language editing instructions and see the interpreted edit plan
2. **Matrix**: Spreadsheet-like variation matrix defining which parameters vary per output
3. **Outputs**: Grid/list view of generated videos with playback and download controls

### Technology Stack
- **React 18**: UI framework
- **Zustand**: State management
- **Vite**: Build tool and dev server
- **Lucide React**: Icons
- **React Dropzone**: File uploads
- **Fetch API**: HTTP client (custom wrapper in `src/api/client.js`)
- **WebSocket**: Real-time render progress updates

## Project Structure

```
massedit/frontend/
├── index.html                 # HTML entry point
├── package.json              # Dependencies
├── vite.config.js            # Vite configuration
├── src/
│   ├── main.jsx              # React 18 entry point
│   ├── App.jsx               # Main layout component
│   ├── api/
│   │   └── client.js         # API client functions
│   ├── stores/
│   │   └── useStore.js       # Zustand global state
│   ├── styles/
│   │   └── tokens.js         # Design tokens (colors, spacing)
│   └── components/
│       ├── TopBar.jsx        # Navigation and view switcher
│       ├── BoxPanel.jsx      # Left sidebar with boxes and clips
│       ├── PromptPanel.jsx   # AI prompt interface
│       ├── MatrixPanel.jsx   # Variation matrix grid
│       ├── OutputGrid.jsx    # Generated outputs gallery
│       └── StatusBar.jsx     # Bottom status bar
└── public/                   # Static assets
```

## Getting Started

### Installation
```bash
npm install
```

### Development
```bash
npm run dev
```
Starts Vite dev server at http://localhost:5173 with proxy to backend API at http://localhost:8000

### Build
```bash
npm run build
```
Generates optimized production bundle in `dist/`

### Preview
```bash
npm run preview
```
Local preview of production build

## Design System

Colors use a dark theme for a professional, premium video editing tool aesthetic:
- **Background**: `#08080c` (darkest)
- **Surface**: `#101018`, `#181824`, `#1e1e2e` (elevation levels)
- **Border**: `#252538` (default), `#1a1a2e` (light)
- **Text**: `#e8e8f0` (primary), `#8585a0` (muted), `#4a4a65` (dim)
- **Accent**: `#7c6aef` (purple) with hover state `#8d7df7`
- **Status Colors**: Green `#34d399`, Orange `#fbbf24`, Red `#f87171`, Blue `#60a5fa`

All inline styles use the `C` token object from `src/styles/tokens.js`.

## API Integration

Backend runs at `http://localhost:8000`. Vite proxy routes `/api` and `/ws` to the backend.

### Key Endpoints
- `POST /projects` - Create project
- `GET /projects/{id}` - Get project details
- `POST /projects/{id}/boxes` - Create box
- `POST /projects/{id}/boxes/{boxId}/clips` - Upload clips
- `POST /projects/{id}/interpret` - Interpret prompt
- `POST /projects/{id}/render` - Start render job
- `WS /ws/{projectId}` - WebSocket for render progress

All requests are handled by `src/api/client.js` with proper error handling.

## State Management (Zustand)

Global state in `src/stores/useStore.js`:

### State
- `currentProject` - Active project object
- `boxes` - Array of box objects with clips
- `prompt` - Current prompt text
- `editPlan` - Interpreted edit steps
- `suggestions` - AI suggestions
- `matrix` - Variation matrix configuration
- `renderJobs` - Array of render job statuses
- `outputCount` - Computed total outputs
- `activeView` - Current view ('prompt', 'matrix', 'outputs')
- `isInterpreting`, `isRendering` - Loading states

### Actions
- `initProject(name)` - Create default project
- `loadProject(id)` - Load existing project
- `addBox(name)` - Create new box
- `uploadClipsToBox(boxId, files, onProgress)` - Upload video clips
- `setPrompt(text)` - Update prompt
- `interpret()` - Call AI interpretation
- `updateMatrix(varKey, boxId, mode, params)` - Modify matrix
- `startRender()` - Begin rendering
- `connectWS()` - Establish WebSocket connection

## Component Patterns

All components:
- Import and use `useStore` hook for state and actions
- Use inline `style={{}}` for all CSS (no CSS modules/styled-components)
- Implement proper hover states with `onMouseEnter`/`onMouseLeave`
- Use `useCallback` for event handlers
- Use `useMemo` for computed values
- Include helpful comments for major sections

## Responsive Design

Currently optimized for desktop (1200px+). Uses flexbox throughout with:
- 320px fixed left sidebar
- Flexible center content area
- Custom scrollbar styling
- Proper overflow handling

## Browser Support

Requires modern browser with:
- ES2020+ JavaScript
- CSS Grid/Flexbox
- WebSocket API
- FormData/Fetch API

## Development Notes

1. **Real API Integration**: This is a functional app that connects to the FastAPI backend. Replace demo data with real API responses.

2. **WebSocket**: Real-time render progress via `connectWebSocket()` in client.js. Update `renderJobs` state as progress arrives.

3. **Error Handling**: API client includes error handling. Components should catch and display errors gracefully.

4. **Performance**: Matrix calculations use `useMemo` to avoid recalculation. Large output counts (1000+) may need virtual scrolling.

5. **Accessibility**: Add ARIA labels and semantic HTML as needed for production.

## Future Enhancements

- Virtual scrolling for large output grids (1000+ videos)
- Keyboard shortcuts (Cmd+Z for undo, etc.)
- Clip preview/scrubbing with FFmpeg.wasm
- Real-time prompt suggestions as user types
- Export presets (YouTube, TikTok, Instagram specs)
- Project templates and saved variations
- Collaboration features
