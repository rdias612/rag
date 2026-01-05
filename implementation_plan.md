# Frontend Implementation Plan (Revised)

## Goal
Build a **sophisticated, premium-feel SPA** (Single Page Application) for the RAG system using **React, Vite, and TailwindCSS**. This will replace the previous simple template plan.

## User Review Required
- **Architecture**: A separate `frontend/` directory running React/Vite.
- **Tech Stack**:
  - **Framework**: React 18 + TypeScript + Vite
  - **Styling**: TailwindCSS + Framer Motion (for animations)
  - **Icons**: Lucide React
  - **Markdown**: `react-markdown` for rendering AI responses in rich text.

## Proposed Changes

### [NEW] Frontend Project (`/frontend`)
We will initialize a new Vite project in a `frontend` folder.
- **Commands**: `npm create vite@latest frontend -- --template react-ts`
- **Dependencies**: `tailwindcss`, `postcss`, `autoprefixer`, `framer-motion`, `lucide-react`, `clsx`, `tailwind-merge`.

#### Components
- **Layout**: Glassmorphism sidepanel, blurred backgrounds, smooth transitions.
- **ChatInterface**: Streaming text effect, syntax highlighting for code blocks.
- **UploadModal**: Drag and drop area with progress indicators.

### Backend (`src/app.py` & `src/api/routes.py`)
- [MODIFY] Ensure `CORS` is correctly configured to allow requests from `http://localhost:5173` (Vite dev server) and `http://localhost:3000`.
- [NO CHANGE] Routes remain the same, as they already provide JSON APIs.

## Verification Plan
1. **Setup**: Run `npm install` and `npm run dev` in `frontend/`.
2. **Backend**: Run `python src/app.py`.
3. **Integration Test**:
   - Open `http://localhost:5173`.
   - Send "Hello" to the chat -> Verify streaming response from Flask.
   - Upload file -> Verify `202 Accepted` from Flask.
4. **Build**: Run `npm run build` to ensure production readiness.
